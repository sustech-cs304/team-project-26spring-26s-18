import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

const TOKEN_STORAGE_KEY = 'token'
const USER_INFO_STORAGE_KEY = 'userInfo'

function readStoredToken() {
  return localStorage.getItem(TOKEN_STORAGE_KEY) || ''
}

function readStoredUserInfo() {
  try {
    return JSON.parse(localStorage.getItem(USER_INFO_STORAGE_KEY) || '{}') || {}
  } catch {
    return {}
  }
}

function firstAvailable(...values) {
  return values.find(value => value !== undefined && value !== null && String(value).trim() !== '') || ''
}

export const useUserStore = defineStore('user', () => {
  const storedUserInfo = readStoredUserInfo()
  const id = ref(firstAvailable(storedUserInfo.id, storedUserInfo.user_id, null))
  const userName = ref(firstAvailable(storedUserInfo.userName, storedUserInfo.username, storedUserInfo.name))
  const phone = ref(firstAvailable(storedUserInfo.phone))
  const email = ref(firstAvailable(storedUserInfo.email))
  const userAvatarURL = ref(firstAvailable(storedUserInfo.avatarURL, storedUserInfo.avatarUrl, storedUserInfo.avatar_url, storedUserInfo.avatar))
  const token = ref(firstAvailable(readStoredToken(), storedUserInfo.token))
  const isLoggedIn = computed(() => !!token.value || !!id.value)
  const displayName = computed(() => userName.value || email.value || '用户名')

  function persistUser() {
    if (token.value) {
      localStorage.setItem(TOKEN_STORAGE_KEY, token.value)
    } else {
      localStorage.removeItem(TOKEN_STORAGE_KEY)
    }
    localStorage.setItem(USER_INFO_STORAGE_KEY, JSON.stringify({
      id: id.value,
      userName: userName.value,
      phone: phone.value,
      email: email.value,
      avatarURL: userAvatarURL.value,
    }))
  }

  function setUser(newUser = {}, fallback = {}) {
    const user = newUser || {}
    id.value = firstAvailable(user.id, user.user_id, user.userId, fallback.id, id.value)
    email.value = firstAvailable(user.email, fallback.email, email.value)
    userName.value = firstAvailable(
      user.userName,
      user.username,
      user.name,
      user.displayName,
      fallback.userName,
      fallback.username,
      fallback.name,
      email.value
    )
    phone.value = firstAvailable(user.phone, fallback.phone, phone.value)
    userAvatarURL.value = firstAvailable(user.avatarURL, user.avatarUrl, user.avatar_url, user.avatar, fallback.avatarURL, fallback.avatar, userAvatarURL.value)
    token.value = firstAvailable(user.token, user.access_token, user.jwt, fallback.token, token.value)
    persistUser()
  }

  function loadStoredAuth() {
    const storedInfo = readStoredUserInfo()
    const storedToken = readStoredToken()
    if (!storedToken && Object.keys(storedInfo).length === 0) return
    setUser(storedInfo, { token: storedToken })
  }

  function clearUser() {
    id.value = null
    userName.value = ''
    phone.value = ''
    email.value = ''
    userAvatarURL.value = ''
    token.value = ''
    localStorage.removeItem(TOKEN_STORAGE_KEY)
    localStorage.removeItem(USER_INFO_STORAGE_KEY)
    localStorage.removeItem('user')
  }

  return { id, phone, email, userAvatarURL, userName, token, isLoggedIn, displayName, setUser, loadStoredAuth, clearUser }
}, {
  persist: true
})
