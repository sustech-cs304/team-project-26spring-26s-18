<template>
  <div class="files-container">
    <!-- 顶部：目录选择栏 -->
    <div class="workspace-bar">
      <span class="ws-label">📁 工作目录：</span>
      <input
        v-model="workspace"
        class="ws-input"
        placeholder="请输入目录路径，如 D:\file_helper_demo"
        @keyup.enter="loadTree"
      />
      <button class="ws-btn" @click="loadTree" :disabled="!workspace.trim()">
        🔄 加载
      </button>
    </div>

    <!-- 主体：输入区 + 文件树 + 结果面板 -->
    <div class="files-body">
      <!-- 左侧：输入区 + 思考过程 -->
      <div class="files-left">
        <!-- 自然语言输入区 -->
        <div class="input-section">
          <div v-if="selectedFiles.length > 0" class="file-list">
            <div v-for="(file, index) in selectedFiles" :key="index" class="file-item">
              <span>📎 {{ file.name }}</span>
              <button class="remove-file-btn" @click="removeFile(index)">×</button>
            </div>
          </div>

          <div class="input-row">
            <input type="file" ref="fileInput" multiple class="file-input-hidden" @change="handleFileChange" />
            <button class="icon-btn" @click="triggerFileInput" title="附加文件">📎</button>
            <input
              v-model="inputMessage"
              class="chat-input"
              placeholder="例如：把所有PDF按课程归类 / 找出大于100MB的视频"
              @keyup.enter="handleSend('execute')"
            />
          </div>

          <div class="action-row">
            <button class="mode-btn execute-btn" :disabled="!canSend" @click="handleSend('execute')">
              ▶ 执行
            </button>
            <button class="mode-btn preview-btn" :disabled="!canSend" @click="handleSend('preview')">
              📋 预览
            </button>
          </div>
        </div>

        <!-- 思考过程面板 -->
        <div class="thinking-panel">
          <div class="thinking-header" @click="thinkingCollapsed = !thinkingCollapsed">
            <span>{{ thinkingCollapsed ? '▶' : '▼' }}</span>
            <span class="thinking-title">执行过程</span>
            <span v-if="thinkingLogs.length > 0" class="thinking-count">{{ thinkingLogs.length }} 步</span>
          </div>

          <div v-show="!thinkingCollapsed" class="thinking-content">
            <div v-if="thinkingLogs.length === 0 && !loading" class="thinking-empty">
              发送命令后，这里将显示执行步骤...
            </div>
            <div v-for="(log, idx) in thinkingLogs" :key="idx" class="thinking-log-item" :class="'log-' + log.type">
              <span class="log-icon">{{ getLogIcon(log.type) }}</span>
              <span class="log-text">{{ log.text }}</span>
            </div>
            <div v-if="loading" class="thinking-log-item log-loading">
              <span class="log-icon">⏳</span>
              <span class="log-text">处理中...</span>
            </div>
          </div>
        </div>

        <!-- 结果面板（与思考过程并列） -->
        <div class="result-panel" v-if="resultPanel.length > 0">
          <div class="result-header" @click="resultCollapsed = !resultCollapsed">
            <span>{{ resultCollapsed ? '▶' : '▼' }}</span>
            <span>📊 操作结果</span>
            <span class="thinking-count">{{ resultPanel.length }} 项</span>
          </div>
          <div v-show="!resultCollapsed" class="result-content">
            <div v-for="(r, idx) in resultPanel" :key="idx" class="result-item" :class="'result-' + r.status">
              <span>{{ r.status === 'ok' ? '✅' : r.status === 'fail' ? '❌' : '⚠️' }}</span>
              <span>{{ r.text }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：文件树 + 结果面板 -->
      <div class="files-right">
        <!-- 文件树 -->
        <div class="file-tree-header">
          <span>📁 {{ treePath || '请先选择工作目录' }}</span>
          <button class="refresh-btn" @click="loadTree" :disabled="!workspace.trim()" title="刷新">🔄</button>
        </div>

        <div class="file-tree-content" ref="treeContent">
          <div v-if="tree.length === 0 && !treeLoading" class="tree-empty">
            暂无文件，请确认目录路径是否正确
          </div>
          <div v-if="treeLoading" class="tree-loading">加载中...</div>
          <div v-for="item in tree" :key="item.path" class="tree-node">
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
                    <span class="tree-icon">{{ getFileIcon(child.name) }}</span>
                    <span class="tree-name">{{ child.name }}</span>
                  </div>
                </div>
              </div>
            </template>
            <!-- 文件 -->
            <template v-else>
              <div class="tree-item tree-file">
                <span class="tree-icon">{{ getFileIcon(item.name) }}</span>
                <span class="tree-name" :title="item.path">{{ item.name }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
// const API_BASE = `http://${ip}:5000/api/files`
const API_BASE = `/api/files`

// ── 工作目录 ──────────────────────────────────────
const workspace = ref('D:\\file_helper_demo')
const tree = ref([])
const treePath = ref('')
const treeLoading = ref(false)

// ── 输入相关 ──────────────────────────────────────
const inputMessage = ref('')
const fileInput = ref(null)
const selectedFiles = ref([])
const loading = ref(false)
const canSend = computed(() => inputMessage.value.trim() && !loading.value)

function triggerFileInput() {
  fileInput.value.click()
}

function handleFileChange(e) {
  const files = e.target.files
  if (files.length > 0) {
    selectedFiles.value = [...selectedFiles.value, ...Array.from(files)]
  }
  e.target.value = ''
}

function removeFile(index) {
  selectedFiles.value.splice(index, 1)
}

// ── 思考过程日志 ────────────────────────────────────
const thinkingLogs = ref([])
const thinkingCollapsed = ref(false)

function getLogIcon(type) {
  const map = { info: '💡', success: '✅', error: '❌', warn: '⚠️', step: '➡️' }
  return map[type] || '➡️'
}

// ── 结果面板 ──────────────────────────────────────
const resultPanel = ref([])
const resultCollapsed = ref(false)

// ── API 调用 ─────────────────────────────────────

async function handleSend(mode) {
  const cmd = inputMessage.value.trim()
  if (!cmd || !workspace.value.trim()) return

  loading.value = true
  thinkingLogs.value = []
  resultPanel.value = []
  thinkingCollapsed.value = false

  try {
    const isPreview = mode === 'preview'
    // 执行模式用 SSE 流式推送，预览模式用普通请求
    if (!isPreview) {
      // ===== 流式 SSE =====
      const url = `${API_BASE}/chat_stream`
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: workspace.value.trim(),
          command: cmd,
        }),
      })

      if (!resp.ok) {
        thinkingLogs.value.push({ type: 'error', text: `请求失败：${resp.status}` })
        return
      }

      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = 'log'  // 默认事件类型

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() // 保留不完整的行

        let dataLine = null

        for (const line of lines) {
          const trimmed = line.trim()
          if (trimmed.startsWith('event: ')) {
            currentEvent = trimmed.slice(7).trim()
          } else if (trimmed.startsWith('data: ')) {
            dataLine = trimmed.slice(6).trim()
          } else if (trimmed === '' && dataLine !== null) {
            // 空行表示一个事件结束，处理 data
            try {
              const event = JSON.parse(dataLine)

              if (currentEvent === 'log') {
                // 每个日志事件都追加到思考过程（实时）
                thinkingLogs.value.push(event)
              } else if (currentEvent === 'done') {
                // 执行完成，更新结果面板
                const r = event
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
                resultPanel.value = panel
              }
            } catch (e) {
              // 忽略解析错误
            }
            dataLine = null
            currentEvent = 'log'
          }
        }
      }

      // 完成后刷新文件树
      loadTree()
    } else {
      // ===== 预览模式（普通请求）=====
      const url = `${API_BASE}/preview`
      const resp = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace: workspace.value.trim(),
          command: cmd,
        }),
      })

      const data = await resp.json()
      if (data.error) {
        thinkingLogs.value.push({ type: 'error', text: `错误：${data.error}` })
        return
      }

      if (data.logs && Array.isArray(data.logs)) {
        thinkingLogs.value = data.logs
      }
    }
  } catch (e) {
    thinkingLogs.value.push({ type: 'error', text: `请求失败：${e.message}` })
  } finally {
    loading.value = false
    inputMessage.value = ''
    selectedFiles.value = []
  }
}

async function loadTree() {
  if (!workspace.value.trim()) return
  treeLoading.value = true
  try {
    const resp = await fetch(`${API_BASE}/tree?path=${encodeURIComponent(workspace.value.trim())}&depth=2`)
    const data = await resp.json()
    if (data.error) {
      tree.value = []
      treePath.value = data.error
      return
    }
    tree.value = data.tree || []
    treePath.value = data.path || workspace.value
  } catch (e) {
    tree.value = []
    treePath.value = '加载失败：' + e.message
  } finally {
    treeLoading.value = false
  }
}

function toggleDir(item) {
  if (!item.children) {
    // 懒加载子目录（调用 /api/files/list）
    loadChildren(item)
    return
  }
  item.expanded = !item.expanded
}

async function loadChildren(item) {
  try {
    const resp = await fetch(`${API_BASE}/list?path=${encodeURIComponent(item.path)}`)
    const data = await resp.json()
    if (data.items) {
      item.children = data.items
      item.expanded = true
    }
  } catch (e) {
    console.error('加载子目录失败', e)
  }
}

function getFileIcon(filename) {
  const ext = filename.split('.').pop().toLowerCase()
  const map = {
    pdf: '📄', docx: '📝', doc: '📝', xlsx: '📊', xls: '📊',
    pptx: '📊', ppt: '📊', txt: '📃', md: '📑', py: '🐍',
    js: '📜', ts: '📜', java: '☕', sql: '🗃️', mp4: '🎬',
    jpg: '🖼️', jpeg: '🖼️', png: '🖼️', gif: '🖼️', zip: '📦',
    rar: '📦', mp3: '🎵', wav: '🎵',
  }
  return map[ext] || '📎'
}

onMounted(() => {
  loadTree()
})
</script>

<style scoped>
/* ── 整体布局 ─────────────────────────────────── */
.files-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 50px);
  background: #fafafa;
}

/* ── 工作目录选择栏 ───────────────────────────── */
.workspace-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.ws-label {
  font-size: 14px;
  font-weight: 500;
  color: #555;
  white-space: nowrap;
}

.ws-input {
  flex: 1;
  height: 34px;
  padding: 0 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.ws-input:focus {
  border-color: #2196f3;
}

.ws-btn {
  height: 34px;
  padding: 0 16px;
  background: #2196f3;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.ws-btn:hover:not(:disabled) {
  background: #1976d2;
}

.ws-btn:disabled {
  background: #bdbdbd;
  cursor: not-allowed;
}

/* ── 主体 ──────────────────────────────────────── */
.files-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* ── 左侧区域 ──────────────────────────────────── */
.files-left {
  flex: 65;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e0e0e0;
  overflow: hidden;
}

/* ── 输入区 ───────────────────────────────────── */
.input-section {
  flex-shrink: 0;
  padding: 16px 20px;
  background: #fff;
  border-bottom: 1px solid #e0e0e0;
}

.file-list {
  margin-bottom: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.file-item {
  display: flex;
  align-items: center;
  gap: 6px;
  background: #e3f2fd;
  border-radius: 8px;
  padding: 4px 10px;
  font-size: 13px;
  color: #1565c0;
}

.remove-file-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 16px;
  cursor: pointer;
  line-height: 1;
  padding: 0;
}

.remove-file-btn:hover {
  color: #d32f2f;
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.file-input-hidden {
  display: none;
}

.icon-btn {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s;
}

.icon-btn:hover {
  background: #e3f2fd;
  border-color: #2196f3;
}

.chat-input {
  flex: 1;
  height: 36px;
  padding: 0 14px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.chat-input:focus {
  border-color: #2196f3;
}

.action-row {
  display: flex;
  gap: 8px;
}

.mode-btn {
  padding: 6px 16px;
  border: 1px solid #e0e0e0;
  border-radius: 16px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn:hover:not(:disabled) {
  background: #f5f5f5;
  border-color: #2196f3;
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.execute-btn:hover:not(:disabled) {
  background: #e8f5e9;
  border-color: #4caf50;
  color: #2e7d32;
}

.preview-btn:hover:not(:disabled) {
  background: #fff3e0;
  border-color: #ff9800;
  color: #e65100;
}

/* ── 思考过程面板 ───────────────────────────────── */
.thinking-panel {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  margin: 12px 12px 6px 12px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.thinking-header {
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

.thinking-header:hover {
  background: #f0f0f0;
}

.thinking-title {
  flex: 1;
}

.thinking-count {
  font-size: 11px;
  background: #e3f2fd;
  color: #1976d2;
  padding: 2px 8px;
  border-radius: 10px;
}

.thinking-content {
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

.thinking-log-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.log-icon {
  flex-shrink: 0;
  width: 20px;
  text-align: center;
}

.log-text {
  flex: 1;
  color: #333;
  white-space: pre-wrap;
  word-break: break-word;
}

.log-info .log-text  { color: #1565c0; }
.log-success .log-text { color: #2e7d32; }
.log-error .log-text  { color: #d32f2f; }
.log-warn .log-text  { color: #e65100; }
.log-thinking .log-text { color: #7b1fa2; font-style: italic; }
.log-loading .log-text { color: #888; animation: pulse 1.2s infinite; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* ── 右侧：文件树 + 结果面板 ─────────────── */
.files-right {
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
  border-radius: 0 12px 0 0;
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

.tree-children {
  /* 子节点缩进由 paddingLeft 控制 */
}

/* ── 结果面板（与思考过程并列）──────────────────── */
.result-panel {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #fff;
  margin: 6px 12px 12px 12px;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
}

.result-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
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

.result-header:hover {
  background: #f0f0f0;
}

.result-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 16px 12px;
}

.result-item {
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
</style>
