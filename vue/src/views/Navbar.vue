<template>
  <div>
    <div v-if="toast.show" id="toast" class="toast">{{ toast.msg }}</div>
    <nav class="navbar">
      <div class="navbar-left">
        <img src="@/assets/logo.png" alt="Logo" class="logo" />
      </div>
      <div class="navbar-title">
        <img src="@/assets/title.png" alt="Title" class="navbar-title-image" />
      </div>
      <div class="navbar-center">
        <RouterLink to="/chat" class="nav-link navbar-create-center" :class="{ 'navbar-active': isActive('/chat') }"
          @click="requireLogin">AI 聊天</RouterLink>
        <RouterLink to="/rag" class="nav-link" :class="{ 'navbar-active': isActive('/rag') }">RAG 页面</RouterLink>
      </div>
      <div class="navbar-right">
        <RouterLink to="/user" class="navbar-user-info" style="text-decoration:none; color:inherit;"
          @click="requireLogin">
          <img :src="userStore.userAvatarURL || defaultAvatar" alt="User Icon" class="navbar-user-icon" />
          <span class="username">{{ userStore.userName || '用户名' }}</span>
          <span class="user-tooltip">点击进入用户中心</span>
        </RouterLink>
        <RouterLink to="/login" class="nav-link">登录/注册</RouterLink>
      </div>
    </nav>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import { useUserStore } from '@/stores/user'
import defaultAvatar from '@/assets/default-avatar.png'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const toast = ref({ show: false, msg: '' })

function showToast(msg, duration = 2000) {
  toast.value.msg = msg
  toast.value.show = true
  setTimeout(() => {
    toast.value.show = false
  }, duration)
}

function isActive(path) {
  return route.path === path
}

function requireLogin(e) {
  if (!userStore.isLoggedIn) {
    e.preventDefault()
    showToast('请先登录！')
    setTimeout(() => {
      router.push('/login')
    }, 1200)
    return false
  }
  return true
}

onMounted(() => {
})
</script>

<style scoped>
/* 直接复制原有样式 */
.navbar {
  display: flex;
  height: 50px;
  background-color: #fff;
  border-bottom: 1px solid #eee;
  align-items: center;
}

.navbar-left {
  margin-left: 10px;
}

.logo {
  height: 32px;
  width: auto;
  display: block;
}

.navbar-title {
  margin-left: 0px;
}

.navbar-title-image {
  height: 20px;
  width: auto;
  display: block;
}

.navbar-center {
  margin-left: 25px;
  display: flex;
  gap: 24px;
}

.nav-link {
  text-decoration: none;
  color: #333;
  font-size: 16px;
}

.nav-link:hover {
  font-weight: bold;
}

.navbar-right {
  margin-left: auto;
  margin-right: 10px;
  display: flex;
  align-items: center;
}

.navbar-user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 16px;
  transition: transform 0.2s;
  cursor: pointer;
}

.navbar-user-info:hover {
  text-decoration: none;
  color: inherit;
  transform: scale(1.1);
}

.user-tooltip {
  display: none;
  position: absolute;
  left: 50%;
  bottom: -32px;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
  opacity: 0.9;
  pointer-events: none;
}

.navbar-user-info:hover .user-tooltip {
  display: block;
}

.navbar-user-icon {
  height: 32px;
  width: 32px;
  border-radius: 50%;
  display: block;
}

.nav-link.navbar-active {
  font-weight: bold;
  position: relative;
}

.nav-link.navbar-active::after {
  content: \"\";
  position: absolute;
  left: 0;
  right: 0;
  height: 2px;
  background: #000;
  bottom: -14px;
}

.toast {
  display: block;
  position: fixed;
  top: 30px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.7);
  color: #fff;
  padding: 12px 32px;
  border-radius: 6px;
  z-index: 9999;
  font-size: 16px;
}
</style>