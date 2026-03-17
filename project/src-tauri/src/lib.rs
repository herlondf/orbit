use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct SessionContract {
    account_id: String,
    profile: String,
    service_url: String,
    storage_partition: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
struct RuntimeProbe {
    shell: &'static str,
    target: &'static str,
    session_isolation: &'static str,
    notifications: &'static str,
    tray: &'static str,
}

#[tauri::command]
fn runtime_probe() -> RuntimeProbe {
    RuntimeProbe {
        shell: "tauri-v2",
        target: "windows-first",
        session_isolation: "per-account webview partition",
        notifications: "native planned",
        tray: "native planned",
    }
}

#[tauri::command]
fn build_session_contract(account_id: String, profile: String, service_url: String) -> SessionContract {
    SessionContract {
        storage_partition: format!("octochat::{account_id}"),
        account_id,
        profile,
        service_url,
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![runtime_probe, build_session_contract])
        .run(tauri::generate_context!())
        .expect("error while running octochat application");
}
