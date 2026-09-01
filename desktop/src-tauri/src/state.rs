use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum StateError {
    #[error("STATE_IO: {0}")]
    Io(String),
    #[error("STATE_FORMAT: {0}")]
    Format(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct BindingState {
    pub notebook_id: String,
    pub folder: String,
    pub device_id: String,
    pub cursor: i64,
    pub paused: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct ClientState {
    pub endpoint: String,
    pub bindings: Vec<BindingState>,
}

pub fn state_path(app_data_dir: &Path) -> PathBuf {
    app_data_dir.join("LifeQuest").join("client-state.json")
}

pub fn save_state(app_data_dir: &Path, state: &ClientState) -> Result<(), StateError> {
    let target = state_path(app_data_dir);
    let parent = target
        .parent()
        .ok_or_else(|| StateError::Io("state parent missing".to_string()))?;
    std::fs::create_dir_all(parent).map_err(|error| StateError::Io(error.to_string()))?;
    let temporary = parent.join(format!("client-state.{}.tmp", std::process::id()));
    let content =
        serde_json::to_vec_pretty(state).map_err(|error| StateError::Format(error.to_string()))?;
    std::fs::write(&temporary, content).map_err(|error| StateError::Io(error.to_string()))?;
    std::fs::rename(&temporary, target).map_err(|error| StateError::Io(error.to_string()))?;
    Ok(())
}

pub fn load_state(app_data_dir: &Path) -> Result<ClientState, StateError> {
    let content = std::fs::read(state_path(app_data_dir))
        .map_err(|error| StateError::Io(error.to_string()))?;
    serde_json::from_slice(&content).map_err(|error| StateError::Format(error.to_string()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn state_round_trip_keeps_binding_and_cursor() {
        let root = tempdir().unwrap();
        let state = ClientState {
            endpoint: "https://lifequest.test".to_string(),
            bindings: vec![BindingState {
                notebook_id: "notebook".to_string(),
                folder: "D:/Notes".to_string(),
                device_id: "device".to_string(),
                cursor: 42,
                paused: false,
            }],
        };
        save_state(root.path(), &state).unwrap();
        assert_eq!(load_state(root.path()).unwrap(), state);
    }
}
