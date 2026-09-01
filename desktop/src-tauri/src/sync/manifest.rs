use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteManifest {
    pub notebook_id: String,
    pub revision: i64,
    pub items: Vec<RemoteManifestItem>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteManifestItem {
    pub node_id: String,
    pub parent_id: Option<String>,
    pub node_type: String,
    pub name: String,
    pub path: String,
    pub content_revision: Option<i64>,
    pub content_hash: Option<String>,
    pub updated_at: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct RemoteContentResponse {
    pub notebook_id: String,
    pub contents: std::collections::HashMap<String, String>,
}
