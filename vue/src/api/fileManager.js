import { ip } from '@/config/config'
import { useUserStore } from '@/stores/user'
import { request } from '@/api/request'

function buildUrl(path) {
  return `http://${ip}${path}`
}

/**
 * 执行自然语言命令，返回 SSE 流
 * 每条消息格式：{ type, ...fields }
 *   type = 'thought'          → { content }
 *   type = 'action'           → { tool, args }
 *   type = 'observation'      → { result }
 *   type = 'confirm_required' → { operation_id, action, files: [{name, path}] }
 *   type = 'done'             → { summary, files }
 *   type = 'error'            → { message }
 *   type = 'end'              → 流结束
 *
 * @param {string} command   自然语言命令
 * @param {string} workspace 工作目录路径
 * @param {function} onStep  每收到一条事件时的回调 (step) => void
 */
export async function executeCommand(command, workspace, onStep) {
  const userStore = useUserStore()
  const response = await fetch(buildUrl('/file/execute'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(userStore.token ? { token: userStore.token } : {}),
    },
    body: JSON.stringify({ command, workspace }),
  })

  if (!response.ok) {
    throw new Error(`请求失败(${response.status})`)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // 保留未完整的行

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (!raw) continue
        try {
          const step = JSON.parse(raw)
          onStep(step)
        } catch {
          // 忽略解析失败的行
        }
      }
    }
  }
}

/**
 * 确认或取消危险操作
 * @param {string} operationId
 * @param {boolean} confirmed
 */
export async function confirmOperation(operationId, confirmed) {
  return request('/file/confirm', {
    method: 'POST',
    body: JSON.stringify({ operation_id: operationId, confirmed }),
  })
}

/**
 * 获取目录树
 * @param {string} path  目录路径
 * @param {number} depth 展开深度（默认3）
 */
export async function getFileTree(path, depth = 3) {
  const params = new URLSearchParams({ path, depth })
  return request(`/file/tree?${params}`)
}

/**
 * 从 TIS 爬取课程，SSE 流式推送日志
 * @param {string} tisUsername
 * @param {string} tisPassword
 * @param {string} operationId
 * @param {function} onStep  (step) => void
 */
export async function fetchTIS(tisUsername, tisPassword, operationId, onStep) {
  const userStore = useUserStore()
  const response = await fetch(buildUrl('/file/fetchTIS'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(userStore.token ? { token: userStore.token } : {}),
    },
    body: JSON.stringify({ tis_username: tisUsername, tis_password: tisPassword, operation_id: operationId }),
  })
  if (!response.ok) throw new Error(`请求失败(${response.status})`)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop()
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const raw = line.slice(6).trim()
        if (!raw) continue
        try { onStep(JSON.parse(raw)) } catch {}
      }
    }
  }
}

/**
 * TIS 获取完成后继续执行课程整理
 * @param {string} operationId
 */
export async function resumeOrganize(operationId) {
  return request('/file/resumeOrganize', {
    method: 'POST',
    body: JSON.stringify({ operation_id: operationId }),
  })
}

/**
 * 验证工作目录是否存在，返回目录信息
 * @param {string} path
 */
export async function validateWorkspace(path) {
  return request('/file/workspace', {
    method: 'POST',
    body: JSON.stringify({ path }),
  })
}
