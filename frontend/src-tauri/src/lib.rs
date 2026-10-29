
mod odm_commands;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()

        // ==================================================
        // TAURI PLUGINS
        // ==================================================

        .plugin(tauri_plugin_dialog::init())

        // ==================================================
        // APPLICATION STATE
        // ==================================================

        .manage(odm_commands::ODMJobState::default())

        // ==================================================
        // BACKEND COMMANDS
        // ==================================================

        .invoke_handler(tauri::generate_handler![
            odm_commands::odm_system_info,
            odm_commands::odm_start,
            odm_commands::odm_cancel,
        ])

        // ==================================================
        // START APPLICATION
        // ==================================================

        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
