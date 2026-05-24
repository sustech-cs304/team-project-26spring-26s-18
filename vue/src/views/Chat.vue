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

      <!-- ══ TIS 弹窗 ══ -->
      <div v-if="fmTisDialog" class="fm-tis-overlay">
        <div class="fm-tis-dialog">
          <div class="fm-tis-title">📚 获取课程数据</div>
          <p class="fm-tis-desc">{{ fmTisDialog.message }}</p>
          <template v-if="!fmTisFetching">
            <div class="fm-tis-fields">
              <input v-model="fmTisUsername" class="fm-dir-input" placeholder="SUSTech 学号" />
              <input v-model="fmTisPassword" class="fm-dir-input" type="password" placeholder="密码" />
            </div>
            <div class="fm-tis-actions">
              <button class="fm-btn-primary" @click="fmStartTIS">开始获取</button>
              <button class="fm-btn-cancel" @click="fmCancelTIS">取消整理</button>
            </div>
          </template>
          <template v-else>
            <div class="fm-tis-log" ref="fmTisLogRef">
              <div v-for="(line, i) in fmTisLogs" :key="i" class="fm-tis-line">{{ line }}</div>
            </div>
          </template>
        </div>
      </div>

      <!-- ══ 文件管理模式内容区 ══ -->
      <div v-if="selectedMode === 'files'" class="fm-body">
        <!-- 工作目录栏 -->
        <div class="fm-topbar">
          <span class="fm-label">工作目录</span>
          <input v-model="fmWorkspace" class="fm-dir-input" placeholder="输入工作目录路径" @keyup.enter="fmSetWorkspace" />
          <button class="fm-set-btn" @click="fmSetWorkspace">设置</button>
          <span v-if="fmWorkspaceInfo" class="fm-workspace-meta">{{ fmWorkspaceInfo.name }} · {{ fmWorkspaceInfo.file_count }} 个文件</span>
        </div>

        <!-- 三栏 -->
        <div class="fm-panels">
          <!-- 左列：思维链 + 文件列表 -->
          <div class="fm-left-col">
            <!-- 思维链 -->
            <div class="fm-panel fm-chain-panel">
              <div class="fm-panel-hd">
                🧠 Agent 思维链
                <span v-if="fmRunning" class="fm-dot"></span>
              </div>
              <div class="fm-chain-scroll" ref="fmChainRef">
                <div v-if="fmChain.length === 0" class="fm-empty">执行命令后，Agent 的推理过程会在这里实时显示</div>
                <div v-for="(s, i) in fmChain" :key="i" class="fm-step" :class="`fm-step-${s.type}`">
                  <span class="fm-step-icon">{{ fmStepIcon(s.type) }}</span>
                  <span class="fm-step-body">
                    <template v-if="s.type === 'action'"><b>{{ s.tool }}</b><span class="fm-step-args">{{ fmFormatArgs(s.args) }}</span></template>
                    <template v-else-if="s.type === 'observation'">{{ fmFormatObs(s.result) }}</template>
                    <template v-else-if="s.type === 'thought'">{{ s.content }}</template>
                    <template v-else-if="s.type === 'done'">{{ s.summary }}</template>
                    <template v-else-if="s.type === 'error'">{{ s.message }}</template>
                  </span>
                </div>
              </div>
            </div>

            <!-- 文件列表 / 确认 -->
            <div class="fm-panel fm-files-panel" :class="{ 'fm-panel-warn': fmPending }">
              <div class="fm-panel-hd">
                <span v-if="fmPending">⚠️ 确认{{ fmPending.action === 'delete' ? '删除' : '移动' }} {{ fmPending.files.length }} 个文件</span>
                <span v-else>📄 文件列表 <span v-if="fmFiles.length" class="fm-count">{{ fmFiles.length }} 个</span></span>
              </div>
              <div class="fm-files-scroll">
                <div v-if="!fmPending && fmFiles.length === 0" class="fm-empty">搜索或操作的文件会在这里显示</div>
                <div v-for="(f, i) in fmPending ? fmPending.files : fmFiles" :key="i" class="fm-file-row" :class="{ 'fm-file-danger': fmPending }">
                  <span class="fm-file-icon">{{ fmFileIcon(f.name || f) }}</span>
                  <span class="fm-file-nm">{{ f.name || f }}</span>
                </div>
                <div v-if="fmPending" class="fm-confirm-bar">
                  <button class="fm-btn-danger" @click="fmConfirm(true)">✅ 确认{{ fmPending.action === 'delete' ? '删除' : '移动' }}</button>
                  <button class="fm-btn-cancel" @click="fmConfirm(false)">❌ 取消</button>
                </div>
              </div>
            </div>
          </div>

          <!-- 右列：文件树 -->
          <div class="fm-right-col">
            <div class="fm-panel fm-tree-panel">
              <div class="fm-panel-hd">
                📁 文件资源管理器
                <button class="fm-refresh" @click="fmRefreshTree">↻</button>
              </div>
              <div class="fm-tree-scroll">
                <div v-if="!fmWorkspaceInfo" class="fm-empty">请先设置工作目录</div>
                <el-tree v-else :data="fmTreeData" :props="{ children: 'children', label: 'name' }" node-key="path" default-expand-all :expand-on-click-node="false">
                  <template #default="{ data }">
                    <span class="fm-tree-row">
                      <span>{{ data.type === 'dir' ? '📁' : fmFileIcon(data.name) }}</span>
                      <span class="fm-tree-nm">{{ data.name }}</span>
                      <span v-if="data.type === 'file' && data.size" class="fm-tree-sz">{{ fmFmtSize(data.size) }}</span>
                    </span>
                  </template>
                </el-tree>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ══ 普通聊天内容区 ══ -->
      <div v-else class="chat-content" ref="chatContentRef">
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
      <!-- v-else 结束 -->

      <!-- 模式选择区域 -->
      <div class="mode-selector">
        <span class="mode-label">模式选择：</span>
        <div class="mode-options">
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'default' }" 
            @click="selectMode('default')"
          >
            💬 默认模式
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'campus' }" 
            @click="selectMode('campus')"
          >
            🏫 校园助手
          </button>
          <button 
            class="mode-btn" 
            :class="{ active: selectedMode === 'learning' }" 
            @click="selectMode('learning')"
          >
            📚 学习助手
          </button>
          <button 
            class="mode-btn" 
            type="button"
            title="自动检索知识库与网络资料，在对话中展示相关文件"
            :class="{ active: selectedMode === 'recommend' }" 
            @click="selectMode('recommend')"
          >
            ✨ 推荐模式
          </button>
          <button
            class="mode-btn"
            :class="{ active: selectedMode === 'agent' }"
            @click="selectMode('agent')"
          >
            🤖 Agent模式
          </button>
          <button
            class="mode-btn"
            :class="{ active: selectedMode === 'files' }"
            @click="selectMode('files')"
          >
            🗂️ 文件管理
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
            :placeholder="selectedMode === 'files' ? '输入文件管理命令，如：找到所有区块链相关文件' : '输入消息...'"
            @keyup.enter="selectedMode === 'files' ? fmExecute() : sendMessage()"
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
        <button class="send-btn" @click="selectedMode === 'files' ? fmExecute() : sendMessage()">
          {{ selectedMode === 'files' ? '执行' : '发送' }}
        </button>
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
import { executeCommand, confirmOperation, getFileTree, validateWorkspace, fetchTIS, resumeOrganize } from '@/api/fileManager'
import { ElMessage } from 'element-plus'
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
const CHAT_MODE_STORAGE_KEY = 'selectedChatMode'
const DEFAULT_CHAT_MODE = 'default'
const CHAT_MODE_VALUES = ['default', 'campus', 'learning', 'recommend', 'agent', 'files']

function getSavedChatMode() {
  const savedMode = localStorage.getItem(CHAT_MODE_STORAGE_KEY)
  return CHAT_MODE_VALUES.includes(savedMode) ? savedMode : DEFAULT_CHAT_MODE
}

const selectedMode = ref(getSavedChatMode()) // 默认模式
const loadingResources = ref(false)
const committedSpeechTranscript = ref('')

function selectMode(mode) {
  if (!CHAT_MODE_VALUES.includes(mode)) return
  selectedMode.value = mode
  localStorage.setItem(CHAT_MODE_STORAGE_KEY, mode)
}

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

// 发送消息
async function sendMessage() {
  if (!inputMessage.value.trim()) return

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

// ═══════════════════════════════════════════
// 文件管理模式
// ═══════════════════════════════════════════
const fmWorkspace = ref('D:/file_helper_demo')
const fmWorkspaceInfo = ref(null)
const fmRunning = ref(false)
const fmChain = ref([])
const fmChainRef = ref(null)
const fmFiles = ref([])
const fmPending = ref(null)
const fmTreeData = ref([])

// TIS 相关
const fmTisDialog = ref(null)   // { message, operation_id }
const fmTisUsername = ref('')
const fmTisPassword = ref('')
const fmTisFetching = ref(false)
const fmTisLogs = ref([])
const fmTisLogRef = ref(null)

async function fmSetWorkspace() {
  if (!fmWorkspace.value.trim()) return
  try {
    const res = await validateWorkspace(fmWorkspace.value.trim())
    fmWorkspaceInfo.value = res.data
    ElMessage.success(`已设置工作目录：${res.data.name}`)
    await fmRefreshTree()
  } catch (e) {
    ElMessage.error('目录不存在或无法访问')
  }
}

async function fmRefreshTree() {
  if (!fmWorkspace.value) return
  try {
    const res = await getFileTree(fmWorkspace.value, 3)
    fmTreeData.value = res.data?.children || []
  } catch (_) {}
}

async function fmExecute() {
  const cmd = inputMessage.value.trim()
  if (!cmd || !fmWorkspace.value || fmRunning.value) return
  inputMessage.value = ''
  fmRunning.value = true
  fmChain.value = []
  fmFiles.value = []
  fmPending.value = null

  try {
    await executeCommand(cmd, fmWorkspace.value, fmHandleStep)
  } catch (e) {
    ElMessage.error('执行失败：' + e.message)
  } finally {
    fmRunning.value = false
    await fmRefreshTree()
  }
}

function fmHandleStep(step) {
  const t = step.type
  if (t === 'thought' || t === 'action' || t === 'observation' || t === 'done' || t === 'error') {
    fmChain.value.push(step)
    nextTick(() => {
      if (fmChainRef.value) fmChainRef.value.scrollTop = fmChainRef.value.scrollHeight
    })
    // 从 observation 结果里提取文件列表（search_files 的结果）
    if (t === 'observation' && step.result?.files?.length) {
      const rawFiles = step.result.files
      if (typeof rawFiles[0] === 'string') {
        fmFiles.value = rawFiles.map(p => ({
          name: p.replace(/\\/g, '/').split('/').pop(),
          path: p
        }))
      }
    }
    if (t === 'done' && step.files?.length) fmFiles.value = step.files
    if (t === 'error') ElMessage.error(step.message)
  } else if (t === 'tis_required') {
    fmTisDialog.value = { message: step.message, operation_id: step.operation_id }
    fmTisLogs.value = []
    fmTisFetching.value = false
    fmChain.value.push({ type: 'observation', result: { message: `需要课程数据：弹窗已显示，等待 TIS 登录` } })
    nextTick(() => { if (fmChainRef.value) fmChainRef.value.scrollTop = fmChainRef.value.scrollHeight })
  } else if (t === 'confirm_required') {
    fmPending.value = { operation_id: step.operation_id, action: step.action, files: step.files }
    fmChain.value.push({ type: 'observation', result: { message: `需要确认：${step.action === 'delete' ? '删除' : '移动'} ${step.files.length} 个文件` } })
    nextTick(() => {
      if (fmChainRef.value) fmChainRef.value.scrollTop = fmChainRef.value.scrollHeight
    })
  }
}

async function fmConfirm(confirmed) {
  if (!fmPending.value) return
  const { operation_id, action } = fmPending.value
  fmPending.value = null
  fmFiles.value = []
  try {
    const res = await confirmOperation(operation_id, confirmed)
    if (confirmed) {
      const d = res.data
      let msg = `成功 ${d.success_count} 个`
      if (d.skipped_count) msg += `，跳过 ${d.skipped_count} 个`
      if (d.failed_count) msg += `，失败 ${d.failed_count} 个`
      ElMessage.success(msg)
      fmChain.value.push({ type: 'done', summary: '操作完成：' + msg })
    } else {
      ElMessage.info('已取消')
      fmChain.value.push({ type: 'done', summary: '用户取消了操作' })
    }
    await fmRefreshTree()
  } catch (e) {
    ElMessage.error('操作失败：' + e.message)
  }
}

function fmStepIcon(type) {
  return { thought: '💭', action: '🔧', observation: '✅', done: '🏁', error: '⚠️' }[type] || '·'
}

function fmFormatArgs(args) {
  if (!args) return ''
  const entries = Object.entries(args).filter(([k]) => k !== 'file_paths').map(([k, v]) => {
    if (Array.isArray(v)) return `${k}=[${v.slice(0,3).join(',')}${v.length>3?'...':''}]`
    return `${k}=${v}`
  })
  const fp = args.file_paths ? ` files=${args.file_paths.length}` : ''
  const s = entries.join(', ') + fp
  return s ? ` (${s})` : ''
}

function fmFormatObs(r) {
  if (!r) return ''
  return r.message || (r.count !== undefined ? `找到 ${r.count} 个文件` : (r.success_count !== undefined ? `完成：成功 ${r.success_count}` : JSON.stringify(r).slice(0, 60)))
}

function fmFileIcon(name) {
  if (!name) return '📄'
  const ext = (name.split('.').pop() || '').toLowerCase()
  return ({ pdf:'📕', doc:'📘', docx:'📘', ppt:'📙', pptx:'📙', xls:'📗', xlsx:'📗', jpg:'🖼', jpeg:'🖼', png:'🖼', mp4:'🎬', zip:'📦', py:'🐍', js:'📜' })[ext] || '📄'
}

function fmFmtSize(b) {
  if (b < 1024) return b + 'B'
  if (b < 1048576) return (b/1024).toFixed(1) + 'KB'
  return (b/1048576).toFixed(1) + 'MB'
}

async function fmStartTIS() {
  if (!fmTisUsername.value || !fmTisPassword.value) {
    ElMessage.warning('请输入学号和密码')
    return
  }
  fmTisFetching.value = true
  fmTisLogs.value = []
  const opId = fmTisDialog.value.operation_id

  try {
    await fetchTIS(fmTisUsername.value, fmTisPassword.value, opId, (step) => {
      if (step.type === 'log') {
        // 追加到 TIS 日志（弹窗内）和思维链
        fmTisLogs.value.push(step.message)
        fmChain.value.push({ type: 'thought', content: step.message })
        nextTick(() => {
          if (fmTisLogRef.value) fmTisLogRef.value.scrollTop = fmTisLogRef.value.scrollHeight
          if (fmChainRef.value) fmChainRef.value.scrollTop = fmChainRef.value.scrollHeight
        })
      } else if (step.type === 'tis_done') {
        ElMessage.success(`课程数据获取成功，共 ${step.course_count} 门课程`)
        fmChain.value.push({ type: 'observation', result: { message: `TIS 获取完成，共 ${step.course_count} 门课程，开始整理文件...` } })
      } else if (step.type === 'error') {
        ElMessage.error(step.message)
        fmChain.value.push({ type: 'error', message: step.message })
      }
    })

    // TIS 完成，继续课程整理
    fmTisDialog.value = null
    const res = await resumeOrganize(opId)
    const d = res.data
    const msg = `课程整理完成：成功 ${d.success_count} 个，失败 ${d.failed_count} 个`
    ElMessage.success(msg)
    fmChain.value.push({ type: 'done', summary: msg })
    await fmRefreshTree()
  } catch (e) {
    ElMessage.error('TIS 获取失败：' + e.message)
    fmTisDialog.value = null
  } finally {
    fmTisFetching.value = false
    fmTisUsername.value = ''
    fmTisPassword.value = ''
  }
}

function fmCancelTIS() {
  fmTisDialog.value = null
  fmChain.value.push({ type: 'done', summary: '用户取消了 TIS 获取，整理操作已终止' })
}
</script>

<style scoped>
/* ═══ 文件管理模式样式 ═══ */
.fm-body { display:flex; flex-direction:column; flex:1; overflow:hidden; background:#ecf0f3; position:relative; }
.fm-topbar { display:flex; align-items:center; gap:8px; padding:8px 16px; background:#fff; border-bottom:1px solid #dde1e7; flex-shrink:0; }
.fm-label { font-size:13px; color:#888; }
.fm-dir-input { flex:1; height:34px; padding:0 12px; border:none; border-radius:8px; background:#ecf0f3; box-shadow:inset 2px 2px 4px #d1d9e6,inset -2px -2px 4px #f9f9f9; font-size:13px; outline:none; }
.fm-set-btn { padding:5px 14px; border:none; border-radius:8px; background:#4B70E2; color:#fff; font-size:13px; cursor:pointer; }
.fm-workspace-meta { font-size:12px; color:#4B70E2; white-space:nowrap; }
.fm-panels { display:flex; flex:1; gap:12px; padding:12px; overflow:hidden; }
.fm-left-col { display:flex; flex-direction:column; gap:10px; flex:0 0 55%; min-width:0; overflow:hidden; }
.fm-right-col { flex:1; min-width:0; display:flex; flex-direction:column; }
.fm-panel { background:#ecf0f3; border-radius:12px; box-shadow:5px 5px 10px #d1d9e6,-5px -5px 10px #f9f9f9; display:flex; flex-direction:column; overflow:hidden; }
.fm-panel-hd { padding:8px 12px; font-size:13px; font-weight:600; color:#555; border-bottom:1px solid #dde1e7; display:flex; align-items:center; gap:6px; flex-shrink:0; }
.fm-panel-warn { box-shadow:5px 5px 10px #f0c0bb,-5px -5px 10px #f9f9f9; }
.fm-panel-warn .fm-panel-hd { color:#c0392b; }
.fm-chain-panel { flex:1; min-height:0; }
.fm-chain-scroll { flex:1; overflow-y:auto; padding:8px 12px; display:flex; flex-direction:column; gap:6px; }
.fm-step { display:flex; align-items:flex-start; gap:7px; padding:5px 8px; border-radius:7px; font-size:13px; }
.fm-step-thought { background:rgba(75,112,226,0.06); }
.fm-step-action  { background:rgba(39,174,96,0.06); }
.fm-step-observation { background:rgba(0,0,0,0.03); }
.fm-step-done { background:rgba(75,112,226,0.10); }
.fm-step-error { background:rgba(231,76,60,0.08); }
.fm-step-icon { flex-shrink:0; }
.fm-step-body { color:#444; word-break:break-word; line-height:1.5; }
.fm-step-args { color:#999; font-size:12px; }
.fm-files-panel { flex:0 0 auto; max-height:38%; }
.fm-files-scroll { flex:1; overflow-y:auto; padding:6px 12px; display:flex; flex-direction:column; gap:3px; }
.fm-file-row { display:flex; align-items:center; gap:7px; padding:4px 7px; border-radius:6px; font-size:13px; color:#444; }
.fm-file-row:hover { background:rgba(0,0,0,0.04); }
.fm-file-danger { border-left:3px solid #e74c3c; padding-left:4px; }
.fm-file-icon { flex-shrink:0; }
.fm-file-nm { word-break:break-all; }
.fm-count { color:#4B70E2; font-size:12px; margin-left:4px; }
.fm-confirm-bar { display:flex; gap:10px; padding:8px 0 2px; border-top:1px solid #dde1e7; margin-top:4px; }
.fm-btn-danger { padding:7px 18px; border:none; border-radius:8px; background:#e74c3c; color:#fff; font-size:13px; cursor:pointer; }
.fm-btn-cancel { padding:7px 14px; border:none; border-radius:8px; background:#ecf0f3; color:#555; font-size:13px; cursor:pointer; box-shadow:3px 3px 6px #d1d9e6,-3px -3px 6px #f9f9f9; }
.fm-tree-panel { flex:1; }
.fm-tree-scroll { flex:1; overflow-y:auto; padding:6px; }
.fm-tree-row { display:flex; align-items:center; gap:5px; font-size:13px; }
.fm-tree-nm { color:#333; }
.fm-tree-sz { color:#aaa; font-size:11px; margin-left:3px; }
.fm-empty { color:#b0b6be; font-size:13px; text-align:center; padding:18px 0; }
.fm-dot { width:7px; height:7px; border-radius:50%; background:#4B70E2; animation:fmpulse 1s infinite; margin-left:4px; }
.fm-refresh { margin-left:auto; border:none; background:none; cursor:pointer; font-size:15px; color:#888; padding:0 2px; }
.fm-refresh:hover { color:#4B70E2; }
@keyframes fmpulse { 0%,100%{opacity:1} 50%{opacity:.3} }
.fm-tis-overlay { position:absolute; inset:0; background:rgba(0,0,0,0.35); display:flex; align-items:center; justify-content:center; z-index:100; }
.fm-tis-dialog { background:#ecf0f3; border-radius:14px; box-shadow:8px 8px 20px #c8d0dc,-8px -8px 20px #ffffff; padding:24px; width:420px; max-width:90%; }
.fm-tis-title { font-size:16px; font-weight:700; color:#333; margin-bottom:10px; }
.fm-tis-desc { font-size:13px; color:#666; margin-bottom:16px; line-height:1.6; }
.fm-tis-fields { display:flex; flex-direction:column; gap:10px; margin-bottom:16px; }
.fm-tis-actions { display:flex; gap:10px; }
.fm-btn-primary { padding:8px 20px; border:none; border-radius:8px; background:#4B70E2; color:#fff; font-size:14px; cursor:pointer; }
.fm-tis-log { background:#1e1e2e; border-radius:8px; padding:10px 12px; height:200px; overflow-y:auto; }
.fm-tis-line { font-size:12px; color:#a6e3a1; font-family:monospace; line-height:1.6; }
:deep(.el-tree) { background:transparent; }
:deep(.el-tree-node__content) { height:26px; border-radius:5px; }
:deep(.el-tree-node__content:hover) { background:rgba(75,112,226,0.08); }

/* ═══ 原有样式 ═══ */
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
</style>
