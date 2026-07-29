import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './style.css'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router).use(i18n)

const auth = useAuthStore()
auth.bootstrapSession().finally(() => {
  app.mount('#app')
})
