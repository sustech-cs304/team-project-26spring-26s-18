<template>
  <section class="todo-ai-panel">
    <div class="panel-header">
      <div>
        <div class="eyebrow">TODO 助手</div>
        <h2>AI 规划助手</h2>
      </div>
      <div class="status-pill">轻量模式</div>
    </div>

    <div class="assistant-main-scroll">
      <div class="conversation-area">
        <div
          v-for="message in messages"
          :key="message.id"
          class="message-row"
          :class="message.role"
        >
          <div class="bubble">
            {{ message.content }}
          </div>
        </div>
        <div v-if="loading" class="message-row assistant">
          <div class="bubble loading-bubble">正在解析操作草案...</div>
        </div>
      </div>

      <section class="analysis-panel">
        <div class="analysis-panel-top">
          <div>
            <div class="analysis-eyebrow">Schedule Analysis</div>
            <h3>优化方案提出与选择</h3>
          </div>
          <button class="analysis-trigger" :disabled="analysisLoading" @click="emit('run-analysis')">
            {{ analysisTriggerLabel }}
          </button>
        </div>

        <div class="analysis-card">
          <div class="analysis-card-title">数据来源</div>
          <div class="analysis-source-overview">
            <div class="analysis-metric">
              <span>分析范围</span>
              <strong>{{ dataSourceSummary.rangeLabel || '当前视图' }}</strong>
            </div>
            <div class="analysis-metric">
              <span>待办总量</span>
              <strong>{{ dataSourceSummary.totalTodoCount || 0 }}</strong>
            </div>
            <div class="analysis-metric">
              <span>未完成个人事项</span>
              <strong>{{ dataSourceSummary.pendingTodoCount || 0 }}</strong>
            </div>
          </div>
          <div class="analysis-source-list">
            <div
              v-for="source in dataSourceSummary.includedSources || []"
              :key="source.key"
              class="analysis-source-item"
            >
              <strong>{{ source.label }}</strong>
              <span>{{ source.count }} 条</span>
              <small>{{ source.detail }}</small>
            </div>
          </div>
          <div class="analysis-helper">
            分析基于已导入的课程表、校历和 Blackboard 数据；日历显示开关不会改变分析结果。
          </div>
        </div>

        <template v-if="analysisVisible">
          <div v-if="analysisError" class="analysis-card analysis-card-error">
            {{ analysisError }}
          </div>

          <template v-else-if="analysisLoading">
            <div class="analysis-card analysis-card-loading">正在聚合当前周的日程、课程和截止事项...</div>
          </template>

          <template v-else-if="analysisData">
            <div class="analysis-card">
              <div class="analysis-card-title">检测结果</div>
              <div class="analysis-metric-list">
                <div class="analysis-metric">
                  <span>风险等级</span>
                  <strong>{{ riskLabel }}</strong>
                </div>
                <div class="analysis-metric">
                  <span>时间冲突</span>
                  <strong>{{ summary.conflict_count || 0 }}</strong>
                </div>
                <div class="analysis-metric">
                  <span>堆积时段</span>
                  <strong>{{ summary.pileup_count || 0 }}</strong>
                </div>
                <div class="analysis-metric">
                  <span>候选建议</span>
                  <strong>{{ summary.suggestion_count || 0 }}</strong>
                </div>
              </div>
              <div v-if="topInsights.length" class="analysis-insight-list">
                <div
                  v-for="item in topInsights"
                  :key="item.key"
                  class="analysis-insight-item"
                >
                  <strong>{{ item.label }}</strong>
                  <span>{{ item.text }}</span>
                </div>
              </div>
              <div v-else class="analysis-empty">
                当前范围内没有明显冲突或堆积，整体安排较平稳。
              </div>
            </div>

            <div class="analysis-card">
              <div class="analysis-card-title">AI 候选优化方案（当前分析参考）</div>
              <div class="analysis-helper">
                候选方案基于 aggregate-analysis 的结构化结果由 AI 生成。选择后会在周历上预览建议调整，但不会保存到后端，也不会直接改写当前 Todo。
              </div>
              <div v-if="planGenerationLoading" class="analysis-card-loading">
                Generating AI suggestions...
              </div>
              <div v-else-if="planGenerationError" class="analysis-empty">
                {{ planGenerationError }}
              </div>
              <div v-else-if="candidatePlans.length" class="plan-list">
                <article
                  v-for="plan in candidatePlans"
                  :key="plan.id"
                  class="plan-card"
                  :class="{ selected: selectedPlanId === plan.id }"
                  @click="selectPlan(plan)"
                >
                  <div class="plan-card-head">
                    <div>
                      <strong>{{ plan.name }}</strong>
                      <div class="plan-subtitle">优先目标：{{ plan.goal }}</div>
                    </div>
                    <div class="plan-badges">
                      <span class="plan-badge">{{ plan.adjustmentCount }} 项调整</span>
                      <span class="plan-badge ai">AI 生成</span>
                    </div>
                  </div>
                  <p class="plan-reason">{{ plan.summary }}</p>
                  <div class="plan-action-list">
                    <div
                      v-for="item in plan.adjustments"
                      :key="item.key"
                      class="plan-action-item"
                    >
                      <strong>{{ item.itemTitle }}</strong>
                      <span class="plan-timing">{{ item.currentTime }} → {{ item.suggestedTime }}</span>
                      <small>原因：{{ item.reason }}</small>
                      <small>预期效果：{{ item.expectedEffect }}</small>
                      <small v-if="!canApplyPlanAdjustment(item)" class="plan-action-warning">
                        缺少目标事项或建议时间，只能作为预览参考。
                      </small>
                      <div class="plan-action-controls">
                        <button
                          class="plan-action-btn apply"
                          :disabled="isPlanActionBusy || !canApplyPlanAdjustment(item)"
                          @click.stop="emit('apply-plan-adjustment', { planId: plan.id, adjustmentId: item.id })"
                        >
                          {{ planActionBusyId === getPlanActionBusyId(plan, item) ? '应用中...' : '应用此建议' }}
                        </button>
                        <button
                          class="plan-action-btn ignore"
                          :disabled="isPlanActionBusy"
                          @click.stop="emit('cancel-plan-adjustment', { planId: plan.id, adjustmentId: item.id })"
                        >
                          忽略
                        </button>
                      </div>
                    </div>
                  </div>
                  <button
                    class="plan-select-btn"
                    :class="{ selected: selectedPlanId === plan.id }"
                    @click.stop="selectPlan(plan)"
                  >
                    {{ selectedPlanId === plan.id ? '取消日历预览' : '在周历中预览此方案' }}
                  </button>
                </article>
              </div>
              <div v-else class="analysis-empty">
                当前分析尚未生成 AI 候选方案。
              </div>
            </div>
          </template>

          <div v-else class="analysis-card analysis-empty-state">
            点击 “Analyze My Schedule” 后，将基于当前 Todo、课程表、校历和 Blackboard 数据生成优化建议。
          </div>
        </template>
      </section>

      <div class="confirmation-card">
        <div class="card-title">待确认操作</div>
        <template v-if="previewAction">
          <div class="card-item">
            <span>操作类型</span>
            <strong>{{ actionLabel(previewAction.action) }}</strong>
          </div>
          <div v-if="previewAction.target" class="card-item">
            <span>匹配事项</span>
            <strong>{{ formatTodoSummary(previewAction.target) }}</strong>
          </div>
          <div v-else-if="previewAction.targetHint" class="card-item">
            <span>目标线索</span>
            <strong>{{ previewAction.targetHint }}</strong>
          </div>

          <template v-if="previewAction.action === 'create'">
            <div class="card-item">
              <span>标题</span>
              <strong>{{ previewAction.payload.title }}</strong>
            </div>
            <div class="card-item">
              <span>内容</span>
              <strong>{{ previewAction.payload.content || '无' }}</strong>
            </div>
            <div class="card-item card-item-stack">
              <span>最终时间</span>
              <strong>{{ formatDraftTiming(previewAction.payload) }}</strong>
            </div>
            <div class="card-item">
              <span>优先级</span>
              <strong>{{ priorityText(previewAction.payload.priority) }}</strong>
            </div>
          </template>

          <template v-else-if="previewAction.action === 'update'">
            <div
              v-for="field in previewAction.changedFields"
              :key="field.label"
              class="card-item card-item-stack"
            >
              <span>{{ field.label }}</span>
              <strong>{{ field.to }}</strong>
              <small>原值：{{ field.from }}</small>
            </div>
            <div class="card-item card-item-stack">
              <span>最终时间</span>
              <strong>{{ formatDraftTiming(previewAction.payload) }}</strong>
            </div>
          </template>

          <template v-else-if="previewAction.action === 'delete'">
            <div class="card-note danger-note">确认后会删除该事项，后端不会自动回滚。</div>
          </template>

          <template v-else>
            <div class="card-item">
              <span>目标状态</span>
              <strong>{{ statusText(previewAction.payload.status) }}</strong>
            </div>
          </template>

          <div v-if="previewAction.blockedReason" class="card-note blocked-note">
            {{ previewAction.blockedReason }}
          </div>
          <div
            v-if="previewAction.candidates?.length && !previewAction.canConfirm"
            class="candidate-list"
          >
            <div
              v-for="item in previewAction.candidates"
              :key="item.id"
              class="candidate-item"
            >
              {{ formatTodoSummary(item) }}
            </div>
          </div>
          <div class="card-actions">
            <button class="confirm-btn" :disabled="confirmDisabled" @click="confirmAction">确认执行</button>
            <button class="cancel-btn" :disabled="confirming" @click="clearPreview">取消</button>
          </div>
        </template>
        <div v-else class="card-note">
          输入自然语言后，AI 会先返回结构化操作草案。只有你点击“确认执行”后，才会调用后端新增、修改、删除或更新状态。
        </div>
      </div>
    </div>

    <div class="input-area">
      <textarea
        v-model="draft"
        class="chat-input"
        placeholder="例如：把周三下午 3 点的数据库作业改到 4 点，或者删除明晚 8 点的跑步提醒"
        @keyup.ctrl.enter="sendDraft"
      />
      <button class="send-btn" :disabled="loading || !draft.trim()" @click="sendDraft">发送</button>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { ip } from '@/config/config'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { matchTodoActionTarget } from '@/utils/todoActionMatcher'
import {
  BEIJING_TIMEZONE,
  findConflictingRangeTodo,
  formatDisplayLocalDateTime,
  getTodoTimingSummary,
  formatLocalDateTime,
  getBeijingNowParts,
  normalizeAiTodoDraft,
  compareLocalDateTime,
} from '@/utils/todoTime'

const props = defineProps({
  todos: {
    type: Array,
    default: () => [],
  },
  confirming: {
    type: Boolean,
    default: false,
  },
  actionFeedback: {
    type: Object,
    default: null,
  },
  aggregateAnalysis: {
    type: Object,
    default: null,
  },
  analysisLoading: {
    type: Boolean,
    default: false,
  },
  planGenerationLoading: {
    type: Boolean,
    default: false,
  },
  analysisError: {
    type: String,
    default: '',
  },
  planGenerationError: {
    type: String,
    default: '',
  },
  analysisVisible: {
    type: Boolean,
    default: false,
  },
  dataSourceSummary: {
    type: Object,
    default: () => ({}),
  },
  aiCandidatePlans: {
    type: Array,
    default: () => [],
  },
  selectedPlanId: {
    type: String,
    default: '',
  },
  planActionBusyId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits([
  'confirm-action',
  'run-analysis',
  'select-plan',
  'apply-plan-adjustment',
  'cancel-plan-adjustment',
])
const userStore = useUserStore()

const draft = ref('')
const loading = ref(false)
const activeSessionId = ref(null)
const previewAction = ref(null)
const messages = ref([
  {
    id: 1,
    role: 'assistant',
    content: '你可以直接描述新增、修改、删除或状态变更，我会先整理成可确认的操作草案。',
  },
  {
    id: 2,
    role: 'assistant',
    content: '我不会直接调用后端。只有确认卡片里的“确认执行”才会真正提交操作。',
  },
])

const confirmDisabled = computed(() => {
  return props.confirming || !previewAction.value?.canConfirm
})

const analysisTriggerLabel = computed(() => {
  if (props.analysisLoading) return '分析中...'
  return 'Analyze My Schedule'
})

const analysisData = computed(() => props.aggregateAnalysis?.analysis || null)

const summary = computed(() => analysisData.value?.summary || {})

const riskLabel = computed(() => {
  const risk = summary.value?.risk_level
  if (risk === 'high') return '高风险'
  if (risk === 'medium') return '中风险'
  return '低风险'
})

const topInsights = computed(() => {
  const analysis = analysisData.value
  if (!analysis) return []

  const conflictItems = (analysis.conflicts || []).slice(0, 2).map((item, index) => ({
    key: `conflict-${index}`,
    label: '时间冲突',
    text: `${item.left_event?.title || '事项'} 与 ${item.right_event?.title || '事项'} 重叠`,
  }))
  const pileupItems = (analysis.pileups || []).slice(0, 2).map((item, index) => ({
    key: `pileup-${index}`,
    label: '堆积提醒',
    text: item.reason || `发现 ${item.event_count || 0} 个集中事项`,
  }))

  return [...conflictItems, ...pileupItems].slice(0, 4)
})

const candidatePlans = computed(() => {
  return props.aiCandidatePlans.map((plan, planIndex) => ({
    ...plan,
    id: String(plan.id || `plan-${planIndex + 1}`),
    name: plan.name || `方案 ${planIndex + 1}`,
    goal: plan.goal || '待补充',
    summary: plan.summary || '',
    adjustmentCount: Array.isArray(plan.adjustments) ? plan.adjustments.length : 0,
    adjustments: Array.isArray(plan.adjustments)
      ? plan.adjustments.map((item, itemIndex) => ({
        ...item,
        key: `${plan.id || planIndex}-${itemIndex}`,
        itemTitle: item.item_title || '未命名事项',
        currentTime: item.current_time || '未提供时间',
        suggestedTime: item.suggested_time || '未提供时间',
        reason: item.reason || '未提供原因',
        expectedEffect: item.expected_effect || '未提供预期效果',
      }))
      : [],
  }))
})

const isPlanActionBusy = computed(() => Boolean(props.planActionBusyId))

function getPlanActionBusyId(plan, adjustment) {
  return `${String(plan?.id || '')}:${String(adjustment?.id || '')}`
}

function canApplyPlanAdjustment(adjustment) {
  return adjustment?.can_apply !== false
}

watch(
  () => props.actionFeedback,
  (feedback) => {
    if (!feedback?.id || !feedback.message) return

    messages.value.push({
      id: feedback.id,
      role: 'assistant',
      content: feedback.message,
    })

    if (feedback.type === 'success') {
      previewAction.value = null
    }
  }
)

function stripCodeFences(text) {
  const trimmed = text.trim()
  if (trimmed.startsWith('```')) {
    return trimmed
      .replace(/^```json\s*/i, '')
      .replace(/^```\s*/i, '')
      .replace(/\s*```$/, '')
      .trim()
  }
  return trimmed
}

function pushAssistantMessage(content) {
  messages.value.push({
    id: Date.now() + Math.random(),
    role: 'assistant',
    content,
  })
}

function normalizeActionType(action) {
  const normalized = String(action || '').trim().toLowerCase()
  if (['create', 'add', 'insert'].includes(normalized)) return 'create'
  if (['update', 'edit', 'modify'].includes(normalized)) return 'update'
  if (['delete', 'remove'].includes(normalized)) return 'delete'
  if (['mark_done', 'done', 'complete'].includes(normalized)) return 'mark_done'
  if (['mark_pending', 'pending', 'undo'].includes(normalized)) return 'mark_pending'
  return ''
}

function normalizePriority(priority) {
  const value = Number(priority)
  return [1, 2, 3].includes(value) ? value : null
}

function hasMeaningfulText(value) {
  return typeof value === 'string' && value.trim().length > 0
}

function priorityText(priority) {
  if (priority === 3) return '高'
  if (priority === 1) return '低'
  return '中'
}

function statusText(status) {
  if (status === 'done') return '已完成'
  if (status === 'cancelled') return '已取消'
  return '待办中'
}

function actionLabel(action) {
  if (action === 'create') return '新增 todo'
  if (action === 'update') return '修改 todo'
  if (action === 'delete') return '删除 todo'
  if (action === 'mark_done') return '标记完成'
  if (action === 'mark_pending') return '标记待办'
  return '未知操作'
}

function formatTodoSummary(todo) {
  if (!todo) return ''
  return `${todo.title} | ${getTodoTimingSummary(todo)}`
}

function formatDraftTiming(payload) {
  if (payload?.start_time && payload?.end_time) {
    return `${formatDisplayLocalDateTime(payload.start_time)} - ${formatDisplayLocalDateTime(payload.end_time)}`
  }
  if (payload?.deadline) {
    return formatDisplayLocalDateTime(payload.deadline)
  }
  return '未设置'
}

function getRangeConflictPreviewMessage(conflictingTodo) {
  if (!conflictingTodo) {
    return '这个日程时间块与现有专注事项冲突，请调整时间后再确认。'
  }
  return `这个日程时间块与现有专注事项冲突：${conflictingTodo.title}（${getTodoTimingSummary(conflictingTodo)}）。请调整时间后再确认。`
}

function buildTargetHint(raw) {
  return [raw.target_hint, raw.title]
    .map((item) => (typeof item === 'string' ? item.trim() : ''))
    .find(Boolean) || ''
}

function buildTimingPayload(raw, fallbackPayload, nowParts) {
  const hasTimeFields = [
    raw.date_text,
    raw.time_text,
    raw.end_date_text,
    raw.end_time_text,
    raw.deadline,
    raw.start_time,
    raw.end_time,
  ].some(hasMeaningfulText)

  if (!hasTimeFields) {
    return {
      ok: true,
      value: {
        deadline: fallbackPayload.deadline ?? null,
        start_time: fallbackPayload.start_time ?? null,
        end_time: fallbackPayload.end_time ?? null,
      },
    }
  }

  const normalized = normalizeAiTodoDraft(
    {
      title: '__timing__',
      content: '',
      priority: 2,
      time_mode: raw.time_mode,
      date_text: raw.date_text,
      time_text: raw.time_text,
      end_date_text: raw.end_date_text,
      end_time_text: raw.end_time_text,
      deadline: raw.deadline,
      start_time: raw.start_time,
      end_time: raw.end_time,
    },
    nowParts
  )

  if (!normalized.ok) {
    return { ok: false, message: normalized.message }
  }

  return {
    ok: true,
    value: {
      deadline: normalized.value.deadline ?? null,
      start_time: normalized.value.startTime ?? null,
      end_time: normalized.value.endTime ?? null,
    },
  }
}

function buildChangedFields(target, payload) {
  const fields = []

  if (payload.title !== target.title) {
    fields.push({
      label: '标题',
      from: target.title || '无',
      to: payload.title || '无',
    })
  }

  if ((payload.content || '') !== (target.content || '')) {
    fields.push({
      label: '内容',
      from: target.content || '无',
      to: payload.content || '无',
    })
  }

  if (
    payload.deadline !== target.deadline ||
    payload.start_time !== target.start_time ||
    payload.end_time !== target.end_time
  ) {
    fields.push({
      label: '时间',
      from: getTodoTimingSummary(target),
      to: formatDraftTiming(payload),
    })
  }

  if (payload.priority !== target.priority) {
    fields.push({
      label: '优先级',
      from: priorityText(target.priority),
      to: priorityText(payload.priority),
    })
  }

  return fields
}

function buildActionPreview(raw, nowParts) {
  const action = normalizeActionType(raw.action)
  if (!action) {
    return { ok: false, message: '我没有识别出新增、修改、删除或状态变更意图，请换一种更明确的说法。' }
  }

  if (action === 'create') {
    const normalized = normalizeAiTodoDraft(raw, nowParts)
    if (!normalized.ok) {
      return { ok: false, message: normalized.message }
    }

    const payload = {
      title: normalized.value.title,
      content: normalized.value.content,
      priority: normalized.value.priority,
      deadline: normalized.value.deadline,
      start_time: normalized.value.startTime,
      end_time: normalized.value.endTime,
      status: 'pending',
    }
    const conflictTodo = findConflictingRangeTodo(payload, props.todos)
    if (conflictTodo) {
      const message = getRangeConflictPreviewMessage(conflictTodo)
      return {
        ok: true,
        value: {
          action,
          canConfirm: false,
          payload,
          blockedReason: message,
        },
        message,
      }
    }

    return {
      ok: true,
      value: {
        action,
        canConfirm: true,
        payload,
      },
      message: `已生成新增草案：${normalized.value.title}，时间为 ${formatDraftTiming(payload)}。请确认后执行。`,
    }
  }

  const targetHint = buildTargetHint(raw)
  const matchResult = matchTodoActionTarget(
    {
      action,
      targetHint,
      title: typeof raw.title === 'string' ? raw.title.trim() : '',
      content: typeof raw.content === 'string' ? raw.content.trim() : '',
      dateText: typeof raw.date_text === 'string' ? raw.date_text.trim() : '',
      timeText: typeof raw.time_text === 'string' ? raw.time_text.trim() : '',
    },
    props.todos,
    nowParts
  )

  if (matchResult.status !== 'matched') {
    return {
      ok: true,
      value: {
        action,
        canConfirm: false,
        targetHint,
        blockedReason: matchResult.message,
        candidates: matchResult.candidates || [],
      },
      message: matchResult.message,
    }
  }

  const target = matchResult.todo

  if (action === 'delete') {
    return {
      ok: true,
      value: {
        action,
        target,
        targetId: target.id,
        targetHint,
        canConfirm: true,
        payload: null,
      },
      message: `已定位到要删除的事项：${formatTodoSummary(target)}。请确认后执行删除。`,
    }
  }

  if (action === 'mark_done' || action === 'mark_pending') {
    const nextStatus = action === 'mark_done' ? 'done' : 'pending'
    if (target.status === nextStatus) {
      return {
        ok: true,
        value: {
          action,
          target,
          targetId: target.id,
          canConfirm: false,
          payload: { status: nextStatus },
          blockedReason: `该事项当前已经是${statusText(nextStatus)}。`,
        },
        message: `已定位到事项：${formatTodoSummary(target)}，但它已经是${statusText(nextStatus)}。`,
      }
    }

    return {
      ok: true,
      value: {
        action,
        target,
        targetId: target.id,
        canConfirm: true,
        payload: { status: nextStatus },
      },
      message: `已定位到事项：${formatTodoSummary(target)}。确认后会更新为${statusText(nextStatus)}。`,
    }
  }

  const payload = {
    title: target.title,
    content: target.content || null,
    deadline: target.deadline || null,
    start_time: target.start_time || null,
    end_time: target.end_time || null,
    priority: target.priority ?? 2,
    status: target.status || 'pending',
  }

  if (hasMeaningfulText(raw.title)) {
    payload.title = raw.title.trim()
  }

  if (hasMeaningfulText(raw.content)) {
    payload.content = raw.content.trim()
  }

  const nextPriority = normalizePriority(raw.priority)
  if (nextPriority) {
    payload.priority = nextPriority
  }

  const mergedTiming = buildTimingPayload(raw, payload, nowParts)
  if (!mergedTiming.ok) {
    return { ok: false, message: mergedTiming.message }
  }
  payload.deadline = mergedTiming.value.deadline
  payload.start_time = mergedTiming.value.start_time
  payload.end_time = mergedTiming.value.end_time

  if (payload.start_time && payload.end_time && compareLocalDateTime(payload.end_time, payload.start_time) < 0) {
    return { ok: false, message: '结束时间不能早于开始时间' }
  }

  const conflictTodo = findConflictingRangeTodo(payload, props.todos, { excludeTodoId: target.id })
  if (conflictTodo) {
    const message = getRangeConflictPreviewMessage(conflictTodo)
    return {
      ok: true,
      value: {
        action,
        target,
        targetId: target.id,
        payload,
        canConfirm: false,
        blockedReason: message,
      },
      message,
    }
  }

  const changedFields = buildChangedFields(target, payload)
  if (!changedFields.length) {
    return {
      ok: true,
      value: {
        action,
        target,
        targetId: target.id,
        payload,
        canConfirm: false,
        blockedReason: '我已找到目标事项，但没有识别到明确的修改内容，请补充新的标题、内容、时间或优先级。',
      },
      message: '我已找到目标事项，但没有识别到明确的修改内容，请补充新的标题、内容、时间或优先级。',
    }
  }

  return {
    ok: true,
    value: {
      action,
      target,
      targetId: target.id,
      payload,
      changedFields,
      canConfirm: true,
    },
    message: `已定位到要修改的事项：${formatTodoSummary(target)}。请确认变更后执行。`,
  }
}

async function ensureSession(content) {
  if (activeSessionId.value) return

  let sessionTitle = content.slice(0, 8)
  if (content.length > 8) {
    sessionTitle += '...'
  }

  const createResponse = await fetch(`http://${ip}/session/create`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      token: userStore.token,
    },
    body: JSON.stringify({
      user_id: userStore.id,
      title: sessionTitle || 'Todo 助手',
    }),
  })

  if (!createResponse.ok) {
    throw new Error('创建 AI 会话失败')
  }

  const createResult = await createResponse.json()
  if (!createResult?.data?.id) {
    throw new Error(createResult?.message || '创建 AI 会话失败')
  }

  activeSessionId.value = createResult.data.id
}

async function sendDraft() {
  const content = draft.value.trim()
  if (!content) return
  if (!userStore.isLoggedIn) {
    ElMessage.error('请先登录')
    return
  }

  messages.value.push({
    id: Date.now(),
    role: 'user',
    content,
  })

  draft.value = ''
  loading.value = true

  try {
    await ensureSession(content)
    const beijingNow = getBeijingNowParts()
    const beijingNowText = formatLocalDateTime(beijingNow)

    const prompt = [
      '请将下面的用户自然语言需求解析为一个个人 todo 操作草案。',
      `当前北京时间: ${beijingNowText}`,
      `时区固定为: ${BEIJING_TIMEZONE}`,
      '必须使用北京时间解析相对日期，不要使用 UTC，不要使用其他时区。',
      '你只能识别以下 action：create、update、delete、mark_done、mark_pending。',
      '只返回 JSON，不要返回 markdown，不要返回解释，不要返回代码块。',
      'JSON 必须严格为以下字段：',
      '{"action": "create" | "update" | "delete" | "mark_done" | "mark_pending", "target_hint": string, "title": string, "content": string, "time_mode": "deadline" | "range" | "", "date_text": string, "time_text": string, "end_date_text": string, "end_time_text": string, "priority": 1 | 2 | 3 | null}',
      '规则：',
      '1. create 时，title/priority 需要尽量明确；截止型待办返回 time_mode=deadline 和 date_text/time_text；日程时间块返回 time_mode=range 和 date_text/time_text/end_date_text/end_time_text。',
      '2. update/delete/mark_done/mark_pending 时，target_hint 必须提炼出用户要操作的原事项线索，例如标题关键词、日期、时间、课程名。',
      '3. update 时，只填写用户明确要求修改的新值；没有提到的字段请返回空字符串，priority 无变化时返回 null，time_mode 无变化时返回空字符串。',
      '4. delete/mark_done/mark_pending 时，title/content/date_text/time_text/end_date_text/end_time_text 如果不是新的修改值就返回空字符串，priority 返回 null。',
      '5. 中文时间词必须明确转换为 24 小时语义，例如：上午9点=09:00，下午3点=15:00，晚上8点=20:00，凌晨1点=01:00，中午12点=12:00，3点半=03:30。',
      '6. date_text / end_date_text 请尽量返回明确日期表达，例如 今天、明天、本周四、下周二、2026-04-09、4月9日。',
      '7. time_text / end_time_text 请返回明确时间表达，例如 下午3点、晚上8点半、09:30、18:00。',
      `用户输入：${content}`,
    ].join('\n')

    const aiResponse = await fetch(`http://${ip}/session/aicontent`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        token: userStore.token,
      },
      body: JSON.stringify({
        session_id: activeSessionId.value,
        content: prompt,
        files: null,
        file_types: null,
        file_names: null,
      }),
    })

    if (!aiResponse.ok) {
      throw new Error('AI 请求失败')
    }

    const aiResult = await aiResponse.json()
    if (!aiResult?.data?.length) {
      throw new Error(aiResult?.message || 'AI 返回为空')
    }

    const newMessages = aiResult.data
    const assistantMessage = [...newMessages].reverse().find((item) => item.role === 'assistant')
    if (!assistantMessage?.content) {
      throw new Error('未收到有效 AI 回复')
    }

    const parsed = JSON.parse(stripCodeFences(assistantMessage.content))
    const built = buildActionPreview(parsed, beijingNow)
    if (!built.ok) {
      throw new Error(built.message)
    }

    previewAction.value = built.value
    pushAssistantMessage(built.message)
  } catch (error) {
    previewAction.value = null
    pushAssistantMessage('这次解析失败了。请补充更明确的标题或时间，例如“把 2026-04-09 晚上 8 点的实验报告改到 9 点”。')
    ElMessage.error(error.message || 'AI 操作草案解析失败')
  } finally {
    loading.value = false
  }
}

function clearPreview() {
  previewAction.value = null
}

function selectPlan(plan) {
  if (props.selectedPlanId && props.selectedPlanId === plan?.id) {
    emit('select-plan', null)
    return
  }

  emit('select-plan', plan)
}

function confirmAction() {
  if (!previewAction.value) {
    ElMessage.error('当前没有可确认的操作草案')
    return
  }
  if (!previewAction.value.canConfirm) {
    ElMessage.error(previewAction.value.blockedReason || '当前草案不能执行')
    return
  }

  emit('confirm-action', { ...previewAction.value })
}
</script>

<style scoped>
.todo-ai-panel {
  height: calc(100vh - 90px);
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 22px;
  border-radius: 24px;
  background: linear-gradient(180deg, #0e2238 0%, #122e4c 100%);
  color: #eef5fb;
  box-shadow: 0 18px 48px rgba(17, 37, 61, 0.18);
  overflow: hidden;
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex: 0 0 auto;
  gap: 12px;
  margin-bottom: 18px;
}

.eyebrow {
  font-size: 12px;
  letter-spacing: 0.16em;
  color: #9fc6ea;
  margin-bottom: 6px;
}

.panel-header h2 {
  margin: 0;
  font-size: 26px;
}

.status-pill {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.12);
  font-size: 12px;
}

.assistant-main-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.conversation-area {
  min-height: 0;
  overflow: visible;
  display: flex;
  flex-direction: column;
  gap: 14px;
  margin-bottom: 18px;
}

.analysis-panel {
  margin-bottom: 18px;
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 12px;
}

.analysis-panel-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.analysis-eyebrow {
  font-size: 11px;
  letter-spacing: 0.14em;
  color: #8eb6d8;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.analysis-panel-top h3 {
  margin: 0;
  font-size: 18px;
  color: #f1f7fc;
}

.analysis-trigger {
  border: none;
  border-radius: 12px;
  padding: 10px 14px;
  background: #d8ebff;
  color: #12304d;
  font-weight: 700;
  cursor: pointer;
}

.analysis-trigger:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.analysis-card {
  border-radius: 18px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.analysis-card-title {
  font-size: 14px;
  font-weight: 700;
  color: #f4f8fc;
  margin-bottom: 12px;
}

.analysis-helper {
  margin-bottom: 12px;
  color: #c6daea;
  font-size: 12px;
  line-height: 1.5;
}

.analysis-card-error {
  color: #ffd6d1;
  background: rgba(200, 64, 39, 0.22);
}

.analysis-card-loading,
.analysis-empty-state,
.analysis-empty {
  color: #c9dcee;
  line-height: 1.5;
}

.analysis-source-overview,
.analysis-metric-list {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.analysis-metric {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.analysis-metric span {
  font-size: 12px;
  color: #9ec2de;
}

.analysis-metric strong {
  font-size: 16px;
  color: #f5fbff;
}

.analysis-source-list,
.analysis-insight-list,
.plan-action-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analysis-source-item,
.analysis-insight-item,
.plan-action-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.05);
}

.analysis-source-item span,
.analysis-insight-item span,
.plan-action-item span,
.analysis-source-item small {
  color: #c6daea;
  font-size: 12px;
  line-height: 1.45;
}

.plan-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.plan-card {
  border-radius: 16px;
  padding: 14px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid transparent;
  cursor: pointer;
}

.plan-card.selected {
  border-color: #8fc0ea;
  background: rgba(143, 192, 234, 0.14);
}

.plan-card-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
}

.plan-subtitle {
  margin-top: 4px;
  color: #b9d3e8;
  font-size: 12px;
}

.plan-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.plan-badge {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  background: rgba(255, 255, 255, 0.1);
  color: #dceaf6;
}

.plan-badge.risk {
  background: rgba(161, 208, 250, 0.14);
}

.plan-badge.ai {
  background: rgba(106, 214, 181, 0.14);
}

.plan-reason {
  margin: 0 0 10px;
  color: #d8e7f3;
  font-size: 13px;
  line-height: 1.5;
}

.plan-timing {
  color: #d8e7f3;
}

.plan-action-item small {
  color: #c6daea;
  font-size: 12px;
  line-height: 1.45;
}

.plan-action-warning {
  color: #ffd7b5;
}

.plan-action-controls {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 6px;
}

.plan-action-btn {
  border: none;
  border-radius: 9px;
  padding: 7px 10px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.plan-action-btn.apply {
  background: #d7ebff;
  color: #12304d;
}

.plan-action-btn.ignore {
  background: rgba(255, 255, 255, 0.1);
  color: #f1f8ff;
}

.plan-action-btn:disabled {
  opacity: 0.58;
  cursor: not-allowed;
}

.plan-select-btn {
  margin-top: 10px;
  border: none;
  border-radius: 10px;
  padding: 9px 12px;
  background: rgba(255, 255, 255, 0.1);
  color: #f1f8ff;
  font-weight: 700;
  cursor: pointer;
}

.plan-select-btn.selected {
  background: #d7ebff;
  color: #12304d;
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.bubble {
  max-width: 88%;
  padding: 12px 14px;
  border-radius: 16px;
  line-height: 1.55;
  font-size: 14px;
}

.assistant .bubble {
  background: rgba(255, 255, 255, 0.1);
}

.user .bubble {
  background: linear-gradient(135deg, #43c4ff 0%, #2b7fff 100%);
}

.confirmation-card {
  padding: 16px;
  margin-bottom: 16px;
  min-height: 0;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.card-title {
  font-size: 15px;
  font-weight: 700;
  margin-bottom: 12px;
}

.card-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 14px;
}

.card-item-stack {
  flex-direction: column;
  align-items: flex-start;
}

.card-item span {
  color: #9fc6ea;
}

.card-item small {
  color: #c4d8ea;
  line-height: 1.4;
}

.card-note {
  font-size: 12px;
  color: #c4d8ea;
  line-height: 1.5;
}

.blocked-note {
  margin-top: 10px;
  color: #ffd6d6;
}

.danger-note {
  margin-top: 4px;
  color: #ffd6d6;
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}

.candidate-item {
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.08);
  font-size: 13px;
  line-height: 1.45;
}

.card-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
}

.confirm-btn,
.cancel-btn {
  height: 38px;
  border: none;
  border-radius: 12px;
  padding: 0 14px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.confirm-btn {
  background: linear-gradient(135deg, #43c4ff 0%, #2b7fff 100%);
  color: #fff;
}

.cancel-btn {
  background: rgba(255, 255, 255, 0.12);
  color: #d9e8f6;
}

.input-area {
  display: flex;
  flex: 0 0 auto;
  min-height: 0;
  flex-direction: column;
  gap: 12px;
}

.chat-input {
  min-height: 110px;
  resize: none;
  padding: 14px;
  border: none;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.95);
  color: #203246;
  font-size: 14px;
  outline: none;
}

.send-btn {
  align-self: flex-end;
  min-width: 96px;
  height: 42px;
  border: none;
  border-radius: 14px;
  background: linear-gradient(135deg, #43c4ff 0%, #2b7fff 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
}

.send-btn:disabled,
.confirm-btn:disabled,
.cancel-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.loading-bubble {
  opacity: 0.8;
}

@media (max-width: 960px) {
  .todo-ai-panel {
    height: calc(100vh - 80px);
  }

  .analysis-source-overview,
  .analysis-metric-list {
    grid-template-columns: 1fr;
  }

  .analysis-panel-top,
  .plan-card-head {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
