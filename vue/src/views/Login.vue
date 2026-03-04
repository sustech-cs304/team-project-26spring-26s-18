<template>
  <div class="center-container">
    <div class="shell">
      <div :class="['container', 'a-container', isLogin ? '' : 'is-txl']">
        <form class="form" @submit.prevent="onRegister">
          <h2 class="form_title title">创建账号/重置密码</h2>
          <span class="form_span">若邮箱未注册过,则为注册;若邮箱已注册过,则为重置密码</span>
          <input v-model="registerEmail" type="email" class="form_input" placeholder="邮箱" />
          <input v-model="registerPassword" type="password" class="form_input" placeholder="密码，至少6位" />
          <div style="display: flex; align-items: center; justify-content: center; width: 100%;">
            <input v-model="registerCode" type="text" class="Code_text" placeholder="验证码" />
            <button class="Code_button" type="button" :disabled="codeBtnDisabled" @click="sendVerificationCode">{{
              codeBtnText }}</button>
          </div>
          <button class="form_button button submit" type="submit">注册</button>
        </form>
      </div>

      <div :class="['container', 'b-container', isLogin ? 'is-z' : 'is-txl']">
        <form class="form" @submit.prevent="onLogin">
          <h2 class="form_title title">登录</h2>
          <span class="form_span">登录方式为电子邮箱登录</span>
          <input v-model="loginEmail" type="email" class="form_input" placeholder="邮箱" />
          <input v-model="loginPassword" type="password" class="form_input" placeholder="密码" />
          <button class="form_button button submit" type="submit">登录</button>
        </form>
      </div>

      <div :class="['switch', isAnimating ? 'is-gx' : '', isLogin ? '' : 'is-txr']">
        <div class="switch_circle"></div>
        <div class="switch_circle switch_circle-t"></div>
        <div class="switch_container" v-show="isLogin">
          <h2 class="switch_title title" style="letter-spacing: 0;">Hello Friend!</h2>
          <p class="switch_description description">去注册一个账号，或者重置密码</p>
          <button class="switch_button button switch-btn" @click="changeForm">去注册/重置密码</button>
        </div>
        <div class="switch_container" v-show="!isLogin">
          <h2 class="switch_title title" style="letter-spacing: 0;">Welcome Back!</h2>
          <p class="switch_description description">已经有账号了嘛，去登入账号吧！！！</p>
          <button class="switch_button button switch-btn" @click="changeForm">去登录</button>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup>

import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import { useRouter } from 'vue-router'
import { ip } from '../config/config.js'

const isLogin = ref(true)
const isAnimating = ref(false)


// 登录表单
const loginEmail = ref('')
const loginPassword = ref('')

// 注册表单
const registerEmail = ref('')
const registerPassword = ref('')
const registerCode = ref('')

// 验证码按钮状态
const codeBtnText = ref('获取验证码')
const codeBtnDisabled = ref(false)
let codeTimer = null

const userStore = useUserStore()
const router = useRouter()

function changeForm() {
  isAnimating.value = true
  isLogin.value = !isLogin.value
  setTimeout(() => {
    isAnimating.value = false
  }, 1500)
}
async function onLogin() {
  if (!loginEmail.value || !loginPassword.value) {
    ElMessage.error('请输入邮箱和密码')
    return
  }
  try {
    const res = await fetch(`http://${ip}/user/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: loginEmail.value,
        password: loginPassword.value
      })
    })
    const data = await res.json()
    if (data.code === 1) {
      userStore.setUser(data.data)
      console.log(data.data)
      ElMessage.success('登录成功')
      router.push('/create')
    } else {
      ElMessage.error('登录失败：' + data.message)
    }
  } catch (e) {
    ElMessage.error('登录请求出错！')
  }
}

// 发送验证码
async function sendVerificationCode() {
  if (!registerEmail.value) {
    ElMessage.error('请输入邮箱')
    return
  }
  try {
    await fetch(`http://${ip}/user/sendCode`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: registerEmail.value })
    })
    ElMessage.success('验证码已发送，请查收！')
    // 倒计时
    let count = 60
    codeBtnDisabled.value = true
    codeBtnText.value = `${count}秒后重发`
    codeTimer && clearInterval(codeTimer)
    codeTimer = setInterval(() => {
      count--
      codeBtnText.value = `${count}秒后重发`
      if (count === 0) {
        clearInterval(codeTimer)
        codeBtnDisabled.value = false
        codeBtnText.value = '获取验证码'
      }
    }, 1000)
  } catch (e) {
    ElMessage.error('验证码发送失败')
  }
}

// 注册
async function onRegister() {
  if (!registerEmail.value || !registerPassword.value || !registerCode.value) {
    ElMessage.error('请填写完整信息')
    return
  }
  if (registerPassword.value.length < 6) {
    ElMessage.error('密码至少6位！')
    return
  }
  try {
    const res = await fetch(`http://${ip}/user/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: registerEmail.value,
        password: registerPassword.value,
        code: registerCode.value
      })
    })
    const data = await res.json()
    if (data.code === 1) {
      //展示data.data中的用户信息
      console.log(data)
      userStore.setUser(data.data)
      ElMessage.success('注册成功')
      router.push('/create')
    } else {
      ElMessage.error('注册失败：' + data.message)
    }
  } catch (e) {
    ElMessage.error('注册请求出错！')
    //展示错误信息
    console.error(e)
  }
}


</script>
<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  /* 字体无法选中 */
  user-select: none;
}

body {
  width: 100%;
  height: 100vh;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  background-color: #ffffff;
  color: #a0a5a8;
}

.center-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}

.shell {
  position: relative;
  width: 1000px;
  min-width: 1000px;
  min-height: 600px;
  height: 600px;
  padding: 25px;
  background-color: #ecf0f3;
  box-shadow: 10px 10px 10px #d1d9e6, -10px -10px 10px #f9f9f9;
  border-radius: 12px;
  overflow: hidden;
}

/* 设置响应式 */
@media (max-width: 1200px) {
  .shell {
    transform: scale(0.7);
  }
}

@media (max-width: 1000px) {
  .shell {
    transform: scale(0.6);
  }
}

@media (max-width: 800px) {
  .shell {
    transform: scale(0.5);
  }
}

@media (max-width: 600px) {
  .shell {
    transform: scale(0.4);
  }
}

.container {
  display: flex;
  justify-content: center;
  align-items: center;
  position: absolute;
  top: 0;
  width: 600px;
  height: 100%;
  padding: 25px;
  background-color: #ecf0f3;
  transition: 1.25s;
}

.form {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.iconfont {
  margin: 0 5px;
  border: rgba(0, 0, 0, 0.5) 2px solid;
  border-radius: 50%;
  font-size: 25px;
  padding: 3px;
  opacity: 0.5;
  transition: 0.1s;
}

.iconfont:hover {
  opacity: 1;
  transition: 0.15s;
  cursor: pointer;
}

.form_input {
  width: 350px;
  height: 40px;
  margin: 4px 0;
  padding-left: 25px;
  font-size: 13px;
  letter-spacing: 0.15px;
  border: none;
  outline: none;
  background-color: #ecf0f3;
  transition: 0.25s ease;
  border-radius: 8px;
  box-shadow: inset 2px 2px 4px #d1d9e6, inset -2px -2px 4px #f9f9f9;
}

.Code_text {
  width: 200px;
  height: 40px;
  margin: 4px 0;
  padding-left: 25px;
  font-size: 13px;
  letter-spacing: 0.15px;
  border: none;
  outline: none;
  background-color: #ecf0f3;
  transition: 0.25s ease;
  border-radius: 8px;
  box-shadow: inset 2px 2px 4px #d1d9e6, inset -2px -2px 4px #f9f9f9;
}

.Code_button {
  width: 120px;
  height: 40px;
  margin-left: 20px;
  font-size: 13px;
  letter-spacing: 0.15px;
  border: none;
  outline: none;
  background-color: #4B70E2;
  color: #f9f9f9;
  box-shadow: 4px 4px 8px #d1d9e6, -4px -4px 8px #f9f9f9;
  border-radius: 8px;
  cursor: pointer;
  transition: 0.25s ease;
}

.Code_button:hover {
  box-shadow: 6px 6px 10px #d1d9e6, -6px -6px 10px #f9f9f9;
  transform: scale(0.985);
  transition: 0.25s;
}

.form_input:focus {
  box-shadow: inset 4px 4px 4px #d1d9e6, inset -4px -4px 4px #f9f9f9;
}

.form_span {
  margin-top: 30px;
  margin-bottom: 12px;
}

.form_link {
  color: #181818;
  font-size: 15px;
  margin-top: 25px;
  border-bottom: 1px solid #a0a5a8;
  line-height: 2;
}

.title {
  font-size: 34px;
  font-weight: 700;
  line-height: 3;
  color: #181818;
  letter-spacing: 10px;
}

.description {
  font-size: 14px;
  letter-spacing: 0.25px;
  text-align: center;
  line-height: 1.6;
}

.button {
  width: 180px;
  height: 50px;
  border-radius: 25px;
  margin-top: 50px;
  font-weight: 700;
  font-size: 14px;
  letter-spacing: 1.15px;
  background-color: #4B70E2;
  color: #f9f9f9;
  box-shadow: 8px 8px 16px #d1d9e6, -8px -8px 16px #f9f9f9;
  border: none;
  outline: none;
}

.a-container {
  z-index: 100;
  left: calc(100% - 600px);
}

.b-container {
  left: calc(100% - 600px);
  z-index: 0;
}

.switch {
  display: flex;
  justify-content: center;
  align-items: center;
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 400px;
  padding: 50px;
  z-index: 200;
  transition: 1.25s;
  background-color: #ecf0f3;
  overflow: hidden;
  box-shadow: 4px 4px 10px #d1d9e6, -4px -4px 10px #d1d9e6;
}

.switch_circle {
  position: absolute;
  width: 500px;
  height: 500px;
  border-radius: 50%;
  background-color: #ecf0f3;
  box-shadow: inset 8px 8px 12px #b8bec7, inset -8px -8px 12px #fff;
  bottom: -60%;
  left: -60%;
  transition: 1.25s;
}

.switch_circle-t {
  top: -30%;
  left: 60%;
  width: 300px;
  height: 300px;
}

.switch_container {
  display: flex;
  justify-content: center;
  align-items: center;
  flex-direction: column;
  position: absolute;
  width: 400px;
  padding: 50px 55px;
  transition: 1.25s;
}

.switch_button {
  cursor: pointer;
}

.switch_button:hover,
.submit:hover {
  box-shadow: 6px 6px 10px #d1d9e6, -6px -6px 10px #f9f9f9;
  transform: scale(0.985);
  transition: 0.25s;
}

.switch_button:active,
.switch_button:focus {
  box-shadow: 2px 2px 6px #d1d9e6, -2px -2px 6px #f9f9f9;
  transform: scale(0.97);
  transition: 0.25s;
}

.is-txr {
  left: calc(100% - 400px);
  transition: 1.25s;
  transform-origin: left;
}

.is-txl {
  left: 0;
  transition: 1.25s;
  transform-origin: right;
}

.is-z {
  z-index: 200;
  transition: 1.25s;
}

.is-hidden {
  visibility: hidden;
  opacity: 0;
  position: absolute;
  transition: 1.25s;
}

.is-gx {
  animation: is-gx 1.25s;
}

@keyframes is-gx {
  0% {
    width: 400px;
  }

  10% {
    width: 400px;
  }

  30% {
    width: 500px;
  }

  50% {
    width: 500px;
  }

  100% {
    width: 400px;
  }
}
</style>