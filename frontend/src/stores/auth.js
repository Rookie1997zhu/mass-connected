import { defineStore } from 'pinia'
import { factoryRegister, memberLogin, memberRegister } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    accessToken: null,
    profile: null,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.accessToken),
    role: (state) => state.user?.role || null,
    isMember: (state) => state.user?.role === 'member',
    isFactory: (state) => state.user?.role === 'factory',
  },
  actions: {
    setSession(user, tokens, profile = null) {
      this.user = user
      this.accessToken = tokens?.access || null
      this.profile = profile
      window.__memberAccessToken = tokens?.access || null
    },
    async login(payload) {
      const res = await memberLogin(payload)
      this.setSession(res.data.user, res.data.tokens, res.data.profile || null)
      return res
    },
    async register(payload) {
      const res = await memberRegister(payload)
      this.setSession(res.data.user, res.data.tokens)
      return res
    },
    async registerFactory(payload) {
      return factoryRegister(payload)
    },
    logout() {
      this.user = null
      this.accessToken = null
      this.profile = null
      window.__memberAccessToken = null
    },
  },
})
