<template>
  <div class="todo-page">
    <div class="todo-shell">
      <TodoAiPanel
        :todos="allTodos"
        :confirming="aiConfirming"
        :action-feedback="aiActionFeedback"
        @confirm-action="handleConfirmAction"
      />

      <div class="todo-main">
        <section class="view-switcher-panel">
          <div>
            <div class="view-switcher-eyebrow">Scheduler Workspace</div>
            <h2>Todo 与课表</h2>
          </div>
          <div class="view-switcher-tabs">
            <button
              class="view-switcher-tab"
              :class="{ active: activeMainTab === 'schedule' }"
              @click="activeMainTab = 'schedule'"
            >
              日程视图
            </button>
            <button
              class="view-switcher-tab"
              :class="{ active: activeMainTab === 'timetable' }"
              @click="activeMainTab = 'timetable'"
            >
              课表视图
            </button>
          </div>
        </section>

        <TodoCalendar
          v-if="activeMainTab === 'schedule'"
          :week-days="weekDays"
          :week-range-label="weekRangeLabel"
          :events="filteredCurrentWeekTodos"
          :background-markers="visibleOfficialCalendarBackgroundMarkers"
          @change-week="changeWeek"
          @open-add="handleOpenManualAdd"
          @select-event="handleSelectEvent"
          @create-at-slot="handleCreateAtSlot"
        >
          <template #header-extra>
            <div class="calendar-header-tools">
              <TodoFilterBar v-model="activeFilter" :options="todoFilterOptions" />
              <div class="calendar-side-tools">
                <label class="background-toggle">
                  <input v-model="showOfficialCalendarBackground" type="checkbox" />
                  <span>显示校历背景</span>
                </label>
                <label class="background-toggle blackboard-toggle">
                  <input v-model="showBlackboardItems" type="checkbox" />
                  <span>显示 Blackboard 事项</span>
                </label>
                <div class="import-actions">
                  <button class="import-btn secondary" @click="openImportDialog('official-calendar')">导入官方校历</button>
                  <button class="import-btn" @click="openImportDialog('course-schedule')">导入课程表</button>
                  <button class="import-btn blackboard" @click="openImportDialog('blackboard')">导入 Blackboard</button>
                </div>
              </div>
            </div>
          </template>
        </TodoCalendar>

        <CourseTimetable
          v-else
          :courses="courseScheduleEvents"
          @import-course-schedule="openImportDialog('course-schedule')"
        />

        <section class="source-preview-panel">
          <div class="source-preview-top">
            <div>
              <div class="preview-eyebrow">Source Import</div>
              <h3>已导入来源预览</h3>
            </div>
            <div class="preview-tabs">
              <button
                class="preview-tab"
                :class="{ active: activeSourceTab === 'official-calendar' }"
                @click="activeSourceTab = 'official-calendar'"
              >
                官方校历
              </button>
              <button
                class="preview-tab"
                :class="{ active: activeSourceTab === 'course-schedule' }"
                @click="activeSourceTab = 'course-schedule'"
              >
                课程表
              </button>
              <button
                class="preview-tab"
                :class="{ active: activeSourceTab === 'blackboard' }"
                @click="activeSourceTab = 'blackboard'"
              >
                Blackboard
              </button>
            </div>
          </div>

          <div v-if="lastImportSummary" class="import-summary">
            <strong>{{ lastImportSummary.sourceLabel }}</strong>
            已导入 {{ lastImportSummary.importedCount }} 条，跳过 {{ lastImportSummary.skippedCount }} 条。
            <span v-if="lastImportSummary.previewCount"> 预览已刷新 {{ lastImportSummary.previewCount }} 条。</span>
            <div v-if="lastImportSummary.skippedRows?.length" class="import-skipped">
              {{ lastImportSummary.skippedRows.slice(0, 3).join('；') }}
            </div>
          </div>

          <div v-if="activeSourceTab === 'official-calendar'" class="source-list">
            <div v-if="officialCalendarEvents.length" class="source-count">共 {{ officialCalendarEvents.length }} 条官方校历事件</div>
            <div v-else class="empty-state">暂无官方校历数据</div>
            <article v-for="event in officialCalendarEvents" :key="`official-${event.id}`" class="source-card">
              <div class="source-card-head">
                <strong>{{ event.title }}</strong>
                <div class="source-badges">
                  <span class="source-tag" :class="event.display_mode === 'background' ? 'is-background' : 'is-event'">
                    {{ getOfficialDisplayModeLabel(event.display_mode) }}
                  </span>
                  <span class="source-tag">{{ event.event_type || 'event' }}</span>
                </div>
              </div>
              <div v-if="event.source_year" class="source-meta">来源年份：{{ event.source_year }}</div>
              <div class="source-meta">{{ formatSourceDateRange(event.start_time, event.end_time) }}</div>
              <div v-if="event.location" class="source-meta">{{ event.location }}</div>
              <p v-if="event.description" class="source-desc">{{ event.description }}</p>
            </article>
          </div>

          <div v-else-if="activeSourceTab === 'course-schedule'" class="source-list">
            <div v-if="courseScheduleEvents.length" class="source-count">共 {{ courseScheduleEvents.length }} 条课程表事件</div>
            <div v-else class="empty-state">暂无课程表数据</div>
            <article v-for="event in courseScheduleEvents" :key="`course-${event.id}`" class="source-card">
              <div class="source-card-head">
                <strong>{{ event.course_name || event.title }}</strong>
                <span v-if="event.course_code" class="source-tag">{{ event.course_code }}</span>
              </div>
              <div class="source-meta">{{ formatSourceDateRange(event.start_time, event.end_time) }}</div>
              <div v-if="event.location" class="source-meta">{{ event.location }}</div>
              <div v-if="event.instructor" class="source-meta">教师：{{ event.instructor }}</div>
              <p v-if="event.description" class="source-desc">{{ event.description }}</p>
            </article>
          </div>

          <div v-else class="source-list">
            <div v-if="blackboardTodos.length" class="source-count">共 {{ blackboardTodos.length }} 条 Blackboard 截止事项</div>
            <div v-else class="empty-state">暂无 Blackboard 导入数据</div>
            <article v-for="todo in blackboardTodos" :key="`blackboard-${todo.id}`" class="source-card">
              <div class="source-card-head">
                <strong>{{ todo.title }}</strong>
                <span class="source-tag blackboard-tag">deadline</span>
              </div>
              <div v-if="todo.deadline" class="source-meta">截止时间：{{ formatSourceDateRange(todo.deadline, todo.deadline) }}</div>
              <p v-if="todo.content" class="source-desc">{{ todo.content }}</p>
            </article>
          </div>
        </section>
      </div>
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

    <TodoSourceImportDialog
      v-model="importDialogVisible"
      :form="importForm"
      :submitting="importSubmitting"
      @update:form="handleImportFormUpdate"
      @submit="handleSubmitImport"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import TodoAiPanel from '@/components/todo/TodoAiPanel.vue'
import TodoCalendar from '@/components/todo/TodoCalendar.vue'
import CourseTimetable from '@/components/todo/CourseTimetable.vue'
import TodoDetailDialog from '@/components/todo/TodoDetailDialog.vue'
import TodoFilterBar from '@/components/todo/TodoFilterBar.vue'
import TodoManualAddDialog from '@/components/todo/TodoManualAddDialog.vue'
import TodoSourceImportDialog from '@/components/todo/TodoSourceImportDialog.vue'
import {
  createTodo,
  deleteTodo,
  getBlackboardList,
  getCourseScheduleList,
  getOfficialCalendarList,
  getTodoList,
  importBlackboard,
  importCourseSchedule,
  importCourseScheduleXlsx,
  importOfficialCalendar,
  updateTodo,
  updateTodoStatus,
} from '@/api/todo'
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
const importDialogVisible = ref(false)
const importSubmitting = ref(false)
const activeMainTab = ref('schedule')
const activeSourceTab = ref('official-calendar')
const officialCalendarEvents = ref([])
const courseScheduleEvents = ref([])
const blackboardTodos = ref([])
const officialCalendarBackgroundMarkers = ref([])
const showOfficialCalendarBackground = ref(true)
const showBlackboardItems = ref(true)
const lastImportSummary = ref(null)
const importForm = ref(buildDefaultImportForm())

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
      if (showBlackboardItems.value) {
        return true
      }
      return todo.import_source !== 'blackboard'
    })
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

const currentWeekQueryRange = computed(() => {
  const startKey = formatDateParts(currentWeekStart.value)
  const endVisibleDay = addDays(currentWeekEnd.value, -1)
  const endKey = formatDateParts(endVisibleDay)
  return {
    start_time: `${startKey}T00:00:00`,
    end_time: `${endKey}T23:59:59`,
  }
})

const visibleOfficialCalendarBackgroundMarkers = computed(() => {
  if (!showOfficialCalendarBackground.value) {
    return []
  }
  return officialCalendarBackgroundMarkers.value
})

function buildDefaultImportForm(sourceType = 'official-calendar') {
  const isCourseSchedule = sourceType === 'course-schedule'
  const now = new Date()
  const currentMonth = now.getMonth() + 1
  const defaultTerm = currentMonth >= 9 ? 'fall' : 'spring'
  return {
    sourceType,
    contentType: sourceType === 'blackboard' ? 'ics' : isCourseSchedule ? 'xlsx' : 'auto',
    inputMode: isCourseSchedule ? 'file' : 'paste',
    replaceExisting: true,
    term: defaultTerm,
    year: now.getFullYear(),
    content: '',
    fileName: '',
    file: null,
  }
}

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

async function loadImportedSources() {
  if (!userStore.isLoggedIn) {
    officialCalendarEvents.value = []
    courseScheduleEvents.value = []
    blackboardTodos.value = []
    return
  }

  try {
    const [officialResult, courseResult, blackboardResult] = await Promise.all([
      getOfficialCalendarList(),
      getCourseScheduleList(),
      getBlackboardList(),
    ])
    officialCalendarEvents.value = Array.isArray(officialResult.data) ? officialResult.data : []
    courseScheduleEvents.value = Array.isArray(courseResult.data) ? courseResult.data : []
    blackboardTodos.value = Array.isArray(blackboardResult.data) ? blackboardResult.data : []
  } catch (error) {
    ElMessage.error(error.message || '加载导入来源失败')
  }
}

async function loadOfficialCalendarBackgroundMarkers() {
  if (!userStore.isLoggedIn) {
    officialCalendarBackgroundMarkers.value = []
    return
  }

  try {
    const result = await getOfficialCalendarList({
      display_mode: 'background',
      start_time: currentWeekQueryRange.value.start_time,
      end_time: currentWeekQueryRange.value.end_time,
    })
    officialCalendarBackgroundMarkers.value = Array.isArray(result.data) ? result.data : []
  } catch (error) {
    ElMessage.error(error.message || '加载校历背景失败')
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

function openImportDialog(sourceType) {
  importForm.value = buildDefaultImportForm(sourceType)
  activeSourceTab.value = sourceType
  importDialogVisible.value = true
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

function handleImportFormUpdate(nextForm) {
  importForm.value = nextForm
}

function formatSourceDateRange(startTime, endTime) {
  const start = getSourceDisplayTime(startTime)
  const end = getSourceDisplayTime(endTime)
  if (!start && !end) return '未提供时间'
  if (!end || start === end) return start
  return `${start} - ${end}`
}

function getSourceDisplayTime(value) {
  if (!value) return ''
  const text = String(value).replace('T', ' ')
  return text.length > 16 ? text.slice(0, 16) : text
}

function getOfficialDisplayModeLabel(value) {
  return value === 'background' ? '背景标记' : '官方活动'
}

async function handleSubmitImport() {
  if (!userStore.isLoggedIn) {
    ElMessage.error('请先登录')
    return
  }

  const isCourseScheduleXlsx = importForm.value.sourceType === 'course-schedule'
    && importForm.value.inputMode === 'file'
    && importForm.value.contentType === 'xlsx'

  if (isCourseScheduleXlsx && !importForm.value.file) {
    ElMessage.error('请先选择 .xlsx 课程表文件')
    return
  }

  if (isCourseScheduleXlsx && !['spring', 'fall'].includes(importForm.value.term)) {
    ElMessage.error('请选择有效学期')
    return
  }

  if (isCourseScheduleXlsx && !Number.isInteger(Number(importForm.value.year))) {
    ElMessage.error('请选择有效年份')
    return
  }

  const content = (importForm.value.content || '').trim()
  if (!isCourseScheduleXlsx && !content) {
    ElMessage.error('请先提供导入内容')
    return
  }

  importSubmitting.value = true
  try {
    const result = isCourseScheduleXlsx
      ? await importCourseScheduleXlsx(importForm.value.file, importForm.value.replaceExisting, {
        term: importForm.value.term,
        year: Number(importForm.value.year),
      })
      : await (
        importForm.value.sourceType === 'course-schedule'
          ? importCourseSchedule({
            content,
            content_type: importForm.value.contentType,
            replace_existing: importForm.value.replaceExisting,
          })
          : importForm.value.sourceType === 'blackboard'
            ? importBlackboard({
              content,
              content_type: importForm.value.contentType,
              replace_existing: importForm.value.replaceExisting,
            })
            : importOfficialCalendar({
              content,
              content_type: importForm.value.contentType,
              replace_existing: importForm.value.replaceExisting,
            })
      )
    const importData = result?.data || {}
    lastImportSummary.value = {
      sourceType: importForm.value.sourceType,
      sourceLabel: importForm.value.sourceType === 'course-schedule'
        ? '课程表'
        : importForm.value.sourceType === 'blackboard'
          ? 'Blackboard'
          : '官方校历',
      importedCount: Number(importData.imported_count || 0),
      skippedCount: Number(importData.skipped_count || 0),
      previewCount: Number(importData.preview_count || 0),
      skippedRows: Array.isArray(importData.skipped_rows) ? importData.skipped_rows : [],
    }

    await loadImportedSources()
    if (importForm.value.sourceType === 'official-calendar') {
      await loadOfficialCalendarBackgroundMarkers()
    }
    importDialogVisible.value = false
    ElMessage.success(`${lastImportSummary.value.sourceLabel}导入完成`)
  } catch (error) {
    ElMessage.error(error.message || '导入失败')
  } finally {
    importSubmitting.value = false
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
  loadImportedSources()
  loadOfficialCalendarBackgroundMarkers()
})

watch(
  () => userStore.isLoggedIn,
  (isLoggedIn) => {
    if (isLoggedIn) {
      loadTodos()
      loadImportedSources()
      loadOfficialCalendarBackgroundMarkers()
    } else {
      allTodos.value = []
      officialCalendarEvents.value = []
      courseScheduleEvents.value = []
      blackboardTodos.value = []
      officialCalendarBackgroundMarkers.value = []
      lastImportSummary.value = null
    }
  }
)

watch(
  () => [currentWeekQueryRange.value.start_time, currentWeekQueryRange.value.end_time, userStore.isLoggedIn],
  ([, , isLoggedIn]) => {
    if (isLoggedIn) {
      loadOfficialCalendarBackgroundMarkers()
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

.todo-main {
  display: flex;
  flex-direction: column;
}

.view-switcher-panel {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: center;
  padding: 20px 24px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(107, 135, 181, 0.16);
  box-shadow: 0 18px 40px rgba(79, 103, 137, 0.12);
}

.view-switcher-eyebrow {
  color: #4d6c98;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.view-switcher-panel h2 {
  margin: 6px 0 0;
  color: #203047;
}

.view-switcher-tabs {
  display: inline-flex;
  gap: 10px;
  padding: 6px;
  border-radius: 999px;
  background: #edf3fb;
}

.view-switcher-tab {
  border: none;
  border-radius: 999px;
  padding: 11px 18px;
  background: transparent;
  color: #47607f;
  cursor: pointer;
  font-weight: 700;
}

.view-switcher-tab.active {
  background: linear-gradient(135deg, #153e8f, #2f73d9);
  color: #fff;
  box-shadow: 0 10px 18px rgba(32, 71, 132, 0.22);
}

@media (max-width: 1200px) {
  .todo-shell {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .view-switcher-panel {
    flex-direction: column;
    align-items: stretch;
  }

  .view-switcher-tabs {
    width: 100%;
    justify-content: space-between;
  }
}

.calendar-header-tools {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.calendar-side-tools {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}

.background-toggle {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(232, 239, 251, 0.9);
  color: #35506f;
  font-size: 13px;
  font-weight: 600;
}

.background-toggle input {
  margin: 0;
}

.background-toggle.blackboard-toggle {
  background: rgba(245, 234, 217, 0.92);
  color: #72561d;
}

.import-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.import-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #1745a3, #2f73d9);
  color: #fff;
  font-weight: 600;
  cursor: pointer;
}

.import-btn.secondary {
  background: linear-gradient(135deg, #14576b, #2288a6);
}

.import-btn.blackboard {
  background: linear-gradient(135deg, #6a4f1d, #9e7730);
}

.source-preview-panel {
  margin-top: 18px;
  padding: 20px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.84);
  border: 1px solid rgba(107, 135, 181, 0.16);
  box-shadow: 0 18px 40px rgba(79, 103, 137, 0.12);
}

.source-preview-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.preview-eyebrow {
  color: #4d6c98;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.source-preview-top h3 {
  margin: 6px 0 0;
  color: #203047;
}

.preview-tabs {
  display: flex;
  gap: 10px;
}

.preview-tab {
  border: 1px solid rgba(69, 96, 142, 0.18);
  background: #fff;
  color: #47607f;
  border-radius: 999px;
  padding: 9px 14px;
  cursor: pointer;
  font-weight: 600;
}

.preview-tab.active {
  background: #153e8f;
  color: #fff;
}

.import-summary {
  margin-top: 16px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #eef5ff;
  color: #274166;
}

.import-skipped {
  margin-top: 8px;
  font-size: 13px;
  color: #5c6f8f;
}

.source-list {
  margin-top: 16px;
  display: grid;
  gap: 12px;
}

.source-count {
  color: #58708f;
  font-size: 13px;
}

.empty-state {
  padding: 18px;
  border-radius: 16px;
  background: #f5f8fc;
  color: #647991;
}

.source-card {
  padding: 16px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(252, 253, 255, 0.98), rgba(244, 248, 253, 0.96));
  border: 1px solid rgba(107, 135, 181, 0.14);
}

.source-card-head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.source-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.source-tag {
  padding: 4px 10px;
  border-radius: 999px;
  background: #e8effb;
  color: #31538c;
  font-size: 12px;
}

.source-tag.is-background {
  background: #e8f4ec;
  color: #2d6b46;
}

.source-tag.is-event {
  background: #fff1df;
  color: #8a5716;
}

.source-tag.blackboard-tag {
  background: #f5ead9;
  color: #7b5b1a;
}

.source-meta {
  margin-top: 8px;
  color: #546b86;
  font-size: 13px;
}

.source-desc {
  margin: 10px 0 0;
  color: #33455e;
  line-height: 1.6;
}
</style>
