<template>
  <div class="todo-page">
    <div class="todo-shell">
      <TodoAiPanel
        :todos="allTodos"
        :confirming="aiConfirming"
        :action-feedback="aiActionFeedback"
        :aggregate-analysis="aggregateAnalysis"
        :analysis-loading="analysisLoading"
        :plan-generation-loading="analysisPlanLoading"
        :analysis-error="analysisError"
        :plan-generation-error="analysisPlanError"
        :analysis-visible="analysisVisible"
        :data-source-summary="dataSourceSummary"
        :ai-candidate-plans="analysisCandidatePlans"
        :selected-plan-id="selectedPlanId"
        @confirm-action="handleConfirmAction"
        @run-analysis="handleRunAnalysis"
        @select-plan="handleSelectPlan"
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
          :ai-preview-adjustments="selectedPlanPreviewAdjustments"
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

        <section class="source-preview-panel" :class="{ collapsed: sourcePreviewCollapsed }">
          <div class="source-preview-top">
            <div>
              <div class="preview-eyebrow">Source Import</div>
              <h3>{{ sourcePreviewCollapsed ? 'Imported items' : '已导入来源预览' }}</h3>
            </div>
            <div class="source-preview-controls">
              <div class="source-preview-actions">
                <span class="source-preview-count">{{ importedSourceItemCount }} items</span>
                <button class="preview-collapse-btn" @click="sourcePreviewCollapsed = !sourcePreviewCollapsed">
                  {{ sourcePreviewCollapsed ? '展开' : '收起' }}
                </button>
              </div>
              <div v-if="!sourcePreviewCollapsed" class="preview-tabs">
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
          </div>

          <div v-if="!sourcePreviewCollapsed" class="source-preview-body">
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
import { createSession, sendAiContent } from '@/api/session'
import {
  createTodo,
  deleteTodo,
  getBlackboardList,
  getCourseScheduleList,
  getOfficialCalendarList,
  getScheduleAggregateAnalysis,
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
const sourcePreviewCollapsed = ref(false)
const officialCalendarBackgroundMarkers = ref([])
const showOfficialCalendarBackground = ref(true)
const showBlackboardItems = ref(true)
const lastImportSummary = ref(null)
const importForm = ref(buildDefaultImportForm())
const aggregateAnalysis = ref(null)
const analysisLoading = ref(false)
const analysisPlanLoading = ref(false)
const analysisError = ref('')
const analysisPlanError = ref('')
const analysisCandidatePlans = ref([])
const selectedPlan = ref(null)
const analysisVisible = ref(false)
const analysisRequestVersion = ref(0)
const analysisAiSessionId = ref(null)
const selectedPlanId = computed(() => String(selectedPlan.value?.id || ''))
const importedSourceItemCount = computed(() => {
  return officialCalendarEvents.value.length + courseScheduleEvents.value.length + blackboardTodos.value.length
})

function resetAnalysisState() {
  analysisRequestVersion.value += 1
  aggregateAnalysis.value = null
  analysisError.value = ''
  analysisPlanError.value = ''
  analysisVisible.value = false
  analysisLoading.value = false
  analysisPlanLoading.value = false
  analysisCandidatePlans.value = []
  selectedPlan.value = null
}

function invalidateAnalysisAfterDataChange() {
  resetAnalysisState()
}

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

function hasExplicitWindowOverlap(item, startTime, endTime) {
  if (!item?.start_time || !item?.end_time) return false
  if (startTime && compareLocalDateTime(item.end_time, startTime) < 0) return false
  if (endTime && compareLocalDateTime(item.start_time, endTime) > 0) return false
  return true
}

function isDeadlineInWindow(item, startTime, endTime) {
  if (!item?.deadline) return false
  if (startTime && compareLocalDateTime(item.deadline, startTime) < 0) return false
  if (endTime && compareLocalDateTime(item.deadline, endTime) > 0) return false
  return true
}

function buildAnalysisSourceSummary({ rangeLabel, personalTodos, blackboardItems, officialEvents, courseEvents }) {
  const scheduledTodoCount = personalTodos.filter((todo) => todo.start_time && todo.end_time).length
  const deadlineTodoCount = personalTodos.filter((todo) => todo.deadline && !(todo.start_time && todo.end_time)).length
  const pendingTodoCount = personalTodos.filter((todo) => todo.status !== 'done' && todo.status !== 'cancelled').length
  const officialEventCount = officialEvents.filter((event) => event.display_mode !== 'background').length
  const officialBackgroundCount = officialEvents.filter((event) => event.display_mode === 'background').length
  const totalTodoCount = personalTodos.length + blackboardItems.length

  return {
    rangeLabel,
    totalTodoCount,
    pendingTodoCount,
    includedSources: [
      {
        key: 'personal_todo',
        label: '个人 Todo',
        count: personalTodos.length,
        detail: `${scheduledTodoCount} 条日程块 / ${deadlineTodoCount} 条截止事项`,
      },
      {
        key: 'official_calendar',
        label: '官方校历',
        count: officialEvents.length,
        detail: `${officialEventCount} 条官方活动 / ${officialBackgroundCount} 条背景标记`,
      },
      {
        key: 'course_schedule',
        label: '课程表',
        count: courseEvents.length,
        detail: '固定课程时间块',
      },
      {
        key: 'blackboard',
        label: 'Blackboard',
        count: blackboardItems.length,
        detail: '导入的截止型事项',
      },
    ],
  }
}

const dataSourceSummary = computed(() => {
  const rangeLabel = weekRangeLabel.value
  const timeline = Array.isArray(aggregateAnalysis.value?.timeline) ? aggregateAnalysis.value.timeline : null

  if (timeline) {
    return buildAnalysisSourceSummary({
      rangeLabel,
      personalTodos: timeline.filter((event) => event.source === 'personal_todo' && event.source_meta?.import_source !== 'blackboard'),
      blackboardItems: timeline.filter((event) => event.source === 'personal_todo' && event.source_meta?.import_source === 'blackboard'),
      officialEvents: timeline.filter((event) => event.source === 'official_calendar_event'),
      courseEvents: timeline.filter((event) => event.source === 'course_schedule_event'),
    })
  }

  const { start_time: startTime, end_time: endTime } = currentWeekQueryRange.value
  const personalTodos = allTodos.value.filter((todo) => {
    if (todo.status === 'done' || todo.status === 'cancelled') return false
    if (todo.import_source === 'blackboard') return false
    return hasExplicitWindowOverlap(todo, startTime, endTime) || isDeadlineInWindow(todo, startTime, endTime)
  })
  const blackboardItems = blackboardTodos.value.filter((todo) => {
    if (todo.status === 'done' || todo.status === 'cancelled') return false
    return hasExplicitWindowOverlap(todo, startTime, endTime) || isDeadlineInWindow(todo, startTime, endTime)
  })

  return buildAnalysisSourceSummary({
    rangeLabel,
    personalTodos,
    blackboardItems,
    officialEvents: officialCalendarEvents.value.filter((event) => hasExplicitWindowOverlap(event, startTime, endTime)),
    courseEvents: courseScheduleEvents.value.filter((event) => hasExplicitWindowOverlap(event, startTime, endTime)),
  })
})

function stripCodeFences(text) {
  const trimmed = String(text || '').trim()
  if (trimmed.startsWith('```')) {
    return trimmed
      .replace(/^```json\s*/i, '')
      .replace(/^```\s*/i, '')
      .replace(/\s*```$/, '')
      .trim()
  }
  return trimmed
}

function cleanInlineText(value) {
  return typeof value === 'string' ? value.replace(/\s+/g, ' ').trim() : ''
}

function normalizePlanId(value, index) {
  const normalized = cleanInlineText(value)
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-|-$/g, '')
  return normalized || `plan-${index + 1}`
}

function getAnalysisEventTimeLabel(event) {
  if (!event) return '未提供时间'
  if (event.start_time && event.end_time) {
    return formatSourceDateRange(event.start_time, event.end_time)
  }
  if (event.deadline) {
    return `截止 ${getSourceDisplayTime(event.deadline)}`
  }
  if (event.start_time) {
    return getSourceDisplayTime(event.start_time)
  }
  return '未提供时间'
}

function buildCompactEvent(event) {
  if (!event) return null
  return {
    event_id: event.source_id,
    title: event.title || '未命名事项',
    current_time: getAnalysisEventTimeLabel(event),
    start_time: normalizePreviewDateTime(event.start_time),
    end_time: normalizePreviewDateTime(event.end_time),
    deadline: normalizePreviewDateTime(event.deadline),
    source: event.source || '',
    kind: event.kind || '',
    level: event.level || '',
    priority: event.priority ?? null,
    status: event.status || '',
    is_flexible: Boolean(event.is_flexible),
  }
}

function buildEventLookup(timeline = []) {
  const lookup = new Map()
  timeline.forEach((event) => {
    const compact = buildCompactEvent(event)
    if (!compact) return
    const key = String(compact.event_id)
    if (!lookup.has(key)) {
      lookup.set(key, compact)
    }
  })
  return lookup
}

function getEventSummaryById(eventLookup, eventId) {
  return eventLookup.get(String(eventId)) || null
}

function buildCompactSuggestion(suggestion, eventLookup) {
  const relatedItems = Array.isArray(suggestion?.related_events)
    ? suggestion.related_events.map(buildCompactEvent).filter(Boolean).slice(0, 4)
    : []

  const resolveTargetEvent = (eventId) => {
    return relatedItems.find((item) => String(item.event_id) === String(eventId))
      || getEventSummaryById(eventLookup, eventId)
      || null
  }

  const rescheduleOptions = Array.isArray(suggestion?.candidate_reschedule_options)
    ? suggestion.candidate_reschedule_options.slice(0, 2).map((option) => {
      const targetEvent = resolveTargetEvent(option.target_event_id)
      return {
        action: option.action || 'reschedule',
        target_event_id: option.target_event_id,
        target_title: targetEvent?.title || `事项 ${option.target_event_id}`,
        current_time: targetEvent?.current_time || '未提供时间',
        original_start: targetEvent?.start_time || targetEvent?.deadline || null,
        original_end: targetEvent?.end_time || targetEvent?.deadline || null,
        suggested_time: formatSourceDateRange(option.suggested_start_time, option.suggested_end_time),
        suggested_start: normalizePreviewDateTime(option.suggested_start_time),
        suggested_end: normalizePreviewDateTime(option.suggested_end_time),
        reason: option.reason || '',
        rank: option.rank ?? 1,
      }
    })
    : []

  const focusBlockOptions = Array.isArray(suggestion?.candidate_focus_blocks)
    ? suggestion.candidate_focus_blocks.slice(0, 2).map((option) => {
      const intendedItems = (option.intended_for_event_ids || []).map((eventId) => {
        return resolveTargetEvent(eventId)
      }).filter(Boolean)

      return {
        intended_event_ids: option.intended_for_event_ids || [],
        intended_titles: intendedItems.length
          ? intendedItems.map((item) => item.title)
          : (option.intended_for_event_ids || []).map((eventId) => `事项 ${eventId}`),
        intended_current_times: intendedItems.map((item) => item.current_time).filter(Boolean),
        suggested_time: formatSourceDateRange(option.suggested_start_time, option.suggested_end_time),
        suggested_start: normalizePreviewDateTime(option.suggested_start_time),
        suggested_end: normalizePreviewDateTime(option.suggested_end_time),
        reason: option.reason || '',
        rank: option.rank ?? 1,
      }
    })
    : []

  const splitOptions = Array.isArray(suggestion?.candidate_split_options)
    ? suggestion.candidate_split_options.slice(0, 1).map((option) => {
      const targetEvent = resolveTargetEvent(option.target_event_id)
      const suggestedSegments = (option.segments || []).map((segment) => ({
        suggested_time: formatSourceDateRange(segment.suggested_start_time, segment.suggested_end_time),
        suggested_start: normalizePreviewDateTime(segment.suggested_start_time),
        suggested_end: normalizePreviewDateTime(segment.suggested_end_time),
      })).filter((segment) => segment.suggested_start)

      return {
        action: option.action || 'split',
        target_event_id: option.target_event_id,
        target_title: targetEvent?.title || `事项 ${option.target_event_id}`,
        current_time: targetEvent?.current_time || '未提供时间',
        original_start: targetEvent?.start_time || targetEvent?.deadline || null,
        original_end: targetEvent?.end_time || targetEvent?.deadline || null,
        suggested_time: suggestedSegments.map((segment) => segment.suggested_time).join(' / '),
        suggested_segments: suggestedSegments,
        total_duration_minutes: option.total_duration_minutes ?? 0,
        reason: option.reason || '',
        rank: option.rank ?? 1,
      }
    })
    : []

  return {
    type: suggestion?.type || '',
    level: suggestion?.level || 'info',
    message: suggestion?.message || '',
    related_items: relatedItems,
    reschedule_options: rescheduleOptions,
    focus_block_options: focusBlockOptions,
    split_options: splitOptions,
  }
}

function normalizePreviewType(value) {
  const normalized = cleanInlineText(value).toLowerCase()
  if (['move', 'focus_block', 'split', 'reschedule'].includes(normalized)) {
    return normalized
  }
  return ''
}

function normalizePreviewDateTime(value) {
  if (typeof value !== 'string') return ''

  const normalized = cleanInlineText(value).replace(' ', 'T')
  const parsed = parseLocalDateTimeString(normalized)
  if (parsed) {
    return formatLocalDateTime(parsed)
  }

  const match = normalized.match(/(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2})(?::(\d{2}))?/)
  if (!match) return ''
  return `${match[1]}T${match[2]}:${match[3] || '00'}`
}

function parsePreviewRangeText(value) {
  const normalized = cleanInlineText(value).replace(/^截止\s*/, '')
  if (!normalized) return null

  const matches = normalized.match(/\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}(?::\d{2})?/g)
  if (!matches?.length) return null

  const start = normalizePreviewDateTime(matches[0])
  const end = normalizePreviewDateTime(matches[1])
  if (!start) return null

  return {
    start,
    end: end && compareLocalDateTime(end, start) >= 0 ? end : '',
  }
}

function normalizePreviewSegments(rawSegments = []) {
  if (!Array.isArray(rawSegments)) {
    return []
  }

  return rawSegments.map((segment, index) => {
    const start = normalizePreviewDateTime(segment?.start || segment?.suggested_start)
    const end = normalizePreviewDateTime(segment?.end || segment?.suggested_end)
    const fallbackRange = parsePreviewRangeText(segment?.suggested_time || segment?.time || '')
    const suggestedStart = start || fallbackRange?.start || ''
    const suggestedEnd = end || fallbackRange?.end || ''

    if (!suggestedStart) {
      return null
    }

    return {
      id: `segment-${index + 1}`,
      suggested_start: suggestedStart,
      suggested_end: suggestedEnd,
      suggested_time: segment?.suggested_time
        || formatSourceDateRange(suggestedStart, suggestedEnd || suggestedStart),
    }
  }).filter(Boolean)
}

function normalizePreviewMatchText(value) {
  return cleanInlineText(value)
    .replace(/[，、]/g, ' ')
    .replace(/\s+/g, ' ')
    .toLowerCase()
}

function isPreviewTextMatch(left, right) {
  const normalizedLeft = normalizePreviewMatchText(left)
  const normalizedRight = normalizePreviewMatchText(right)
  if (!normalizedLeft || !normalizedRight) return false
  return normalizedLeft === normalizedRight
    || normalizedLeft.includes(normalizedRight)
    || normalizedRight.includes(normalizedLeft)
}

function buildAnalysisPreviewCandidates(aggregateResult) {
  const analysis = aggregateResult?.analysis || {}
  const timeline = Array.isArray(aggregateResult?.timeline) ? aggregateResult.timeline : []
  const eventLookup = buildEventLookup(timeline)
  const previewCandidates = []

  const resolveTargetEvent = (eventId) => getEventSummaryById(eventLookup, eventId)

  ;(analysis.suggestions || []).forEach((suggestion, suggestionIndex) => {
    ;(suggestion?.candidate_reschedule_options || []).slice(0, 2).forEach((option, optionIndex) => {
      const targetEvent = resolveTargetEvent(option.target_event_id)
      if (!targetEvent?.title) return

      previewCandidates.push({
        id: `reschedule-${suggestionIndex}-${optionIndex}`,
        preview_type: 'reschedule',
        item_title: targetEvent.title,
        match_titles: [targetEvent.title],
        current_time: targetEvent.current_time || '',
        suggested_time: formatSourceDateRange(option.suggested_start_time, option.suggested_end_time),
        original_start: targetEvent.start_time || targetEvent.deadline || '',
        original_end: targetEvent.end_time || targetEvent.deadline || '',
        suggested_start: normalizePreviewDateTime(option.suggested_start_time),
        suggested_end: normalizePreviewDateTime(option.suggested_end_time),
        suggested_segments: [],
      })
    })

    ;(suggestion?.candidate_focus_blocks || []).slice(0, 2).forEach((option, optionIndex) => {
      const intendedItems = (option.intended_for_event_ids || []).map((eventId) => {
        return resolveTargetEvent(eventId)
      }).filter(Boolean)
      const intendedTitles = intendedItems.length
        ? intendedItems.map((item) => item.title)
        : (option.intended_for_event_ids || []).map((eventId) => `事项 ${eventId}`)

      previewCandidates.push({
        id: `focus-${suggestionIndex}-${optionIndex}`,
        preview_type: 'focus_block',
        item_title: intendedTitles.join(' / '),
        match_titles: intendedTitles,
        current_time: intendedItems.map((item) => item.current_time).filter(Boolean).join(' / '),
        suggested_time: formatSourceDateRange(option.suggested_start_time, option.suggested_end_time),
        original_start: '',
        original_end: '',
        suggested_start: normalizePreviewDateTime(option.suggested_start_time),
        suggested_end: normalizePreviewDateTime(option.suggested_end_time),
        suggested_segments: [],
      })
    })

    ;(suggestion?.candidate_split_options || []).slice(0, 1).forEach((option, optionIndex) => {
      const targetEvent = resolveTargetEvent(option.target_event_id)
      if (!targetEvent?.title) return

      const suggestedSegments = (option.segments || []).map((segment, segmentIndex) => {
        const suggestedStart = normalizePreviewDateTime(segment?.suggested_start_time)
        const suggestedEnd = normalizePreviewDateTime(segment?.suggested_end_time)
        if (!suggestedStart) return null

        return {
          id: `split-${suggestionIndex}-${optionIndex}-${segmentIndex}`,
          suggested_start: suggestedStart,
          suggested_end: suggestedEnd,
          suggested_time: formatSourceDateRange(suggestedStart, suggestedEnd || suggestedStart),
        }
      }).filter(Boolean)

      previewCandidates.push({
        id: `split-${suggestionIndex}-${optionIndex}`,
        preview_type: 'split',
        item_title: targetEvent.title,
        match_titles: [targetEvent.title],
        current_time: targetEvent.current_time || '',
        suggested_time: suggestedSegments.map((segment) => segment.suggested_time).join(' / '),
        original_start: targetEvent.start_time || targetEvent.deadline || '',
        original_end: targetEvent.end_time || targetEvent.deadline || '',
        suggested_start: suggestedSegments[0]?.suggested_start || '',
        suggested_end: suggestedSegments[0]?.suggested_end || '',
        suggested_segments: suggestedSegments,
      })
    })
  })

  return previewCandidates
}

function findMatchingPreviewCandidate(adjustment, previewCandidates = []) {
  const itemTitle = adjustment?.item_title || ''
  const currentTime = adjustment?.current_time || ''
  const suggestedTime = adjustment?.suggested_time || ''

  const matchesTitle = (candidate) => {
    return [candidate.item_title, ...(candidate.match_titles || [])].some((title) => {
      return isPreviewTextMatch(itemTitle, title)
    })
  }

  return previewCandidates.find((candidate) => {
    return matchesTitle(candidate) && isPreviewTextMatch(suggestedTime, candidate.suggested_time)
  })
    || previewCandidates.find((candidate) => {
      return matchesTitle(candidate) && isPreviewTextMatch(currentTime, candidate.current_time)
    })
    || previewCandidates.find((candidate) => matchesTitle(candidate))
    || null
}

function inferPreviewType(rawType, matchedPreview, suggestedSegments, originalStart, suggestedStart, suggestedEnd) {
  if (rawType) return rawType
  if (matchedPreview?.preview_type) return matchedPreview.preview_type
  if (suggestedSegments.length > 1) return 'split'
  if (originalStart && suggestedStart && originalStart !== suggestedStart) return 'move'
  if (suggestedStart || suggestedEnd) return 'focus_block'
  return 'reschedule'
}

function buildAiPlanPromptPayload(aggregateResult) {
  const analysis = aggregateResult?.analysis || {}
  const timeline = Array.isArray(aggregateResult?.timeline) ? aggregateResult.timeline : []
  const eventLookup = buildEventLookup(timeline)

  return {
    range_label: dataSourceSummary.value.rangeLabel || weekRangeLabel.value,
    source_summary: {
      total_todo_count: dataSourceSummary.value.totalTodoCount || 0,
      pending_todo_count: dataSourceSummary.value.pendingTodoCount || 0,
      included_sources: (dataSourceSummary.value.includedSources || []).map((source) => ({
        label: source.label,
        count: source.count,
        detail: source.detail,
      })),
    },
    summary: analysis.summary || {},
    ai_context: analysis.ai_context || {},
    conflicts: (analysis.conflicts || []).slice(0, 4).map((conflict) => ({
      level: conflict.level,
      reason: conflict.reason,
      overlap_time: formatSourceDateRange(conflict.overlap_start_time, conflict.overlap_end_time),
      left_item: buildCompactEvent(conflict.left_event),
      right_item: buildCompactEvent(conflict.right_event),
    })),
    pileups: (analysis.pileups || []).slice(0, 4).map((pileup) => ({
      level: pileup.level,
      reason: pileup.reason,
      event_count: pileup.event_count,
      time_window: formatSourceDateRange(pileup.start_time, pileup.end_time),
      items: (pileup.events || []).slice(0, 5).map(buildCompactEvent).filter(Boolean),
    })),
    suggestions: (analysis.suggestions || []).slice(0, 8).map((suggestion) => {
      return buildCompactSuggestion(suggestion, eventLookup)
    }),
  }
}

function buildAiPlanPrompt(aggregateResult) {
  const promptPayload = buildAiPlanPromptPayload(aggregateResult)
  return [
    '忽略本 session 中任何旧对话，只根据本次提供的 schedule aggregate-analysis 结果生成候选优化方案。',
    '你不能根据原始 todo 自行脑补新的空闲时间、时长、事项或冲突；只能使用输入 JSON 中已经给出的事实。',
    '优先复用 suggestions 里的候选时间、focus block、split option 和 ai_context 信息，生成具体可执行的调整方案。',
    '请返回严格 JSON，不要返回 markdown，不要返回解释，不要返回代码块。',
    'JSON 必须严格符合以下结构：',
    '{"plans":[{"id":"kebab-case-id","name":"方案名称","goal":"方案优先目标","summary":"方案概述","adjustments":[{"item_title":"事项标题","current_time":"当前时间","suggested_time":"建议时间","reason":"调整原因","expected_effect":"预期效果","preview_type":"move","original_start":"2026-04-16T09:00:00","original_end":"2026-04-16T10:00:00","suggested_start":"2026-04-16T11:00:00","suggested_end":"2026-04-16T12:00:00","suggested_segments":[]}]}]}',
    '硬性要求：',
    '1. 返回 2 到 3 个 plan。',
    '2. 每个 plan 必须包含 2 到 4 个 adjustments，且 adjustments 必须具体、可执行、时间明确。',
    '3. item_title 必须来自输入中的真实事项标题；current_time 和 suggested_time 必须是北京时间的人类可读时间。',
    '4. preview_type 必须是 move、focus_block、split、reschedule 之一。',
    '5. original_start、original_end、suggested_start、suggested_end、suggested_segments 必须直接复用输入 JSON 中已经提供的精确时间；不要自造新时间。',
    '6. 如果某个 adjustment 没有 original_start/original_end，就返回 null；split 类型请在 suggested_segments 中返回所有拆分片段，每个片段使用 {"start":"...","end":"..."}。',
    '7. goal 和 summary 要体现该方案的优化重点，但不能只是泛泛的策略标签。',
    '8. 如果输入里没有足够依据，就不要编造；请优先选择已有候选时间最明确的事项。',
    `分析输入 JSON：${JSON.stringify(promptPayload)}`,
  ].join('\n')
}

function normalizeAiPlanAdjustment(rawAdjustment, index, previewCandidates = []) {
  const itemTitle = cleanInlineText(rawAdjustment?.item_title)
  const currentTime = cleanInlineText(rawAdjustment?.current_time)
  const suggestedTime = cleanInlineText(rawAdjustment?.suggested_time)
  const reason = cleanInlineText(rawAdjustment?.reason)
  const expectedEffect = cleanInlineText(rawAdjustment?.expected_effect)

  if (!itemTitle || !currentTime || !suggestedTime || !reason || !expectedEffect) {
    return null
  }

  const matchedPreview = findMatchingPreviewCandidate(
    {
      item_title: itemTitle,
      current_time: currentTime,
      suggested_time: suggestedTime,
    },
    previewCandidates
  )
  const currentRange = parsePreviewRangeText(currentTime)
  const suggestedRange = parsePreviewRangeText(suggestedTime)
  const rawSegments = normalizePreviewSegments(rawAdjustment?.suggested_segments)
  const matchedSegments = Array.isArray(matchedPreview?.suggested_segments) ? matchedPreview.suggested_segments : []
  const suggestedSegments = rawSegments.length ? rawSegments : matchedSegments
  const originalStart = normalizePreviewDateTime(rawAdjustment?.original_start)
    || matchedPreview?.original_start
    || currentRange?.start
    || ''
  const originalEnd = normalizePreviewDateTime(rawAdjustment?.original_end)
    || matchedPreview?.original_end
    || currentRange?.end
    || ''
  const suggestedStart = normalizePreviewDateTime(rawAdjustment?.suggested_start)
    || suggestedSegments[0]?.suggested_start
    || matchedPreview?.suggested_start
    || suggestedRange?.start
    || ''
  const suggestedEnd = normalizePreviewDateTime(rawAdjustment?.suggested_end)
    || suggestedSegments[0]?.suggested_end
    || matchedPreview?.suggested_end
    || suggestedRange?.end
    || ''
  const previewType = inferPreviewType(
    normalizePreviewType(rawAdjustment?.preview_type),
    matchedPreview,
    suggestedSegments,
    originalStart,
    suggestedStart,
    suggestedEnd
  )

  return {
    id: `adjustment-${index + 1}-${itemTitle}`,
    item_title: itemTitle,
    current_time: currentTime,
    suggested_time: suggestedTime,
    reason,
    expected_effect: expectedEffect,
    preview_type: previewType,
    original_start: originalStart,
    original_end: originalEnd,
    suggested_start: suggestedStart,
    suggested_end: suggestedEnd,
    suggested_segments: suggestedSegments,
  }
}

function normalizeAiCandidatePlan(rawPlan, index, previewCandidates = []) {
  const name = cleanInlineText(rawPlan?.name)
  const goal = cleanInlineText(rawPlan?.goal)
  const summaryText = cleanInlineText(rawPlan?.summary)
  const rawAdjustments = Array.isArray(rawPlan?.adjustments) ? rawPlan.adjustments : []
  const adjustments = rawAdjustments
    .slice(0, 4)
    .map((adjustment, adjustmentIndex) => normalizeAiPlanAdjustment(adjustment, adjustmentIndex, previewCandidates))
    .filter(Boolean)

  if (!name || !goal || !summaryText || adjustments.length < 2) {
    return null
  }

  return {
    id: normalizePlanId(rawPlan?.id, index),
    name,
    goal,
    summary: summaryText,
    adjustments,
  }
}

function parseAiCandidatePlansResponse(content, aggregateResult) {
  const parsed = JSON.parse(stripCodeFences(content))
  const rawPlans = Array.isArray(parsed) ? parsed : parsed?.plans
  if (!Array.isArray(rawPlans) || !rawPlans.length) {
    throw new Error('AI 未返回有效的候选优化方案')
  }

  const previewCandidates = buildAnalysisPreviewCandidates(aggregateResult)
  const normalizedPlans = rawPlans
    .slice(0, 3)
    .map((plan, index) => normalizeAiCandidatePlan(plan, index, previewCandidates))
    .filter(Boolean)

  if (normalizedPlans.length < 2) {
    throw new Error('AI 返回的候选优化方案不足 2 个')
  }

  return normalizedPlans
}

async function ensureAnalysisAiSession() {
  if (analysisAiSessionId.value) {
    return analysisAiSessionId.value
  }

  const result = await createSession({
    user_id: userStore.id,
    title: '日程优化方案',
  })

  const sessionId = result?.data?.id
  if (!sessionId) {
    throw new Error(result?.message || '创建优化方案 AI 会话失败')
  }

  analysisAiSessionId.value = sessionId
  return sessionId
}

async function requestAiCandidatePlans(prompt) {
  let attempt = 0
  while (attempt < 2) {
    attempt += 1
    try {
      const sessionId = await ensureAnalysisAiSession()
      return await sendAiContent({
        session_id: sessionId,
        content: prompt,
        files: null,
        file_types: null,
        file_names: null,
      })
    } catch (error) {
      if (attempt >= 2) {
        throw error
      }
      analysisAiSessionId.value = null
    }
  }
  throw new Error('AI 候选方案请求失败')
}

async function generateAiCandidatePlans(aggregateResult) {
  const prompt = buildAiPlanPrompt(aggregateResult)
  const aiResult = await requestAiCandidatePlans(prompt)
  const newMessages = Array.isArray(aiResult?.data) ? aiResult.data : []
  const assistantMessage = [...newMessages].reverse().find((item) => item.role === 'assistant')
  if (!assistantMessage?.content) {
    throw new Error('未收到有效的 AI 优化方案回复')
  }
  return parseAiCandidatePlansResponse(assistantMessage.content, aggregateResult)
}

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

async function loadBlackboardTodosOnly() {
  if (!userStore.isLoggedIn) {
    blackboardTodos.value = []
    return
  }

  try {
    const result = await getBlackboardList()
    blackboardTodos.value = Array.isArray(result.data) ? result.data : []
  } catch (error) {
    ElMessage.error(error.message || '加载 Blackboard 导入数据失败')
  }
}

function isImportedBlackboardTodo(todo) {
  return todo?.import_source === 'blackboard'
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

async function refreshTodoStateAfterMutation() {
  invalidateAnalysisAfterDataChange()
  await loadTodos()
}

async function refreshBlackboardSourceStateAfterMutation(todo) {
  if (!isImportedBlackboardTodo(todo)) return
  await loadBlackboardTodosOnly()
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

function buildSelectedPlanPreviewAdjustments(plan) {
  if (!plan?.adjustments?.length) {
    return []
  }

  return plan.adjustments.flatMap((adjustment, adjustmentIndex) => {
    const suggestedSegments = Array.isArray(adjustment?.suggested_segments) && adjustment.suggested_segments.length
      ? adjustment.suggested_segments
      : adjustment?.suggested_start
        ? [{
          suggested_start: adjustment.suggested_start,
          suggested_end: adjustment.suggested_end,
          suggested_time: adjustment.suggested_time,
        }]
        : []

    return suggestedSegments.map((segment, segmentIndex) => {
      const suggestedStart = segment?.suggested_start || ''
      const suggestedEnd = segment?.suggested_end || ''
      if (!suggestedStart) return null

      return {
        id: `${plan.id}-${adjustment.id}-${segmentIndex + 1}`,
        plan_id: plan.id,
        adjustment_id: adjustment.id,
        item_title: adjustment.item_title,
        original_start: adjustment.original_start || '',
        original_end: adjustment.original_end || '',
        suggested_start: suggestedStart,
        suggested_end: suggestedEnd,
        current_time: adjustment.current_time,
        suggested_time: segment?.suggested_time || formatSourceDateRange(suggestedStart, suggestedEnd || suggestedStart),
        reason: adjustment.reason,
        expected_effect: adjustment.expected_effect,
        preview_type: adjustment.preview_type || 'reschedule',
        preview_label: suggestedSegments.length > 1 ? `AI Preview ${segmentIndex + 1}` : 'AI Preview',
      }
    }).filter(Boolean)
  })
}

const selectedPlanPreviewAdjustments = computed(() => {
  return buildSelectedPlanPreviewAdjustments(selectedPlan.value)
})

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
    const createdTodoPayload = {
      ...payload,
      status: 'pending',
    }
    const result = await createTodo(createdTodoPayload)
    const createdTodo = result?.data || createdTodoPayload
    ElMessage.success('Todo 已创建')
    dialogVisible.value = false
    await Promise.all([
      refreshTodoStateAfterMutation(),
      refreshBlackboardSourceStateAfterMutation(createdTodo),
    ])
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

    invalidateAnalysisAfterDataChange()
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

async function handleRunAnalysis() {
  if (!userStore.isLoggedIn) {
    ElMessage.error('请先登录')
    return
  }

  const requestVersion = analysisRequestVersion.value + 1
  analysisRequestVersion.value = requestVersion
  analysisVisible.value = true
  analysisLoading.value = true
  analysisPlanLoading.value = false
  analysisError.value = ''
  analysisPlanError.value = ''
  analysisCandidatePlans.value = []
  selectedPlan.value = null

  let nextAggregateAnalysis = null

  try {
    const result = await getScheduleAggregateAnalysis({
      start_time: currentWeekQueryRange.value.start_time,
      end_time: currentWeekQueryRange.value.end_time,
      include_blackboard: true,
      include_background_markers: true,
      include_completed: false,
      include_course_schedule: true,
    })
    if (requestVersion !== analysisRequestVersion.value) return
    nextAggregateAnalysis = result?.data || null
    aggregateAnalysis.value = nextAggregateAnalysis
  } catch (error) {
    if (requestVersion !== analysisRequestVersion.value) return
    aggregateAnalysis.value = null
    analysisError.value = error.message || '分析失败'
    ElMessage.error(error.message || '日程分析失败')
  } finally {
    if (requestVersion === analysisRequestVersion.value) {
      analysisLoading.value = false
    }
  }

  if (!nextAggregateAnalysis || requestVersion !== analysisRequestVersion.value) {
    return
  }

  analysisPlanLoading.value = true
  try {
    const plans = await generateAiCandidatePlans(nextAggregateAnalysis)
    if (requestVersion !== analysisRequestVersion.value) return
    analysisCandidatePlans.value = plans
  } catch (error) {
    if (requestVersion !== analysisRequestVersion.value) return
    analysisCandidatePlans.value = []
    analysisPlanError.value = error.message || 'AI 候选优化方案生成失败'
    ElMessage.error(error.message || 'AI 候选优化方案生成失败')
  } finally {
    if (requestVersion === analysisRequestVersion.value) {
      analysisPlanLoading.value = false
    }
  }
}

function handleSelectPlan(plan) {
  const nextPlanId = String(plan?.id || '')
  if (!nextPlanId) {
    selectedPlan.value = null
    return
  }

  if (selectedPlan.value?.id === nextPlanId) {
    selectedPlan.value = null
    return
  }

  selectedPlan.value = analysisCandidatePlans.value.find((item) => String(item.id) === nextPlanId) || plan
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
    let mutatedTodo = actionDraft.target || null

    if (actionDraft.action === 'create') {
      const result = await createTodo(actionDraft.payload)
      mutatedTodo = result?.data || actionDraft.payload
      ElMessage.success('Todo 已创建')
      pushAiFeedback('success', `已创建事项：${actionDraft.payload.title}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'update') {
      const result = await updateTodo(actionDraft.targetId, actionDraft.payload)
      mutatedTodo = result?.data
        ? { ...(actionDraft.target || {}), ...result.data }
        : { ...(actionDraft.target || {}), ...actionDraft.payload }
      ElMessage.success('Todo 已更新')
      pushAiFeedback('success', `已更新事项：${actionDraft.target?.title || actionDraft.payload.title}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'delete') {
      await deleteTodo(actionDraft.targetId)
      ElMessage.success('Todo 已删除')
      pushAiFeedback('success', `已删除事项：${actionDraft.target?.title || '待办事项'}。周历和待办列表已同步刷新。`)
    } else if (actionDraft.action === 'mark_done' || actionDraft.action === 'mark_pending') {
      const result = await updateTodoStatus(actionDraft.targetId, actionDraft.payload.status)
      mutatedTodo = result?.data
        ? { ...(actionDraft.target || {}), ...result.data }
        : { ...(actionDraft.target || {}), ...actionDraft.payload }
      ElMessage.success('状态已更新')
      pushAiFeedback(
        'success',
        `已将事项“${actionDraft.target?.title || '待办事项'}”更新为${actionDraft.payload.status === 'done' ? '已完成' : '待办中'}。周历和待办列表已同步刷新。`
      )
    }

    await Promise.all([
      refreshTodoStateAfterMutation(),
      refreshBlackboardSourceStateAfterMutation(mutatedTodo),
    ])
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
    const previousTodo = selectedTodo.value
    const result = await updateTodo(previousTodo.id, payload)
    const updatedTodo = result?.data
      ? { ...previousTodo, ...result.data }
      : { ...previousTodo, ...payload }
    syncSelectedTodo(updatedTodo)
    ElMessage.success('Todo 已更新')
    await Promise.all([
      refreshTodoStateAfterMutation(),
      refreshBlackboardSourceStateAfterMutation(updatedTodo),
    ])
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
    const deletedTodo = selectedTodo.value
    await deleteTodo(deletedTodo.id)
    ElMessage.success('Todo 已删除')
    detailDialogVisible.value = false
    syncSelectedTodo(null)
    await Promise.all([
      refreshTodoStateAfterMutation(),
      refreshBlackboardSourceStateAfterMutation(deletedTodo),
    ])
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
    const previousTodo = selectedTodo.value
    const result = await updateTodoStatus(previousTodo.id, status)
    const updatedTodo = result?.data
      ? { ...previousTodo, ...result.data }
      : { ...previousTodo, status }
    syncSelectedTodo(updatedTodo)
    ElMessage.success('状态已更新')
    await Promise.all([
      refreshTodoStateAfterMutation(),
      refreshBlackboardSourceStateAfterMutation(updatedTodo),
    ])
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
      analysisAiSessionId.value = null
      allTodos.value = []
      officialCalendarEvents.value = []
      courseScheduleEvents.value = []
      blackboardTodos.value = []
      officialCalendarBackgroundMarkers.value = []
      lastImportSummary.value = null
      resetAnalysisState()
    }
  }
)

watch(
  () => [currentWeekQueryRange.value.start_time, currentWeekQueryRange.value.end_time, userStore.isLoggedIn],
  ([, , isLoggedIn]) => {
    if (isLoggedIn) {
      resetAnalysisState()
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
  align-items: flex-start;
}

.todo-main {
  display: flex;
  flex-direction: column;
  min-width: 0;
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
  height: 46vh;
  min-height: 320px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.source-preview-panel.collapsed {
  height: auto;
  min-height: 0;
}

.source-preview-top {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.source-preview-controls {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.source-preview-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.source-preview-count {
  padding: 8px 12px;
  border-radius: 999px;
  background: #edf3fb;
  color: #47607f;
  font-size: 13px;
  font-weight: 700;
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

.preview-collapse-btn {
  border: 1px solid rgba(69, 96, 142, 0.18);
  background: #fff;
  color: #47607f;
  border-radius: 999px;
  padding: 9px 14px;
  cursor: pointer;
  font-weight: 700;
}

.preview-tab.active {
  background: #153e8f;
  color: #fff;
}

.source-preview-body {
  flex: 1;
  min-height: 0;
  margin-top: 16px;
  overflow-y: auto;
  padding-right: 4px;
}

.source-preview-body .import-summary {
  margin-top: 0;
}

.source-preview-body > .source-list:first-child {
  margin-top: 0;
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
