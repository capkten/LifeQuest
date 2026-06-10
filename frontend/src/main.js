import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import router from './router'

import VMdEditor from '@kangc/v-md-editor'
import '@kangc/v-md-editor/lib/style/base-editor.css'
import githubTheme from '@kangc/v-md-editor/lib/theme/github.js'
import '@kangc/v-md-editor/lib/theme/style/github.css'
import Prism from 'prismjs'

VMdEditor.use(githubTheme, {
  Prism
})

const app = createApp(App)

const CHUNK_RELOAD_FLAG = '__lifequest_chunk_reload__'
function reloadOnceForChunkMismatch() {
  if (typeof window === 'undefined') return
  if (sessionStorage.getItem(CHUNK_RELOAD_FLAG) === '1') return
  sessionStorage.setItem(CHUNK_RELOAD_FLAG, '1')
  window.location.reload()
}

window.addEventListener('vite:preloadError', (event) => {
  event.preventDefault()
  reloadOnceForChunkMismatch()
})

app.use(createPinia())
app.use(router)
app.use(VMdEditor)

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component)
}

router.onError((error) => {
  const message = String(error?.message || error || '')
  if (message.includes('Failed to fetch dynamically imported module') || message.includes('Loading chunk')) {
    reloadOnceForChunkMismatch()
  }
})

app.mount('#app')
