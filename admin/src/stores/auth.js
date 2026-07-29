import { defineStore } from 'pinia'
import axios from 'axios'
import { adminLogin, adminLogout } from '../api'

const AUTH_STORAGE_KEY = 'oem_admin_auth'

function readStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    if (!data?.user) return null
    return { user: data.user }
  } catch {
    return null
  }
}

function writeStoredAuth(data) {
  if (!data?.user) {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ user: data.user }))
}

const stored = readStoredAuth()

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: stored?.user ?? null,
    accessToken: null,
    bootstrapped: false,
  }),
  getters: { isLoggedIn: (state) => Boolean(state.accessToken) },
  actions: {
    persist() {
      writeStoredAuth(this.accessToken && this.user ? { user: this.user } : null)
    },
    setSession(user, tokens) {
      this.user = user
      this.accessToken = tokens?.access || null
      this.persist()
    },
    clearLocal() {
      this.user = null
      this.accessToken = null
      this.persist()
    },
    async login(payload) {
      const res = await adminLogin(payload)
      this.setSession(res.data.user, res.data.tokens)
    },
    async refreshAccessToken() {
      const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
      const res = await axios.post(
        `${baseURL}/admin/auth/refresh`,
        {},
        { withCredentials: true },
      )
      const body = res.data
      const access = body.access ?? body.data?.access
      if (!access) {
        throw new Error('Refresh failed')
      }
      this.accessToken = access
      this.persist()
      return this.accessToken
    },
    async bootstrapSession() {
      if (this.bootstrapped) return
      this.bootstrapped = true
      if (!this.user) return
      try {
        await this.refreshAccessToken()
      } catch {
        this.clearLocal()
      }
    },
    async logout() {
      try {
        await adminLogout()
      } catch {
        /* 仍清本地态 */
      }
      this.clearLocal()
    },
  },
})
