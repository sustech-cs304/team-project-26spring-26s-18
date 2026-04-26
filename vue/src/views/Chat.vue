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
          :class="[
            message.role === 'user' ? 'user-message' : 'ai-message',
            message.content_type === 'recommendation' ? 'recommendation-message' : ''
          ]"
        >
          <div class="message-content">
            <!-- assistant的消息全部当markdown解析 -->
            <div v-if="message.role === 'assistant' && message.content_type === 'text'" class="message-markdown" v-html="renderMarkdown(message.content)"></div>
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
            <!-- 推荐资源消息 - 在对话中展示文件卡片 -->
            <div v-else-if="message.content_type === 'recommendation'" class="recommendation-content">
              <div class="recommendation-header">
                <span class="recommendation-icon">📚</span>
                <span class="recommendation-title">相关学习资料</span>
                <span v-if="message.query_used" class="recommendation-query">检索: {{ message.query_used }}</span>
              </div>

              <!-- 分类文件展示区 -->
              <div class="categorized-files">
                <!-- 课件/教材 -->
                <div v-if="message.lecture?.length" class="file-category">
                  <div class="category-header">
                    <span class="category-icon">📖</span>
                    <span class="category-title">课件 & 教材</span>
                    <span class="category-count">{{ message.lecture.length }}个</span>
                  </div>
                  <div class="file-cards compact">
                    <div v-for="(file, idx) in message.lecture.slice(0, 5)" :key="'lec'+idx" class="file-card compact" :class="{ 'file-not-found': !file.file_exists }">
                      <div class="file-card-header compact">
                        <span class="file-type-icon small" :class="'file-type-' + file.file_type">
                          {{ getFileIcon(file.file_type) }}
                        </span>
                        <span class="file-name" :title="file.source">{{ file.source }}</span>
                        <span class="file-score" title="相关度">{{ (file.score * 100).toFixed(0) }}%</span>
                      </div>
                      <div v-if="file.file_exists" class="file-card-actions compact">
                        <a :href="'http://' + ip + file.download_url" target="_blank" rel="noopener" class="file-action-btn small">
                          📥
                        </a>
                        <a :href="'http://' + ip + file.preview_url" target="_blank" rel="noopener" class="file-action-btn small">
                          👁️
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 实验/习题 -->
                <div v-if="message.exercise?.length" class="file-category">
                  <div class="category-header">
                    <span class="category-icon">📝</span>
                    <span class="category-title">实验 & 习题</span>
                    <span class="category-count">{{ message.exercise.length }}个</span>
                  </div>
                  <div class="file-cards compact">
                    <div v-for="(file, idx) in message.exercise.slice(0, 5)" :key="'ex'+idx" class="file-card compact" :class="{ 'file-not-found': !file.file_exists }">
                      <div class="file-card-header compact">
                        <span class="file-type-icon small" :class="'file-type-' + file.file_type">
                          {{ getFileIcon(file.file_type) }}
                        </span>
                        <span class="file-name" :title="file.source">{{ file.source }}</span>
                        <span class="file-score" title="相关度">{{ (file.score * 100).toFixed(0) }}%</span>
                      </div>
                      <div v-if="file.file_exists" class="file-card-actions compact">
                        <a :href="'http://' + ip + file.download_url" target="_blank" rel="noopener" class="file-action-btn small">
                          📥
                        </a>
                        <a :href="'http://' + ip + file.preview_url" target="_blank" rel="noopener" class="file-action-btn small">
                          👁️
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 参考资料 -->
                <div v-if="message.reference?.length" class="file-category">
                  <div class="category-header">
                    <span class="category-icon">📎</span>
                    <span class="category-title">参考资料</span>
                    <span class="category-count">{{ message.reference.length }}个</span>
                  </div>
                  <div class="file-cards compact">
                    <div v-for="(file, idx) in message.reference.slice(0, 3)" :key="'ref'+idx" class="file-card compact" :class="{ 'file-not-found': !file.file_exists }">
                      <div class="file-card-header compact">
                        <span class="file-type-icon small" :class="'file-type-' + file.file_type">
                          {{ getFileIcon(file.file_type) }}
                        </span>
                        <span class="file-name" :title="file.source">{{ file.source }}</span>
                      </div>
                      <div v-if="file.file_exists" class="file-card-actions compact">
                        <a :href="'http://' + ip + file.download_url" target="_blank" rel="noopener" class="file-action-btn small">
                          📥
                        </a>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 其他文件（兼容模式，显示所有未分类） -->
                <div v-if="message.rag?.length && !message.lecture?.length && !message.exercise?.length && !message.reference?.length" class="file-category">
                  <div class="category-header">
                    <span class="category-icon">📁</span>
                    <span class="category-title">相关文档</span>
                    <span class="category-count">{{ message.rag.length }}个</span>
                  </div>
                  <div class="file-cards compact">
                    <div v-for="(file, idx) in message.rag.slice(0, 5)" :key="'rag'+idx" class="file-card compact" :class="{ 'file-not-found': !file.file_exists }">
                      <div class="file-card-header compact">
                        <span class="file-type-icon small" :class="'file-type-' + file.file_type">
                          {{ getFileIcon(file.file_type) }}
                        </span>
                        <span class="file-name" :title="file.source">{{ file.source }}</span>
                        <span class="file-score" title="相关度">{{ (file.score * 100).toFixed(0) }}%</span>
                      </div>
                      <div v-if="file.file_exists" class="file-card-actions compact">
                        <a :href="'http://' + ip + file.download_url" target="_blank" rel="noopener" class="file-action-btn small">
                          📥
                        </a>
                        <a :href="'http://' + ip + file.preview_url" target="_blank" rel="noopener" class="file-action-btn small">
                          👁️
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MOOC课程推荐 -->
              <div v-if="message.course_resources?.mooc?.length" class="resource-section mooc-section">
                <div class="category-header">
                  <span class="category-icon">🎓</span>
                  <span class="category-title">MOOC课程</span>
                  <span v-if="message.has_course_resources" class="category-badge">匹配课程</span>
                </div>
                <div class="resource-list">
                  <a v-for="(item, idx) in message.course_resources.mooc.slice(0, 4)" :key="'mooc'+idx"
                     :href="item.url" target="_blank" rel="noopener noreferrer"
                     class="resource-item">
                    <span class="resource-icon">🎓</span>
                    <div class="resource-info">
                      <span class="resource-title">{{ item.title }}</span>
                      <span v-if="item.source" class="resource-source">{{ item.source }}</span>
                    </div>
                  </a>
                </div>
              </div>

              <!-- GitHub仓库推荐 -->
              <div v-if="message.course_resources?.github?.length" class="resource-section github-section">
                <div class="category-header">
                  <span class="category-icon">💻</span>
                  <span class="category-title">开源项目 & 代码</span>
                </div>
                <div class="resource-list">
                  <a v-for="(item, idx) in message.course_resources.github.slice(0, 4)" :key="'github'+idx"
                     :href="item.url" target="_blank" rel="noopener noreferrer"
                     class="resource-item">
                    <span class="resource-icon">⭐</span>
                    <div class="resource-info">
                      <span class="resource-title">{{ item.title }}</span>
                      <span v-if="item.stars" class="resource-meta">{{ item.stars }}</span>
                    </div>
                  </a>
                </div>
              </div>

              <!-- 交互式教程 -->
              <div v-if="message.course_resources?.tutorials?.length" class="resource-section tutorial-section">
                <div class="category-header">
                  <span class="category-icon">🎯</span>
                  <span class="category-title">交互式教程 & 工具</span>
                </div>
                <div class="resource-list">
                  <a v-for="(item, idx) in message.course_resources.tutorials.slice(0, 3)" :key="'tutorial'+idx"
                     :href="item.url" target="_blank" rel="noopener noreferrer"
                     class="resource-item">
                    <span class="resource-icon">🎯</span>
                    <div class="resource-info">
                      <span class="resource-title">{{ item.title }}</span>
                      <span v-if="item.desc" class="resource-desc">{{ item.desc }}</span>
                    </div>
                  </a>
                </div>
              </div>

              <!-- 推荐书籍 -->
              <div v-if="message.course_resources?.books?.length" class="resource-section book-section">
                <div class="category-header">
                  <span class="category-icon">📚</span>
                  <span class="category-title">推荐教材</span>
                </div>
                <div class="resource-list">
                  <a v-for="(item, idx) in message.course_resources.books.slice(0, 2)" :key="'book'+idx"
                     :href="item.url" target="_blank" rel="noopener noreferrer"
                     class="resource-item">
                    <span class="resource-icon">📖</span>
                    <div class="resource-info">
                      <span class="resource-title">{{ item.title }}</span>
                      <span v-if="item.desc" class="resource-desc">{{ item.desc }}</span>
                    </div>
                  </a>
                </div>
              </div>

              <!-- 练习平台（通用资源） -->
              <div v-if="message.course_resources?.practice?.length" class="resource-section practice-section">
                <div class="category-header">
                  <span class="category-icon">🏃</span>
                  <span class="category-title">练习平台</span>
                </div>
                <div class="resource-list">
                  <a v-for="(item, idx) in message.course_resources.practice.slice(0, 3)" :key="'practice'+idx"
                     :href="item.url" target="_blank" rel="noopener noreferrer"
                     class="resource-item">
                    <span class="resource-icon">💪</span>
                    <div class="resource-info">
                      <span class="resource-title">{{ item.title }}</span>
                      <span v-if="item.desc" class="resource-desc">{{ item.desc }}</span>
                    </div>
                  </a>
                </div>
              </div>

              <!-- AI 推荐网络资源 -->
              <div v-if="message.web?.length" class="resource-section web-section">
                <div class="category-header">
                  <span class="category-icon">🌐</span>
                  <span class="category-title">推荐学习资源</span>
                </div>
                <div class="web-links">
                  <div v-for="(link, idx) in message.web.slice(0, 3)" :key="'web'+idx" class="web-link-item">
                    <!-- 主链接：尝试直接访问 -->
                    <a :href="link.url" target="_blank" rel="noopener noreferrer" class="web-link-main">
                      <span class="web-link-title">{{ link.title }}</span>
                      <span v-if="link.platform" class="web-link-platform">{{ link.platform }}</span>
                    </a>
                    <!-- 描述 -->
                    <span v-if="link.description" class="web-link-desc">{{ link.description }}</span>
                    <!-- 难度标识和验证标记 -->
                    <span class="web-link-meta">
                      <span class="difficulty-badge" :class="'difficulty-' + link.difficulty">
                        {{ link.difficulty || 'unknown' }}
                      </span>
                      <span v-if="link.url_verified" class="verified-badge" title="链接已通过搜索验证">✓ 已验证</span>
                      <span v-else-if="!link.is_specific_url" class="unverified-badge">AI生成链接</span>
                    </span>
                    <!-- 备用搜索链接（如果不是具体URL） -->
                    <a v-if="link.search_url && !link.is_specific_url"
                       :href="link.search_url"
                       target="_blank" rel="noopener noreferrer"
                       class="web-link-fallback">
                      🔍 搜索该资源
                    </a>
                  </div>
                </div>
              </div>

              <!-- 会话中的链接 -->
              <div v-if="message.session_links?.length" class="session-links-section">
                <div class="category-header">
                  <span class="category-icon">💬</span>
                  <span class="category-title">会话中的资源</span>
                </div>
                <div class="session-links">
                  <a v-for="(link, idx) in message.session_links" :key="'sess'+idx"
                     :href="link.url" target="_blank" rel="noopener noreferrer"
                     class="session-link-item">
                    <span class="link-kind">{{ link.kind === 'image' ? '🖼️' : '🔗' }}</span>
                    <span class="link-title">{{ link.title || link.url }}</span>
                  </a>
                </div>
              </div>

              <!-- 空状态 -->
              <div v-if="!message.rag?.length && !message.web?.length && !message.session_links?.length" class="recommendation-empty">
                未检索到相关资料，可尝试更换关键词或在 RAG 页上传文档。
              </div>
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
            type="button"
            title="自动检索知识库与网络资料，在对话中展示相关文件"
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
const loadingResources = ref(false)

// 文件图标映射
function getFileIcon(fileType) {
  const iconMap = {
    'pdf': '📄',
    'docx': '📝',
    'pptx': '📊',
    'markdown': '📑',
    'text': '📃',
    'unknown': '📎'
  }
  return iconMap[fileType] || '📎'
}

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

    // 清空文件列表
    selectedFiles.value = []

    try {
      // 推荐模式：先获取资源卡片，再请求AI回复
      if (selectedMode.value === 'recommend') {
        console.log('推荐模式：先获取相关资源...')
        await fetchRecommendResources(messageContent)
      }

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
          // 推荐模式使用精简回复接口
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

async function fetchRecommendResources(queryText = '') {
  if (!userStore.isLoggedIn || !userStore.id) {
    alert('请先登录')
    return
  }
  if (!activeSessionId.value) {
    alert('请先选择或创建一个会话')
    return
  }

  const searchQuery = queryText || inputMessage.value.trim()

  loadingResources.value = true
  try {
    const res = await fetch(`http://${ip}/session/recommend/resources`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        token: userStore.token,
      },
      body: JSON.stringify({
        user_id: userStore.id,
        session_id: activeSessionId.value,
        query: searchQuery,
      }),
    })
    const json = await res.json()
    if (json.code !== 1) {
      console.error('检索失败:', json.message)
      return null
    }

    // 智能判断：只有满足以下条件才显示推荐卡片
    const hasContent = json.data.should_show_recommendation ||
                       (json.data.lecture?.length > 0) ||
                       (json.data.exercise?.length > 0) ||
                       (json.data.reference?.length > 0) ||
                       (json.data.web?.length > 0) ||
                       (json.data.session_links?.length > 0) ||
                       json.data.has_course_resources ||
                       (json.data.course_resources?.mooc?.length > 0) ||
                       (json.data.course_resources?.github?.length > 0) ||
                       (json.data.course_resources?.tutorials?.length > 0)

    if (!hasContent) {
      console.log('智能推荐：内容不足，不显示推荐卡片')
      return json.data
    }

    // 将推荐结果作为一条AI消息添加到对话中
    const recommendationMessage = {
      id: Date.now(),
      role: 'assistant',
      content_type: 'recommendation',
      query_used: json.data.query_used,
      // 知识库分类数据
      lecture: json.data.lecture || [],
      exercise: json.data.exercise || [],
      reference: json.data.reference || [],
      other: json.data.other || [],
      // 在线资源
      course_resources: json.data.course_resources || {},
      has_course_resources: json.data.has_course_resources || false,
      course_name: json.data.course_name,
      // 网络资源
      web: json.data.web || [],
      session_links: json.data.session_links || [],
      created_at: new Date().toISOString()
    }

    // 检查是否已存在相同的推荐消息（避免重复）
    const existingIndex = messages.value.findIndex(
      m => m.content_type === 'recommendation' &&
           m.query_used === json.data.query_used &&
           Date.now() - m.id < 60000 // 1分钟内的重复
    )

    if (existingIndex === -1) {
      messages.value.push(recommendationMessage)
      scrollToBottom()
    }

    return json.data
  } catch (e) {
    console.error('推荐请求失败:', e)
    return null
  } finally {
    loadingResources.value = false
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

/* AI回复Markdown样式 */
.message-markdown {
  font-size: 14px;
  line-height: 1.6;
}

.message-markdown :deep(a) {
  color: #1565c0;
  text-decoration: none;
  border-bottom: 1px dashed #1565c0;
  transition: all 0.2s;
  padding: 0 2px;
}

.message-markdown :deep(a:hover) {
  color: #0d47a1;
  border-bottom: 1px solid #0d47a1;
  background: rgba(21, 101, 192, 0.1);
  border-radius: 3px;
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

  .recommendation-content {
    min-width: 300px;
  }

  .categorized-files {
    grid-template-columns: 1fr;
  }
}

/* 资源推荐区域样式 */
.resource-section {
  margin-bottom: 16px;
  padding: 12px;
  background: white;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.resource-section:hover {
  border-color: #2196f3;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.1);
}

.mooc-section {
  background: linear-gradient(135deg, #fff8e1 0%, #fff 100%);
  border-left: 4px solid #ffc107;
}

.github-section {
  background: linear-gradient(135deg, #f3e5f5 0%, #fff 100%);
  border-left: 4px solid #9c27b0;
}

.tutorial-section {
  background: linear-gradient(135deg, #e8f5e9 0%, #fff 100%);
  border-left: 4px solid #4caf50;
}

.book-section {
  background: linear-gradient(135deg, #fff3e0 0%, #fff 100%);
  border-left: 4px solid #ff9800;
}

.practice-section {
  background: linear-gradient(135deg, #e3f2fd 0%, #fff 100%);
  border-left: 4px solid #2196f3;
}

.category-badge {
  font-size: 10px;
  color: #4caf50;
  background: #e8f5e9;
  padding: 2px 8px;
  border-radius: 10px;
  font-weight: 500;
}

.resource-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 8px;
}

.resource-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(255,255,255,0.8);
  border-radius: 6px;
  text-decoration: none;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.resource-item:hover {
  background: white;
  border-color: #e0e0e0;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  transform: translateX(4px);
}

.resource-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.resource-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}

.resource-title {
  font-size: 13px;
  color: #1565c0;
  font-weight: 500;
  line-height: 1.4;
}

.resource-source {
  font-size: 11px;
  color: #666;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 4px;
  align-self: flex-start;
}

.resource-meta {
  font-size: 11px;
  color: #ff9800;
}

.resource-desc {
  font-size: 11px;
  color: #666;
  line-height: 1.3;
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

.recommend-resources-panel {
  padding: 10px 20px 12px;
  background-color: #fafafa;
  border-top: 1px solid #e0e0e0;
  max-height: 220px;
  overflow-y: auto;
}

.recommend-resources-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.recommend-fetch-btn {
  padding: 6px 14px;
  font-size: 13px;
  border-radius: 16px;
  border: 1px solid #1976d2;
  background: #e3f2fd;
  color: #0d47a1;
  cursor: pointer;
  transition: background-color 0.2s, border-color 0.2s;
}

.recommend-fetch-btn:hover:not(:disabled) {
  background: #bbdefb;
}

.recommend-fetch-btn:disabled {
  opacity: 0.65;
  cursor: not-allowed;
}

.recommend-resources-hint {
  font-size: 12px;
  color: #666;
  flex: 1;
  min-width: 200px;
}

.recommend-resources-results {
  font-size: 13px;
  color: #333;
}

.recommend-query-used {
  font-weight: 600;
  margin-bottom: 8px;
  color: #1565c0;
}

.recommend-section {
  margin-bottom: 10px;
}

.recommend-section-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 600;
  color: #444;
}

.recommend-link-list {
  margin: 0;
  padding-left: 18px;
}

.recommend-link-list a {
  color: #1565c0;
  word-break: break-all;
}

.recommend-snippet {
  margin: 4px 0 0;
  font-size: 12px;
  color: #666;
}

.recommend-rag-list {
  margin: 0;
  padding-left: 0;
  list-style: none;
}

.recommend-rag-list li {
  margin-bottom: 8px;
  padding: 8px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}

.recommend-rag-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.recommend-rag-source {
  font-weight: 600;
  word-break: break-all;
}

.recommend-badge {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: #ffecb3;
  color: #f57f17;
}

.recommend-score {
  font-size: 12px;
  color: #888;
}

.recommend-preview {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
  color: #555;
  max-height: 80px;
  overflow: hidden;
}

.recommend-kind {
  font-size: 11px;
  color: #888;
  margin-right: 6px;
}

/* 推荐消息样式 */
.recommendation-message {
  max-width: 90% !important;
}

.recommendation-content {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8ecef 100%);
  border-radius: 12px;
  padding: 16px;
  min-width: 500px;
}

.recommendation-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid #e0e0e0;
}

.recommendation-icon {
  font-size: 20px;
}

.recommendation-title {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}

.recommendation-query {
  font-size: 12px;
  color: #666;
  background: #e3f2fd;
  padding: 2px 8px;
  border-radius: 12px;
  margin-left: auto;
}

/* 分类文件展示 */
.categorized-files {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.file-category {
  background: white;
  border-radius: 8px;
  padding: 10px;
  border: 1px solid #e0e0e0;
}

.category-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f0f0f0;
}

.category-icon {
  font-size: 14px;
}

.category-title {
  font-size: 12px;
  font-weight: 600;
  color: #444;
  flex: 1;
}

.category-count {
  font-size: 11px;
  color: #888;
  background: #f5f5f5;
  padding: 1px 6px;
  border-radius: 8px;
}

/* 紧凑文件卡片 */
.file-cards.compact {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.file-card.compact {
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 8px 10px;
  transition: all 0.15s;
}

.file-card.compact:hover {
  background: white;
  border-color: #2196f3;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.file-card-header.compact {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 0;
}

.file-type-icon.small {
  font-size: 14px;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  border-radius: 4px;
}

.file-card-actions.compact {
  display: flex;
  gap: 4px;
  margin-top: 6px;
  padding-left: 30px;
}

.file-action-btn.small {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
  text-decoration: none;
  background: #e3f2fd;
  color: #1976d2;
}

.file-action-btn.small:hover {
  background: #bbdefb;
}

/* 原有样式保留 */
.file-section,
.web-section,
.session-links-section {
  margin-bottom: 14px;
}

.file-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #555;
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.file-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.file-card {
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  padding: 12px;
  transition: all 0.2s;
}

.file-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  border-color: #2196f3;
}

.file-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.file-type-icon {
  font-size: 20px;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 6px;
}

.file-type-pdf { background: #ffebee; }
.file-type-docx { background: #e3f2fd; }
.file-type-pptx { background: #fff3e0; }
.file-type-markdown { background: #f3e5f5; }
.file-type-text { background: #e8f5e9; }

.file-name {
  flex: 1;
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-score {
  font-size: 11px;
  color: #4caf50;
  background: #e8f5e9;
  padding: 2px 6px;
  border-radius: 10px;
}

.file-card-actions {
  display: flex;
  gap: 8px;
}

.file-action-btn {
  font-size: 12px;
  padding: 6px 12px;
  border-radius: 6px;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  transition: all 0.2s;
}

.download-btn {
  background: #e3f2fd;
  color: #1976d2;
}

.download-btn:hover {
  background: #bbdefb;
}

.preview-btn {
  background: #f5f5f5;
  color: #555;
}

.preview-btn:hover {
  background: #e0e0e0;
}

.web-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.web-link-item {
  display: flex;
  flex-direction: column;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 10px 12px;
  text-decoration: none;
  transition: all 0.2s;
}

.web-link-item:hover {
  border-color: #2196f3;
  background: #fafafa;
}

.web-link-title {
  font-size: 13px;
  color: #1565c0;
  font-weight: 500;
}

.web-link-snippet {
  font-size: 11px;
  color: #666;
  margin-top: 4px;
  line-height: 1.4;
}

/* 增强版网页链接样式 */
.web-link-main {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  margin-bottom: 6px;
}

.web-link-platform {
  font-size: 11px;
  color: #4caf50;
  background: #e8f5e9;
  padding: 2px 8px;
  border-radius: 12px;
  font-weight: 500;
}

.web-link-desc {
  font-size: 12px;
  color: #555;
  line-height: 1.5;
  margin: 4px 0;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.web-link-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
}

.difficulty-badge {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.difficulty-beginner {
  background: #c8e6c9;
  color: #2e7d32;
}

.difficulty-intermediate {
  background: #fff3e0;
  color: #ef6c00;
}

.difficulty-advanced {
  background: #ffcdd2;
  color: #c62828;
}

.source-badge {
  font-size: 10px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.verified-badge {
  font-size: 10px;
  color: #2e7d32;
  background: #c8e6c9;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 500;
}

.unverified-badge {
  font-size: 10px;
  color: #666;
  background: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
}

.web-link-fallback {
  font-size: 11px;
  color: #2196f3;
  text-decoration: none;
  margin-top: 6px;
  padding: 4px 8px;
  background: #e3f2fd;
  border-radius: 4px;
  display: inline-block;
  transition: all 0.2s;
}

.web-link-fallback:hover {
  background: #bbdefb;
}

.session-links {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.session-link-item {
  display: flex;
  align-items: center;
  gap: 8px;
  background: white;
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  padding: 8px 12px;
  text-decoration: none;
  transition: all 0.2s;
}

.session-link-item:hover {
  border-color: #2196f3;
}

.link-kind {
  font-size: 14px;
}

.link-title {
  font-size: 12px;
  color: #1565c0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.recommendation-empty {
  text-align: center;
  padding: 20px;
  color: #888;
  font-size: 13px;
}

/* 文件不存在时的样式 */
.file-card.file-not-found {
  opacity: 0.85;
  background: #fafafa;
  border-style: dashed;
}

.file-missing-badge {
  font-size: 10px;
  color: #999;
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  margin-left: 4px;
}

.file-missing-hint {
  font-size: 11px;
  color: #999;
  font-style: italic;
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