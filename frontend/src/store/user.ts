import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as authApi from '@/api/auth'
import { setTokens, clearTokens, parseJwt } from '@/utils/auth'

export const useUserStore = defineStore('user', () => {
  const id = ref('')
  const username = ref('')
  const displayName = ref('')
  const roles = ref<string[]>([])
  const permissions = ref<string[]>([])
  const isAuthenticated = ref(false)

  async function login(account: string, password: string) {
    const res = await authApi.login(account, password)
    const { access_token, refresh_token, user } = res.data.data
    setTokens(access_token, refresh_token)
    applyUser(user)
  }

  function applyUser(u: any) {
    id.value = u.id
    username.value = u.username
    displayName.value = u.display_name || u.username
    roles.value = u.roles || []
    permissions.value = u.permissions || []
    isAuthenticated.value = true
  }

  async function fetchMe() {
    const res = await authApi.me()
    applyUser(res.data.data)
    return res.data.data
  }

  async function logout() {
    const rt = localStorage.getItem('baize_refresh')
    if (rt) {
      try {
        await authApi.logout(rt)
      } catch {
        /* ignore */
      }
    }
    clearTokens()
    id.value = ''
    username.value = ''
    roles.value = []
    permissions.value = []
    isAuthenticated.value = false
  }

  return { id, username, displayName, roles, permissions, isAuthenticated, login, fetchMe, logout }
})
