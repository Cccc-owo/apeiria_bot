<template>
  <div ref="container" class="monaco-editor-host" :style="{ height: normalizedHeight }" />
</template>

<script setup lang="ts">
  import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

  interface MonacoModule {
    editor: {
      create: (
        element: HTMLElement,
        options: Record<string, unknown>,
      ) => MonacoEditorInstance
      setTheme: (theme: string) => void
    }
    languages: {
      register: (language: { id: string }) => void
      setLanguageConfiguration: (languageId: string, configuration: Record<string, unknown>) => void
      setMonarchTokensProvider: (languageId: string, provider: Record<string, unknown>) => void
    }
  }

  interface MonacoEditorInstance {
    dispose: () => void
    getValue: () => string
    layout: () => void
    onDidChangeModelContent: (listener: () => void) => { dispose: () => void }
    setValue: (value: string) => void
    updateOptions: (options: Record<string, unknown>) => void
  }

  const props = withDefaults(defineProps<{
    height?: number | string
    language?: string
    modelValue: string
    readOnly?: boolean
  }>(), {
    height: 360,
    language: 'toml',
    readOnly: false,
  })

  const emit = defineEmits<{
    'update:modelValue': [value: string]
  }>()

  const container = ref<HTMLElement | null>(null)
  const normalizedHeight = computed(() =>
    typeof props.height === 'number' ? `${props.height}px` : props.height,
  )

  let monaco: MonacoModule | null = null
  let editor: MonacoEditorInstance | null = null
  let changeSubscription: { dispose: () => void } | null = null
  let tomlRegistered = false

  function currentTheme () {
    return localStorage.getItem('apeiria-theme') === 'light' ? 'vs' : 'vs-dark'
  }

  function ensureTomlLanguage (monacoModule: MonacoModule) {
    if (tomlRegistered) return
    tomlRegistered = true
    monacoModule.languages.register({ id: 'toml' })
    monacoModule.languages.setLanguageConfiguration('toml', {
      autoClosingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '"', close: '"' },
      ],
      brackets: [
        ['{', '}'],
        ['[', ']'],
      ],
      comments: {
        lineComment: '#',
      },
      surroundingPairs: [
        { open: '{', close: '}' },
        { open: '[', close: ']' },
        { open: '"', close: '"' },
      ],
    })
    monacoModule.languages.setMonarchTokensProvider('toml', {
      brackets: [
        { open: '{', close: '}', token: 'delimiter.curly' },
        { open: '[', close: ']', token: 'delimiter.square' },
      ],
      defaultToken: '',
      ignoreCase: false,
      keywords: ['true', 'false'],
      escapes: /\\(?:[btnfr"\\]|u[0-9A-Fa-f]{4})/,
      tokenizer: {
        root: [
          [/^\s*\[[^[\]]+\]\s*$/, 'type.identifier'],
          [/[A-Za-z0-9_-]+(?=\s*=)/, 'key'],
          [/#.*$/, 'comment'],
          [/"([^"\\]|\\.)*$/, 'string.invalid'],
          [/"/, { token: 'string.quote', next: '@string' }],
          [/-?\d+\.\d+([eE][+-]?\d+)?/, 'number.float'],
          [/-?\d+/, 'number'],
          [/\b(?:true|false)\b/, 'keyword'],
          [/[{}[\]]/, '@brackets'],
          [/[=,]/, 'delimiter'],
        ],
        string: [
          [/[^\\"]+/, 'string'],
          [/@escapes/, 'string.escape'],
          [/\\./, 'string.escape.invalid'],
          [/"/, { token: 'string.quote', next: '@pop' }],
        ],
      },
    })
  }

  onMounted(async () => {
    if (!container.value) return
    const monacoModule = (await import('monaco-editor/esm/vs/editor/editor.api.js')) as unknown as MonacoModule
    monaco = monacoModule
    if (props.language === 'toml') {
      ensureTomlLanguage(monacoModule)
    }
    monacoModule.editor.setTheme(currentTheme())
    const instance = monacoModule.editor.create(container.value, {
      automaticLayout: true,
      language: props.language,
      minimap: { enabled: false },
      readOnly: props.readOnly,
      scrollBeyondLastLine: false,
      value: props.modelValue,
      wordWrap: 'on',
    })
    editor = instance
    changeSubscription = instance.onDidChangeModelContent(() => {
      emit('update:modelValue', instance.getValue())
    })
  })

  watch(
    () => props.modelValue,
    nextValue => {
      if (!editor || editor.getValue() === nextValue) return
      editor.setValue(nextValue)
    },
  )

  watch(
    () => props.readOnly,
    nextValue => {
      editor?.updateOptions({ readOnly: nextValue })
    },
  )

  watch(normalizedHeight, () => {
    editor?.layout()
  })

  onBeforeUnmount(() => {
    changeSubscription?.dispose()
    editor?.dispose()
  })
</script>

<style scoped>
.monaco-editor-host {
  min-height: 240px;
  border-radius: 14px;
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}
</style>
