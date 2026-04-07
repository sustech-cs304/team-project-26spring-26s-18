import { request } from '@/api/request'

export function getTodoList(status) {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return request(`/scheduler/todo/list${query}`)
}

export function createTodo(payload) {
  return request('/scheduler/todo', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateTodo(todoId, payload) {
  return request(`/scheduler/todo/${todoId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export function deleteTodo(todoId) {
  return request(`/scheduler/todo/${todoId}`, {
    method: 'DELETE',
  })
}

export function updateTodoStatus(todoId, status) {
  return request(`/scheduler/todo/${todoId}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}
