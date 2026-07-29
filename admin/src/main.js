import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import './style.css'
import { useAuthStore } from './stores/auth'

document.title = i18n.global.t('app.title')

const app = createApp(App)
const pinia = createPinia()
app.use(pinia).use(router).use(i18n).use(ElementPlus)

const auth = useAuthStore()
auth.bootstrapSession().finally(() => {
  app.mount('#app')
})
