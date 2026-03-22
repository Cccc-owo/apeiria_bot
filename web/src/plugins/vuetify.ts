import { createVuetify } from 'vuetify'
import '@mdi/font/css/materialdesignicons.css'
import 'vuetify/styles'

const THEME_STORAGE_KEY = 'apeiria-theme'
const initialTheme =
  typeof window !== 'undefined' && localStorage.getItem(THEME_STORAGE_KEY) === 'light'
    ? 'light'
    : 'dark'

export default createVuetify({
  theme: {
    defaultTheme: initialTheme,
    themes: {
      light: {
        dark: false,
        colors: {
          primary: '#1565C0',
          secondary: '#42A5F5',
          accent: '#7C4DFF',
          background: '#F5F5F5',
          surface: '#FFFFFF',
          error: '#E53935',
          warning: '#FB8C00',
          success: '#43A047',
          info: '#1E88E5',
        },
      },
      dark: {
        dark: true,
        colors: {
          primary: '#42A5F5',
          secondary: '#1565C0',
          accent: '#7C4DFF',
          background: '#121212',
          surface: '#1E1E2E',
          error: '#FF5252',
          warning: '#FFD740',
          success: '#69F0AE',
          info: '#448AFF',
        },
      },
    },
  },
  defaults: {
    VCard: { rounded: 'lg', elevation: 2 },
    VBtn: { rounded: 'lg' },
    VTextField: { variant: 'outlined', density: 'comfortable' },
  },
})
