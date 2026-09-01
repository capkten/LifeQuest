use std::collections::HashMap;

use serde::{Deserialize, Serialize};

use super::manifest::RemoteManifestItem;
use crate::fs::LocalEntry;
use crate::fs::ManifestEntry;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "snake_case")]
pub enum DiffAction {
    Download,
    Upload,
    KeepLocal,
    KeepRemote,
    Conflict,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct DiffItem {
    pub relative_path: String,
    pub node_id: Option<String>,
    pub node_type: String,
    pub action: DiffAction,
    pub reason: String,
}

pub fn plan_diff(
    local: &[LocalEntry],
    remote: &[RemoteManifestItem],
    synced: &[ManifestEntry],
) -> Vec<DiffItem> {
    let local_by_path: HashMap<_, _> = local
        .iter()
        .map(|entry| (entry.relative_path.clone(), entry))
        .collect();
    let remote_by_path: HashMap<_, _> = remote
        .iter()
        .map(|entry| (entry.path.trim_start_matches('/').to_string(), entry))
        .collect();
    let synced_by_path: HashMap<_, _> = synced
        .iter()
        .map(|entry| (entry.relative_path.clone(), entry))
        .collect();
    let mut paths: Vec<String> = local_by_path
        .keys()
        .chain(remote_by_path.keys())
        .cloned()
        .collect();
    paths.sort();
    paths.dedup();

    paths
        .into_iter()
        .map(|path| {
            let local_entry = local_by_path.get(&path).copied();
            let remote_entry = remote_by_path.get(&path).copied();
            let synced_entry = synced_by_path.get(&path).copied();
            match (local_entry, remote_entry) {
                (Some(local), Some(remote)) if local.node_type != remote.node_type => DiffItem {
                    relative_path: path,
                    node_id: Some(remote.node_id.clone()),
                    node_type: remote.node_type.clone(),
                    action: DiffAction::Conflict,
                    reason: "local and remote types differ".to_string(),
                },
                (Some(local), Some(remote)) => {
                    let local_hash = local.content_hash.as_deref();
                    let remote_hash = remote.content_hash.as_deref();
                    let synced_hash = synced_entry.and_then(|entry| entry.content_hash.as_deref());
                    let action = if local_hash == remote_hash {
                        DiffAction::KeepRemote
                    } else if synced_hash == local_hash {
                        DiffAction::Download
                    } else if synced_hash == remote_hash {
                        DiffAction::Upload
                    } else {
                        DiffAction::Conflict
                    };
                    DiffItem {
                        relative_path: path,
                        node_id: Some(remote.node_id.clone()),
                        node_type: remote.node_type.clone(),
                        action,
                        reason: "content hash comparison".to_string(),
                    }
                }
                (Some(local), None) => DiffItem {
                    relative_path: path,
                    node_id: synced_entry.map(|entry| entry.node_id.clone()),
                    node_type: local.node_type.clone(),
                    action: if synced_entry.is_some() {
                        DiffAction::Conflict
                    } else {
                        DiffAction::Upload
                    },
                    reason: if synced_entry.is_some() {
                        "remote deletion requires review"
                    } else {
                        "local-only entry"
                    }
                    .to_string(),
                },
                (None, Some(remote)) => DiffItem {
                    relative_path: path,
                    node_id: Some(remote.node_id.clone()),
                    node_type: remote.node_type.clone(),
                    action: DiffAction::Download,
                    reason: "remote-only entry".to_string(),
                },
                (None, None) => unreachable!(),
            }
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::fs::{sha256, LocalEntry};

    fn note(path: &str, content: &str) -> LocalEntry {
        LocalEntry {
            relative_path: path.to_string(),
            node_type: "note".to_string(),
            content_hash: Some(sha256(content)),
            content: Some(content.to_string()),
        }
    }

    fn remote(path: &str, content: &str) -> RemoteManifestItem {
        RemoteManifestItem {
            node_id: format!("id-{path}"),
            parent_id: None,
            node_type: "note".to_string(),
            name: path.trim_end_matches(".md").to_string(),
            path: format!("/{path}"),
            content_revision: Some(1),
            content_hash: Some(sha256(content)),
            updated_at: "2026-09-01T00:00:00Z".to_string(),
        }
    }

    #[test]
    fn classifies_equal_remote_and_local_only_entries() {
        let items = plan_diff(
            &[note("same.md", "same"), note("local.md", "local")],
            &[remote("same.md", "same")],
            &[],
        );
        assert_eq!(
            items
                .iter()
                .find(|item| item.relative_path == "same.md")
                .unwrap()
                .action,
            DiffAction::KeepRemote
        );
        assert_eq!(
            items
                .iter()
                .find(|item| item.relative_path == "local.md")
                .unwrap()
                .action,
            DiffAction::Upload
        );
    }

    #[test]
    fn classifies_remote_change_and_concurrent_change() {
        let base = sha256("base");
        let synced = vec![ManifestEntry {
            node_id: "id-remote.md".to_string(),
            relative_path: "remote.md".to_string(),
            node_type: "note".to_string(),
            content_hash: Some(base.clone()),
            remote_revision: Some(1),
            last_synced_content: Some("base".to_string()),
            updated_at: "2026-09-01T00:00:00Z".to_string(),
        }];
        let download = plan_diff(
            &[note("remote.md", "base")],
            &[remote("remote.md", "remote")],
            &synced,
        );
        assert_eq!(download[0].action, DiffAction::Download);
        let conflict = plan_diff(
            &[note("remote.md", "local")],
            &[remote("remote.md", "remote")],
            &synced,
        );
        assert_eq!(conflict[0].action, DiffAction::Conflict);
    }
}
