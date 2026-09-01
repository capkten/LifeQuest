mod commands;
pub mod fs;
pub mod state;
pub mod sync;

pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            commands::select_sync_folder,
            commands::preview_sync,
            commands::start_sync,
            commands::sync_now,
            commands::pause_sync,
            commands::resume_sync,
            commands::resolve_conflict
        ])
        .run(tauri::generate_context!())
        .expect("error while running LifeQuest desktop client");
}
