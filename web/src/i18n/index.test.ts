import { describe, it, expect, beforeEach } from 'vitest'
import i18n, { setLocale, type AppLocale } from '@/i18n'

describe('i18n', () => {
  beforeEach(() => {
    localStorage.clear()
    setLocale('zh')
  })

  it('默认 locale 应为 zh', () => {
    expect(i18n.global.locale.value).toBe('zh')
  })

  it('setLocale(en) 应切换到英文', () => {
    setLocale('en')
    expect(i18n.global.locale.value).toBe('en')
    expect(localStorage.getItem('locale')).toBe('en')
  })

  it('setLocale(zh) 应切换回中文', () => {
    setLocale('en')
    setLocale('zh')
    expect(i18n.global.locale.value).toBe('zh')
    expect(localStorage.getItem('locale')).toBe('zh')
  })

  it('fallbackLocale 应为 en', () => {
    expect(i18n.global.fallbackLocale.value).toBe('en')
  })

  it('应能翻译已知的 key', () => {
    setLocale('zh')
    // locales.json 中应存在一些 key，这里测试 t 函数不抛错
    const result = i18n.global.t('app.title' as never)
    expect(typeof result).toBe('string')
  })
})
