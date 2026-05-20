<template>
  <div class="user-main">
    <!-- 用户资料卡片 -->
    <div class="user-basic-card">
      <div class="user-avatar" @click="onAvatarClick">
        <img :src="userStore.userAvatarURL || defaultAvatar" alt="用户头像" />
        <div class="avatar-tip">点击更换头像</div>
        <input ref="avatarInput" type="file" accept="image/*" style="display:none;" @change="onAvatarChange" />
      </div>
      <div class="user-info">
        <div class="username-span">昵称:</div>
        <div
          class="username-real"
          :title="isEditing ? editUserName : (userStore.userName || '用户名')"
        >
          <span v-if="!isEditing" class="username-real-text">{{ userStore.userName || '用户名' }}</span>
          <input
            v-else
            v-model="editUserName"
            type="text"
            class="username-field-input"
          />
        </div>
      </div>
      <div class="user-info">
        <div class="username-span">邮箱:</div>
        <div class="username-real" :title="userStore.email || '用户邮箱'">
          <span class="username-real-text">{{ userStore.email || '用户邮箱' }}</span>
        </div>
      </div>
      <div class="user-info">
        <div class="username-span">电话:</div>
        <div
          class="username-real"
          :title="isEditing ? editPhone : (userStore.phone || '用户电话')"
        >
          <span v-if="!isEditing" class="username-real-text">{{ userStore.phone || '用户电话' }}</span>
          <input
            v-else
            v-model="editPhone"
            type="text"
            class="username-field-input"
          />
        </div>
      </div>
      <button class="user-btn-edit" @click="onEditClick">{{ isEditing ? '保存信息' : '修改个人信息' }}</button>
      <button class="user-btn-cancel" :class="{ enabled: isEditing }" :disabled="!isEditing"
        @click="onCancelClick">取消修改</button>
    </div>
    <div class="user-visible">
      <div class="user-corner"></div>
    </div>
    <div class="user-files"></div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useUserStore } from '@/stores/user'
import defaultAvatar from '@/assets/default-avatar.png'
import { ip } from '../config/config.js'
const userStore = useUserStore()
const isEditing = ref(false)
const editUserName = ref(userStore.userName)
const editPhone = ref(userStore.phone)
const avatarInput = ref(null)

function onAvatarClick() {
  avatarInput.value && avatarInput.value.click()
}

function onAvatarChange(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async function (evt) {
    const base64 = evt.target.result
    // 预览头像
    userStore.userAvatarURL = base64
    // 上传到服务器
    try {
      const res = await fetch(`http://${ip}/user/updateAvatar`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'token': userStore.token },
        body: JSON.stringify({ id: userStore.id, image: base64 })
      })
      const data = await res.json()
      if (data && data.code === 1 && data.data) {
        console.log(data.data)
        userStore.userAvatarURL = data.data
        userStore.setUser({
          id: userStore.id,
          userName: userStore.userName,
          phone: userStore.phone,
          email: userStore.email,
          avatarURL: data.data,
          token: userStore.token
        })
      } else {
        console.log(data)
      }
    } catch { }
  }
  reader.readAsDataURL(file)
}

function onEditClick() {
  if (!isEditing.value) {
    isEditing.value = true
    editUserName.value = userStore.userName
    editPhone.value = userStore.phone
  } else {
    // 保存
    fetch(`http://${ip}/user/updateInfo`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'token': userStore.token },
      body: JSON.stringify({ id: userStore.id, userName: editUserName.value, phone: editPhone.value })
    })
      .then(res => res.json())
      .then(data => {
        if (data && data.code === 1) {
          userStore.setUser({
            id: userStore.id,
            userName: editUserName.value,
            phone: editPhone.value,
            email: userStore.email,
            avatarURL: userStore.userAvatarURL,
            token: userStore.token
          })
          isEditing.value = false
        }
      })
  }
}

function onCancelClick() {
  isEditing.value = false
}
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  user-select: none;
}

.user-main {
  margin: 20px auto;
  width: 80%;
  max-width: 2000px;
  min-width: 500px;
  height: 700px;
  display: grid;
  grid-template-columns: 330px 1fr;
  grid-template-rows: 500px 1fr;
  grid-template-areas:
    "card files"
    "visible files";
  gap: 0;
}

.user-basic-card {
  grid-area: card;
  width: 300px;
  height: 470px;
  background-color: #ecf0f3;
  box-shadow: 5px 5px 10px #d1d9e6, -5px -5px 10px #f9f9f9;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

.user-avatar {
  position: relative;
  cursor: pointer;
  display: inline-block;
}

.user-avatar img {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  object-fit: cover;
  box-shadow: 5px 5px 10px #d1d9e6, -5px -5px 10px #f9f9f9;
  transition: filter 0.3s;
  display: block;
}

.avatar-tip {
  display: flex;
  align-items: center;
  justify-content: center;
  position: absolute;
  left: 0;
  top: 0;
  width: 80px;
  height: 80px;
  border-radius: 50%;
  color: #4b70e2;
  font-size: 13px;
  font-weight: bold;
  background: rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(4px);
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s;
  text-align: center;
  white-space: pre-line;
  z-index: 2;
}

.user-avatar:hover .avatar-tip {
  opacity: 1;
}

.user-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 90%;
  min-width: 0;
  gap: 4px;
}

.username-span {
  color: #b0b6be;
  font-size: 16px;
  font-weight: bold;
  margin-left: 0;
  letter-spacing: 0.5px;
}

.username-real {
  font-weight: bold;
  background-color: #e7e9eb;
  border-radius: 12px;
  min-height: 40px;
  height: 40px;
  width: 100%;
  min-width: 0;
  font-size: 20px;
  display: flex;
  align-items: center;
  padding: 0 12px 0 16px;
  overflow: hidden;
  transition: background-color 0.3s, color 0.3s;
}

.username-real-text {
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.username-field-input {
  min-width: 0;
  flex: 1 1 0;
  width: 100%;
  height: 70%;
  font-size: 18px;
  border: none;
  background: transparent;
  outline: none;
}

.user-btn-edit {
  width: 82%;
  height: 40px;
  border: none;
  border-radius: 20px;
  background-color: #4b70e2;
  color: white;
  font-size: 16px;
  cursor: pointer;
  box-shadow: 3px 3px 6px #d1d9e6, -3px -3px 6px #f9f9f9;
  transition: background-color 0.3s, box-shadow 0.3s;
}

.user-btn-edit:hover {
  box-shadow: 6px 6px 10px #d1d9e6, -6px -6px 10px #f9f9f9;
  transform: scale(0.985);
  transition: 0.25s;
}

.user-btn-cancel {
  width: 82%;
  height: 40px;
  border: none;
  border-radius: 20px;
  background-color: #7d7c7c;
  color: white;
  font-size: 16px;
  cursor: not-allowed;
  box-shadow: 3px 3px 6px #d1d9e6, -3px -3px 6px #f9f9f9;
  transition: background-color 0.3s, box-shadow 0.3s;
}

.user-btn-edit,
.user-btn-cancel {
  transition: background-color 0.3s, color 0.3s;
}

.user-btn-cancel.enabled {
  background-color: #c7d1e1 !important;
  cursor: pointer !important;
}

.user-visible {
  grid-area: visible;
  position: relative;
  background-color: #ecf0f3;
  box-shadow: -5px 5px 2px #f9f9f9;
  border-radius: 12px 0 0 12px;
}

.user-corner {
  position: absolute;
  top: -27px;
  right: -5px;
  width: 32px;
  height: 32px;
  pointer-events: none;
  z-index: 3;
  background: url('data:image/svg+xml;utf8,<svg width="32" height="32" xmlns="http://www.w3.org/2000/svg"><rect width="32" height="32" fill="%23ecf0f3"/><circle cx="32" cy="0" r="32" fill="white"/></svg>') no-repeat center/cover;
  transform: scaleX(-1) scale(0.7);
}

.user-files {
  grid-area: files;
  background-color: #ecf0f3;
  box-shadow: 5px 5px 10px #f9f9f9;
  border-radius: 12px 12px 12px 0;
}
</style>
