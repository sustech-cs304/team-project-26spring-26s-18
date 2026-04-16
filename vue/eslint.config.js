import pluginVue from 'eslint-plugin-vue'
import prettierConfig from '@vue/eslint-config-prettier/skip-formatting'

export default [
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{js,vue}'],
    rules: {
      'vue/multi-word-component-names': 'off',
    },
  },
  prettierConfig,
]