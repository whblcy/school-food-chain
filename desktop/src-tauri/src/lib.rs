// Tauri 应用主逻辑
// 桌面端特有能力：系统通知、菜单、托盘等

use tauri::Manager;
use tauri_plugin_notification::NotificationExt;

/// 应用配置：后端 API 地址
/// 桌面端默认连接本地后端，可通过配置文件覆盖
const DEFAULT_API_BASE: &str = "http://localhost:8000/api/v1";

/// 发送系统通知（前端可调用）
#[tauri::command]
async fn send_notification(
    app: tauri::AppHandle,
    title: String,
    body: String,
) -> Result<(), String> {
    app.notification()
        .builder()
        .title(&title)
        .body(&body)
        .show()
        .map_err(|e| e.to_string())?;
    Ok(())
}

/// 获取 API 基础地址
#[tauri::command]
fn get_api_base() -> String {
    // 优先从环境变量读取，否则使用默认值
    std::env::var("API_BASE_URL").unwrap_or_else(|_| DEFAULT_API_BASE.to_string())
}

/// 获取应用版本
#[tauri::command]
fn get_app_version(app: tauri::AppHandle) -> String {
    app.package_info().version.to_string()
}

/// 应用入口
#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    env_logger::init();

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_notification::init())
        .plugin(tauri_plugin_os::init())
        .invoke_handler(tauri::generate_handler![
            send_notification,
            get_api_base,
            get_app_version,
        ])
        .setup(|app| {
            log::info!("学校食材供应链桌面端启动 v{}", app.package_info().version);

            // 设置窗口标题
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.set_title(&format!(
                    "学校食材供应链管理平台 v{}",
                    app.package_info().version
                ));
            }

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("运行 Tauri 应用时出错");
}
