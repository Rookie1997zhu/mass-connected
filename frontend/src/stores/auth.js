import { defineStore } from 'pinia'
import axios from 'axios'
import { memberLogin, memberRegister } from '../api'

const AUTH_STORAGE_KEY = 'oem_member_auth'

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
  window.__memberAccessToken = stored.accessToken
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: stored?.user ?? null,
    accessToken: stored?.accessToken ?? null,
    refreshToken: stored?.refreshToken ?? null,
    profile: stored?.profile ?? null,
  }),
  getters: {
    isLoggedIn: (state) => Boolean(state.accessToken),
    role: (state) => state.user?.role || null,
    memberType: (state) => state.user?.member_type || null,
    isMember: (state) => state.user?.role === 'member' || state.user?.role === 'factory',
    isBuyer: (state) => state.user?.role === 'member' || state.user?.role === 'factory',
    isIndividual: (state) =>
      state.user?.role === 'member' && state.user?.member_type === 'individual',
    isEnterprise: (state) =>
      state.user?.role === 'member'
        ? state.user?.member_type === 'enterprise'
        : state.user?.role === 'factory',
    factoryProfile: (state) => state.profile || state.user?.factory_profile || null,
    isSupplier: (state) => {
      const profile = state.profile || state.user?.factory_profile
      if (!profile || profile.status !== 'approved') return false
      const user = state.user
      if (!user) return false
      if (user.role === 'factory') return true
      return user.role === 'member' && user.member_type === 'enterprise'
    },
    isFactoryPending: (state) => {
      const profile = state.profile || state.user?.factory_profile
      return Boolean(profile && profile.status === 'pending')
    },
    /** @deprecated use isSupplier */
    isFactory: (state) => {
      const profile = state.profile || state.user?.factory_profile
      return Boolean(profile && profile.status === 'approved')
    },
  },
  actions: {
    persist() {
      if (!this.accessToken) {
        writeStoredAuth(null)
        window.__memberAccessToken = null
        return
      }
      writeStoredAuth({
        user: this.user,
        accessToken: this.accessToken,
        refreshToken: this.refreshToken,
        profile: this.profile,
      })
      window.__memberAccessToken = this.accessToken
    },
    setSession(user, tokens, profile = null) {
      this.user = user
      this.accessToken = tokens?.access || null
      this.refreshToken = tokens?.refresh || null
      this.profile = profile || user?.factory_profile || null
      this.persist()
    },
    async login(payload) {
      const res = await memberLogin(payload)
      this.setSession(res.data.user, res.data.tokens, res.data.profile || null)
      return res
    },
    async register(payload) {
      const res = await memberRegister(payload)
      this.setSession(res.data.user, res.data.tokens, res.data.profile || null)
      return res
    },
    async refreshAccessToken() {
      if (!this.refreshToken) {
        throw new Error('No refresh token')
      }
      const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
      const res = await axios.post(`${baseURL}/member/auth/refresh`, {
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
      this.profile = null
      this.persist()
    },
  },
})
