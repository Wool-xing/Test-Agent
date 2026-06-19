#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

#[tauri::command]
fn get_version() -> String {
    "2.0.0".to_string()
}

#[tauri::command]
fn restart_engine() -> Result<String, String> {
    Ok("engine restarted".to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![get_version, restart_engine])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
