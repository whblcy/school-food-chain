// Tauri 桌面端桥接工具
// 检测是否运行在 Tauri 环境中，并提供原生能力调用

declare global {
  interface Window {
    __TAURI_INTERNALS__?: unknown
    __TAURI__?: {
      invoke: <T = unknown>(cmd: string, args?: Record<string, unknown>) => Promise<T>
    }
  }
}

/** 是否运行在 Tauri 桌面端环境 */
export const isTauri = (): boolean => {
  return typeof window !== 'undefined' && (!!window.__TAURI_INTERNALS__ || !!window.__TAURI__)
}

/** 调用 Tauri 命令 */
export async function invoke<T = unknown>(cmd: string, args?: Record<string, unknown>): Promise<T> {
  if (!isTauri() || !window.__TAURI__) {
    throw new Error('Not running in Tauri environment')
  }
  return window.__TAURI__.invoke<T>(cmd, args)
}

/** 获取后端 API 地址（桌面端从 Rust 侧获取配置） */
export async function getApiBase(): Promise<string> {
  if (!isTauri()) {
    // Web 开发环境回退
    return import.meta.env.VITE_API_BASE_URL || '/api/v1'
  }
  try {
    return await invoke<string>('get_api_base')
  } catch {
    return 'http://localhost:8000/api/v1'
  }
}

/** 发送系统通知 */
export async function sendNotification(title: string, body: string): Promise<void> {
  if (!isTauri()) {
    // Web 环境使用浏览器通知
    if ('Notification' in window) {
      if (Notification.permission === 'granted') {
        new Notification(title, { body })
      } else if (Notification.permission !== 'denied') {
        const permission = await Notification.requestPermission()
        if (permission === 'granted') {
          new Notification(title, { body })
        }
      }
    }
    return
  }
  await invoke('send_notification', { title, body })
}

/** 获取应用版本 */
export async function getAppVersion(): Promise<string> {
  if (!isTauri()) return '2.0.0'
  try {
    return await invoke<string>('get_app_version')
  } catch {
    return '2.0.0'
  }
}

/** 初始化桌面端桥接 */
export async function initDesktopBridge(): Promise<void> {
  if (!isTauri()) return

  // 设置桌面端特有样式
  document.documentElement.setAttribute('data-platform', 'desktop')

  // 请求通知权限
  if ('Notification' in window && Notification.permission === 'default') {
    await Notification.requestPermission()
  }
}
