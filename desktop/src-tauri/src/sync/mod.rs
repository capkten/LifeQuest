pub mod diff;
pub mod manifest;
pub mod merge;
pub mod queue;

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::mpsc::{self, Sender};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use notify::{RecursiveMode, Watcher};
use reqwest::header::{HeaderMap, HeaderValue, AUTHORIZATION};
use serde::{Deserialize, Serialize};
use thiserror::Error;
use uuid::Uuid;

use crate::fs::{self, FsError, LocalManifest, ManifestEntry};
use diff::{plan_diff, DiffAction, DiffItem};
use manifest::{RemoteContentResponse, RemoteManifest, RemoteManifestItem};

#[derive(Debug, Error)]
pub enum SyncError {
    #[error("SYNC_HTTP: {0}")]
    Http(String),
    #[error("SYNC_FORMAT: {0}")]
    Format(String),
    #[error("SYNC_FS: {0}")]
    Fs(String),
    #[error("SYNC_QUEUE: {0}")]
    Queue(String),
}

impl From<FsError> for SyncError {
    fn from(error: FsError) -> Self {
        Self::Fs(error.to_string())
    }
}

#[derive(Clone)]
pub struct SyncClient {
    endpoint: String,
    token: String,
    http: reqwest::Client,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ApplyResult {
    client_operation_id: String,
    status: String,
    node: Option<RemoteManifestItem>,
    error_code: Option<String>,
    message: Option<String>,
    conflict_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ApplyResponse {
    notebook_id: String,
    revision: i64,
    results: Vec<ApplyResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ResolveResponse {
    notebook_id: String,
    revision: i64,
    results: Vec<ApplyResult>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct RemoteConflict {
    id: String,
    local_path: String,
    remote_revision: Option<i64>,
    status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct ConflictListResponse {
    conflicts: Vec<RemoteConflict>,
}

impl SyncClient {
    pub fn new(endpoint: impl Into<String>, token: impl Into<String>) -> Self {
        Self {
            endpoint: endpoint
                .into()
                .trim_end_matches('/')
                .trim_end_matches("/api")
                .to_string(),
            token: token.into(),
            http: reqwest::Client::new(),
        }
    }

    fn url(&self, path: &str) -> String {
        format!("{}/api/notes{}", self.endpoint, path)
    }

    fn headers(&self) -> Result<HeaderMap, SyncError> {
        let mut headers = HeaderMap::new();
        let value = HeaderValue::from_str(&format!("Bearer {}", self.token))
            .map_err(|error| SyncError::Http(error.to_string()))?;
        headers.insert(AUTHORIZATION, value);
        Ok(headers)
    }

    async fn decode<T: for<'de> Deserialize<'de>>(
        response: reqwest::Response,
    ) -> Result<T, SyncError> {
        let status = response.status();
        if !status.is_success() {
            let body = response.text().await.unwrap_or_default();
            return Err(SyncError::Http(format!("{} {}", status.as_u16(), body)));
        }
        response
            .json()
            .await
            .map_err(|error| SyncError::Format(error.to_string()))
    }

    pub async fn manifest(&self, notebook_id: &str) -> Result<RemoteManifest, SyncError> {
        let response = self
            .http
            .get(self.url(&format!("/notebooks/{notebook_id}/sync/manifest")))
            .headers(self.headers()?)
            .send()
            .await
            .map_err(|error| SyncError::Http(error.to_string()))?;
        Self::decode(response).await
    }

    pub async fn content(
        &self,
        notebook_id: &str,
        node_ids: &[String],
    ) -> Result<HashMap<String, String>, SyncError> {
        let response = self
            .http
            .post(self.url(&format!("/notebooks/{notebook_id}/sync/content")))
            .headers(self.headers()?)
            .json(&serde_json::json!({"node_ids": node_ids}))
            .send()
            .await
            .map_err(|error| SyncError::Http(error.to_string()))?;
        Ok(Self::decode::<RemoteContentResponse>(response)
            .await?
            .contents)
    }

    async fn apply(
        &self,
        notebook_id: &str,
        operation: serde_json::Value,
    ) -> Result<ApplyResponse, SyncError> {
        let response = self
            .http
            .post(self.url(&format!("/notebooks/{notebook_id}/sync/apply")))
            .headers(self.headers()?)
            .json(&serde_json::json!({"operations": [operation]}))
            .send()
            .await
            .map_err(|error| SyncError::Http(error.to_string()))?;
        Self::decode(response).await
    }

    async fn conflicts(&self, notebook_id: &str) -> Result<Vec<RemoteConflict>, SyncError> {
        let response = self
            .http
            .get(self.url(&format!("/notebooks/{notebook_id}/sync/conflicts")))
            .headers(self.headers()?)
            .send()
            .await
            .map_err(|error| SyncError::Http(error.to_string()))?;
        Ok(Self::decode::<ConflictListResponse>(response)
            .await?
            .conflicts)
    }

    async fn resolve_conflict(
        &self,
        notebook_id: &str,
        conflict_id: &str,
        resolution: &str,
        content: Option<&str>,
        base_revision: Option<i64>,
    ) -> Result<ResolveResponse, SyncError> {
        let response = self
            .http
            .post(self.url(&format!(
                "/notebooks/{notebook_id}/sync/conflicts/{conflict_id}/resolve"
            )))
            .headers(self.headers()?)
            .json(&serde_json::json!({
                "resolution": resolution,
                "content": content,
                "base_revision": base_revision
            }))
            .send()
            .await
            .map_err(|error| SyncError::Http(error.to_string()))?;
        Self::decode(response).await
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SyncBinding {
    pub notebook_id: String,
    pub folder: String,
    pub device_id: String,
    pub cursor: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SyncPreview {
    pub notebook_id: String,
    pub folder: String,
    pub revision: i64,
    pub items: Vec<diff::DiffItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SyncStatus {
    pub state: String,
    pub notebook_id: String,
    pub folder: String,
    pub cursor: i64,
    pub pending_operations: usize,
    pub conflicts: usize,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SyncReport {
    pub status: SyncStatus,
    pub applied: usize,
    pub downloaded: usize,
    pub uploaded: usize,
    pub conflicts: Vec<diff::DiffItem>,
}

fn read_local_manifest(
    folder: &Path,
    notebook_id: &str,
    device_id: &str,
) -> Result<LocalManifest, SyncError> {
    match fs::read_manifest(folder) {
        Ok(manifest) if manifest.notebook_id == notebook_id => Ok(manifest),
        Ok(_) => Ok(LocalManifest {
            schema_version: 1,
            notebook_id: notebook_id.to_string(),
            device_id: device_id.to_string(),
            entries: vec![],
        }),
        Err(FsError::ManifestIo(_)) if !fs::manifest_path(folder).exists() => Ok(LocalManifest {
            schema_version: 1,
            notebook_id: notebook_id.to_string(),
            device_id: device_id.to_string(),
            entries: vec![],
        }),
        Err(error) => Err(error.into()),
    }
}

fn relative_parent(path: &str) -> Option<String> {
    path.rsplit_once('/')
        .map(|(parent, _)| parent.to_string())
        .filter(|parent| !parent.is_empty())
}

fn remote_by_path<'a>(
    remote: &'a [RemoteManifestItem],
    relative: &str,
) -> Option<&'a RemoteManifestItem> {
    remote
        .iter()
        .find(|item| item.path.trim_start_matches('/') == relative)
}

fn synced_by_path<'a>(synced: &'a [ManifestEntry], relative: &str) -> Option<&'a ManifestEntry> {
    synced.iter().find(|item| item.relative_path == relative)
}

impl SyncEngine {
    fn load_queue(&self) -> Result<queue::DurableQueue, SyncError> {
        let Some(app_data_dir) = &self.app_data_dir else {
            return Ok(queue::DurableQueue::default());
        };
        queue::load_queue_or_default(app_data_dir)
            .map_err(|error| SyncError::Queue(error.to_string()))
    }

    fn save_queue(&self, value: &queue::DurableQueue) -> Result<(), SyncError> {
        let Some(app_data_dir) = &self.app_data_dir else {
            return Ok(());
        };
        queue::save_queue(app_data_dir, value).map_err(|error| SyncError::Queue(error.to_string()))
    }

    fn pending_operations(&self, notebook_id: &str) -> Result<usize, SyncError> {
        Ok(self.load_queue()?.pending_for_notebook(notebook_id))
    }

    fn now_timestamp() -> i64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|duration| duration.as_secs() as i64)
            .unwrap_or_default()
    }

    async fn apply_operation(
        &self,
        binding: &SyncBinding,
        operation: serde_json::Value,
    ) -> Result<ApplyResponse, SyncError> {
        let operation_id = operation
            .get("client_operation_id")
            .and_then(serde_json::Value::as_str)
            .ok_or_else(|| SyncError::Format("operation id missing".to_string()))?
            .to_string();

        if self.app_data_dir.is_some() {
            let mut pending = self.load_queue()?;
            pending.enqueue_for_notebook(
                &binding.notebook_id,
                operation_id.clone(),
                operation.clone(),
            );
            self.save_queue(&pending)?;
        }

        match self.client.apply(&binding.notebook_id, operation).await {
            Ok(response) => {
                if self.app_data_dir.is_some() {
                    let mut pending = self.load_queue()?;
                    pending.acknowledge(&operation_id);
                    self.save_queue(&pending)?;
                }
                Ok(response)
            }
            Err(error) => {
                if self.app_data_dir.is_some() {
                    let mut pending = self.load_queue()?;
                    pending.failed(&operation_id, Self::now_timestamp());
                    self.save_queue(&pending)?;
                }
                Err(error)
            }
        }
    }

    async fn flush_pending(&self, binding: &SyncBinding) -> Result<usize, SyncError> {
        let mut flushed = 0;
        loop {
            let pending_operation = self
                .load_queue()?
                .ready_for_notebook(&binding.notebook_id, Self::now_timestamp())
                .cloned();
            let Some(pending_operation) = pending_operation else {
                return Ok(flushed);
            };

            match self
                .client
                .apply(&binding.notebook_id, pending_operation.payload)
                .await
            {
                Ok(_) => {
                    let mut pending = self.load_queue()?;
                    pending.acknowledge(&pending_operation.operation_id);
                    self.save_queue(&pending)?;
                    flushed += 1;
                }
                Err(error) => {
                    let mut pending = self.load_queue()?;
                    pending.failed(&pending_operation.operation_id, Self::now_timestamp());
                    self.save_queue(&pending)?;
                    return Err(error);
                }
            }
        }
    }

    pub async fn preview(&self, binding: &SyncBinding) -> Result<SyncPreview, SyncError> {
        let folder = Path::new(&binding.folder);
        fs::validate_root(folder)?;
        let local = fs::scan_markdown(folder)?;
        let local_manifest = read_local_manifest(folder, &binding.notebook_id, &binding.device_id)?;
        let remote = self.client.manifest(&binding.notebook_id).await?;
        Ok(SyncPreview {
            notebook_id: binding.notebook_id.clone(),
            folder: binding.folder.clone(),
            revision: remote.revision,
            items: plan_diff(&local, &remote.items, &local_manifest.entries),
        })
    }

    pub async fn sync_now(&self, binding: &SyncBinding) -> Result<SyncReport, SyncError> {
        let folder = Path::new(&binding.folder);
        fs::validate_root(folder)?;
        let local_manifest = read_local_manifest(folder, &binding.notebook_id, &binding.device_id)?;
        let mut local = fs::scan_markdown(folder)?;
        let mut remote = self.client.manifest(&binding.notebook_id).await?;
        let flushed = self.flush_pending(binding).await?;
        if flushed > 0 {
            remote = self.client.manifest(&binding.notebook_id).await?;
        }
        let mut remote_note_ids: Vec<String> = remote
            .items
            .iter()
            .filter(|item| item.node_type == "note")
            .map(|item| item.node_id.clone())
            .collect();
        remote_note_ids.sort();
        remote_note_ids.dedup();
        let remote_content = self
            .client
            .content(&binding.notebook_id, &remote_note_ids)
            .await?;
        let diff_items = plan_diff(&local, &remote.items, &local_manifest.entries);
        let mut downloaded = 0;
        let mut uploaded = 0;
        let mut applied = 0;
        let mut conflicts = Vec::new();

        for item in diff_items
            .iter()
            .filter(|item| item.action == DiffAction::Download)
        {
            if item.node_type == "folder" {
                fs::ensure_folder(folder, &item.relative_path)?;
            } else if let Some(remote_node) = remote_by_path(&remote.items, &item.relative_path) {
                if let Some(content) = remote_content.get(&remote_node.node_id) {
                    fs::write_markdown(folder, &item.relative_path, content)?;
                    downloaded += 1;
                }
            }
        }

        local = fs::scan_markdown(folder)?;
        let mut created_ids: HashMap<String, String> = HashMap::new();
        let mut upload_items: Vec<DiffItem> = diff_items
            .iter()
            .filter(|item| item.action == DiffAction::Upload)
            .cloned()
            .collect();
        upload_items.sort_by_key(|item| (item.node_type != "folder", item.relative_path.clone()));
        for item in upload_items {
            let local_entry = local
                .iter()
                .find(|entry| entry.relative_path == item.relative_path)
                .ok_or_else(|| {
                    SyncError::Format("local snapshot changed during sync".to_string())
                })?;
            let parent_id = relative_parent(&item.relative_path).and_then(|parent| {
                created_ids.get(&parent).cloned().or_else(|| {
                    remote_by_path(&remote.items, &parent).map(|node| node.node_id.clone())
                })
            });
            let operation_id = format!("{}:{}", binding.device_id, Uuid::new_v4());
            let operation = if item.node_type == "folder" {
                serde_json::json!({
                    "client_operation_id": operation_id,
                    "kind": "create_folder",
                    "parent_id": parent_id,
                    "name": item.relative_path.rsplit('/').next().unwrap_or_default(),
                    "path": format!("/{}", item.relative_path),
                    "local_path": item.relative_path
                })
            } else if let Some(existing) =
                synced_by_path(&local_manifest.entries, &item.relative_path)
            {
                let remote_node = remote_by_path(&remote.items, &item.relative_path)
                    .ok_or_else(|| SyncError::Format("remote node missing".to_string()))?;
                serde_json::json!({
                    "client_operation_id": operation_id,
                    "kind": "update_note",
                    "node_id": existing.node_id,
                    "path": format!("/{}", item.relative_path),
                    "content": local_entry.content.clone().unwrap_or_default(),
                    "base_revision": existing.remote_revision.or(remote_node.content_revision),
                    "base_hash": existing.content_hash.clone(),
                    "local_path": item.relative_path
                })
            } else {
                serde_json::json!({
                    "client_operation_id": operation_id,
                    "kind": "create_note",
                    "parent_id": parent_id,
                    "name": item.relative_path.rsplit('/').next().unwrap_or_default(),
                    "path": format!("/{}", item.relative_path),
                    "content": local_entry.content.clone().unwrap_or_default(),
                    "local_path": item.relative_path
                })
            };
            let response = self.apply_operation(binding, operation).await?;
            if let Some(result) = response.results.into_iter().next() {
                if result.status == "applied" || result.status == "already_applied" {
                    applied += 1;
                    uploaded += 1;
                    if let Some(node) = result.node {
                        created_ids.insert(item.relative_path.clone(), node.node_id);
                    }
                } else {
                    let mut conflict = item.clone();
                    conflict.action = DiffAction::Conflict;
                    conflict.reason = result
                        .error_code
                        .or(result.message)
                        .unwrap_or_else(|| "remote rejected operation".to_string());
                    conflicts.push(conflict);
                }
            }
        }

        for item in diff_items
            .iter()
            .filter(|item| item.action == DiffAction::Conflict)
        {
            if item.node_type != "note" {
                conflicts.push(item.clone());
                continue;
            }
            let local_entry = local
                .iter()
                .find(|entry| entry.relative_path == item.relative_path);
            let remote_node = remote_by_path(&remote.items, &item.relative_path);
            let synced_entry = synced_by_path(&local_manifest.entries, &item.relative_path);
            let merged = match (local_entry, remote_node, synced_entry) {
                (Some(local_entry), Some(remote_node), Some(synced_entry)) => {
                    let local_content = local_entry.content.as_deref().unwrap_or_default();
                    let remote_text = remote_content
                        .get(&remote_node.node_id)
                        .map(String::as_str)
                        .unwrap_or_default();
                    merge::three_way_merge(
                        synced_entry
                            .last_synced_content
                            .as_deref()
                            .unwrap_or_default(),
                        local_content,
                        remote_text,
                    )
                    .map_merged()
                }
                _ => None,
            };
            if let Some(content) = merged {
                if let Some(remote_node) = remote_node {
                    let operation = serde_json::json!({
                        "client_operation_id": format!("{}:{}", binding.device_id, Uuid::new_v4()),
                        "kind": "update_note",
                        "node_id": remote_node.node_id,
                        "path": remote_node.path,
                        "content": content.clone(),
                        "base_revision": remote_node.content_revision,
                        "base_hash": remote_node.content_hash.clone(),
                        "local_path": item.relative_path
                    });
                    let response = self.apply_operation(binding, operation).await?;
                    if response.results.first().is_some_and(|result| {
                        result.status == "applied" || result.status == "already_applied"
                    }) {
                        fs::write_markdown(folder, &item.relative_path, &content)?;
                        applied += 1;
                        uploaded += 1;
                        continue;
                    }
                }
            }
            fs::write_conflict_artifact(
                folder,
                &item.relative_path,
                local_entry
                    .and_then(|entry| entry.content.as_deref())
                    .unwrap_or_default(),
            )?;
            conflicts.push(item.clone());
        }

        remote = self.client.manifest(&binding.notebook_id).await?;
        let mut final_ids: Vec<String> = remote
            .items
            .iter()
            .filter(|item| item.node_type == "note")
            .map(|item| item.node_id.clone())
            .collect();
        final_ids.sort();
        final_ids.dedup();
        let final_content = self
            .client
            .content(&binding.notebook_id, &final_ids)
            .await?;
        let entries = remote
            .items
            .iter()
            .map(|item| ManifestEntry {
                node_id: item.node_id.clone(),
                relative_path: item.path.trim_start_matches('/').to_string(),
                node_type: item.node_type.clone(),
                content_hash: item.content_hash.clone(),
                remote_revision: item.content_revision,
                last_synced_content: if item.node_type == "note" {
                    final_content.get(&item.node_id).cloned()
                } else {
                    None
                },
                updated_at: item.updated_at.clone(),
            })
            .collect();
        fs::write_manifest(
            folder,
            &LocalManifest {
                schema_version: 1,
                notebook_id: binding.notebook_id.clone(),
                device_id: binding.device_id.clone(),
                entries,
            },
        )?;
        let status = SyncStatus {
            state: if conflicts.is_empty() {
                "synced"
            } else {
                "conflict"
            }
            .to_string(),
            notebook_id: binding.notebook_id.clone(),
            folder: binding.folder.clone(),
            cursor: remote.revision,
            pending_operations: self.pending_operations(&binding.notebook_id)?,
            conflicts: conflicts.len(),
            error: None,
        };
        Ok(SyncReport {
            status,
            applied,
            downloaded,
            uploaded,
            conflicts,
        })
    }
}

pub struct SyncEngine {
    client: SyncClient,
    app_data_dir: Option<PathBuf>,
}

pub struct WatchHandle {
    stop: Option<Sender<()>>,
}

impl WatchHandle {
    pub fn stop(mut self) {
        if let Some(sender) = self.stop.take() {
            let _ = sender.send(());
        }
    }
}

fn should_sync_event(root: &Path, path: &Path) -> bool {
    let Ok(relative) = path.strip_prefix(root) else {
        return true;
    };
    if relative.as_os_str().is_empty() {
        return true;
    }
    !relative.components().any(|component| {
        let name = component.as_os_str().to_string_lossy();
        name.starts_with('.')
    })
}

pub fn watch_folder<F>(folder: PathBuf, mut on_change: F) -> Result<WatchHandle, SyncError>
where
    F: FnMut() + Send + 'static,
{
    let root = fs::validate_root(&folder)?;
    let (event_sender, event_receiver) = mpsc::channel();
    let event_root = root.clone();
    let mut watcher = notify::recommended_watcher(move |event: notify::Result<notify::Event>| {
        if let Ok(event) = event {
            if event.paths.is_empty()
                || event
                    .paths
                    .iter()
                    .any(|path| should_sync_event(&event_root, path))
            {
                let _ = event_sender.send(());
            }
        }
    })
    .map_err(|error| SyncError::Fs(error.to_string()))?;
    watcher
        .watch(&root, RecursiveMode::Recursive)
        .map_err(|error| SyncError::Fs(error.to_string()))?;
    let (stop_sender, stop_receiver) = mpsc::channel();
    thread::spawn(move || {
        loop {
            if stop_receiver.try_recv().is_ok() {
                break;
            }
            match event_receiver.recv_timeout(Duration::from_millis(500)) {
                Ok(()) => {
                    while event_receiver.try_recv().is_ok() {}
                    on_change();
                }
                Err(mpsc::RecvTimeoutError::Timeout) => {}
                Err(mpsc::RecvTimeoutError::Disconnected) => break,
            }
        }
        drop(watcher);
    });
    Ok(WatchHandle {
        stop: Some(stop_sender),
    })
}

impl SyncEngine {
    pub fn new(endpoint: impl Into<String>, token: impl Into<String>) -> Self {
        Self {
            client: SyncClient::new(endpoint, token),
            app_data_dir: None,
        }
    }

    pub fn with_app_data_dir(mut self, app_data_dir: PathBuf) -> Self {
        self.app_data_dir = Some(app_data_dir);
        self
    }

    pub async fn resolve_conflict(
        &self,
        binding: &SyncBinding,
        conflict_id: &str,
        resolution: &str,
        content: Option<&str>,
        base_revision: Option<i64>,
    ) -> Result<SyncReport, SyncError> {
        let conflict = self
            .client
            .conflicts(&binding.notebook_id)
            .await?
            .into_iter()
            .find(|item| item.id == conflict_id)
            .ok_or_else(|| SyncError::Format("conflict not found".to_string()))?;
        let local_path = conflict.local_path.trim_start_matches('/').to_string();
        let local_path = fs::normalize_relative_path(Path::new(&local_path))?;
        let resolved_content = match resolution {
            "keep_local" => match content {
                Some(value) => Some(value.to_string()),
                None => Some(fs::read_markdown(Path::new(&binding.folder), &local_path)?),
            },
            "merged_content" => Some(
                content
                    .ok_or_else(|| SyncError::Format("merged content missing".to_string()))?
                    .to_string(),
            ),
            "keep_remote" => None,
            _ => return Err(SyncError::Format("unknown conflict resolution".to_string())),
        };
        let response = self
            .client
            .resolve_conflict(
                &binding.notebook_id,
                conflict_id,
                resolution,
                resolved_content.as_deref(),
                base_revision.or(conflict.remote_revision),
            )
            .await?;
        let _ = response;

        if resolution == "keep_remote" {
            fs::delete_markdown(Path::new(&binding.folder), &local_path)?;
        } else if let Some(content) = resolved_content {
            fs::write_markdown(Path::new(&binding.folder), &local_path, &content)?;
        }

        self.sync_now(binding).await
    }
}

trait MergeResultExt {
    fn map_merged(self) -> Option<String>;
}

impl MergeResultExt for merge::MergeResult {
    fn map_merged(self) -> Option<String> {
        match self {
            merge::MergeResult::Merged(content) => Some(content),
            merge::MergeResult::Conflict => None,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ignores_internal_sync_files_in_watcher() {
        let root = PathBuf::from("notes-root");
        assert!(!should_sync_event(
            &root,
            &root.join(".lifequest/manifest.json")
        ));
        assert!(!should_sync_event(
            &root,
            &root.join(".lifequest-conflicts/today__note.md")
        ));
        assert!(should_sync_event(&root, &root.join("Journal/today.md")));
    }
}
