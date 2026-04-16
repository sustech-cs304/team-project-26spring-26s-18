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

export function importOfficialCalendar(payload) {
  return request('/scheduler/official-calendar/import', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getOfficialCalendarList(params = {}) {
  const query = new URLSearchParams()
  if (params.source_year) query.set('source_year', params.source_year)
  if (params.display_mode) query.set('display_mode', params.display_mode)
  if (params.start_time) query.set('start_time', params.start_time)
  if (params.end_time) query.set('end_time', params.end_time)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/scheduler/official-calendar/list${suffix}`)
}

export function importCourseSchedule(payload) {
  return request('/scheduler/course-schedule/import', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function importCourseScheduleXlsx(file, replaceExisting = true, options = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('replace_existing', String(replaceExisting))
  formData.append('term', String(options.term || ''))
  formData.append('year', String(options.year || ''))
  return request('/scheduler/course-schedule/import/xlsx', {
    method: 'POST',
    body: formData,
  })
}

export function importBlackboard(payload) {
  return request('/scheduler/blackboard/import', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getCourseScheduleList(params = {}) {
  const query = new URLSearchParams()
  if (params.start_time) query.set('start_time', params.start_time)
  if (params.end_time) query.set('end_time', params.end_time)
  const suffix = query.toString() ? `?${query.toString()}` : ''
  return request(`/scheduler/course-schedule/list${suffix}`)
}

export function getBlackboardList() {
  return request('/scheduler/blackboard/list')
}
