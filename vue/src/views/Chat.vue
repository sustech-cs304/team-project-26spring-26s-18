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
            <!-- assistant的消息全部当markdown解析 -->
            <div v-if="message.role === 'assistant'" class="message-markdown" v-html="renderMarkdown(message.content)"></div>
            <!-- 用户文本内容 -->
            <div v-else-if="message.content_type === 'text'" class="message-text">{{ message.content }}</div>
            <!-- 用户图片内容 -->
            <div v-else-if="message.content_type === 'image'" class="message-image">
              <img 
                :src="message.content.replace(/[`]/g, '')" 
                alt="图片"
                class="message-image-img"
                style="max-width: 100px; max-height: 100px; object-fit: contain; border-radius: 8px;"
              />
            </div>
            <!-- 用户PDF内容，仅显示文件名 -->
            <div v-else-if="message.content_type === 'pdf'" class="message-text">
              <span style="color: #1976d2; font-weight: bold;">{{ message.name || '无名PDF文件' }}</span>
            </div>
            <!-- user的Markdown内容 只显示文件名 -->
            <div
              v-else-if="message.content_type === 'markdown' && message.role === 'user'"
              class="message-text"
            >
              <span style="color: #1976d2; font-weight: bold;">{{ message.name || '无名Markdown文件' }}</span>
            </div>
            <!-- 其他类型内容 -->
            <div v-else class="message-text">{{ message.content }}</div>
          </div>
        </div>
        <div v-if="loading" class="loading-message">
          <div class="loading-spinner"></div>
          <span>AI 正在思考...</span>
        </div>
      </div>
      
      <!-- 模式选择区域 -->
      <div class="mode-selector">
        <span class="mode-label">模式选择：</span>
        <div class="mode-options">
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'default' }" 
            @click="selectedMode = 'default'"
          >
            默认模式
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'campus' }" 
            @click="selectedMode = 'campus'"
          >
            校园助手
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'learning' }" 
            @click="selectedMode = 'learning'"
          >
            学习助手
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'recommend' }" 
            @click="selectedMode = 'recommend'"
          >
            推荐模式
          </button>
        </div>
      </div>
      
      <!-- 输入框区域 -->
      <div class="chat-input-area">
        <div class="input-container">
          <input 
            type="text" 
            v-model="inputMessage"
            class="chat-input"
            placeholder="输入消息..."
            @keyup.enter="sendMessage"
          />
          <input 
            type="file" 
            ref="fileInput"
            multiple
            class="file-input"
            @change="handleFileChange"
            style="display: none;"
          />
          <button class="file-btn" @click="triggerFileInput">
            📎
          </button>
        </div>
        <button class="send-btn" @click="sendMessage">发送</button>
      </div>
      <!-- 文件列表 -->
      <div v-if="selectedFiles.length > 0" class="file-list">
        <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
          <span>{{ file.name }}</span>
          <button class="remove-file-btn" @click="removeFile(index)">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import { useUserStore } from '@/stores/user'
import { ip } from '@/config/config'
import { marked } from 'marked'

const userStore = useUserStore()
const sessions = ref([])
const messages = ref([])
const activeSessionId = ref(null)
const inputMessage = ref('')
const loading = ref(false)
const chatContentRef = ref(null)
const fileInput = ref(null)
const selectedFiles = ref([])
const selectedMode = ref('default') // 默认模式
// 解析Markdown文本
function renderMarkdown(mdText) {
  return marked.parse(mdText)
}
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
      console.log('获取会话内容返回：', result)
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
  selectedFiles.value = []
}

// 触发文件选择
function triggerFileInput() {
  fileInput.value.click()
}

// 处理文件选择
function handleFileChange(e) {
  const files = e.target.files
  if (files.length > 0) {
    // 检查文件格式是否一致
    const fileType = files[0].type
    const allSameType = Array.from(files).every(file => file.type === fileType)
    
    if (!allSameType) {
      alert('请上传同一格式的文件')
      return
    }
    
    // 添加文件到列表
    selectedFiles.value = [...selectedFiles.value, ...Array.from(files)]
  }
}

// 移除文件
function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

// 文件转base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1]) // 移除data:image/...;base64,前缀
    reader.onerror = error => reject(error)
    reader.readAsDataURL(file)
  })
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
    
    // 处理文件，转换为base64，并收集文件名
    let filesBase64 = []
    let fileTypes = []
    let fileNames = []
    if (selectedFiles.value.length > 0) {
      filesBase64 = await Promise.all(selectedFiles.value.map(file => fileToBase64(file)))
      fileTypes = selectedFiles.value.map(file => file.type)
      fileNames = selectedFiles.value.map(file => file.name)
    }
    
    // 触发AI回复并获取完整对话
    loading.value = true
    
    // 构建请求数据，增加 file_names 字段
    const requestData = {
      session_id: activeSessionId.value,
      content: messageContent,
      files: filesBase64.length > 0 ? filesBase64 : null,
      file_types: fileTypes.length > 0 ? fileTypes : null,
      file_names: fileNames.length > 0 ? fileNames : null
    }
    
    // 输出实际传输的内容
    console.log('发送给后端的消息数据:', requestData)
    
    // 先添加用户消息到界面
    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: messageContent,
      content_type: 'text',
      created_at: new Date().toISOString()
    }
    messages.value.push(userMessage)
    scrollToBottom()
    
    // 添加一个空的AI消息占位符，用于实时更新内容
    const aiMessageId = Date.now() + 1
    const aiMessage = {
      id: aiMessageId,
      role: 'assistant',
      content: '',
      content_type: 'text',
      created_at: new Date().toISOString()
    }
    messages.value.push(aiMessage)
    scrollToBottom()
    
    try {
      // 根据选择的模式确定接口URL
      let apiUrl = ''
      switch (selectedMode.value) {
        case 'campus':
          apiUrl = `/session/aicontent/stream_less_history_more_rag`
          break
        case 'learning':
          apiUrl = `/session/aicontent/stream_more_history_no_rag`
          break
        case 'recommend':
          apiUrl = `/session/aicontent/stream_recommend`
          break
        default:
          apiUrl = `/session/aicontent/stream`
      }
      
      const aiResponse = await fetch(`http://${ip}${apiUrl}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'token': userStore.token
        },
        body: JSON.stringify(requestData)
      })
      
      if (aiResponse.ok) {
        const reader = aiResponse.body.getReader()
        const decoder = new TextDecoder()
        
        let accumulatedContent = ''
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value, { stream: true })
          accumulatedContent += chunk
          
          // 更新AI消息内容
          const aiMessageIndex = messages.value.findIndex(msg => msg.id === aiMessageId)
          if (aiMessageIndex !== -1) {
            messages.value[aiMessageIndex].content = accumulatedContent
            scrollToBottom()
          }
        }
        
        // 流式传输完成
        console.log('流式传输完成')
        
        // 清空文件列表
        selectedFiles.value = []
      } else {
        console.error('API请求失败:', aiResponse.status)
      }
    } catch (error) {
      console.error('流式请求失败:', error)
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

/* 图片消息 */
.message-image {
  display: inline-block;
  max-width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.message-image-img {
  max-width: 300px;
  max-height: 300px;
  object-fit: contain;
  border-radius: 8px;
  transition: transform 0.2s;
  cursor: pointer;
}

.message-image-img:hover {
  transform: scale(1.02);
}

/* 响应式图片 */
@media (max-width: 768px) {
  .message-image-img {
    max-width: 200px;
    max-height: 200px;
  }
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

/* 模式选择区域 */
.mode-selector {
  padding: 12px 20px;
  border-top: 1px solid #e0e0e0;
  background-color: white;
  display: flex;
  align-items: center;
  gap: 12px;
}

.mode-label {
  font-size: 14px;
  font-weight: 500;
  color: #666;
}

.mode-options {
  display: flex;
  gap: 8px;
}

.mode-btn {
  padding: 6px 12px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  background-color: white;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s;
}

.mode-btn:hover {
  background-color: #f5f5f5;
  border-color: #2196f3;
}

.mode-btn.active {
  background-color: #e3f2fd;
  border-color: #2196f3;
  color: #1976d2;
  font-weight: 500;
}

/* 输入框区域 */
.chat-input-area {
  padding: 20px;
  border-top: 1px solid #e0e0e0;
  background-color: white;
  display: flex;
  gap: 12px;
  align-items: flex-end;
}

.input-container {
  flex: 1;
  display: flex;
  align-items: center;
  position: relative;
}

.chat-input {
  flex: 1;
  padding: 12px 40px 12px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 24px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.3s;
  resize: none;
}

.chat-input:focus {
  border-color: #2196f3;
}

.file-btn {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 5px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.file-btn:hover {
  background-color: #e0e0e0;
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
  height: 44px;
  align-self: center;
}

.send-btn:hover {
  background-color: #1976d2;
}

.send-btn:disabled {
  background-color: #bdbdbd;
  cursor: not-allowed;
}

/* 文件列表 */
.file-list {
  padding: 0 20px 20px;
  background-color: white;
  border-top: 1px solid #e0e0e0;
  max-height: 120px;
  overflow-y: auto;
}

.file-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  margin-bottom: 8px;
  background-color: #e3f2fd;
  border-radius: 16px;
  font-size: 13px;
}

.remove-file-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  color: #666;
  padding: 0 5px;
  border-radius: 50%;
  transition: background-color 0.2s;
}

.remove-file-btn:hover {
  background-color: #bbdefb;
  color: #333;
}
</style>