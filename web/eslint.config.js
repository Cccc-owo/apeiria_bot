import vuetify from 'eslint-config-vuetify'
import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from './node_modules/.pnpm/node_modules/@vue/eslint-config-typescript/dist/index.mjs'

export default defineConfigWithVueTs(...vuetify, vueTsConfigs.recommended)
