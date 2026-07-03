import { defineStore } from 'pinia'
import axios from 'axios'
import { adminLogin } from '../api'

const AUTH_STORAGE_KEY = 'oem_admin_auth'

function readStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    return data?.accessToken ? data : null
  } catch {
    return null
  }
}

function writeStoredAuth(data) {
  if (!data?.accessToken) {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return
  }
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(data))
}

const stored = readStoredAuth()
if (stored?.accessToken) {
  window.__adminAccessToken = stored.accessToken
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: stored?.user ?? null,
    accessToken: stored?.accessToken ?? null,
    refreshToken: stored?.refreshToken ?? null,
  }),
  getters: { isLoggedIn: (state) => Boolean(state.accessToken) },
  actions: {
    persist() {
      if (!this.accessToken) {
        writeStoredAuth(null)
        window.__adminAccessToken = null
        return
      }
      writeStoredAuth({
        user: this.user,
        accessToken: this.accessToken,
        refreshToken: this.refreshToken,
      })
      window.__adminAccessToken = this.accessToken
    },
    setSession(user, tokens) {
      this.user = user
      this.accessToken = tokens?.access || null
      this.refreshToken = tokens?.refresh || null
      this.persist()
    },
    async login(payload) {
      const res = await adminLogin(payload)
      this.setSession(res.data.user, res.data.tokens)
    },
    async refreshAccessToken() {
      if (!this.refreshToken) {
        throw new Error('No refresh token')
      }
      const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
      const res = await axios.post(`${baseURL}/admin/auth/refresh`, {
        refresh: this.refreshToken,
      })
      const body = res.data
      const access = body.access ?? body.data?.access
      const refresh = body.refresh ?? body.data?.refresh
      if (!access) {
        throw new Error('Refresh failed')
      }
      this.accessToken = access
      if (refresh) this.refreshToken = refresh
      this.persist()
      return this.accessToken
    },
    logout() {
      this.user = null
      this.accessToken = null
      this.refreshToken = null
      this.persist()
    },
  },
})
