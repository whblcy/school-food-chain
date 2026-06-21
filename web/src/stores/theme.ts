import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem('theme') as ThemeMode) ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
  )

  const isDark = computed(() => mode.value === 'dark')

  function toggle() {
    setMode(mode.value === 'light' ? 'dark' : 'light')
  }

  function setMode(m: ThemeMode) {
    mode.value = m
    localStorage.setItem('theme', m)
  }

  return { mode, isDark, toggle, setMode }
})
