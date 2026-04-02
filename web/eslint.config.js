import vuetify from 'eslint-config-vuetify'
import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from '@vue/eslint-config-typescript'

export default await vuetify({}, ...defineConfigWithVueTs(vueTsConfigs.recommended))
