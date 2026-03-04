
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'

import App from './App.vue'
import router from './router'

import ElementPlus from 'element-plus'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

import 'element-plus/dist/index.css'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(ElementPlus)

app.mount('#app')
