// Tauri 主进程入口
// 防止 Windows Release 构建时出现控制台窗口
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    school_food_desktop_lib::run()
}
