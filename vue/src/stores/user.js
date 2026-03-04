import { ref, computed } from 'vue'
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', () => {
  const id = ref(null)
  const userName = ref('')
  const phone = ref('')
  const email = ref('')
  const userAvatarURL = ref('')
  const token = ref('')
  const isLoggedIn = computed(() => !!id.value)
  function setUser(newUser) {
    id.value = newUser.id
    userName.value = newUser.userName
    phone.value = newUser.phone
    email.value = newUser.email
    userAvatarURL.value = newUser.avatarURL
    token.value = newUser.token
  }

  return { id, phone, email, userAvatarURL, userName, token, isLoggedIn, setUser }
}, {
  persist: true
})
