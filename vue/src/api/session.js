import { request } from '@/api/request'

export function createSession(payload) {
  return request('/session/create', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function sendAiContent(payload) {
  return request('/session/aicontent', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function deleteSession(sessionId) {
  return request(`/session/${sessionId}`, {
    method: 'DELETE',
  })
}
