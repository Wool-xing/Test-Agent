#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;

#[tauri::command]
fn get_version() -> String {
    env!("CARGO_PKG_VERSION").to_string() // from tauri.conf.json / Cargo.toml — no hardcoded version
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
