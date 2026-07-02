import { defineStore } from 'pinia'
import { adminLogin } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ user: null, accessToken: null }),
  getters: { isLoggedIn: (state) => Boolean(state.accessToken) },
  actions: {
    async login(payload) {
      const res = await adminLogin(payload)
      this.user = res.data.user
      this.accessToken = res.data.tokens.access
      window.__adminAccessToken = res.data.tokens.access
    },
    logout() {
      this.user = null
      this.accessToken = null
      window.__adminAccessToken = null
    },
  },
})
