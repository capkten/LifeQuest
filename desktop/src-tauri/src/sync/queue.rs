use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use thiserror::Error;

#[derive(Debug, Error)]
pub enum QueueError {
    #[error("QUEUE_IO: {0}")]
    Io(String),
    #[error("QUEUE_FORMAT: {0}")]
    Format(String),
    #[error("QUEUE_NOT_FOUND")]
    NotFound,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct QueuedOperation {
    #[serde(default)]
    pub notebook_id: String,
    pub operation_id: String,
    pub payload: serde_json::Value,
    pub attempts: u32,
    pub next_retry_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct DurableQueue {
    pub operations: Vec<QueuedOperation>,
    pub paused: bool,
}

impl DurableQueue {
    pub fn enqueue(&mut self, operation_id: impl Into<String>, payload: serde_json::Value) -> bool {
        self.enqueue_for_notebook("", operation_id, payload)
    }

    pub fn enqueue_for_notebook(
        &mut self,
        notebook_id: impl Into<String>,
        operation_id: impl Into<String>,
        payload: serde_json::Value,
    ) -> bool {
        let notebook_id = notebook_id.into();
        let operation_id = operation_id.into();
        if self
            .operations
            .iter()
            .any(|operation| operation.operation_id == operation_id)
        {
            return false;
        }
        self.operations.push(QueuedOperation {
            notebook_id,
            operation_id,
            payload,
            attempts: 0,
            next_retry_at: 0,
        });
        true
    }

    pub fn ready(&self, now: i64) -> Option<&QueuedOperation> {
        if self.paused {
            return None;
        }
        self.operations
            .iter()
            .find(|operation| operation.next_retry_at <= now)
    }

    pub fn ready_for_notebook(&self, notebook_id: &str, now: i64) -> Option<&QueuedOperation> {
        if self.paused {
            return None;
        }
        self.operations.iter().find(|operation| {
            operation.notebook_id == notebook_id && operation.next_retry_at <= now
        })
    }

    pub fn pending_for_notebook(&self, notebook_id: &str) -> usize {
        self.operations
            .iter()
            .filter(|operation| operation.notebook_id == notebook_id)
            .count()
    }

    pub fn acknowledge(&mut self, operation_id: &str) {
        self.operations
            .retain(|operation| operation.operation_id != operation_id);
    }

    pub fn failed(&mut self, operation_id: &str, now: i64) {
        if let Some(operation) = self
            .operations
            .iter_mut()
            .find(|operation| operation.operation_id == operation_id)
        {
            operation.attempts = operation.attempts.saturating_add(1);
            let delay = 2_i64.pow(operation.attempts.min(8));
            operation.next_retry_at = now + delay;
        }
    }
}

pub fn queue_path(app_data_dir: &Path) -> PathBuf {
    app_data_dir.join("LifeQuest").join("sync-queue.json")
}

pub fn save_queue(app_data_dir: &Path, queue: &DurableQueue) -> Result<(), QueueError> {
    let target = queue_path(app_data_dir);
    let parent = target
        .parent()
        .ok_or_else(|| QueueError::Io("queue parent missing".to_string()))?;
    std::fs::create_dir_all(parent).map_err(|error| QueueError::Io(error.to_string()))?;
    let temporary = parent.join(format!("sync-queue.{}.tmp", std::process::id()));
    let content =
        serde_json::to_vec_pretty(queue).map_err(|error| QueueError::Format(error.to_string()))?;
    std::fs::write(&temporary, content).map_err(|error| QueueError::Io(error.to_string()))?;
    std::fs::rename(&temporary, target).map_err(|error| QueueError::Io(error.to_string()))?;
    Ok(())
}

pub fn load_queue(app_data_dir: &Path) -> Result<DurableQueue, QueueError> {
    let content = std::fs::read(queue_path(app_data_dir)).map_err(|error| {
        if error.kind() == std::io::ErrorKind::NotFound {
            QueueError::NotFound
        } else {
            QueueError::Io(error.to_string())
        }
    })?;
    serde_json::from_slice(&content).map_err(|error| QueueError::Format(error.to_string()))
}

pub fn load_queue_or_default(app_data_dir: &Path) -> Result<DurableQueue, QueueError> {
    match load_queue(app_data_dir) {
        Ok(queue) => Ok(queue),
        Err(QueueError::NotFound) => Ok(DurableQueue::default()),
        Err(error) => Err(error),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn deduplicates_operations_and_retries_with_backoff() {
        let mut queue = DurableQueue::default();
        assert!(queue.enqueue("device:1", serde_json::json!({"kind": "update_note"})));
        assert!(!queue.enqueue("device:1", serde_json::json!({"kind": "update_note"})));
        queue.failed("device:1", 10);
        assert_eq!(queue.ready(11), None);
        assert_eq!(queue.ready(12).unwrap().attempts, 1);
        queue.acknowledge("device:1");
        assert!(queue.operations.is_empty());
    }

    #[test]
    fn persists_queue_across_restart() {
        let root = tempdir().unwrap();
        let mut queue = DurableQueue::default();
        queue.enqueue("device:2", serde_json::json!({"kind": "create_note"}));
        save_queue(root.path(), &queue).unwrap();
        assert_eq!(load_queue(root.path()).unwrap(), queue);
    }
}
