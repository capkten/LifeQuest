use crate::fs;
use crate::state::{self, BindingState, ClientState};
use crate::sync::{SyncBinding, SyncEngine, SyncPreview, SyncReport, SyncStatus};
use std::path::PathBuf;
use std::sync::{Mutex, OnceLock};
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::Mutex as AsyncMutex;

static ACTIVE_WATCHER: OnceLock<Mutex<Option<crate::sync::WatchHandle>>> = OnceLock::new();
static ACTIVE_SYNC: OnceLock<AsyncMutex<()>> = OnceLock::new();

fn watcher_slot() -> &'static Mutex<Option<crate::sync::WatchHandle>> {
    ACTIVE_WATCHER.get_or_init(|| Mutex::new(None))
}

fn stop_watcher() {
    if let Ok(mut slot) = watcher_slot().lock() {
        if let Some(handle) = slot.take() {
            handle.stop();
        }
    }
}

fn sync_slot() -> &'static AsyncMutex<()> {
    ACTIVE_SYNC.get_or_init(|| AsyncMutex::new(()))
}

fn app_data_dir(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map_err(|error| format!("APP_DATA_DIR: {error}"))
}

fn load_client_state(app_data_dir: &std::path::Path) -> Result<ClientState, String> {
    if !state::state_path(app_data_dir).exists() {
        return Ok(ClientState::default());
    }
    state::load_state(app_data_dir).map_err(|error| error.to_string())
}

fn persist_binding(
    app: &AppHandle,
    endpoint: &str,
    binding: &SyncBinding,
    paused: bool,
) -> Result<(), String> {
    let data_dir = app_data_dir(app)?;
    let mut client_state = load_client_state(&data_dir)?;
    client_state.endpoint = endpoint.trim_end_matches('/').to_string();
    client_state
        .bindings
        .retain(|item| item.notebook_id != binding.notebook_id);
    client_state.bindings.push(BindingState {
        notebook_id: binding.notebook_id.clone(),
        folder: binding.folder.clone(),
        device_id: binding.device_id.clone(),
        cursor: binding.cursor,
        paused,
    });
    state::save_state(&data_dir, &client_state).map_err(|error| error.to_string())
}

fn set_queue_paused(app: &AppHandle, paused: bool) -> Result<(), String> {
    let data_dir = app_data_dir(app)?;
    let mut queue =
        crate::sync::queue::load_queue_or_default(&data_dir).map_err(|error| error.to_string())?;
    queue.paused = paused;
    crate::sync::queue::save_queue(&data_dir, &queue).map_err(|error| error.to_string())
}

fn install_watcher(
    app: &AppHandle,
    binding: SyncBinding,
    endpoint: String,
    token: String,
) -> Result<(), String> {
    stop_watcher();
    let app_handle = app.clone();
    let watcher_binding = binding.clone();
    let watcher_endpoint = endpoint.clone();
    let watcher_token = token.clone();
    let handle = crate::sync::watch_folder(PathBuf::from(&binding.folder), move || {
        let app_handle = app_handle.clone();
        let binding = watcher_binding.clone();
        let sync_endpoint = watcher_endpoint.clone();
        let sync_token = watcher_token.clone();
        let _ = app_handle.emit(
            "sync://progress",
            serde_json::json!({
                "state": "syncing",
                "notebook_id": binding.notebook_id,
                "folder": binding.folder,
            }),
        );
        tauri::async_runtime::spawn(async move {
            match sync_binding(&app_handle, binding, sync_endpoint, sync_token).await {
                Ok(_) => {}
                Err(error) => {
                    let _ = app_handle.emit(
                        "sync://error",
                        serde_json::json!({ "error": error.to_string() }),
                    );
                }
            }
        });
    })
    .map_err(|error| error.to_string())?;
    watcher_slot()
        .lock()
        .map_err(|error| error.to_string())?
        .replace(handle);
    Ok(())
}

#[tauri::command]
pub async fn select_sync_folder() -> Result<fs::SyncFolder, String> {
    let selected = tauri::async_runtime::spawn_blocking(|| {
        rfd::FileDialog::new()
            .set_title("选择 LifeQuest 笔记文件夹")
            .pick_folder()
    })
    .await
    .map_err(|error| error.to_string())?;
    let path = selected.ok_or_else(|| "FOLDER_SELECTION_CANCELLED".to_string())?;
    fs::validate_root(&path).map_err(|error| error.to_string())?;
    Ok(fs::SyncFolder {
        path: path.to_string_lossy().into_owned(),
    })
}

fn resolve_device_id(value: Option<String>) -> String {
    value.unwrap_or_else(|| uuid::Uuid::new_v4().to_string())
}

#[tauri::command]
pub async fn preview_sync(
    notebook_id: String,
    folder: String,
    device_id: Option<String>,
    endpoint: String,
    token: String,
) -> Result<SyncPreview, String> {
    SyncEngine::new(endpoint, token)
        .preview(&SyncBinding {
            notebook_id,
            folder,
            device_id: resolve_device_id(device_id),
            cursor: 0,
        })
        .await
        .map_err(|error| error.to_string())
}

async fn sync_binding(
    app: &AppHandle,
    binding: SyncBinding,
    endpoint: String,
    token: String,
) -> Result<SyncReport, String> {
    let _guard = sync_slot().lock().await;
    let data_dir = app_data_dir(app)?;
    let report = SyncEngine::new(endpoint.clone(), token)
        .with_app_data_dir(data_dir)
        .sync_now(&binding)
        .await
        .map_err(|error| error.to_string())?;
    let _ = app.emit("sync://status", &report.status);
    if !report.conflicts.is_empty() {
        let _ = app.emit("sync://conflict", &report.conflicts);
    }
    let mut persisted_binding = binding;
    persisted_binding.cursor = report.status.cursor;
    persist_binding(app, &endpoint, &persisted_binding, false)?;
    Ok(report)
}

#[tauri::command]
pub async fn start_sync(
    app: AppHandle,
    binding: SyncBinding,
    endpoint: String,
    token: String,
) -> Result<SyncStatus, String> {
    set_queue_paused(&app, false)?;
    let report = sync_binding(&app, binding.clone(), endpoint.clone(), token.clone()).await?;
    install_watcher(&app, binding, endpoint, token)?;
    Ok(report.status)
}

#[tauri::command]
pub async fn sync_now(
    app: AppHandle,
    binding: SyncBinding,
    endpoint: String,
    token: String,
) -> Result<SyncReport, String> {
    sync_binding(&app, binding, endpoint, token).await
}

#[tauri::command]
pub async fn pause_sync(
    app: AppHandle,
    binding: SyncBinding,
    endpoint: String,
) -> Result<SyncStatus, String> {
    stop_watcher();
    set_queue_paused(&app, true)?;
    let data_dir = app_data_dir(&app)?;
    let pending_operations = crate::sync::queue::load_queue_or_default(&data_dir)
        .map_err(|error| error.to_string())?
        .pending_for_notebook(&binding.notebook_id);
    persist_binding(&app, &endpoint, &binding, true)?;
    Ok(SyncStatus {
        state: "paused".to_string(),
        notebook_id: binding.notebook_id,
        folder: binding.folder,
        cursor: binding.cursor,
        pending_operations,
        conflicts: 0,
        error: None,
    })
}

#[tauri::command]
pub async fn resume_sync(
    app: AppHandle,
    binding: SyncBinding,
    endpoint: String,
    token: String,
) -> Result<SyncStatus, String> {
    set_queue_paused(&app, false)?;
    let report = sync_binding(&app, binding.clone(), endpoint.clone(), token.clone()).await?;
    install_watcher(&app, binding, endpoint, token)?;
    Ok(report.status)
}

#[tauri::command]
pub async fn resolve_conflict(
    app: AppHandle,
    binding: SyncBinding,
    conflict_id: String,
    resolution: String,
    content: Option<String>,
    base_revision: Option<i64>,
    endpoint: String,
    token: String,
) -> Result<SyncReport, String> {
    let _guard = sync_slot().lock().await;
    let data_dir = app_data_dir(&app)?;
    let report = SyncEngine::new(endpoint.clone(), token)
        .with_app_data_dir(data_dir)
        .resolve_conflict(
            &binding,
            &conflict_id,
            &resolution,
            content.as_deref(),
            base_revision,
        )
        .await
        .map_err(|error| error.to_string())?;
    let _ = app.emit("sync://status", &report.status);
    let mut persisted_binding = binding;
    persisted_binding.cursor = report.status.cursor;
    persist_binding(&app, &endpoint, &persisted_binding, false)?;
    Ok(report)
}
