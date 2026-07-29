import { defineStore } from 'pinia'
import axios from 'axios'
import { memberLogin, memberLogout, memberRegister } from '../api'

const AUTH_STORAGE_KEY = 'oem_member_auth'

function readStoredAuth() {
  try {
    const raw = localStorage.getItem(AUTH_STORAGE_KEY)
    if (!raw) return null
    const data = JSON.parse(raw)
    // 仅恢复非敏感用户摘要；忽略历史 access/refresh
    if (!data?.user) return null
    return { user: data.user, profile: data.profile ?? null }
  } catch {
    return null
  }
}

function writeStoredAuth(data) {
  if (!data?.user) {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    return
  }
  localStorage.setItem(
    AUTH_STORAGE_KEY,
    JSON.stringify({ user: data.user, profile: data.profile ?? null }),
  )
}

const stored = readStoredAuth()

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: stored?.user ?? null,
    accessToken: null,
    profile: stored?.profile ?? null,
    bootstrapped: false,
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
      writeStoredAuth(
        this.accessToken && this.user
          ? { user: this.user, profile: this.profile }
          : null,
      )
    },
    setSession(user, tokens, profile = null) {
      this.user = user
      this.accessToken = tokens?.access || null
      this.profile = profile || user?.factory_profile || null
      this.persist()
    },
    clearLocal() {
      this.user = null
      this.accessToken = null
      this.profile = null
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
      const baseURL = import.meta.env.VITE_API_BASE_URL || '/api'
      const res = await axios.post(
        `${baseURL}/member/auth/refresh`,
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
        await memberLogout()
      } catch {
        /* 仍清本地态 */
      }
      this.clearLocal()
    },
  },
})
