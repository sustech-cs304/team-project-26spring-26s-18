<template>
  <section class="todo-calendar">
    <div class="calendar-top">
      <div>
        <div class="eyebrow">个人TODO</div>
        <h2>本周日程视图</h2>
      </div>

      <div class="calendar-actions">
        <button class="week-btn" @click="$emit('change-week', -1)">上一周</button>
        <div class="week-range">{{ weekRangeLabel }}</div>
        <button class="week-btn" @click="$emit('change-week', 1)">下一周</button>
        <button class="add-btn" @click="$emit('open-add')">手动添加</button>
      </div>
    </div>

    <div class="calendar-header-extra">
      <slot name="header-extra" />
    </div>

    <div class="calendar-grid">
      <div class="days-grid">
        <div class="days-header">
          <div class="time-header-spacer"></div>
          <div class="days-header-row" :style="headerRowStyle">
            <div
              v-for="day in weekDays"
              :key="day.iso"
              class="day-header"
              :class="{ today: day.isToday }"
            >
              <span>{{ day.label }}</span>
              <strong>{{ day.dateLabel }}</strong>
            </div>
          </div>
        </div>

        <div ref="timelineScroller" class="timeline-scroller">
          <div class="timeline-grid">
            <div class="time-column">
              <div v-for="hour in hourLabels" :key="hour" class="time-cell">
                {{ hour }}
              </div>
            </div>

            <div class="days-body">
              <div
                v-for="day in weekDays"
                :key="`${day.iso}-body`"
                class="day-column"
                :class="{ today: day.isToday }"
                @click="handleDayColumnClick(day.iso, $event)"
              >
                <div
                  v-for="marker in getBackgroundMarkersForDay(day.iso)"
                  :key="`marker-${marker.id ?? marker.title}-${day.iso}`"
                  class="background-marker"
                  :style="getBackgroundMarkerStyle(marker)"
                >
                  <div class="background-marker-label" :style="getBackgroundMarkerLabelStyle(marker)">
                    {{ marker.title }}
                  </div>
                </div>

                <div
                  v-for="line in 24"
                  :key="line"
                  class="hour-line"
                ></div>

                <div
                  v-for="segment in getEventsForDay(day.iso)"
                  :key="`${segment.todo.id ?? segment.todo.title}-${day.iso}-${segment.segmentStartMinutes}-${segment.segmentEndMinutes}`"
                  class="todo-event"
                  :class="[
                    priorityClass(segment.todo.priority),
                    statusClass(segment.todo.status),
                    {
                      'is-range': isRangeEvent(segment),
                      'is-multi-day-range': isMultiDayRangeSegment(segment),
                      'is-long': isLongSegment(segment),
                      'is-all-day-like': isAllDayLikeSegment(segment),
                      'is-narrow': isNarrowSegment(segment),
                    },
                  ]"
                  :style="getEventStyle(segment)"
                  :title="segment.todo.title"
                  @click.stop="emit('select-event', segment.todo)"
                >
                  <div v-if="shouldShowTime(segment) || isBlackboardTodo(segment.todo)" class="event-meta-row">
                    <div v-if="shouldShowTime(segment)" class="event-time">{{ formatTime(segment) }}</div>
                    <div v-if="isBlackboardTodo(segment.todo)" class="event-source-badge">bb</div>
                  </div>
                  <div class="event-title">{{ segment.todo.title }}</div>
                </div>

                <div
                  v-for="segment in getPreviewsForDay(day.iso)"
                  :key="`preview-${segment.preview.id}-${day.iso}-${segment.segmentStartMinutes}-${segment.segmentEndMinutes}`"
                  class="todo-event todo-preview-event"
                  :class="[
                    previewTypeClass(segment.preview.preview_type),
                    {
                      'is-range': isRangeEvent(segment),
                      'is-multi-day-range': isMultiDayRangeSegment(segment),
                      'is-long': isLongSegment(segment),
                      'is-all-day-like': isAllDayLikeSegment(segment),
                      'is-narrow': isNarrowSegment(segment),
                    },
                  ]"
                  :style="getPreviewStyle(segment)"
                  :title="formatPreviewTooltip(segment.preview)"
                  @click.stop
                >
                  <div class="event-meta-row preview-meta-row">
                    <div v-if="shouldShowTime(segment)" class="event-time">{{ formatTime(segment) }}</div>
                    <span class="preview-chip">{{ segment.preview.preview_label || 'AI Preview' }}</span>
                  </div>
                  <div class="event-title">{{ segment.preview.item_title }}</div>
                  <div class="preview-actions">
                    <button
                      class="preview-action apply"
                      :disabled="isPreviewActionBusy || segment.preview.can_apply === false"
                      @click.stop="emit('apply-preview-adjustment', segment.preview)"
                    >
                      {{ previewActionBusyId === getPreviewActionBusyId(segment.preview) ? '应用中' : '应用' }}
                    </button>
                    <button
                      class="preview-action cancel"
                      :disabled="isPreviewActionBusy"
                      @click.stop="emit('cancel-preview-adjustment', segment.preview)"
                    >
                      忽略
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { getTodoSegmentDisplayTime, splitTodoIntoDaySegments } from '@/utils/todoTime'

const props = defineProps({
  weekDays: {
    type: Array,
    required: true,
  },
  weekRangeLabel: {
    type: String,
    required: true,
  },
  events: {
    type: Array,
    default: () => [],
  },
  backgroundMarkers: {
    type: Array,
    default: () => [],
  },
  aiPreviewAdjustments: {
    type: Array,
    default: () => [],
  },
  previewActionBusyId: {
    type: String,
    default: '',
  },
})

const emit = defineEmits([
  'change-week',
  'open-add',
  'select-event',
  'create-at-slot',
  'apply-preview-adjustment',
  'cancel-preview-adjustment',
])

const timelineScroller = ref(null)
const HOUR_HEIGHT = 64
const SIDE_PADDING = 8
const COLUMN_GAP = 6
const LONG_DURATION_MINUTES = 8 * 60
const ALL_DAY_LIKE_MINUTES = 23 * 60
const DEADLINE_MIN_HEIGHT = 56
const hourLabels = Array.from({ length: 24 }, (_, index) => `${String(index).padStart(2, '0')}:00`)
const eventSegments = computed(() => props.events.flatMap((item) => splitTodoIntoDaySegments(item)))
const previewSegments = computed(() => props.aiPreviewAdjustments.flatMap((item) => buildPreviewSegments(item)))
const dayBackgroundMarkers = computed(() => {
  return Object.fromEntries(props.weekDays.map((day) => [day.iso, buildDayBackgroundMarkers(day.iso)]))
})
const dayEventLayouts = computed(() => {
  return Object.fromEntries(props.weekDays.map((day) => [day.iso, buildDayLayout(day.iso, eventSegments.value)]))
})
const dayPreviewLayouts = computed(() => {
  return Object.fromEntries(props.weekDays.map((day) => [day.iso, buildDayLayout(day.iso, previewSegments.value)]))
})
const scrollbarOffset = ref(0)
const headerRowStyle = computed(() => ({
  paddingRight: `${scrollbarOffset.value}px`,
}))
const isPreviewActionBusy = computed(() => Boolean(props.previewActionBusyId))

onMounted(() => {
  nextTick(() => {
    if (timelineScroller.value) {
      timelineScroller.value.scrollTop = 8 * HOUR_HEIGHT
    }
    syncScrollbarOffset()
  })
  window.addEventListener('resize', syncScrollbarOffset)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', syncScrollbarOffset)
})

function syncScrollbarOffset() {
  if (!timelineScroller.value) {
    scrollbarOffset.value = 0
    return
  }
  scrollbarOffset.value = Math.max(0, timelineScroller.value.offsetWidth - timelineScroller.value.clientWidth)
}

function getEventsForDay(dayIso) {
  return dayEventLayouts.value[dayIso] || []
}

function getBackgroundMarkersForDay(dayIso) {
  return dayBackgroundMarkers.value[dayIso] || []
}

function getPreviewsForDay(dayIso) {
  return dayPreviewLayouts.value[dayIso] || []
}

function getPreviewActionBusyId(preview) {
  return `${String(preview?.plan_id || '')}:${String(preview?.adjustment_id || '')}`
}

function handleDayColumnClick(dayIso, event) {
  const columnRect = event.currentTarget?.getBoundingClientRect()
  if (!columnRect) return

  const relativeY = Math.max(0, Math.min(event.clientY - columnRect.top, columnRect.height))
  const rawMinutes = (relativeY / columnRect.height) * 24 * 60
  const roundedMinutes = Math.max(0, Math.min(23 * 60 + 30, Math.round(rawMinutes / 30) * 30))
  const hour = Math.floor(roundedMinutes / 60)
  const minute = roundedMinutes % 60
  const time = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
  const localDateTime = `${dayIso}T${time}:00`

  emit('create-at-slot', {
    dayIso,
    time,
    localDateTime,
  })
}

function buildPreviewSegments(preview) {
  const hasRange = Boolean(preview?.suggested_end && preview?.suggested_start && preview.suggested_end > preview.suggested_start)
  const previewTodo = {
    id: `preview-${preview?.id || preview?.item_title || 'slot'}`,
    title: preview?.item_title || 'AI Preview',
    start_time: hasRange ? preview.suggested_start : '',
    end_time: hasRange ? preview.suggested_end : '',
    deadline: hasRange ? '' : preview?.suggested_start || '',
  }

  return splitTodoIntoDaySegments(previewTodo).map((segment) => ({
    ...segment,
    preview,
  }))
}

function buildDayLayout(dayIso, sourceSegments = []) {
  const daySegments = sourceSegments
    .filter((segment) => segment.dayKey === dayIso)
    .sort((a, b) => {
      if (a.segmentStartMinutes !== b.segmentStartMinutes) {
        return a.segmentStartMinutes - b.segmentStartMinutes
      }
      if (a.segmentEndMinutes !== b.segmentEndMinutes) {
        return b.segmentEndMinutes - a.segmentEndMinutes
      }
      return String(a.todo?.id ?? a.todo?.title ?? '').localeCompare(String(b.todo?.id ?? b.todo?.title ?? ''))
    })

  const laidOutSegments = []
  let active = []
  let clusterIndexes = []
  let clusterColumnCount = 0

  const finalizeCluster = () => {
    if (!clusterIndexes.length) return
    const safeColumnCount = Math.max(1, clusterColumnCount)
    clusterIndexes.forEach((index) => {
      laidOutSegments[index].columnCount = safeColumnCount
    })
    clusterIndexes = []
    clusterColumnCount = 0
  }

  daySegments.forEach((segment) => {
    active = active.filter((item) => item.segment.segmentEndMinutes > segment.segmentStartMinutes)

    if (!active.length) {
      finalizeCluster()
    }

    const usedColumns = new Set(active.map((item) => item.columnIndex))
    let columnIndex = 0
    while (usedColumns.has(columnIndex)) {
      columnIndex += 1
    }

    const layoutSegment = {
      ...segment,
      columnIndex,
      columnCount: 1,
    }

    laidOutSegments.push(layoutSegment)
    const layoutIndex = laidOutSegments.length - 1
    active.push({ segment: layoutSegment, columnIndex, layoutIndex })
    clusterIndexes.push(layoutIndex)
    clusterColumnCount = Math.max(clusterColumnCount, active.length, columnIndex + 1)
  })

  finalizeCluster()
  return laidOutSegments
}

function buildDayBackgroundMarkers(dayIso) {
  return props.backgroundMarkers
    .filter((marker) => overlapsDay(marker, dayIso))
    .sort((a, b) => {
      const startCompare = String(a?.start_time || '').localeCompare(String(b?.start_time || ''))
      if (startCompare !== 0) return startCompare
      return String(a?.title || '').localeCompare(String(b?.title || ''))
    })
    .map((marker, index) => ({
      ...marker,
      layerIndex: index,
    }))
}

function overlapsDay(marker, dayIso) {
  const startDay = getLocalDatePart(marker?.start_time)
  const endDay = getLocalDatePart(marker?.end_time || marker?.start_time)
  if (!startDay || !endDay) return false
  return startDay <= dayIso && dayIso <= endDay
}

function getBackgroundMarkerStyle(marker) {
  const stripeWidth = 10 + (marker.layerIndex % 3) * 2
  const palette = [
    ['rgba(201, 161, 88, 0.14)', 'rgba(201, 161, 88, 0.03)'],
    ['rgba(201, 133, 89, 0.14)', 'rgba(201, 133, 89, 0.03)'],
    ['rgba(136, 123, 171, 0.14)', 'rgba(136, 123, 171, 0.03)'],
    ['rgba(173, 151, 104, 0.14)', 'rgba(173, 151, 104, 0.03)'],
  ]
  const [accent, fill] = palette[marker.layerIndex % palette.length]

  return {
    top: '0',
    left: `${4 + marker.layerIndex * 4}px`,
    width: `calc(100% - ${8 + marker.layerIndex * 4}px)`,
    height: '100%',
    background: `linear-gradient(180deg, ${accent} 0%, ${fill} 32%, rgba(255,255,255,0) 100%)`,
    borderLeft: `${stripeWidth}px solid ${accent}`,
    zIndex: 0,
  }
}

function getBackgroundMarkerLabelStyle(marker) {
  return {
    top: `${12 + marker.layerIndex * 28}px`,
    left: `${18 + marker.layerIndex * 4}px`,
    zIndex: 1,
  }
}

function getEventStyle(segment) {
  const safeMinutes = Math.max(0, Math.min(segment.segmentStartMinutes, 24 * 60 - 1))
  const top = (safeMinutes / 60) * HOUR_HEIGHT
  const height = (segment.durationMinutes / 60) * HOUR_HEIGHT
  const isRange = isRangeEvent(segment)

  if (!isRange) {
    const blockHeight = Math.max(DEADLINE_MIN_HEIGHT, height)
    return {
      top: `${top - blockHeight}px`,
      height: `${blockHeight}px`,
      left: `${SIDE_PADDING}px`,
      width: `calc(100% - ${SIDE_PADDING * 2}px)`,
      right: 'auto',
      zIndex: 4,
    }
  }

  const usesStableFullWidth = isLongSegment(segment)
  const usesSoftVisualStyle = usesStableFullWidth || isMultiDayRangeSegment(segment)
  const layoutColumnCount = usesStableFullWidth ? 1 : Math.max(1, segment.columnCount || 1)
  const layoutColumnIndex = usesStableFullWidth ? 0 : Math.max(0, segment.columnIndex || 0)
  const totalGapPx = Math.max(0, layoutColumnCount - 1) * COLUMN_GAP
  const contentWidth = `calc(100% - ${SIDE_PADDING * 2}px)`
  const trackWidth = layoutColumnCount === 1
    ? contentWidth
    : `calc((${contentWidth} - ${totalGapPx}px) / ${layoutColumnCount})`
  const left = layoutColumnIndex === 0
    ? `${SIDE_PADDING}px`
    : `calc(${SIDE_PADDING}px + ${layoutColumnIndex} * (${trackWidth} + ${COLUMN_GAP}px))`

  return {
    top: `${top}px`,
    height: `${Math.max(segment.isRange ? 42 : 38, height)}px`,
    left,
    width: trackWidth,
    right: 'auto',
    zIndex: usesSoftVisualStyle ? 1 : 3,
  }
}

function getPreviewStyle(segment) {
  return {
    ...getEventStyle(segment),
    zIndex: 6,
  }
}

function formatTime(segment) {
  if (isAllDayLikeSegment(segment)) {
    return '全天'
  }

  return getTodoSegmentDisplayTime(segment)
}

function isRangeEvent(segment) {
  return Boolean(segment?.isRange)
}

function getLocalDatePart(value) {
  if (typeof value !== 'string') return ''
  return value.split('T')[0] || ''
}

function isMultiDayRangeSegment(segment) {
  const todo = segment?.todo
  if (!todo?.start_time || !todo?.end_time) return false
  return getLocalDatePart(todo.start_time) !== getLocalDatePart(todo.end_time)
}

function isLongSegment(segment) {
  return Number(segment?.durationMinutes || 0) >= LONG_DURATION_MINUTES
}

function isAllDayLikeSegment(segment) {
  return Number(segment?.durationMinutes || 0) >= ALL_DAY_LIKE_MINUTES
}

function isNarrowSegment(segment) {
  return Number(segment?.columnCount || 1) >= 2
}

function shouldShowTime(segment) {
  if (isAllDayLikeSegment(segment)) {
    return true
  }

  if (isLongSegment(segment) && isNarrowSegment(segment)) {
    return false
  }

  return true
}

function isBlackboardTodo(todo) {
  return todo?.import_source === 'blackboard'
}

function priorityClass(priority) {
  if (priority === 3) return 'is-high'
  if (priority === 1) return 'is-low'
  return 'is-medium'
}

function previewTypeClass(previewType) {
  if (previewType === 'move') return 'is-preview-move'
  if (previewType === 'split') return 'is-preview-split'
  if (previewType === 'focus_block') return 'is-preview-focus'
  return 'is-preview-reschedule'
}

function formatPreviewTooltip(preview) {
  return [
    preview?.item_title || 'AI Preview',
    `当前时间：${preview?.current_time || '未提供'}`,
    `建议时间：${preview?.suggested_time || '未提供'}`,
    `原因：${preview?.reason || '未提供'}`,
  ].join('\n')
}

function statusClass(status) {
  return status === 'done' ? 'is-done' : 'is-pending'
}
</script>

<style scoped>
.todo-calendar {
  --hour-height: 64px;
  display: flex;
  flex-direction: column;
  padding: 24px;
  border-radius: 28px;
  background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%);
  box-shadow: 0 18px 48px rgba(30, 55, 90, 0.12);
}

.calendar-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
  margin-bottom: 20px;
}

.eyebrow {
  margin-bottom: 8px;
  color: #7a8ca8;
  font-size: 12px;
  letter-spacing: 0.16em;
}

.calendar-top h2 {
  margin: 0;
  font-size: 28px;
  color: #1b2c44;
}

.calendar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.week-btn,
.add-btn {
  height: 40px;
  padding: 0 16px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  cursor: pointer;
}

.week-btn {
  background: #eef3f8;
  color: #35506f;
}

.week-range {
  min-width: 170px;
  padding: 0 14px;
  height: 40px;
  border-radius: 12px;
  background: #f8fbff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #29425d;
  font-weight: 600;
}

.add-btn {
  background: linear-gradient(135deg, #17395d 0%, #2560a1 100%);
  color: #fff;
  font-weight: 700;
}

.calendar-grid {
  min-height: 720px;
}

.calendar-header-extra {
  margin-bottom: 18px;
}

.time-cell {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 2px;
  color: #7b8ca4;
  font-size: 12px;
  height: var(--hour-height);
  border-top: 1px solid #e6edf5;
  box-sizing: border-box;
}

.days-grid {
  display: grid;
  grid-template-rows: 70px 1fr;
}

.days-header {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 14px;
}

.time-header-spacer {
  min-width: 0;
}

.days-header-row {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  min-width: 0;
  box-sizing: border-box;
}

.timeline-scroller {
  overflow-y: auto;
  overflow-x: hidden;
  max-height: 720px;
  border-bottom-left-radius: 20px;
  border-bottom-right-radius: 20px;
  scrollbar-gutter: stable;
}

.timeline-grid {
  display: grid;
  grid-template-columns: 72px 1fr;
  gap: 14px;
}

.time-column {
  position: sticky;
  left: 0;
  z-index: 2;
  background: linear-gradient(180deg, #ffffff 0%, #f5f8fc 100%);
}

.days-body {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  min-height: calc(var(--hour-height) * 24);
}

.day-header {
  padding: 12px 14px;
  border-bottom: 1px solid #dbe4ef;
  border-left: 1px solid #e6edf5;
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #5e748e;
  background: rgba(244, 247, 251, 0.88);
}

.day-header strong {
  color: #1f304a;
  font-size: 18px;
}

.day-column {
  position: relative;
  border-left: 1px solid #e6edf5;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(248, 251, 255, 0.96) 100%);
  min-height: calc(var(--hour-height) * 24);
  overflow: hidden;
}

.background-marker {
  position: absolute;
  pointer-events: none;
  border-radius: 18px;
}

.background-marker-label {
  position: absolute;
  max-height: calc(100% - 24px);
  padding: 10px 6px;
  border-radius: 16px;
  background: rgba(255, 250, 242, 0.78);
  color: #80673d;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.08em;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  line-height: 1.15;
  overflow: hidden;
  box-shadow: 0 6px 14px rgba(120, 100, 67, 0.10);
  backdrop-filter: blur(2px);
}

.hour-line {
  position: relative;
  z-index: 1;
  height: var(--hour-height);
  border-top: 1px solid #eef3f8;
  box-sizing: border-box;
}

.today {
  background: rgba(48, 126, 217, 0.07);
}

.todo-event {
  position: absolute;
  z-index: 3;
  padding: 10px 12px;
  border-radius: 14px;
  box-shadow: 0 12px 24px rgba(40, 70, 110, 0.12);
  border: 1px solid transparent;
  box-sizing: border-box;
  max-width: calc(100% - 16px);
  transform: translateY(6px);
  cursor: pointer;
  transition: transform 0.18s, box-shadow 0.18s;
  overflow: hidden;
  backdrop-filter: blur(2px);
}

.todo-event:hover {
  transform: translateY(4px);
  box-shadow: 0 14px 28px rgba(40, 70, 110, 0.16);
}

.todo-preview-event {
  --preview-accent: rgba(86, 88, 99, 0.72);
  --preview-shadow: rgba(95, 88, 126, 0.08);
  --preview-text: #5d5770;
  --preview-fill-start: rgba(247, 243, 255, 0.8);
  --preview-fill-end: rgba(237, 231, 250, 0.7);
  border-width: 1px;
  border-style: dashed;
  border-color: var(--preview-accent);
  background: linear-gradient(135deg, var(--preview-fill-start) 0%, var(--preview-fill-end) 100%);
  color: var(--preview-text);
  box-shadow: 0 10px 20px var(--preview-shadow);
  opacity: 0.86;
}

.todo-preview-event:hover {
  transform: translateY(4px);
  box-shadow: 0 12px 24px rgba(95, 88, 126, 0.1);
}

.todo-preview-event .event-time {
  color: inherit;
  opacity: 0.76;
}

.preview-meta-row {
  margin-bottom: 6px;
}

.preview-chip {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  max-width: 100%;
  min-width: 0;
  height: 18px;
  padding: 0 8px;
  border-radius: 999px;
  background: rgba(250, 248, 255, 0.82);
  color: var(--preview-text);
  border: 1px dashed rgba(86, 88, 99, 0.44);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.04em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 0 0 auto;
}

.preview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}

.preview-action {
  border: none;
  border-radius: 6px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 800;
  cursor: pointer;
}

.preview-action.apply {
  background: rgba(255, 255, 255, 0.9);
  color: #2e4c6f;
}

.preview-action.cancel {
  background: rgba(93, 87, 112, 0.12);
  color: var(--preview-text);
}

.preview-action:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.todo-event.is-range {
  padding-bottom: 14px;
}

.todo-event.is-long {
  box-shadow: 0 8px 18px rgba(40, 70, 110, 0.08);
  opacity: 0.84;
}

.todo-event.is-multi-day-range {
  box-shadow: 0 8px 18px rgba(40, 70, 110, 0.08);
  opacity: 0.8;
}

.todo-event.is-all-day-like {
  border-style: dashed;
  box-shadow: none;
  opacity: 0.72;
}

.todo-event.is-multi-day-range.is-all-day-like {
  box-shadow: 0 8px 18px rgba(40, 70, 110, 0.08);
  opacity: 0.8;
}

.todo-preview-event.is-long,
.todo-preview-event.is-multi-day-range,
.todo-preview-event.is-all-day-like,
.todo-preview-event.is-multi-day-range.is-all-day-like {
  box-shadow: 0 10px 20px var(--preview-shadow);
  opacity: 0.96;
}

.todo-event.is-narrow {
  padding: 8px 9px;
  border-radius: 12px;
}

.todo-event:not(.is-range) {
  padding-top: 11px;
  padding-bottom: 11px;
}

.event-meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
  min-width: 0;
}

.event-time {
  font-size: 12px;
  font-weight: 700;
  opacity: 0.78;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex: 1 1 auto;
}

.event-source-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 18px;
  padding: 0 6px;
  border-radius: 999px;
  background: rgba(48, 108, 184, 0.12);
  color: #2f69a8;
  border: 1px solid rgba(48, 108, 184, 0.14);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.03em;
  flex: 0 0 auto;
}

.event-title {
  font-size: 13px;
  line-height: 1.35;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  word-break: break-word;
}

.todo-event.is-long .event-title {
  -webkit-line-clamp: 1;
}

.todo-event.is-narrow .event-meta-row {
  margin-bottom: 4px;
}

.todo-preview-event.is-narrow .preview-chip {
  height: 17px;
  padding: 0 6px;
  font-size: 9px;
}

.todo-event.is-narrow .event-time {
  font-size: 11px;
}

.todo-event.is-narrow .event-source-badge {
  min-width: 22px;
  height: 17px;
  font-size: 9px;
}

.todo-event.is-narrow .event-title {
  font-size: 12px;
  line-height: 1.25;
  -webkit-line-clamp: 1;
}

.todo-event.is-all-day-like .event-meta-row {
  margin-bottom: 4px;
}

.todo-event.is-all-day-like .event-time {
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.todo-event.is-all-day-like .event-title {
  -webkit-line-clamp: 1;
}

.is-high {
  background: linear-gradient(135deg, #ffe2dc 0%, #ffd0d8 100%);
  color: #8d2438;
  border-color: rgba(197, 76, 92, 0.18);
}

.is-medium {
  background: linear-gradient(135deg, #dcecff 0%, #d2e4ff 100%);
  color: #1f4f8d;
  border-color: rgba(53, 104, 173, 0.16);
}

.is-low {
  background: linear-gradient(135deg, #def7ea 0%, #d7f2e4 100%);
  color: #1f6a4b;
  border-color: rgba(46, 136, 98, 0.16);
}

.is-high.is-long,
.is-high.is-multi-day-range,
.is-high.is-all-day-like {
  background: linear-gradient(135deg, rgba(255, 226, 220, 0.72) 0%, rgba(255, 208, 216, 0.68) 100%);
}

.is-medium.is-long,
.is-medium.is-multi-day-range,
.is-medium.is-all-day-like {
  background: linear-gradient(135deg, rgba(220, 236, 255, 0.72) 0%, rgba(210, 228, 255, 0.68) 100%);
}

.is-low.is-long,
.is-low.is-multi-day-range,
.is-low.is-all-day-like {
  background: linear-gradient(135deg, rgba(222, 247, 234, 0.72) 0%, rgba(215, 242, 228, 0.68) 100%);
}

.is-done {
  opacity: 0.78;
  filter: saturate(0.35);
  box-shadow: 0 8px 18px rgba(64, 79, 96, 0.08);
  text-decoration: line-through;
}

.is-done .event-time {
  color: #6d7a8a;
  opacity: 0.9;
}

.is-done .event-title {
  color: #516071;
}

@media (max-width: 1200px) {
  .calendar-top {
    flex-direction: column;
  }

  .calendar-actions {
    justify-content: flex-start;
  }
}

@media (max-width: 760px) {
  .timeline-grid {
    grid-template-columns: 52px 1fr;
  }
}
</style>
