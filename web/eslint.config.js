import {
  defineConfigWithVueTs,
  vueTsConfigs,
} from '@vue/eslint-config-typescript'
import vuetify from 'eslint-config-vuetify'

export default await vuetify(
  {
    ignore: {
      extendIgnore: ['package.json', 'pnpm-lock.yaml'],
    },
  },
  ...defineConfigWithVueTs(vueTsConfigs.recommended),
)
