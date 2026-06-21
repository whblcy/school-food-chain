import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

type ThemeMode = 'light' | 'dark'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem('theme') as ThemeMode) ||
    (window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'),
  )

  const isDark = computed(() => mode.value === 'dark')

  function toggle() {
    mode.value = mode.value === 'dark' ? 'light' : 'dark'
    localStorage.setItem('theme', mode.value)
  }

  function setMode(m: ThemeMode) {
    mode.value = m
    localStorage.setItem('theme', m)
  }

  return { mode, isDark, toggle, setMode }
})
