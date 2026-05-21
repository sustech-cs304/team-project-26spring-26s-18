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
      <!-- 文件管理模式：完整的文件管理器界面 -->
      <div v-if="selectedMode === 'file'" class="file-mode-container">
        <!-- 顶部：目录选择栏 -->
        <div class="file-mode-bar">
          <span class="file-mode-label">📁 工作目录：</span>
          <input
            v-model="fileWorkspace"
            class="file-mode-input"
            placeholder="输入目录路径，如 D:\file_helper_demo"
            @keyup.enter="loadTree"
          />
          <button class="file-mode-btn" :disabled="!fileWorkspace.trim() || fileLoading" @click="loadTree">🔄 加载</button>
          <button class="file-mode-btn" :disabled="(!inputMessage.trim() && !filePendingCommand) || fileLoading" @click="sendFileCommand('preview')">📋 预览</button>

          <!-- 待确认状态：显示确认按钮 -->
          <template v-if="filePendingConfirm">
            <button class="file-mode-btn confirm-btn" @click="confirmDangerousOperation">⚠️ 确认执行</button>
            <button class="file-mode-btn" @click="filePendingConfirm = false; filePendingCommand = ''; fileThinkingLogs = []">❌ 取消</button>
          </template>
          <template v-else>
            <button class="file-mode-btn execute" :disabled="(!inputMessage.trim() && !filePendingCommand) || fileLoading" @click="sendFileCommand('execute')">▶ 执行</button>
          </template>
        </div>

        <!-- 主体：左侧输入区 + 右侧文件树 -->
        <div class="file-mode-body">
          <!-- 左侧：输入区 + 思维链 -->
          <div class="file-mode-left">
            <!-- 思维链面板 -->
            <div class="file-thinking-panel" :class="{ 'has-logs': fileThinkingLogs.length > 0 }">
              <div class="file-thinking-header" @click="fileThinkingCollapsed = !fileThinkingCollapsed">
                <span>{{ fileThinkingCollapsed ? '▶' : '▼' }}</span>
                <span class="file-thinking-title">🧠 思考过程</span>
                <span class="file-thinking-count" v-if="fileThinkingLogs.length > 0">{{ fileThinkingLogs.length }} 步</span>
                <span class="file-thinking-count loading" v-if="fileLoading">处理中...</span>
              </div>
              <div v-show="!fileThinkingCollapsed" class="file-thinking-content">
                <div v-if="fileThinkingLogs.length === 0 && !fileLoading" class="thinking-empty">
                  输入指令后，这里将显示执行步骤...
                </div>
                <div v-for="(log, idx) in fileThinkingLogs" :key="idx" class="file-thinking-item" :class="'log-' + log.type">
                  <span class="file-thinking-icon">{{ getLogIcon(log.type) }}</span>
                  <span class="file-thinking-text">{{ log.text }}</span>
                </div>
              </div>

              <!-- 结果面板 -->
              <div v-if="fileResultPanel.length > 0" class="file-result-section">
                <div class="file-result-header" @click="fileResultCollapsed = !fileResultCollapsed">
                  <span>{{ fileResultCollapsed ? '▶' : '▼' }}</span>
                  <span>📊 操作结果</span>
                  <span class="file-thinking-count">{{ fileResultPanel.length }} 项</span>
                </div>
                <div v-show="!fileResultCollapsed" class="file-result-content">
                  <div v-for="(r, idx) in fileResultPanel" :key="idx" class="file-result-item" :class="'result-' + r.status">
                    <span>{{ r.status === 'ok' ? '✅' : r.status === 'fail' ? '❌' : '⚠️' }}</span>
                    <span>{{ r.text }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 右侧：文件树 -->
          <div class="file-mode-right">
            <div class="file-tree-header">
              <span>📁 {{ fileTreePath || '请选择工作目录' }}</span>
              <button class="refresh-btn" @click="loadTree" :disabled="!fileWorkspace.trim()" title="刷新">🔄</button>
            </div>

            <div class="file-tree-content" ref="treeContentRef">
              <div v-if="fileTree.length === 0 && !fileTreeLoading && fileWorkspace.trim()" class="tree-empty">
                暂无文件，请确认目录路径是否正确
              </div>
              <div v-if="fileTreeLoading" class="tree-loading">加载中...</div>
              <div v-for="item in fileTree" :key="item.path" class="tree-node">
                <!-- 文件夹 -->
                <template v-if="item.type === 'dir'">
                  <div class="tree-item tree-dir" @click="toggleDir(item)">
                    <span class="tree-arrow">{{ item.expanded ? '▼' : '▶' }}</span>
                    <span class="tree-icon">📁</span>
                    <span class="tree-name">{{ item.name }}</span>
                    <span v-if="item.children && item.children.length" class="tree-badge">{{ item.children.length }}</span>
                  </div>
                  <!-- 子节点 -->
                  <div v-if="item.expanded && item.children" class="tree-children">
                    <div v-for="child in item.children" :key="child.path" class="tree-node">
                      <div
                        v-if="child.type === 'dir'"
                        class="tree-item tree-dir"
                        :style="{ paddingLeft: '24px' }"
                        @click="toggleDir(child)"
                      >
                        <span class="tree-arrow">{{ child.expanded ? '▼' : '▶' }}</span>
                        <span class="tree-icon">📁</span>
                        <span class="tree-name">{{ child.name }}</span>
                      </div>
                      <div
                        v-else
                        class="tree-item tree-file"
                        :style="{ paddingLeft: '24px' }"
                      >
                        <span class="tree-icon">{{ getFileIconFromName(child.name) }}</span>
                        <span class="tree-name" :title="child.path">{{ child.name }}</span>
                      </div>
                    </div>
                  </div>
                </template>
                <!-- 文件 -->
                <template v-else>
                  <div class="tree-item tree-file">
                    <span class="tree-icon">{{ getFileIconFromName(item.name) }}</span>
                    <span class="tree-name" :title="item.path">{{ item.name }}</span>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 对话内容区域（文件管理模式时隐藏） -->
      <div v-if="selectedMode !== 'file'" class="chat-content" ref="chatContentRef">
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
                  <span v-if="message.web.length > 3" class="category-badge">{{ message.web.length }}条</span>
                </div>
                <div class="web-links" :class="{ 'expanded': isWebExpanded(message.id) }">
                  <div v-for="(link, idx) in getDisplayedWebLinks(message)" :key="'web'+idx" class="web-link-item">
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
                <!-- 展开/收起按钮 -->
                <button 
                  v-if="message.web.length > 3" 
                  @click="toggleWebExpand(message.id)"
                  class="web-expand-btn"
                >
                  {{ isWebExpanded(message.id) ? '🔼 收起' : '🔽 展开更多 (' + (message.web.length - 3) + '条)' }}
                </button>
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
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'agent' }" 
            @click="selectedMode = 'agent'"
          >
            Agent模式
          </button>
          <button 
            class="mode-btn" 
            type="button"
            title="自然语言文件管理：查找、移动、复制、删除、整理文件"
            :class="{ active: selectedMode === 'file' }" 
            @click="selectedMode = 'file'"
          >
            文件管理
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
            :placeholder="selectedMode === 'file' ? '例如：查找所有PDF / 复制文件到44 / 删除期中.pdf' : '输入消息...'"
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
          <button
            v-if="isSpeechSupported"
            class="file-btn speech-btn"
            :class="{ listening: speechListening }"
            type="button"
            :title="speechListening ? '停止语音输入' : '开始语音输入'"
            @click="toggleSpeechRecognition"
          >
            {{ speechListening ? '●' : '🎙️' }}
          </button>
          <button class="file-btn" @click="triggerFileInput">
            📎
          </button>
        </div>
        <button class="send-btn" @click="sendMessage">发送</button>
      </div>
      <div v-if="speechInterimTranscript || speechErrorMessage" class="speech-status" :class="{ error: speechErrorMessage }">
        <span v-if="speechInterimTranscript">正在识别：{{ speechInterimTranscript }}</span>
        <span v-else>{{ speechErrorMessage }}</span>
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
import { useSpeechRecognition } from '@/composables/useSpeechRecognition'

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
const committedSpeechTranscript = ref('')

// 文件管理模式状态
const fileWorkspace = ref(localStorage.getItem('file_workspace') || 'D:\\file_helper_demo')
const fileThinkingLogs = ref([])
const fileThinkingCollapsed = ref(false)
const fileResultPanel = ref([])
const fileResultCollapsed = ref(false)
const fileLoading = ref(false)
const fileCommandMode = ref('execute') // 'execute' | 'preview'
const filePendingConfirm = ref(false) // 是否需要用户确认
const filePendingCommand = ref('') // 待确认的命令

// 文件树相关
const fileTree = ref([])
const fileTreePath = ref('')
const fileTreeLoading = ref(false)
const treeContentRef = ref(null)

// 存储展开了网络资源的 message id
const webExpandedIds = ref(new Set())

const {
  isSupported: isSpeechSupported,
  isListening: speechListening,
  interimTranscript: speechInterimTranscript,
  finalTranscript: speechFinalTranscript,
  errorMessage: speechErrorMessage,
  start: startSpeechRecognition,
  stop: stopSpeechRecognition,
} = useSpeechRecognition()

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

function isSchedulerOnlySession(session) {
  return String(session?.title || '').trim() === '日程优化方案'
}

// 滚动到底部
function scrollToBottom() {
  nextTick(() => {
    if (chatContentRef.value) {
      chatContentRef.value.scrollTop = chatContentRef.value.scrollHeight
    }
  })
}

function appendSpeechText(text) {
  const recognizedText = text.trim()
  if (!recognizedText) return

  const currentText = inputMessage.value.trim()
  inputMessage.value = currentText ? `${currentText} ${recognizedText}` : recognizedText
}

function toggleSpeechRecognition() {
  if (speechListening.value) {
    stopSpeechRecognition()
  } else {
    startSpeechRecognition()
  }
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
      sessions.value = result.data.filter(session => !isSchedulerOnlySession(session)).sort((a, b) => {
        return new Date(b.updated_at) - new Date(a.updated_at)
      })
      console.log(sessions.value)

      const activeSessionVisible = sessions.value.some(session => session.id === activeSessionId.value)
      if (!activeSessionVisible) {
        activeSessionId.value = sessions.value.length > 0 ? sessions.value[0].id : null
        messages.value = []
        if (activeSessionId.value) {
          fetchSessionContent(activeSessionId.value)
        }
      }
    }
  } catch (error) {
    console.error('获取会话列表失败:', error)
  }
}

// 获取会话内容
async function fetchSessionContent(sessionId) {
  if (!sessions.value.some(session => session.id === sessionId)) {
    if (activeSessionId.value === sessionId) {
      activeSessionId.value = null
      messages.value = []
    }
    return
  }

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

// ── 文件管理模式 ──────────────────────────────────────────

// 文件图标映射（用于文件树）
function getFileIconFromName(filename) {
  if (!filename) return '📎'
  const ext = filename.split('.').pop()?.toLowerCase() || ''
  const map = {
    pdf: '📄', docx: '📝', doc: '📝', xlsx: '📊', xls: '📊',
    pptx: '📊', ppt: '📊', txt: '📃', md: '📑', py: '🐍',
    js: '📜', ts: '📜', java: '☕', sql: '🗃️', mp4: '🎬',
    jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', zip: '📦',
    rar: '📦', mp3: '🎵', wav: '🎵', tmp: '📋', log: '📋',
    bin: '📦', pickle: '📦', sqlite3: '🗃️',
  }
  return map[ext] || '📎'
}

// 加载文件树
async function loadTree() {
  if (!fileWorkspace.value.trim()) return
  fileTreeLoading.value = true
  try {
    const resp = await fetch(`/api/files/tree?path=${encodeURIComponent(fileWorkspace.value.trim())}&depth=2`)
    const data = await resp.json()
    if (data.error) {
      fileTree.value = []
      fileTreePath.value = data.error
      return
    }
    fileTree.value = data.tree || []
    fileTreePath.value = data.path || fileWorkspace.value
  } catch (e) {
    fileTree.value = []
    fileTreePath.value = '加载失败：' + e.message
  } finally {
    fileTreeLoading.value = false
  }
}

// 展开/折叠目录
function toggleDir(item) {
  if (!item.children) {
    loadChildren(item)
    return
  }
  item.expanded = !item.expanded
}

// 懒加载子目录
async function loadChildren(item) {
  try {
    const resp = await fetch(`/api/files/list?path=${encodeURIComponent(item.path)}`)
    const data = await resp.json()
    if (data.items) {
      item.children = data.items
      item.expanded = true
    }
  } catch (e) {
    console.error('加载子目录失败', e)
  }
}

function getLogIcon(type) {
  const map = { info: '💡', success: '✅', error: '❌', warn: '⚠️', step: '➡️', thinking: '🤔' }
  return map[type] || '➡️'
}

async function sendFileCommand(mode, confirmed = false) {
  const cmd = inputMessage.value.trim()
  if (!cmd && !filePendingCommand.value) return
  if (!fileWorkspace.value.trim()) return

  const actualCmd = filePendingCommand.value || cmd

  fileLoading.value = true
  fileThinkingLogs.value = []
  fileResultPanel.value = []
  fileThinkingCollapsed.value = false
  fileCommandMode.value = mode

  // 保存 workspace
  localStorage.setItem('file_workspace', fileWorkspace.value.trim())

  try {
    // 始终使用 chat 接口，支持 confirmed 参数
    const resp = await fetch('/api/files/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workspace: fileWorkspace.value.trim(),
        command: actualCmd,
        confirmed: confirmed,  // 是否已确认
      }),
    })

    const data = await resp.json()
    if (data.error) {
      fileThinkingLogs.value.push({ type: 'error', text: `错误：${data.error}` })
      filePendingConfirm.value = false
      filePendingCommand.value = ''
      return
    }

    // 思维链日志
    if (data.logs && Array.isArray(data.logs)) {
      fileThinkingLogs.value = data.logs
    }

    // 检查是否需要确认
    if (data.need_confirm && !confirmed) {
      filePendingConfirm.value = true
      filePendingCommand.value = actualCmd
      // 显示确认提示
      fileThinkingLogs.value.push({ type: 'warn', text: '👆 请仔细核对上方文件列表，确认无误后点击「确认执行」按钮' })
      return
    }

    // 已确认或非危险操作，执行完成
    filePendingConfirm.value = false
    filePendingCommand.value = ''

    // 结果面板
    if (data.result) {
      const r = data.result
      const panel = []
      ;(r.success || []).forEach(item => {
        panel.push({ status: 'ok', text: `${item.path?.split('\\').pop() || item.path} — ${item.info || '成功'}` })
      })
      ;(r.failed || []).forEach(item => {
        panel.push({ status: 'fail', text: `${item.path?.split('\\').pop() || item.path} — ${item.reason || '失败'}` })
      })
      ;(r.skipped || []).forEach(item => {
        panel.push({ status: 'skip', text: `${item.path?.split('\\').pop() || item.path} — ${item.reason || '跳过'}` })
      })
      fileResultPanel.value = panel
    }

    // 执行后刷新文件树
    if (mode === 'execute' || confirmed) {
      loadTree()
    }
  } catch (e) {
    fileThinkingLogs.value.push({ type: 'error', text: `请求失败：${e.message}` })
    filePendingConfirm.value = false
    filePendingCommand.value = ''
  } finally {
    fileLoading.value = false
    if (!filePendingConfirm.value) {
      inputMessage.value = ''
      selectedFiles.value = []
    }
  }
}

// 确认执行危险操作
async function confirmDangerousOperation() {
  if (filePendingCommand.value) {
    await sendFileCommand('execute', true)
  }
}

function buildFileResultText(result, logs) {
  if (!result) return '执行完成，无结果'
  const success = result.success_count || 0
  const failed = result.failed_count || 0
  const skipped = result.skipped_count || 0
  const summary = `✅ 成功 ${success} 个 | ❌ 失败 ${failed} 个 | ⚠️ 跳过 ${skipped} 个`
  return summary
}

async function sendFileCommandEnter() {
  await sendFileCommand('execute')
}

// 发送消息
async function sendMessage() {
  if (!inputMessage.value.trim()) return

  // 文件管理模式走独立逻辑
  if (selectedMode.value === 'file') {
    await sendFileCommandEnter()
    return
  }

  const messageContent = inputMessage.value.trim()
  inputMessage.value = ''

  try {
    // 检查是否是新会话
    if (!activeSessionId.value) {
      // 创建新会话
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

    loading.value = true

    const requestData = {
      session_id: activeSessionId.value,
      content: messageContent,
      files: filesBase64.length > 0 ? filesBase64 : null,
      file_types: fileTypes.length > 0 ? fileTypes : null,
      file_names: fileNames.length > 0 ? fileNames : null
    }

    console.log('发送给后端的消息数据:', requestData)

    // 添加用户消息
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
        case 'agent':
          apiUrl = `/session/aicontent/agent`
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
        messages.value.push({
          id: Date.now(),
          role: 'assistant',
          content: '抱歉，请求失败，请稍后重试。',
          content_type: 'text',
          created_at: new Date().toISOString()
        })
        scrollToBottom()
      }
    } catch (error) {
      console.error('流式请求错误:', error)
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: '网络错误或服务异常，请检查连接后重试。',
        content_type: 'text',
        created_at: new Date().toISOString()
      })
      scrollToBottom()
    } finally {
      loading.value = false
    }
  } catch (error) {
    console.error('发送消息失败:', error)
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

// 网络资源展开/收起控制
function isWebExpanded(messageId) {
  return webExpandedIds.value.has(messageId)
}

function toggleWebExpand(messageId) {
  if (webExpandedIds.value.has(messageId)) {
    webExpandedIds.value.delete(messageId)
  } else {
    webExpandedIds.value.add(messageId)
  }
}

function getDisplayedWebLinks(message) {
  if (!message.web) return []
  const expanded = isWebExpanded(message.id)
  return expanded ? message.web : message.web.slice(0, 3)
}

// 监听模式切换，文件管理模式时自动加载文件树
watch(selectedMode, (mode) => {
  if (mode === 'file' && fileWorkspace.value.trim()) {
    loadTree()
  }
})

// 监听语音识别最终文本并追加到输入框
watch(speechFinalTranscript, (newTranscript) => {
  if (!newTranscript) {
    committedSpeechTranscript.value = ''
    return
  }

  let newText = newTranscript
  if (committedSpeechTranscript.value && newTranscript.startsWith(committedSpeechTranscript.value)) {
    newText = newTranscript.slice(committedSpeechTranscript.value.length)
  }

  appendSpeechText(newText)
  committedSpeechTranscript.value = newTranscript
})

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

/* 文件管理模式样式 */
.file-mode-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: #fff;
  border-top: 1px solid #e0e0e0;
  border-bottom: 1px solid #e0e0e0;
}

.file-mode-label {
  font-size: 13px;
  font-weight: 500;
  color: #555;
  white-space: nowrap;
}

.file-mode-input {
  flex: 1;
  height: 32px;
  padding: 0 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 13px;
  outline: none;
  transition: border-color 0.2s;
}

.file-mode-input:focus {
  border-color: #2196f3;
}

.file-mode-btn {
  height: 32px;
  padding: 0 14px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.file-mode-btn:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: #2196f3;
}

.file-mode-btn.execute {
  background: #e8f5e9;
  border-color: #4caf50;
  color: #2e7d32;
}

.file-mode-btn.execute:hover:not(:disabled) {
  background: #c8e6c9;
}

.file-mode-btn.confirm-btn {
  background: #fff3e0;
  border-color: #ff9800;
  color: #e65100;
  font-weight: 600;
  animation: confirm-pulse 1.5s infinite;
}

.file-mode-btn.confirm-btn:hover:not(:disabled) {
  background: #ffe0b2;
}

@keyframes confirm-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 152, 0, 0.4); }
  50% { box-shadow: 0 0 0 6px rgba(255, 152, 0, 0); }
}

.file-mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 文件管理思维链面板 */
.file-thinking-panel {
  max-height: 45vh;
  overflow-y: auto;
  background: #fafafa;
  border-top: 1px solid #e0e0e0;
  border-bottom: 1px solid #e0e0e0;
}

.file-thinking-header, .file-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  background: #f0f0f0;
  transition: background 0.2s;
}

.file-thinking-header:hover, .file-result-header:hover {
  background: #e0e0e0;
}

.file-thinking-title {
  flex: 1;
}

.file-thinking-count {
  font-size: 11px;
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 10px;
}

.file-thinking-content, .file-result-content {
  padding: 10px 20px;
}

.file-thinking-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
  font-size: 13px;
  line-height: 1.5;
}

.file-thinking-icon {
  flex-shrink: 0;
  width: 18px;
  text-align: center;
}

.file-thinking-text {
  flex: 1;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-info .file-thinking-text   { color: #1565c0; }
.log-success .file-thinking-text { color: #2e7d32; }
.log-error .file-thinking-text   { color: #d32f2f; }
.log-warn .file-thinking-text    { color: #e65100; }
.log-thinking .file-thinking-text { color: #7b1fa2; font-style: italic; }
.log-loading .file-thinking-text { color: #888; animation: pulse 1.2s infinite; }

.file-result-section {
  border-top: 1px solid #e0e0e0;
}

.file-result-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}

.result-ok   { color: #2e7d32; }
.result-fail { color: #d32f2f; }
.result-skip { color: #e65100; }

/* 模式按钮文件管理模式激活态 */
.mode-btn.active {
  background-color: #e3f2fd;
  border-color: #2196f3;
  color: #1976d2;
  font-weight: 500;
}

.mode-btn.active[title*="文件管理"] {
  background-color: #fff3e0;
  border-color: #ff9800;
  color: #e65100;
}

/* 文件管理模式的消息气泡 */
.file-mode-message {
  background: linear-gradient(135deg, #fff8e1 0%, #fffde7 100%) !important;
  border-left: 4px solid #ff9800 !important;
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

/* 展开/收起按钮 */
.web-expand-btn {
  width: 100%;
  margin-top: 12px;
  padding: 8px 16px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  color: #666;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.web-expand-btn:hover {
  background: #eeeeee;
  border-color: #bdbdbd;
  color: #333;
}

/* 网络资源区域展开后的最大高度限制（可选滚动） */
.web-links {
  max-height: 400px;
  overflow-y: auto;
}

.web-links.expanded {
  max-height: 600px;
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
  padding: 12px 80px 12px 16px;
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

.speech-btn {
  right: 44px;
}

.speech-btn.listening {
  color: #d32f2f;
  background-color: #ffebee;
}

.speech-status {
  padding: 0 20px 10px;
  background-color: white;
  color: #666;
  font-size: 13px;
  line-height: 1.4;
}

.speech-status.error {
  color: #d32f2f;
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


/* ===== 新增：思考过程消息样式 ===== */
.thought-message {
  align-self: flex-start;
  max-width: 85%;
}

.thought-message .message-content {
  background-color: #f5f7fa;
  color: #6b7a8f;
  font-style: italic;
  border-left: 3px solid #a0b3cc;
  padding: 10px 14px;
  border-radius: 12px;
  box-shadow: none;
  font-size: 13px;
}

.thought-message .message-content::before {
  content: "💭 ";
  opacity: 0.7;
}

/* ===== 文件管理模式样式 ===== */
.file-mode-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fafafa;
}

/* 顶部：目录选择栏 */
.file-mode-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 20px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.file-mode-label {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  white-space: nowrap;
}

.file-mode-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.file-mode-input:focus {
  border-color: #2196f3;
}

.file-mode-btn {
  height: 36px;
  padding: 0 14px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.file-mode-btn:hover:not(:disabled) {
  background: #e3f2fd;
  border-color: #2196f3;
}

.file-mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-mode-btn.execute {
  background: #e8f5e9;
  border-color: #4caf50;
  color: #2e7d32;
}

.file-mode-btn.execute:hover:not(:disabled) {
  background: #c8e6c9;
}

/* 主体：左侧 + 右侧 */
.file-mode-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* 左侧：思维链面板 */
.file-mode-left {
  flex: 65;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  overflow: hidden;
}

.file-thinking-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  margin: 12px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.file-thinking-panel.has-logs {
  flex: 1;
}

.file-thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  font-weight: 500;
  color: #555;
  background: #fafafa;
  border-radius: 12px 12px 0 0;
  transition: background 0.2s;
}

.file-thinking-header:hover {
  background: #f0f0f0;
}

.file-thinking-title {
  flex: 1;
}

.file-thinking-count {
  font-size: 11px;
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 10px;
}

.file-thinking-count.loading {
  background: #fff3e0;
  color: #e65100;
}

.file-thinking-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px 16px;
}

.thinking-empty {
  color: #aaa;
  font-size: 13px;
  text-align: center;
  margin-top: 20px;
}

.file-thinking-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.file-thinking-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.file-thinking-text {
  flex: 1;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-info .file-thinking-text { color: #1565c0; }
.log-success .file-thinking-text { color: #2e7d32; }
.log-error .file-thinking-text { color: #d32f2f; }
.log-warn .file-thinking-text { color: #e65100; }
.log-thinking .file-thinking-text { color: #7b1fa2; font-style: italic; }
.log-loading .file-thinking-text { color: #888; animation: pulse 1.2s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 结果面板 */
.file-result-section {
  border-top: 1px solid #e0e0e0;
  max-height: 40vh;
  display: flex;
  flex-direction: column;
}

.file-result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: #555;
  background: #fafafa;
  transition: background 0.2s;
}

.file-result-header:hover {
  background: #f0f0f0;
}

.file-result-content {
  overflow-y: auto;
  padding: 8px 16px 12px;
}

.file-result-item {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 13px;
  padding: 4px 0;
  border-bottom: 1px solid #f5f5f5;
}

.result-ok { color: #2e7d32; }
.result-fail { color: #d32f2f; }
.result-skip { color: #e65100; }

/* 右侧：文件树 */
.file-mode-right {
  flex: 35;
  display: flex;
  flex-direction: column;
  background: #fff;
  overflow: hidden;
}

.file-tree-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: #fafafa;
  border-bottom: 1px solid #e0e0e0;
  font-size: 13px;
  font-weight: 500;
  color: #555;
}

.refresh-btn {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.refresh-btn:hover:not(:disabled) {
  background: #e0e0e0;
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.file-tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.tree-empty, .tree-loading {
  color: #aaa;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.tree-node {
  width: 100%;
}

.tree-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 5px 8px;
  cursor: default;
  font-size: 13px;
  border-radius: 4px;
  transition: background 0.15s;
  min-height: 30px;
}

.tree-dir {
  cursor: pointer;
}

.tree-dir:hover {
  background: #f5f5f5;
}

.tree-file:hover {
  background: #fafafa;
}

.tree-arrow {
  font-size: 10px;
  color: #aaa;
  width: 12px;
  flex-shrink: 0;
}

.tree-icon {
  font-size: 14px;
  flex-shrink: 0;
}

.tree-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #333;
}

.tree-dir .tree-name {
  font-weight: 500;
}

.tree-badge {
  font-size: 10px;
  background: #e3f2fd;
  color: #1976d2;
  padding: 1px 6px;
  border-radius: 8px;
  flex-shrink: 0;
}
</style>
