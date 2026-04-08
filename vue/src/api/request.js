import { ip } from '@/config/config'
import { useUserStore } from '@/stores/user'

function buildUrl(path) {
  if (path.startsWith('http')) {
    return path
  }
  return `http://${ip}${path}`
}

export async function request(path, options = {}) {
  const userStore = useUserStore()
  const isFormData = typeof FormData !== 'undefined' && options.body instanceof FormData
  const headers = {
    ...(!isFormData && options.body ? { 'Content-Type': 'application/json' } : {}),
    ...(userStore.token ? { token: userStore.token } : {}),
    ...(options.headers || {}),
  }

  const response = await fetch(buildUrl(path), {
    ...options,
    headers,
  })

  let data = null
  const contentType = response.headers.get('content-type') || ''
  if (contentType.includes('application/json')) {
    data = await response.json()
  } else {
    data = await response.text()
  }

  if (!response.ok) {
    const message = data?.message || `请求失败(${response.status})`
    throw new Error(message)
  }

  if (data && typeof data === 'object' && 'code' in data && data.code !== 1) {
    throw new Error(data.message || '请求失败')
  }

  return data
}
