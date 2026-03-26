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

  function currentTheme () {
    return localStorage.getItem('apeiria-theme') === 'light' ? 'vs' : 'vs-dark'
  }

  onMounted(async () => {
    if (!container.value) return
    monaco = await import('monaco-editor')
    monaco.editor.setTheme(currentTheme())
    editor = monaco.editor.create(container.value, {
      automaticLayout: true,
      language: props.language,
      minimap: { enabled: false },
      readOnly: props.readOnly,
      scrollBeyondLastLine: false,
      value: props.modelValue,
      wordWrap: 'on',
    })
    changeSubscription = editor.onDidChangeModelContent(() => {
      if (!editor) return
      emit('update:modelValue', editor.getValue())
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
