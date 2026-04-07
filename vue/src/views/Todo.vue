<template>
  <div class="todo-page">
    <div class="todo-shell">
      <TodoAiPanel
        :todos="allTodos"
        :confirming="aiConfirming"
        :action-feedback="aiActionFeedback"
        @confirm-action="handleConfirmAction"
      />

      <TodoCalendar
        :week-days="weekDays"
        :week-range-label="weekRangeLabel"
        :events="filteredCurrentWeekTodos"
        @change-week="changeWeek"
        @open-add="handleOpenManualAdd"
        @select-event="handleSelectEvent"
        @create-at-slot="handleCreateAtSlot"
      >
        <template #header-extra>
          <TodoFilterBar v-model="activeFilter" :options="todoFilterOptions" />
        </template>
      </TodoCalendar>
    </div>

    <TodoManualAddDialog
      v-model="dialogVisible"
      :initial-values="manualAddInitialValues"
      :submitting="submitting"
      @submit="handleCreateTodo"
    />

    <TodoDetailDialog
      v-model="detailDialogVisible"
      :todo="selectedTodo"
      :save-loading="detailSaving"
      :delete-loading="detailDeleting"
      :status-loading="detailStatusUpdating"
      @save="handleSaveSelectedTodo"
      @delete="handleDeleteSelectedTodo"
      @update-status="handleQuickStatusUpdate"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import TodoAiPanel from '@/components/todo/TodoAiPanel.vue'
import TodoCalendar from '@/components/todo/TodoCalendar.vue'
import TodoDetailDialog from '@/components/todo/TodoDetailDialog.vue'
import TodoFilterBar from '@/components/todo/TodoFilterBar.vue'
import TodoManualAddDialog from '@/components/todo/TodoManualAddDialog.vue'
import { createTodo, deleteTodo, getTodoList, updateTodo, updateTodoStatus } from '@/api/todo'
import { useUserStore } from '@/stores/user'
import {
  addDays,
  buildWeekDays,
  compareLocalDateTime,
  findConflictingRangeTodo,
  formatLocalDateTime,
  formatDateParts,
  getBeijingNowParts,
  getTodoEffectiveRange,
  getTodoPrimaryStart,
  getTodoTimingSummary,
  getWeekStartDateParts,
  isTodoRangeEvent,
  parseLocalDateTimeString,
} from '@/utils/todoTime'

const userStore = useUserStore()
const dialogVisible = ref(false)
const detailDialogVisible = ref(false)
const submitting = ref(false)
const aiConfirming = ref(false)
const detailSaving = ref(false)
const detailDeleting = ref(false)
const detailStatusUpdating = ref(false)
const allTodos = ref([])
const weekOffset = ref(0)
const selectedTodo = ref(null)
const aiActionFeedback = ref(null)
const activeFilter = ref('all')
const manualAddInitialValues = ref(null)

const todoFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '今日', value: 'today' },
  { label: '未完成', value: 'unfinished' },
  { label: '仅截止事项', value: 'deadline-only' },
  { label: '仅日程块', value: 'range-only' },
]

const currentWeekStart = computed(() => {
  const now = getBeijingNowParts()
  const currentWeekStartDate = getWeekStartDateParts(now)
  return addDays(currentWeekStartDate, weekOffset.value * 7)
})

const currentWeekEnd = computed(() => {
  return addDays(currentWeekStart.value, 7)
})

const weekDays = computed(() => {
  const todayKey = formatDateParts(getBeijingNowParts())
  return buildWeekDays(currentWeekStart.value).map((day) => ({
    ...day,
    isToday: day.iso === todayKey,
  }))
})

const weekRangeLabel = computed(() => {
  const start = currentWeekStart.value
  const end = addDays(currentWeekEnd.value, -1)
  return `${start.month}月${start.day}日 - ${end.month}月${end.day}日`
})

const currentWeekTodos = computed(() => {
  const weekStartKey = formatDateParts(currentWeekStart.value)
  const weekEndKey = formatDateParts(currentWeekEnd.value)
  const weekStart = `${weekStartKey}T00:00:00`
  const weekEnd = `${weekEndKey}T00:00:00`
  return allTodos.value
    .filter((todo) => {
      const { start, end } = getTodoEffectiveRange(todo)
      return start < weekEnd && end > weekStart
    })
    .sort((a, b) => compareLocalDateTime(getTodoPrimaryStart(a), getTodoPrimaryStart(b)))
})

const filteredCurrentWeekTodos = computed(() => {
  const filter = activeFilter.value
  if (filter === 'all') {
    return currentWeekTodos.value
  }

  const todayParts = getBeijingNowParts()
  const todayKey = formatDateParts(todayParts)
  const tomorrowKey = formatDateParts(addDays(todayParts, 1))
  const todayStart = `${todayKey}T00:00:00`
  const tomorrowStart = `${tomorrowKey}T00:00:00`

  return currentWeekTodos.value.filter((todo) => {
    if (filter === 'unfinished') {
      return todo.status !== 'done'
    }

    if (filter === 'deadline-only') {
      return Boolean(todo.deadline) && !isTodoRangeEvent(todo)
    }

    if (filter === 'range-only') {
      return isTodoRangeEvent(todo)
    }

    if (filter === 'today') {
      if (isTodoRangeEvent(todo)) {
        const { start, end } = getTodoEffectiveRange(todo)
        return start < tomorrowStart && end > todayStart
      }

      return todo.deadline?.startsWith(todayKey)
    }

    return true
  })
})

async function loadTodos() {
  if (!userStore.isLoggedIn) {
    allTodos.value = []
    return
  }

  try {
    const result = await getTodoList()
    allTodos.value = Array.isArray(result.data) ? result.data : []
  } catch (error) {
    ElMessage.error(error.message || '加载待办失败')
  }
}

function changeWeek(direction) {
  weekOffset.value += direction
}

function addMinutesToLocalDateTime(value, minutesToAdd) {
  const parsed = parseLocalDateTimeString(value)
  if (!parsed) return value

  let totalMinutes = parsed.hour * 60 + parsed.minute + minutesToAdd
  let dayOffset = 0

  while (totalMinutes >= 24 * 60) {
    totalMinutes -= 24 * 60
    dayOffset += 1
  }

  while (totalMinutes < 0) {
    totalMinutes += 24 * 60
    dayOffset -= 1
  }

  const dateParts = addDays(
    {
      year: parsed.year,
      month: parsed.month,
      day: parsed.day,
    },
    dayOffset
  )

  return formatLocalDateTime({
    ...dateParts,
    hour: Math.floor(totalMinutes / 60),
    minute: totalMinutes % 60,
    second: parsed.second ?? 0,
  })
}

function handleOpenManualAdd() {
  manualAddInitialValues.value = null
  dialogVisible.value = true
}

function handleCreateAtSlot(slot) {
  const startTime = slot?.localDateTime || ''
  if (!startTime) return

  manualAddInitialValues.value = {
    timeMode: 'range',
    startTime,
    endTime: addMinutesToLocalDateTime(startTime, 60),
    deadline: startTime,
  }
  dialogVisible.value = true
}

function handleSelectEvent(event) {
  selectedTodo.value = { ...event }
  detailDialogVisible.value = true
}

function syncSelectedTodo(updatedTodo) {
  selectedTodo.value = updatedTodo ? { ...updatedTodo } : null
}

function getRangeConflictMessage(conflictingTodo) {
  if (!conflictingTodo) return '这个日程时间块与现有专注事项冲突，请调整开始或结束时间后再试。'
  return `这个日程时间块与现有专注事项冲突：${conflictingTodo.title}（${getTodoTimingSummary(conflictingTodo)}）。请调整时间后再试。`
}

function findRangeConflict(payload, options = {}) {
  return findConflictingRangeTodo(payload, allTodos.value, options)
}

async function handleCreateTodo(payload) {
  const conflictTodo = findRangeConflict(payload)
  if (conflictTodo) {
    ElMessage.error(getRangeConflictMessage(conflictTodo))
    return
  }

  submitting.value = true
  try {
    await createTodo({
      ...payload,
      status: 'pending',
    })
    ElMessage.success('Todo 已创建')
    dialogVisible.value = false
    await loadTodos()
  } catch (error) {
    ElMessage.error(error.message || '创建 Todo 失败')
  } finally {
    submitting.value = false
  }
}

function pushAiFeedback(type, message) {
  aiActionFeedback.value = {
    id: Date.now(),
    type,
    message,
  }
}

async function handleConfirmAction(actionDraft) {
  if (!actionDraft?.action) return

  if (actionDraft.action === 'create' || actionDraft.action === 'update') {
    const conflictTodo = findRangeConflict(actionDraft.payload, {
      excludeTodoId: actionDraft.action === 'update' ? actionDraft.targetId : null,
    })

    if (conflictTodo) {
      const message = `我没有执行这次${actionDraft.action === 'create' ? '新增' : '修改'}，因为时间块与现有专注事项冲突：${conflictTodo.title}（${getTodoTimingSummary(conflictTodo)}）。你可以调整开始或结束时间后再确认。`
      ElMessage.error(getRangeConflictMessage(conflictTodo))
      pushAiFeedback('error', message)
      return
    }
  }

  aiConfirming.value = true
  try {
    if (actionDraft.action === 'create') {
      await createTodo(actionDraft.payload)
      ElMessage.success('Todo 已创建')
      pushAiFeedback('success', `已创建事项：${actionDraft.payload.title}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'update') {
      await updateTodo(actionDraft.targetId, actionDraft.payload)
      ElMessage.success('Todo 已更新')
      pushAiFeedback('success', `已更新事项：${actionDraft.target?.title || actionDraft.payload.title}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'delete') {
      await deleteTodo(actionDraft.targetId)
      ElMessage.success('Todo 已删除')
      pushAiFeedback('success', `已删除事项：${actionDraft.target?.title || '待办事项'}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'mark_done' || actionDraft.action === 'mark_pending') {
      await updateTodoStatus(actionDraft.targetId, actionDraft.payload.status)
      ElMessage.success('状态已更新')
      pushAiFeedback(
        'success',
        `已将事项“${actionDraft.target?.title || '待办事项'}”更新为${actionDraft.payload.status === 'done' ? '已完成' : '待办中'}。周历和待办列表已同步刷新。`
      )
    }

    await loadTodos()
  } catch (error) {
    ElMessage.error(error.message || '执行 Todo 操作失败')
    pushAiFeedback('error', error.message || '这次后端执行失败了，原事项没有被静默改动。你可以检查描述后重新确认。')
  } finally {
    aiConfirming.value = false
  }
}

async function handleSaveSelectedTodo(payload) {
  if (!selectedTodo.value) return

  const conflictTodo = findRangeConflict(payload, {
    excludeTodoId: selectedTodo.value.id,
  })
  if (conflictTodo) {
    ElMessage.error(getRangeConflictMessage(conflictTodo))
    return
  }

  detailSaving.value = true
  try {
    const result = await updateTodo(selectedTodo.value.id, payload)
    const updatedTodo = result?.data || { ...selectedTodo.value, ...payload }
    syncSelectedTodo(updatedTodo)
    ElMessage.success('Todo 已更新')
    await loadTodos()
    detailDialogVisible.value = false
  } catch (error) {
    ElMessage.error(error.message || '更新 Todo 失败')
  } finally {
    detailSaving.value = false
  }
}

async function handleDeleteSelectedTodo() {
  if (!selectedTodo.value) return

  detailDeleting.value = true
  try {
    await deleteTodo(selectedTodo.value.id)
    ElMessage.success('Todo 已删除')
    detailDialogVisible.value = false
    syncSelectedTodo(null)
    await loadTodos()
  } catch (error) {
    ElMessage.error(error.message || '删除 Todo 失败')
  } finally {
    detailDeleting.value = false
  }
}

async function handleQuickStatusUpdate(status) {
  if (!selectedTodo.value) return

  detailStatusUpdating.value = true
  try {
    const result = await updateTodoStatus(selectedTodo.value.id, status)
    const updatedTodo = result?.data || { ...selectedTodo.value, status }
    syncSelectedTodo(updatedTodo)
    ElMessage.success('状态已更新')
    await loadTodos()
  } catch (error) {
    ElMessage.error(error.message || '更新状态失败')
  } finally {
    detailStatusUpdating.value = false
  }
}

onMounted(() => {
  loadTodos()
})

watch(
  () => userStore.isLoggedIn,
  (isLoggedIn) => {
    if (isLoggedIn) {
      loadTodos()
    } else {
      allTodos.value = []
    }
  }
)
</script>

<style scoped>
.todo-page {
  min-height: calc(100vh - 50px);
  padding: 20px;
  background:
    radial-gradient(circle at top left, rgba(76, 129, 255, 0.12), transparent 26%),
    radial-gradient(circle at right center, rgba(53, 143, 193, 0.1), transparent 22%),
    linear-gradient(180deg, #edf4fb 0%, #f7fafc 100%);
}

.todo-shell {
  width: min(1420px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: 380px 1fr;
  gap: 20px;
  align-items: stretch;
}

@media (max-width: 1200px) {
  .todo-shell {
    grid-template-columns: 1fr;
  }
}
</style>
