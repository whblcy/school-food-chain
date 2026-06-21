import { createI18n } from 'vue-i18n'
import messages from './locales.json'

export type AppLocale = 'zh' | 'en'

function getInitialLocale(): AppLocale {
  const stored = localStorage.getItem('locale')
  return stored === 'en' ? 'en' : 'zh'
}

const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: 'en',
  messages,
})

export default i18n

export function setLocale(locale: AppLocale) {
  i18n.global.locale.value = locale
  localStorage.setItem('locale', locale)
}
