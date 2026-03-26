import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNoticeStore = defineStore('notice', () => {
  const visible = ref(false)
  const message = ref('')
  const color = ref<'success' | 'error' | 'warning' | 'info'>('info')

  function show (nextMessage: string, nextColor: 'success' | 'error' | 'warning' | 'info' = 'info') {
    message.value = nextMessage
    color.value = nextColor
    visible.value = true
  }

  function hide () {
    visible.value = false
  }

  return { visible, message, color, show, hide }
})
