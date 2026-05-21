<template>
  <div class="fm-container">
    <!-- ══ 顶部输入栏 ══ -->
    <div class="fm-topbar">
      <div class="fm-workspace-row">
        <span class="fm-label">工作目录</span>
        <input
          v-model="workspace"
          class="fm-input"
          placeholder="输入工作目录路径，如 D:/file_helper_demo"
          @keyup.enter="handleSetWorkspace"
        />
        <button class="fm-btn-secondary" @click="handleSetWorkspace">设置</button>
        <span v-if="workspaceInfo" class="fm-workspace-info">
          {{ workspaceInfo.name }} · {{ workspaceInfo.file_count }} 个文件
        </span>
      </div>
      <div class="fm-command-row">
        <span class="fm-label">命令</span>
        <input
          v-model="command"
          class="fm-input"
          placeholder="输入自然语言命令，如：找到所有区块链相关文件"
          @keyup.enter="handleExecute"
          :disabled="isRunning"
        />
        <button
          class="fm-btn-primary"
          @click="handleExecute"
          :disabled="isRunning || !workspace || !command"
        >
          {{ isRunning ? '执行中...' : '执行' }}
        </button>
        <button class="fm-btn-secondary" @click="handleClear">清空</button>
      </div>
    </div>

    <!-- ══ 主体三栏 ══ -->
    <div class="fm-body">
      <!-- 左列：思维链 + 文件列表 -->
      <div class="fm-left">
        <!-- 思维链 panel -->
        <div class="fm-panel fm-chain-panel">
          <div class="fm-panel-title">
            🧠 Agent 思维链
            <span v-if="isRunning" class="fm-running-dot"></span>
          </div>
          <div class="fm-chain-content" ref="chainRef">
            <div v-if="chainSteps.length === 0" class="fm-empty-tip">
              执行命令后，Agent 的推理过程会在这里实时显示
            </div>
            <div
              v-for="(step, i) in chainSteps"
              :key="i"
              class="fm-chain-step"
              :class="`fm-step-${step.type}`"
            >
              <!-- 思考 -->
              <template v-if="step.type === 'thought'">
                <span class="fm-step-icon">💭</span>
                <span class="fm-step-text">{{ step.content }}</span>
              </template>
              <!-- 工具调用 -->
              <template v-else-if="step.type === 'action'">
                <span class="fm-step-icon">🔧</span>
                <span class="fm-step-text">
                  <b>{{ step.tool }}</b>
                  <span class="fm-step-args">{{ formatArgs(step.args) }}</span>
                </span>
              </template>
              <!-- 观察结果 -->
              <template v-else-if="step.type === 'observation'">
                <span class="fm-step-icon">{{ step.result?.success === false ? '❌' : '✅' }}</span>
                <span class="fm-step-text">{{ formatObservation(step.result) }}</span>
              </template>
              <!-- 完成 -->
              <template v-else-if="step.type === 'done'">
                <span class="fm-step-icon">🏁</span>
                <span class="fm-step-text fm-step-done">{{ step.summary }}</span>
              </template>
              <!-- 错误 -->
              <template v-else-if="step.type === 'error'">
                <span class="fm-step-icon">⚠️</span>
                <span class="fm-step-text fm-step-error">{{ step.message }}</span>
              </template>
            </div>
          </div>
        </div>

        <!-- 文件列表 panel -->
        <div class="fm-panel fm-files-panel" :class="{ 'fm-panel-warning': pendingConfirm }">
          <div class="fm-panel-title">
            <span v-if="pendingConfirm">
              ⚠️ 确认{{ pendingConfirm.action === 'delete' ? '删除' : '移动' }}
              {{ pendingConfirm.files.length }} 个文件
            </span>
            <span v-else>📄 文件列表</span>
          </div>

          <div class="fm-files-content">
            <div v-if="fileList.length === 0 && !pendingConfirm" class="fm-empty-tip">
              搜索或操作结果会在这里显示
            </div>

            <!-- 文件条目 -->
            <div
              v-for="(file, i) in displayFiles"
              :key="i"
              class="fm-file-item"
              :class="{ 'fm-file-danger': pendingConfirm }"
            >
              <span class="fm-file-icon">{{ getFileIcon(file.name || file) }}</span>
              <span class="fm-file-name">{{ file.name || file }}</span>
            </div>

            <!-- 确认按钮 -->
            <div v-if="pendingConfirm" class="fm-confirm-bar">
              <button class="fm-btn-danger" @click="handleConfirm(true)">
                ✅ 确认{{ pendingConfirm.action === 'delete' ? '删除' : '移动' }}
              </button>
              <button class="fm-btn-secondary" @click="handleConfirm(false)">
                ❌ 取消
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右列：文件树 -->
      <div class="fm-right">
        <div class="fm-panel fm-tree-panel">
          <div class="fm-panel-title">
            📁 文件资源管理器
            <button class="fm-refresh-btn" @click="refreshTree" title="刷新">↻</button>
          </div>
          <div class="fm-tree-content">
            <div v-if="!workspaceInfo" class="fm-empty-tip">
              请先设置工作目录
            </div>
            <el-tree
              v-else
              :data="treeData"
              :props="treeProps"
              node-key="path"
              default-expand-all
              :expand-on-click-node="false"
            >
              <template #default="{ node, data }">
                <span class="fm-tree-node">
                  <span class="fm-tree-icon">{{ data.type === 'dir' ? '📁' : getFileIcon(data.name) }}</span>
                  <span class="fm-tree-name">{{ data.name }}</span>
                  <span v-if="data.type === 'file' && data.size" class="fm-tree-size">
                    {{ formatSize(data.size) }}
                  </span>
                </span>
              </template>
            </el-tree>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { executeCommand, confirmOperation, getFileTree, validateWorkspace } from '@/api/fileManager'

// ── 状态 ──────────────────────────────────────
const workspace = ref('D:/file_helper_demo')
const command = ref('')
const isRunning = ref(false)
const workspaceInfo = ref(null)

const chainSteps = ref([])
const chainRef = ref(null)

const fileList = ref([])          // 搜索/完成后的文件列表
const pendingConfirm = ref(null)  // { operation_id, action, files }

const treeData = ref([])
const treeProps = { children: 'children', label: 'name' }

// ── 计算属性 ──────────────────────────────────
const displayFiles = computed(() => {
  if (pendingConfirm.value) return pendingConfirm.value.files
  return fileList.value
})

// ── 工作目录 ──────────────────────────────────
async function handleSetWorkspace() {
  if (!workspace.value.trim()) return
  try {
    const res = await validateWorkspace(workspace.value.trim())
    if (res.code === 200) {
      workspaceInfo.value = res.data
      ElMessage.success(`已设置工作目录：${res.data.name}`)
      await refreshTree()
    } else {
      ElMessage.error(res.msg || '目录不存在')
    }
  } catch (e) {
    ElMessage.error('设置失败：' + e.message)
  }
}

// ── 文件树 ────────────────────────────────────
async function refreshTree() {
  if (!workspace.value) return
  try {
    const res = await getFileTree(workspace.value, 3)
    if (res.code === 200 && res.data) {
      treeData.value = res.data.children || []
    }
  } catch (e) {
    // 刷新失败静默处理
  }
}

// ── 执行命令 ──────────────────────────────────
async function handleExecute() {
  if (!command.value.trim() || !workspace.value.trim() || isRunning.value) return

  isRunning.value = true
  chainSteps.value = []
  fileList.value = []
  pendingConfirm.value = null

  try {
    await executeCommand(command.value.trim(), workspace.value.trim(), handleStep)
  } catch (e) {
    ElMessage.error('执行失败：' + e.message)
  } finally {
    isRunning.value = false
    await refreshTree()
  }
}

// ── 处理每个 SSE 步骤 ─────────────────────────
function handleStep(step) {
  const type = step.type

  if (type === 'thought' || type === 'action' || type === 'observation') {
    chainSteps.value.push(step)
    scrollChainToBottom()
  } else if (type === 'done') {
    chainSteps.value.push(step)
    scrollChainToBottom()
    // 展示找到的文件
    if (step.files && step.files.length > 0) {
      fileList.value = step.files
    }
  } else if (type === 'confirm_required') {
    pendingConfirm.value = {
      operation_id: step.operation_id,
      action: step.action,
      files: step.files,
    }
    chainSteps.value.push({
      type: 'observation',
      result: {
        success: true,
        message: `需要确认：${step.action === 'delete' ? '删除' : '移动'} ${step.files.length} 个文件`
      }
    })
    scrollChainToBottom()
  } else if (type === 'error') {
    chainSteps.value.push(step)
    scrollChainToBottom()
    ElMessage.error(step.message)
  }
}

// ── 确认/取消危险操作 ─────────────────────────
async function handleConfirm(confirmed) {
  if (!pendingConfirm.value) return
  const { operation_id, action } = pendingConfirm.value
  pendingConfirm.value = null
  fileList.value = []

  try {
    const res = await confirmOperation(operation_id, confirmed)
    if (confirmed) {
      const s = res.data?.success_count ?? 0
      const sk = res.data?.skipped_count ?? 0
      const f = res.data?.failed_count ?? 0
      let msg = `执行完成：成功 ${s} 个`
      if (sk > 0) msg += `，跳过 ${sk} 个（目标已存在）`
      if (f > 0) msg += `，失败 ${f} 个`
      ElMessage.success(msg)
      chainSteps.value.push({ type: 'done', summary: msg })
    } else {
      ElMessage.info('已取消操作')
      chainSteps.value.push({ type: 'done', summary: '用户取消了操作' })
    }
    scrollChainToBottom()
    await refreshTree()
  } catch (e) {
    ElMessage.error('确认操作失败：' + e.message)
  }
}

// ── 清空 ─────────────────────────────────────
function handleClear() {
  command.value = ''
  chainSteps.value = []
  fileList.value = []
  pendingConfirm.value = null
}

// ── 工具函数 ──────────────────────────────────
function scrollChainToBottom() {
  nextTick(() => {
    if (chainRef.value) {
      chainRef.value.scrollTop = chainRef.value.scrollHeight
    }
  })
}

function formatArgs(args) {
  if (!args) return ''
  const brief = Object.entries(args)
    .filter(([k]) => k !== 'file_paths')
    .map(([k, v]) => {
      if (Array.isArray(v)) return `${k}=[${v.slice(0, 3).join(', ')}${v.length > 3 ? '...' : ''}]`
      return `${k}=${v}`
    })
    .join(', ')
  const fp = args.file_paths ? ` file_count=${args.file_paths.length}` : ''
  return brief || fp ? ` (${brief}${fp})` : ''
}

function formatObservation(result) {
  if (!result) return ''
  if (result.message) return result.message
  if (result.count !== undefined) return `找到 ${result.count} 个文件`
  if (result.success_count !== undefined) return `完成：成功 ${result.success_count} 个`
  if (result.file_count !== undefined) return `共 ${result.file_count} 个文件`
  return JSON.stringify(result).slice(0, 80)
}

function formatSize(bytes) {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function getFileIcon(name) {
  if (!name) return '📄'
  const ext = name.split('.').pop().toLowerCase()
  const map = {
    pdf: '📕', doc: '📘', docx: '📘', ppt: '📙', pptx: '📙',
    xls: '📗', xlsx: '📗', txt: '📄', md: '📄',
    jpg: '🖼', jpeg: '🖼', png: '🖼', gif: '🖼', webp: '🖼',
    mp4: '🎬', avi: '🎬', mkv: '🎬', mov: '🎬',
    mp3: '🎵', wav: '🎵', flac: '🎵',
    zip: '📦', rar: '📦', '7z': '📦',
    py: '🐍', js: '📜', ts: '📜', java: '☕', cpp: '⚙️', c: '⚙️',
  }
  return map[ext] || '📄'
}
</script>

<style scoped>
/* ── 整体布局 ── */
.fm-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 50px);
  background-color: #ecf0f3;
  overflow: hidden;
}

/* ── 顶部输入栏 ── */
.fm-topbar {
  padding: 12px 20px;
  background: #ffffff;
  border-bottom: 1px solid #dde1e7;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}

.fm-workspace-row,
.fm-command-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.fm-label {
  font-size: 13px;
  color: #888;
  min-width: 52px;
  text-align: right;
}

.fm-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  background-color: #ecf0f3;
  box-shadow: inset 2px 2px 4px #d1d9e6, inset -2px -2px 4px #f9f9f9;
  font-size: 14px;
  outline: none;
  color: #333;
}

.fm-input:focus {
  box-shadow: inset 2px 2px 4px #c8d0dc, inset -2px -2px 4px #ffffff;
}

.fm-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.fm-workspace-info {
  font-size: 12px;
  color: #4B70E2;
  white-space: nowrap;
}

/* ── 按钮 ── */
.fm-btn-primary {
  padding: 6px 18px;
  border: none;
  border-radius: 8px;
  background-color: #4B70E2;
  color: white;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  box-shadow: 3px 3px 6px #d1d9e6, -3px -3px 6px #f9f9f9;
  transition: opacity 0.2s;
}

.fm-btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fm-btn-primary:not(:disabled):hover {
  opacity: 0.9;
}

.fm-btn-secondary {
  padding: 6px 14px;
  border: none;
  border-radius: 8px;
  background-color: #ecf0f3;
  color: #555;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 3px 3px 6px #d1d9e6, -3px -3px 6px #f9f9f9;
  white-space: nowrap;
  transition: box-shadow 0.2s;
}

.fm-btn-secondary:hover {
  box-shadow: 1px 1px 3px #d1d9e6, -1px -1px 3px #f9f9f9;
}

.fm-btn-danger {
  padding: 8px 20px;
  border: none;
  border-radius: 8px;
  background-color: #e74c3c;
  color: white;
  font-size: 14px;
  cursor: pointer;
  box-shadow: 3px 3px 6px #d1d9e6, -3px -3px 6px #f9f9f9;
  transition: opacity 0.2s;
}

.fm-btn-danger:hover {
  opacity: 0.9;
}

/* ── 主体 ── */
.fm-body {
  display: flex;
  flex: 1;
  gap: 16px;
  padding: 16px;
  overflow: hidden;
}

/* ── 左列 ── */
.fm-left {
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 0 0 55%;
  min-width: 0;
  overflow: hidden;
}

/* ── 右列 ── */
.fm-right {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* ── 通用 panel ── */
.fm-panel {
  background-color: #ecf0f3;
  border-radius: 12px;
  box-shadow: 5px 5px 10px #d1d9e6, -5px -5px 10px #f9f9f9;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.fm-panel-title {
  padding: 10px 14px;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  border-bottom: 1px solid #dde1e7;
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.fm-panel-warning {
  box-shadow: 5px 5px 10px #f0c0bb, -5px -5px 10px #f9f9f9;
}

.fm-panel-warning .fm-panel-title {
  color: #c0392b;
}

/* ── 思维链 panel ── */
.fm-chain-panel {
  flex: 1;
  min-height: 0;
}

.fm-chain-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.fm-chain-step {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 13px;
  line-height: 1.5;
}

.fm-step-thought { background: rgba(75, 112, 226, 0.06); }
.fm-step-action  { background: rgba(39, 174, 96, 0.06); }
.fm-step-observation { background: rgba(0, 0, 0, 0.03); }
.fm-step-done    { background: rgba(75, 112, 226, 0.1); }
.fm-step-error   { background: rgba(231, 76, 60, 0.08); }

.fm-step-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.fm-step-text {
  color: #444;
  word-break: break-word;
}

.fm-step-args {
  color: #888;
  font-size: 12px;
  margin-left: 4px;
}

.fm-step-done { color: #4B70E2; font-weight: 500; }
.fm-step-error { color: #e74c3c; }

/* ── 文件列表 panel ── */
.fm-files-panel {
  flex: 0 0 auto;
  max-height: 40%;
}

.fm-files-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.fm-file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 13px;
  color: #444;
  transition: background 0.15s;
}

.fm-file-item:hover { background: rgba(0,0,0,0.04); }

.fm-file-danger {
  border-left: 3px solid #e74c3c;
  padding-left: 5px;
}

.fm-file-icon { font-size: 15px; flex-shrink: 0; }
.fm-file-name { word-break: break-all; }

.fm-confirm-bar {
  display: flex;
  gap: 10px;
  padding: 10px 0 4px;
  border-top: 1px solid #dde1e7;
  margin-top: 4px;
}

/* ── 文件树 panel ── */
.fm-tree-panel {
  flex: 1;
}

.fm-tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 8px;
}

.fm-tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.fm-tree-icon { flex-shrink: 0; }
.fm-tree-name { color: #333; }
.fm-tree-size {
  color: #aaa;
  font-size: 11px;
  margin-left: 4px;
}

/* ── 空状态 ── */
.fm-empty-tip {
  color: #b0b6be;
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

/* ── 运行指示点 ── */
.fm-running-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #4B70E2;
  animation: pulse 1s infinite;
  margin-left: 4px;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

/* ── 刷新按钮 ── */
.fm-refresh-btn {
  margin-left: auto;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 16px;
  color: #888;
  padding: 0 4px;
  line-height: 1;
}

.fm-refresh-btn:hover { color: #4B70E2; }

/* ── el-tree 样式覆盖 ── */
:deep(.el-tree) {
  background: transparent;
  color: #333;
}

:deep(.el-tree-node__content) {
  height: 28px;
  border-radius: 6px;
}

:deep(.el-tree-node__content:hover) {
  background-color: rgba(75, 112, 226, 0.08);
}
</style>
