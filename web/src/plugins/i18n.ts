import { createI18n } from 'vue-i18n'
import enUS from '@/locales/en_US'
import zhCN from '@/locales/zh_CN'

export const SUPPORTED_LOCALES = ['zh_CN', 'en_US'] as const
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

const locale = (localStorage.getItem('apeiria-locale') as SupportedLocale | null)
  || (navigator.language.toLowerCase().startsWith('zh') ? 'zh_CN' : 'en_US')

const i18n = createI18n({
  legacy: false,
  locale,
  fallbackLocale: 'zh_CN',
  messages: {
    zh_CN: zhCN,
    en_US: enUS,
  },
})

document.documentElement.lang = locale === 'zh_CN' ? 'zh-CN' : 'en-US'

export default i18n
