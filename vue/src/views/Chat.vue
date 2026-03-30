<template>
  <div class="chat-container">
    <!-- 左侧会话列表 -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <h2>AI 助手</h2>
      </div>
      
      <!-- 创建新对话按钮 -->
      <button class="create-chat-btn" @click="clearSession">
        <span class="plus-icon">+</span> 创建新对话
      </button>
      
      <!-- 历史会话列表 -->
      <div class="session-list">
        <div 
          v-for="session in sessions" 
          :key="session.id"
          class="session-item"
          :class="{ active: activeSessionId === session.id }"
          @click="selectSession(session.id)"
        >
          <div class="session-title">{{ session.title }}</div>
          <button class="delete-session-btn" @click.stop="deleteSession(session.id)">
            ×
          </button>
        </div>
      </div>
    </div>
    
    <!-- 右侧对话界面 -->
    <div class="chat-main">
      <!-- 对话内容区域 -->
      <div class="chat-content" ref="chatContentRef">
        <div 
          v-for="message in messages" 
          :key="message.id"
          class="message"
          :class="message.role === 'user' ? 'user-message' : 'ai-message'"
        >
          <div class="message-content">
            <div class="message-text">{{ message.content }}</div>
          </div>
        </div>
        <div v-if="loading" class="loading-message">
          <div class="loading-spinner"></div>
          <span>AI 正在思考...</span>
        </div>
      </div>
      
      <!-- 输入框区域 -->
      <div class="chat-input-area">
        <input 
          type="text" 
          v-model="inputMessage"
          class="chat-input"
          placeholder="输入消息..."
          @keyup.enter="sendMessage"
        />
        <button class="send-btn" @click="sendMessage">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import { ip } from '@/config/config'

const userStore = useUserStore()
const sessions = ref([])
const messages = ref([])
const activeSessionId = ref(null)
const inputMessage = ref('')
const loading = ref(false)
const chatContentRef = ref(null)

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatContentRef.value) {
      chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight
    }
  })
}

// 获取用户会话列表
async function fetchSessions() {
  if (!userStore.isLoggedIn) return
  
  try {
    const response = await fetch(`http://${ip}/session/user/${userStore.id}`, {
      headers: {
        'token': userStore.token
      }
    })
    if (response.ok) {
      const result = await response.json()
      // 按updated_at时间倒序排序，最新的放到最上面
      sessions.value = result.data.sort((a, b) => {
        return new Date(b.updated_at) - new Date(a.updated_at)
      })
      console.log(sessions.value)
      // 如果有会话，默认选择第一个
      if (sessions.value.length > 0 && !activeSessionId.value) {
        selectSession(sessions.value[0].id)
      }
    }
  } catch (error) {
    console.error('获取会话列表失败:', error)
  }
}

// 获取会话内容
async function fetchSessionContent(sessionId) {
  try {
    const response = await fetch(`http://${ip}/session/${sessionId}/content`, {
      headers: {
        'token': userStore.token
      }
    })
    if (response.ok) {
      const result = await response.json()
      messages.value = result.data
      scrollToBottom()
    }
  } catch (error) {
    console.error('获取会话内容失败:', error)
  }
}

// 清空会话状态
function clearSession() {
  if (!userStore.isLoggedIn) {
    alert('请先登录')
    return
  }
  
  // 清空当前会话状态，准备创建新会话
  activeSessionId.value = null
  messages.value = []
}

// 选择会话
function selectSession(sessionId) {
  activeSessionId.value = sessionId
  fetchSessionContent(sessionId)
}

// 发送消息
async function sendMessage() {
  if (!inputMessage.value.trim()) return
  
  const messageContent = inputMessage.value.trim()
  inputMessage.value = ''
  
  try {
    // 检查是否是新会话
    if (!activeSessionId.value) {
      // 创建新会话
      // 取前5个字作为标题，超出加...
      let session_title = messageContent.slice(0, 5)
      if (messageContent.length > 5) {
        session_title += '...'
      }
      const createResponse = await fetch(`http://${ip}/session/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'token': userStore.token
        },
        body: JSON.stringify({
          user_id: userStore.id,
          title: session_title
        })
      })
      
      if (createResponse.ok) {
        const createResult = await createResponse.json()
        const newSession = createResult.data
        activeSessionId.value = newSession.id
        
        // 更新会话列表
        sessions.value = [...sessions.value, newSession].sort((a, b) => {
          return new Date(b.updated_at) - new Date(a.updated_at)
        })
      } else {
        console.error('创建会话失败')
        return
      }
    }
    
    // 触发AI回复并获取完整对话
    loading.value = true
    const aiResponse = await fetch(`http://${ip}/session/aicontent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'token': userStore.token
      },
      body: JSON.stringify({
        session_id: activeSessionId.value,
        content: messageContent
      })
    })
    
    if (aiResponse.ok) {
      const aiResult = await aiResponse.json()
      if (aiResult && aiResult.data) {
        const newMessages = aiResult.data
        
        // 清空当前消息列表并添加新消息
        messages.value = [...messages.value, ...newMessages]
        scrollToBottom()
      } else {
        console.log(aiResult)
        console.error('无效的API响应格式')
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
  } finally {
    loading.value = false
  }
}

// 删除会话
async function deleteSession(sessionId) {
  if (confirm('确定要删除这个会话吗？')) {
    try {
    const response = await fetch(`http://${ip}/session/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'token': userStore.token
      }
    })
    
    if (response.ok) {
      // 删除会话并重新排序，确保最新的在最上面
      sessions.value = sessions.value.filter(s => s.id !== sessionId).sort((a, b) => {
        return new Date(b.updated_at) - new Date(a.updated_at)
      })
      if (activeSessionId.value === sessionId) {
        activeSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
        messages.value = []
        if (activeSessionId.value) {
          fetchSessionContent(activeSessionId.value)
        }
      }
    }
  } catch (error) {
    console.error('删除会话失败:', error)
  }
  }
}

// 监听登录状态变化
watch(() => userStore.isLoggedIn, (isLoggedIn) => {
  if (isLoggedIn) {
    fetchSessions()
  }
})

// 组件挂载时获取会话列表
onMounted(() => {
  if (userStore.isLoggedIn) {
    fetchSessions()
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  height: calc(100vh - 50px);
  width: 100%;
}

/* 左侧会话列表 */
.chat-sidebar {
  width: 300px;
  background-color: #f5f5f5;
  border-right: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e0e0e0;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

.create-chat-btn {
  margin: 20px;
  padding: 12px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  transition: background-color 0.3s;
}

.create-chat-btn:hover {
  background-color: #0069d9;
}

.plus-icon {
  font-size: 18px;
  font-weight: bold;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 10px;
}

.session-item {
  padding: 12px 16px;
  margin: 8px 0;
  background-color: white;
  border-radius: 8px;
  cursor: pointer;
  position: relative;
  transition: all 0.3s;
  border: 1px solid #e0e0e0;
}

.session-item:hover {
  background-color: #f0f0f0;
  transform: translateX(4px);
}

.session-item.active {
  background-color: #e3f2fd;
  border-color: #2196f3;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-time {
  font-size: 12px;
  color: #999;
}

.delete-session-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  background: none;
  border: none;
  font-size: 16px;
  color: #999;
  cursor: pointer;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.3s;
}

.delete-session-btn:hover {
  background-color: #ffeeee;
  color: #ff4444;
}

/* 右侧对话界面 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: #fafafa;
}

.chat-content {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  display: flex;
  align-items: flex-start;
  max-width: 70%;
}

.ai-message {
  align-self: flex-start;
}

.user-message {
  align-self: flex-end;
}

.message-content {
  background-color: white;
  padding: 12px 16px;
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.user-message .message-content {
  background-color: #e3f2fd;
}

.message-text {
  font-size: 14px;
  line-height: 1.4;
  margin-bottom: 4px;
}

.message-time {
  font-size: 12px;
  color: #999;
  text-align: right;
}

.loading-message {
  align-self: flex-start;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background-color: white;
  border-radius: 18px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid #f3f3f3;
  border-top: 2px solid #3498db;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 输入框区域 */
.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background-color: white;
  display: flex;
  gap: 12px;
}

.chat-input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;
}

.chat-input:focus {
  border-color: #2196f3;
}

.send-btn {
  padding: 0 24px;
  background-color: #2196f3;
  color: white;
  border: none;
  border-radius: 24px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background-color 0.3s;
}

.send-btn:hover {
  background-color: #1976d2;
}

.send-btn:disabled {
  background-color: #bdbdbd;
  cursor: not-allowed;
}
</style>