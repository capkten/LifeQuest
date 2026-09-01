use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum MergeResult {
    Merged(String),
    Conflict,
}

pub fn three_way_merge(base: &str, local: &str, remote: &str) -> MergeResult {
    if local == remote {
        return MergeResult::Merged(local.to_string());
    }
    if local == base {
        return MergeResult::Merged(remote.to_string());
    }
    if remote == base {
        return MergeResult::Merged(local.to_string());
    }

    let base_lines: Vec<_> = base.lines().collect();
    let local_lines: Vec<_> = local.lines().collect();
    let remote_lines: Vec<_> = remote.lines().collect();
    if base_lines.len() != local_lines.len() || base_lines.len() != remote_lines.len() {
        return MergeResult::Conflict;
    }
    let mut merged = Vec::with_capacity(base_lines.len());
    for index in 0..base_lines.len() {
        let base_line = base_lines[index];
        let local_line = local_lines[index];
        let remote_line = remote_lines[index];
        if local_line == remote_line {
            merged.push(local_line);
        } else if local_line == base_line {
            merged.push(remote_line);
        } else if remote_line == base_line {
            merged.push(local_line);
        } else {
            return MergeResult::Conflict;
        }
    }
    let suffix = if base.ends_with('\n') || local.ends_with('\n') || remote.ends_with('\n') {
        "\n"
    } else {
        ""
    };
    MergeResult::Merged(format!("{}{}", merged.join("\n"), suffix))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_non_overlapping_line_changes() {
        assert_eq!(
            three_way_merge("one\ntwo\nthree", "ONE\ntwo\nthree", "one\ntwo\nTHREE"),
            MergeResult::Merged("ONE\ntwo\nTHREE".to_string())
        );
    }

    #[test]
    fn keeps_conflicting_line_edits_recoverable() {
        assert_eq!(
            three_way_merge("one", "local", "remote"),
            MergeResult::Conflict
        );
    }
}
