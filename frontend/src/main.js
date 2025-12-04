import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './assets/main.css'
import axios from 'axios'

// CRÍTICO: Garante que o axios sempre use caminhos relativos
// Isso faz com que o proxy (Vite em dev ou nginx em prod) intercepte corretamente
// NÃO defina baseURL como URL absoluta, sempre deixe vazio ou undefined
if (axios.defaults.baseURL) {
  delete axios.defaults.baseURL
}

// Interceptor para FORÇAR caminhos relativos
axios.interceptors.request.use(
  (config) => {
    // Se a URL for absoluta (começa com http:// ou https://), converte para relativa
    if (config.url && (config.url.startsWith('http://') || config.url.startsWith('https://'))) {
      try {
        const url = new URL(config.url)
        config.url = url.pathname + url.search
      } catch (e) {
        // Se falhar ao parsear, mantém como está
      }
    }
    // Garante que baseURL não seja definido
    if (config.baseURL && (config.baseURL.startsWith('http://') || config.baseURL.startsWith('https://'))) {
      config.baseURL = ''
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')
