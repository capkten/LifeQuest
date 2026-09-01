use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use thiserror::Error;

#[derive(Debug, Error, PartialEq, Eq)]
pub enum FsError {
    #[error("FOLDER_NOT_FOUND")]
    FolderNotFound,
    #[error("PATH_ESCAPES_ROOT")]
    PathEscapesRoot,
    #[error("INVALID_MARKDOWN_ENCODING: {0}")]
    InvalidEncoding(String),
    #[error("INVALID_SYNC_NAME")]
    InvalidSyncName,
    #[error("MANIFEST_IO: {0}")]
    ManifestIo(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct SyncFolder {
    pub path: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LocalEntry {
    pub relative_path: String,
    pub node_type: String,
    pub content_hash: Option<String>,
    pub content: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct LocalManifest {
    pub schema_version: u32,
    pub notebook_id: String,
    pub device_id: String,
    pub entries: Vec<ManifestEntry>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ManifestEntry {
    pub node_id: String,
    pub relative_path: String,
    pub node_type: String,
    pub content_hash: Option<String>,
    pub remote_revision: Option<i64>,
    pub last_synced_content: Option<String>,
    pub updated_at: String,
}

pub fn validate_root(path: &Path) -> Result<PathBuf, FsError> {
    if !path.exists() || !path.is_dir() {
        return Err(FsError::FolderNotFound);
    }
    path.canonicalize().map_err(|_| FsError::FolderNotFound)
}

pub fn normalize_relative_path(path: &Path) -> Result<String, FsError> {
    let mut parts = Vec::new();
    for component in path.components() {
        let value = component.as_os_str().to_string_lossy();
        if value.is_empty() || value == "." || value == ".." || value.contains('\\') {
            return Err(FsError::PathEscapesRoot);
        }
        if value.starts_with('.') || value.contains('/') || value.contains(':') {
            return Err(FsError::InvalidSyncName);
        }
        let upper = value.to_ascii_uppercase();
        let reserved_stem = upper.split('.').next().unwrap_or(upper.as_str());
        if matches!(reserved_stem, "CON" | "PRN" | "AUX" | "NUL")
            || (reserved_stem.starts_with("COM") && reserved_stem[3..].parse::<u8>().is_ok())
            || (reserved_stem.starts_with("LPT") && reserved_stem[3..].parse::<u8>().is_ok())
        {
            return Err(FsError::InvalidSyncName);
        }
        parts.push(value.into_owned());
    }
    if parts.is_empty() {
        return Err(FsError::PathEscapesRoot);
    }
    Ok(parts.join("/"))
}

pub fn sha256(content: &str) -> String {
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}

pub fn scan_markdown(root: &Path) -> Result<Vec<LocalEntry>, FsError> {
    let canonical_root = validate_root(root)?;
    let mut entries = Vec::new();
    scan_directory(&canonical_root, &canonical_root, &mut entries)?;
    entries.sort_by(|left, right| left.relative_path.cmp(&right.relative_path));
    Ok(entries)
}

fn scan_directory(
    root: &Path,
    directory: &Path,
    entries: &mut Vec<LocalEntry>,
) -> Result<(), FsError> {
    let read_dir =
        std::fs::read_dir(directory).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    for item in read_dir {
        let item = item.map_err(|error| FsError::ManifestIo(error.to_string()))?;
        let path = item.path();
        let name = item.file_name().to_string_lossy().into_owned();
        if name == ".lifequest" || name == ".lifequest-conflicts" {
            continue;
        }
        let metadata = std::fs::symlink_metadata(&path)
            .map_err(|error| FsError::ManifestIo(error.to_string()))?;
        let canonical = path.canonicalize().map_err(|_| FsError::PathEscapesRoot)?;
        if !canonical.starts_with(root) {
            return Err(FsError::PathEscapesRoot);
        }
        let relative = path
            .strip_prefix(root)
            .map_err(|_| FsError::PathEscapesRoot)?;
        if metadata.is_dir() {
            let relative_path = normalize_relative_path(relative)?;
            entries.push(LocalEntry {
                relative_path,
                node_type: "folder".to_string(),
                content_hash: None,
                content: None,
            });
            scan_directory(root, &canonical, entries)?;
        } else if metadata.is_file()
            && path
                .extension()
                .is_some_and(|extension| extension.to_string_lossy().eq_ignore_ascii_case("md"))
        {
            let relative_path = normalize_relative_path(relative)?;
            let bytes =
                std::fs::read(&path).map_err(|error| FsError::ManifestIo(error.to_string()))?;
            let content = String::from_utf8(bytes)
                .map_err(|_| FsError::InvalidEncoding(relative_path.clone()))?;
            entries.push(LocalEntry {
                relative_path,
                node_type: "note".to_string(),
                content_hash: Some(sha256(&content)),
                content: Some(content),
            });
        }
    }
    Ok(())
}

pub fn manifest_path(root: &Path) -> PathBuf {
    root.join(".lifequest").join("manifest.json")
}

pub fn write_manifest(root: &Path, manifest: &LocalManifest) -> Result<(), FsError> {
    let target = manifest_path(root);
    let directory = target
        .parent()
        .ok_or_else(|| FsError::ManifestIo("manifest parent missing".to_string()))?;
    std::fs::create_dir_all(directory).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    let temporary = directory.join(format!("manifest.{}.tmp", std::process::id()));
    let content = serde_json::to_vec_pretty(manifest)
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    std::fs::write(&temporary, content).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    std::fs::rename(&temporary, &target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    Ok(())
}

pub fn read_manifest(root: &Path) -> Result<LocalManifest, FsError> {
    let content = std::fs::read(manifest_path(root))
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    serde_json::from_slice(&content).map_err(|error| FsError::ManifestIo(error.to_string()))
}

pub fn read_markdown(root: &Path, relative_path: &str) -> Result<String, FsError> {
    let canonical_root = validate_root(root)?;
    let relative = normalize_relative_path(Path::new(relative_path))?;
    if !relative.to_ascii_lowercase().ends_with(".md") {
        return Err(FsError::InvalidSyncName);
    }
    let target = canonical_root.join(&relative);
    let metadata = std::fs::symlink_metadata(&target)
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(FsError::PathEscapesRoot);
    }
    let canonical_target = target
        .canonicalize()
        .map_err(|_| FsError::PathEscapesRoot)?;
    if !canonical_target.starts_with(&canonical_root) {
        return Err(FsError::PathEscapesRoot);
    }
    let bytes =
        std::fs::read(canonical_target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    String::from_utf8(bytes).map_err(|_| FsError::InvalidEncoding(relative))
}

pub fn write_markdown(root: &Path, relative_path: &str, content: &str) -> Result<(), FsError> {
    let canonical_root = validate_root(root)?;
    let relative = normalize_relative_path(Path::new(relative_path))?;
    if !relative.to_ascii_lowercase().ends_with(".md") {
        return Err(FsError::InvalidSyncName);
    }
    let target = canonical_root.join(&relative);
    let parent = target
        .parent()
        .ok_or_else(|| FsError::ManifestIo("file parent missing".to_string()))?;
    std::fs::create_dir_all(parent).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    let canonical_parent = parent
        .canonicalize()
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    if !canonical_parent.starts_with(&canonical_root) {
        return Err(FsError::PathEscapesRoot);
    }
    if target.exists() {
        let metadata = std::fs::symlink_metadata(&target)
            .map_err(|error| FsError::ManifestIo(error.to_string()))?;
        if metadata.file_type().is_symlink() {
            return Err(FsError::PathEscapesRoot);
        }
    }
    let temporary = parent.join(format!(
        ".{}.{}.tmp",
        target.file_name().unwrap().to_string_lossy(),
        std::process::id()
    ));
    std::fs::write(&temporary, content.as_bytes())
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    if target.exists() {
        std::fs::remove_file(&target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    }
    std::fs::rename(&temporary, &target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    Ok(())
}

pub fn delete_markdown(root: &Path, relative_path: &str) -> Result<(), FsError> {
    let canonical_root = validate_root(root)?;
    let relative = normalize_relative_path(Path::new(relative_path))?;
    if !relative.to_ascii_lowercase().ends_with(".md") {
        return Err(FsError::InvalidSyncName);
    }
    let target = canonical_root.join(&relative);
    let metadata = match std::fs::symlink_metadata(&target) {
        Ok(metadata) => metadata,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(()),
        Err(error) => return Err(FsError::ManifestIo(error.to_string())),
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return Err(FsError::PathEscapesRoot);
    }
    let parent = target
        .parent()
        .ok_or_else(|| FsError::ManifestIo("file parent missing".to_string()))?;
    let canonical_parent = parent
        .canonicalize()
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    if !canonical_parent.starts_with(&canonical_root) {
        return Err(FsError::PathEscapesRoot);
    }
    std::fs::remove_file(&target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    Ok(())
}

pub fn ensure_folder(root: &Path, relative_path: &str) -> Result<(), FsError> {
    let canonical_root = validate_root(root)?;
    let relative = normalize_relative_path(Path::new(relative_path))?;
    let target = canonical_root.join(&relative);
    std::fs::create_dir_all(&target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    let canonical_target = target
        .canonicalize()
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    if !canonical_target.starts_with(&canonical_root) {
        return Err(FsError::PathEscapesRoot);
    }
    Ok(())
}

pub fn write_conflict_artifact(
    root: &Path,
    relative_path: &str,
    content: &str,
) -> Result<String, FsError> {
    let canonical_root = validate_root(root)?;
    let clean = normalize_relative_path(Path::new(relative_path))?;
    let conflict_relative = format!(
        ".lifequest-conflicts/{}.{}.md",
        clean.replace('/', "__"),
        chrono::Utc::now().timestamp()
    );
    let target = canonical_root.join(&conflict_relative);
    let parent = target
        .parent()
        .ok_or_else(|| FsError::ManifestIo("conflict parent missing".to_string()))?;
    std::fs::create_dir_all(parent).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    let temporary = parent.join(format!(".conflict.{}.tmp", std::process::id()));
    std::fs::write(&temporary, content.as_bytes())
        .map_err(|error| FsError::ManifestIo(error.to_string()))?;
    std::fs::rename(&temporary, &target).map_err(|error| FsError::ManifestIo(error.to_string()))?;
    Ok(conflict_relative)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::tempdir;

    #[test]
    fn scans_utf8_markdown_and_ignores_reserved_directories() {
        let root = tempdir().unwrap();
        fs::create_dir(root.path().join("Journal")).unwrap();
        fs::write(root.path().join("Journal/today.md"), "你好").unwrap();
        fs::create_dir(root.path().join(".lifequest")).unwrap();
        fs::write(root.path().join(".lifequest/manifest.json"), "{}").unwrap();
        fs::create_dir(root.path().join(".lifequest-conflicts")).unwrap();
        fs::write(
            root.path().join(".lifequest-conflicts/today.md"),
            "conflict",
        )
        .unwrap();
        fs::write(root.path().join("ignored.txt"), "ignored").unwrap();

        let entries = scan_markdown(root.path()).unwrap();
        assert_eq!(entries.len(), 2);
        assert_eq!(entries[0].relative_path, "Journal");
        assert_eq!(entries[1].relative_path, "Journal/today.md");
        assert_eq!(entries[1].content_hash, Some(sha256("你好")));
    }

    #[test]
    fn rejects_invalid_utf8_and_reserved_names() {
        let root = tempdir().unwrap();
        fs::write(root.path().join("bad.md"), [0xff, 0xfe]).unwrap();
        assert!(matches!(
            scan_markdown(root.path()),
            Err(FsError::InvalidEncoding(_))
        ));
        assert_eq!(
            normalize_relative_path(Path::new("CON.md")),
            Err(FsError::InvalidSyncName)
        );
        assert_eq!(
            normalize_relative_path(Path::new("../outside.md")),
            Err(FsError::PathEscapesRoot)
        );
    }

    #[test]
    fn writes_and_reads_manifest_atomically() {
        let root = tempdir().unwrap();
        let manifest = LocalManifest {
            schema_version: 1,
            notebook_id: "notebook".to_string(),
            device_id: "device".to_string(),
            entries: vec![],
        };
        write_manifest(root.path(), &manifest).unwrap();
        assert_eq!(read_manifest(root.path()).unwrap(), manifest);
        assert!(!root.path().join(".lifequest/manifest.999999.tmp").exists());
    }

    #[test]
    fn reads_only_utf8_markdown_inside_the_root() {
        let root = tempdir().unwrap();
        fs::write(root.path().join("note.md"), "content").unwrap();
        assert_eq!(read_markdown(root.path(), "note.md").unwrap(), "content");
        assert!(matches!(
            read_markdown(root.path(), "missing.md"),
            Err(FsError::ManifestIo(_))
        ));
        assert_eq!(
            read_markdown(root.path(), "note.txt"),
            Err(FsError::InvalidSyncName)
        );
    }

    #[test]
    fn deletes_markdown_inside_the_root_and_is_idempotent() {
        let root = tempdir().unwrap();
        fs::write(root.path().join("note.md"), "content").unwrap();

        delete_markdown(root.path(), "note.md").unwrap();
        assert!(!root.path().join("note.md").exists());
        delete_markdown(root.path(), "note.md").unwrap();
    }
}
