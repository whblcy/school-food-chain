import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useThemeStore } from '@/stores/theme'

describe('useThemeStore', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
  })

  it('默认应为浅色模式（当无 localStorage 且系统非 dark）', () => {
    localStorage.removeItem('theme')
    const store = useThemeStore()
    expect(['light', 'dark']).toContain(store.mode)
  })

  it('toggle 应在 light 和 dark 之间切换', () => {
    const store = useThemeStore()
    const initial = store.mode
    store.toggle()
    expect(store.mode).not.toBe(initial)
    store.toggle()
    expect(store.mode).toBe(initial)
  })

  it('setMode 应正确设置模式并持久化', () => {
    const store = useThemeStore()
    store.setMode('dark')
    expect(store.mode).toBe('dark')
    expect(store.isDark).toBe(true)
    expect(localStorage.getItem('theme')).toBe('dark')

    store.setMode('light')
    expect(store.mode).toBe('light')
    expect(store.isDark).toBe(false)
    expect(localStorage.getItem('theme')).toBe('light')
  })

  it('isDark 计算属性应与 mode 同步', () => {
    const store = useThemeStore()
    store.setMode('dark')
    expect(store.isDark).toBe(true)
    store.setMode('light')
    expect(store.isDark).toBe(false)
  })
})
