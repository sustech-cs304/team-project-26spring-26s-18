export const BEIJING_TIMEZONE = 'Asia/Shanghai'

const WEEKDAY_LABELS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
const CHINESE_DIGIT_MAP = {
  零: 0,
  〇: 0,
  一: 1,
  二: 2,
  两: 2,
  三: 3,
  四: 4,
  五: 5,
  六: 6,
  七: 7,
  八: 8,
  九: 9,
}

function pad2(value) {
  return String(value).padStart(2, '0')
}

function extractPartsFromFormatter(parts) {
  const map = {}
  parts.forEach((part) => {
    if (part.type !== 'literal') {
      map[part.type] = part.value
    }
  })
  return {
    year: Number(map.year),
    month: Number(map.month),
    day: Number(map.day),
    hour: Number(map.hour),
    minute: Number(map.minute),
    second: Number(map.second),
  }
}

export function getBeijingNowParts() {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone: BEIJING_TIMEZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  })

  const parts = extractPartsFromFormatter(formatter.formatToParts(new Date()))
  return {
    ...parts,
    weekday: getWeekdayIndex(parts),
  }
}

export function formatDateParts(dateParts) {
  return `${dateParts.year}-${pad2(dateParts.month)}-${pad2(dateParts.day)}`
}

export function formatLocalDateTime(parts) {
  return `${formatDateParts(parts)}T${pad2(parts.hour)}:${pad2(parts.minute)}:${pad2(parts.second ?? 0)}`
}

export function parseLocalDateTimeString(value) {
  if (typeof value !== 'string') return null

  const normalized = value.trim().replace(' ', 'T')
  const match = normalized.match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?$/
  )

  if (!match) return null

  const [, year, month, day, hour, minute, second = '00'] = match
  return {
    year: Number(year),
    month: Number(month),
    day: Number(day),
    hour: Number(hour),
    minute: Number(minute),
    second: Number(second),
  }
}

export function formatDisplayLocalDateTime(value) {
  const parsed = parseLocalDateTimeString(value)
  if (!parsed) return value
  return `${parsed.year}-${pad2(parsed.month)}-${pad2(parsed.day)} ${pad2(parsed.hour)}:${pad2(parsed.minute)}`
}

export function getTimeLabel(value) {
  const parsed = parseLocalDateTimeString(value)
  if (!parsed) return ''
  return `${pad2(parsed.hour)}:${pad2(parsed.minute)}`
}

export function getDateKey(value) {
  const parsed = parseLocalDateTimeString(value)
  if (!parsed) return ''
  return formatDateParts(parsed)
}

export function getMinutesOfDay(value) {
  const parsed = parseLocalDateTimeString(value)
  if (!parsed) return 0
  return parsed.hour * 60 + parsed.minute
}

export function compareLocalDateTime(a, b) {
  return String(a || '').localeCompare(String(b || ''))
}

export function addDays(dateParts, days) {
  const utcDate = new Date(Date.UTC(dateParts.year, dateParts.month - 1, dateParts.day))
  utcDate.setUTCDate(utcDate.getUTCDate() + days)
  return {
    year: utcDate.getUTCFullYear(),
    month: utcDate.getUTCMonth() + 1,
    day: utcDate.getUTCDate(),
  }
}

export function getWeekdayIndex(dateParts) {
  const utcDate = new Date(Date.UTC(dateParts.year, dateParts.month - 1, dateParts.day))
  const weekday = utcDate.getUTCDay()
  return weekday === 0 ? 7 : weekday
}

export function getWeekStartDateParts(dateParts) {
  return addDays(dateParts, 1 - getWeekdayIndex(dateParts))
}

export function buildWeekDays(startDateParts) {
  return Array.from({ length: 7 }, (_, index) => {
    const current = addDays(startDateParts, index)
    return {
      ...current,
      iso: formatDateParts(current),
      label: WEEKDAY_LABELS[(index + 1) % 7],
      dateLabel: `${current.month}/${current.day}`,
    }
  })
}

export function chineseNumberToNumber(raw) {
  if (!raw) return null
  if (/^\d+$/.test(raw)) return Number(raw)

  const text = raw.replace(/两/g, '二')
  if (text === '十') return 10
  if (text.includes('十')) {
    const [left, right] = text.split('十')
    const tens = left ? CHINESE_DIGIT_MAP[left] : 1
    const units = right ? CHINESE_DIGIT_MAP[right] : 0
    if (Number.isInteger(tens) && Number.isInteger(units)) {
      return tens * 10 + units
    }
  }

  let result = ''
  for (const char of text) {
    if (!(char in CHINESE_DIGIT_MAP)) return null
    result += CHINESE_DIGIT_MAP[char]
  }

  return result ? Number(result) : null
}

function extractMinuteText(restText) {
  const text = restText || ''
  if (text.includes('半')) return 30
  if (text.includes('一刻')) return 15
  if (text.includes('三刻')) return 45

  const minuteMatch = text.match(/(?:(\d{1,2}|[零〇一二两三四五六七八九十]{1,3})分?)/)
  if (!minuteMatch) return 0

  const minute = chineseNumberToNumber(minuteMatch[1])
  return Number.isInteger(minute) ? minute : 0
}

export function resolveChineseTimeText(timeText) {
  if (typeof timeText !== 'string' || !timeText.trim()) {
    return { ok: false, message: '缺少时间信息' }
  }

  const normalized = timeText.replace(/\s+/g, '')
  const explicitMatch = normalized.match(/^(\d{1,2})(?::|：)(\d{1,2})$/)
  if (explicitMatch) {
    const hour = Number(explicitMatch[1])
    const minute = Number(explicitMatch[2])
    if (hour >= 0 && hour <= 23 && minute >= 0 && minute <= 59) {
      return { ok: true, hour, minute, text: `${pad2(hour)}:${pad2(minute)}` }
    }
  }

  const periodMatch = normalized.match(/^(凌晨|早上|早晨|上午|中午|下午|傍晚|晚上|晚间)?/)
  const period = periodMatch?.[1] || ''
  const rest = normalized.slice(period.length)
  const hourMatch = rest.match(/^(\d{1,2}|[零〇一二两三四五六七八九十]{1,3})点(.*)$/)

  if (!hourMatch) {
    return { ok: false, message: '无法识别时间，请补充到几点几分' }
  }

  const baseHour = chineseNumberToNumber(hourMatch[1])
  const minute = extractMinuteText(hourMatch[2])

  if (!Number.isInteger(baseHour) || baseHour < 0 || baseHour > 23 || minute < 0 || minute > 59) {
    return { ok: false, message: '时间格式不正确' }
  }

  let hour = baseHour
  if (period === '凌晨') {
    hour = baseHour === 12 ? 0 : baseHour
  } else if (period === '早上' || period === '早晨' || period === '上午') {
    hour = baseHour === 12 ? 0 : baseHour
  } else if (period === '中午') {
    hour = baseHour >= 11 ? baseHour : baseHour + 12
    if (baseHour === 12) hour = 12
  } else if (period === '下午' || period === '傍晚' || period === '晚上' || period === '晚间') {
    hour = baseHour === 12 ? 12 : baseHour + 12
  }

  if (hour < 0 || hour > 23) {
    return { ok: false, message: '时间超出有效范围' }
  }

  return { ok: true, hour, minute, text: `${pad2(hour)}:${pad2(minute)}` }
}

function parseWeekdayText(text) {
  const match = text.match(/(?:周|星期)([一二三四五六日天])/)
  if (!match) return null
  const value = match[1]
  if (value === '日' || value === '天') return 7
  return chineseNumberToNumber(value)
}

export function resolveChineseDateText(dateText, nowParts = getBeijingNowParts()) {
  if (typeof dateText !== 'string' || !dateText.trim()) {
    return { ok: false, message: '缺少日期信息' }
  }

  const normalized = dateText.replace(/\s+/g, '')
  const today = {
    year: nowParts.year,
    month: nowParts.month,
    day: nowParts.day,
  }

  if (normalized === '今天') {
    return { ok: true, dateParts: today, text: formatDateParts(today) }
  }
  if (normalized === '明天') {
    const result = addDays(today, 1)
    return { ok: true, dateParts: result, text: formatDateParts(result) }
  }
  if (normalized === '后天') {
    const result = addDays(today, 2)
    return { ok: true, dateParts: result, text: formatDateParts(result) }
  }

  const explicitIso = normalized.match(/^(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?$/)
  if (explicitIso) {
    const result = {
      year: Number(explicitIso[1]),
      month: Number(explicitIso[2]),
      day: Number(explicitIso[3]),
    }
    return { ok: true, dateParts: result, text: formatDateParts(result) }
  }

  const monthDay = normalized.match(/^(\d{1,2})月(\d{1,2})日?$/)
  if (monthDay) {
    let year = nowParts.year
    const month = Number(monthDay[1])
    const day = Number(monthDay[2])
    if (month < nowParts.month || (month === nowParts.month && day < nowParts.day)) {
      year += 1
    }
    const result = { year, month, day }
    return { ok: true, dateParts: result, text: formatDateParts(result) }
  }

  const weekday = parseWeekdayText(normalized)
  if (weekday) {
    const weekStart = getWeekStartDateParts(today)
    if (normalized.startsWith('下周') || normalized.startsWith('下星期')) {
      const result = addDays(weekStart, 7 + (weekday - 1))
      return { ok: true, dateParts: result, text: formatDateParts(result) }
    }
    if (
      normalized.startsWith('本周') ||
      normalized.startsWith('这周') ||
      normalized.startsWith('本星期') ||
      normalized.startsWith('这星期')
    ) {
      const result = addDays(weekStart, weekday - 1)
      return { ok: true, dateParts: result, text: formatDateParts(result) }
    }
  }

  return { ok: false, message: '日期不明确，请补充为今天/明天/本周四/下周二/2026-04-09 这类格式' }
}

function resolveDateTime(dateText, timeText, nowParts = getBeijingNowParts()) {
  const resolvedDate = resolveChineseDateText(dateText, nowParts)
  if (!resolvedDate.ok) return resolvedDate

  const resolvedTime = resolveChineseTimeText(timeText)
  if (!resolvedTime.ok) return resolvedTime

  return {
    ok: true,
    value: formatLocalDateTime({
      ...resolvedDate.dateParts,
      hour: resolvedTime.hour,
      minute: resolvedTime.minute,
      second: 0,
    }),
    dateText: resolvedDate.text,
    timeText: resolvedTime.text,
  }
}

function normalizeExplicitRange(raw) {
  const start = typeof raw.start_time === 'string' ? parseLocalDateTimeString(raw.start_time.trim()) : null
  const end = typeof raw.end_time === 'string' ? parseLocalDateTimeString(raw.end_time.trim()) : null
  const deadline = typeof raw.deadline === 'string' ? parseLocalDateTimeString(raw.deadline.trim()) : null

  if (start && end) {
    return {
      ok: true,
      value: {
        timeMode: 'range',
        startTime: formatLocalDateTime(start),
        endTime: formatLocalDateTime(end),
        deadline: null,
        dateText: formatDateParts(start),
        timeText: `${pad2(start.hour)}:${pad2(start.minute)}`,
        endDateText: formatDateParts(end),
        endTimeText: `${pad2(end.hour)}:${pad2(end.minute)}`,
      },
    }
  }

  if (deadline) {
    return {
      ok: true,
      value: {
        timeMode: 'deadline',
        deadline: formatLocalDateTime(deadline),
        startTime: null,
        endTime: null,
        dateText: formatDateParts(deadline),
        timeText: `${pad2(deadline.hour)}:${pad2(deadline.minute)}`,
        endDateText: '',
        endTimeText: '',
      },
    }
  }

  return { ok: false, message: '缺少明确的时间信息' }
}

export function normalizeAiTodoDraft(raw, nowParts = getBeijingNowParts()) {
  if (!raw || typeof raw !== 'object') {
    return { ok: false, message: 'AI 返回内容不是对象' }
  }

  const title = typeof raw.title === 'string' ? raw.title.trim() : ''
  const content = typeof raw.content === 'string' ? raw.content.trim() : ''
  const priority = Number(raw.priority)

  if (!title || ![1, 2, 3].includes(priority)) {
    return { ok: false, message: 'AI 返回的标题或优先级无效' }
  }

  const timeMode = String(raw.time_mode || '').trim().toLowerCase()
  const dateText = typeof raw.date_text === 'string' ? raw.date_text.trim() : ''
  const timeText = typeof raw.time_text === 'string' ? raw.time_text.trim() : ''
  const endDateText = typeof raw.end_date_text === 'string' ? raw.end_date_text.trim() : ''
  const endTimeText = typeof raw.end_time_text === 'string' ? raw.end_time_text.trim() : ''

  if ((!dateText || !timeText) && (typeof raw.deadline === 'string' || typeof raw.start_time === 'string')) {
    const explicit = normalizeExplicitRange(raw)
    if (explicit.ok) {
      return {
        ok: true,
        value: {
          title,
          content,
          priority,
          ...explicit.value,
        },
      }
    }
  }

  if (timeMode === 'range' || endDateText || endTimeText) {
    if (!dateText || !timeText || !endTimeText) {
      return { ok: false, message: 'AI 返回的日程时间段不完整，请补充开始和结束时间。' }
    }

    const resolvedStart = resolveDateTime(dateText, timeText, nowParts)
    if (!resolvedStart.ok) {
      return { ok: false, message: resolvedStart.message }
    }

    const resolvedEnd = resolveDateTime(endDateText || dateText, endTimeText, nowParts)
    if (!resolvedEnd.ok) {
      return { ok: false, message: resolvedEnd.message }
    }

    if (compareLocalDateTime(resolvedEnd.value, resolvedStart.value) < 0) {
      return { ok: false, message: '结束时间不能早于开始时间' }
    }

    return {
      ok: true,
      value: {
        title,
        content,
        priority,
        timeMode: 'range',
        startTime: resolvedStart.value,
        endTime: resolvedEnd.value,
        deadline: null,
        dateText: resolvedStart.dateText,
        timeText: resolvedStart.timeText,
        endDateText: resolvedEnd.dateText,
        endTimeText: resolvedEnd.timeText,
      },
    }
  }

  if (!dateText || !timeText) {
    return { ok: false, message: 'AI 没有返回明确的日期和时间，请补充更具体的时间描述' }
  }

  const resolvedDeadline = resolveDateTime(dateText, timeText, nowParts)
  if (!resolvedDeadline.ok) {
    return { ok: false, message: resolvedDeadline.message }
  }

  return {
    ok: true,
    value: {
      title,
      content,
      priority,
      timeMode: 'deadline',
      deadline: resolvedDeadline.value,
      startTime: null,
      endTime: null,
      dateText: resolvedDeadline.dateText,
      timeText: resolvedDeadline.timeText,
      endDateText: '',
      endTimeText: '',
    },
  }
}

export function getTodoPrimaryStart(todo) {
  return todo?.start_time || todo?.deadline || todo?.end_time || ''
}

export function getTodoPrimaryEnd(todo) {
  return todo?.end_time || todo?.deadline || todo?.start_time || ''
}

export function getTodoEffectiveRange(todo) {
  if (todo?.start_time && todo?.end_time) {
    return {
      start: todo.start_time,
      end: todo.end_time,
    }
  }

  const point = todo?.deadline || todo?.start_time || todo?.end_time || ''
  return {
    start: point,
    end: point,
  }
}

export function isTodoRangeEvent(todo) {
  return Boolean(todo?.start_time && todo?.end_time)
}

export function doLocalDateTimeRangesOverlap(aStart, aEnd, bStart, bEnd) {
  if (!aStart || !aEnd || !bStart || !bEnd) return false
  return compareLocalDateTime(aStart, bEnd) < 0 && compareLocalDateTime(bStart, aEnd) < 0
}

export function findConflictingRangeTodo(candidateTodo, todos, options = {}) {
  if (!isTodoRangeEvent(candidateTodo)) return null

  const excludeTodoId = options.excludeTodoId ?? null

  return (todos || []).find((todo) => {
    if (!isTodoRangeEvent(todo)) return false
    if (todo.status === 'cancelled') return false
    if (excludeTodoId !== null && todo.id === excludeTodoId) return false

    return doLocalDateTimeRangesOverlap(
      candidateTodo.start_time,
      candidateTodo.end_time,
      todo.start_time,
      todo.end_time
    )
  }) || null
}

export function getTodoDateKey(todo) {
  return getDateKey(getTodoPrimaryStart(todo))
}

export function getTodoMinutesRange(todo) {
  const startValue = getTodoPrimaryStart(todo)
  const endValue = getTodoPrimaryEnd(todo)
  const start = parseLocalDateTimeString(startValue)
  const end = parseLocalDateTimeString(endValue)

  if (!start) {
    return {
      startMinutes: 0,
      endMinutes: 0,
      durationMinutes: 30,
      isRange: false,
    }
  }

  const startMinutes = start.hour * 60 + start.minute
  const hasRange = Boolean(todo?.start_time && todo?.end_time && end)
  const rawEndMinutes = end ? end.hour * 60 + end.minute : startMinutes
  const endMinutes = Math.max(startMinutes, rawEndMinutes)
  const durationMinutes = hasRange ? Math.max(30, endMinutes - startMinutes || 30) : 30

  return {
    startMinutes,
    endMinutes,
    durationMinutes,
    isRange: hasRange,
  }
}

function formatMinutesLabel(totalMinutes) {
  const safeMinutes = Math.max(0, Math.min(totalMinutes, 24 * 60))
  const hour = Math.floor(safeMinutes / 60)
  const minute = safeMinutes % 60
  return `${pad2(hour)}:${pad2(minute)}`
}

function buildSingleDaySegment(todo) {
  const { startMinutes, endMinutes, durationMinutes, isRange } = getTodoMinutesRange(todo)
  const segmentEndMinutes = isRange ? Math.max(startMinutes, endMinutes) : startMinutes + durationMinutes

  return [{
    dayKey: getTodoDateKey(todo),
    segmentStartMinutes: startMinutes,
    segmentEndMinutes,
    durationMinutes,
    isRange,
    isStart: true,
    isEnd: true,
    todo,
  }]
}

export function splitTodoIntoDaySegments(todo) {
  const start = parseLocalDateTimeString(todo?.start_time)
  const end = parseLocalDateTimeString(todo?.end_time)

  if (!start || !end || compareLocalDateTime(todo?.end_time, todo?.start_time) <= 0) {
    return buildSingleDaySegment(todo)
  }

  const startDayKey = formatDateParts(start)
  const endDayKey = formatDateParts(end)

  if (startDayKey === endDayKey) {
    return buildSingleDaySegment(todo)
  }

  const segments = []
  let currentDay = { year: start.year, month: start.month, day: start.day }
  const endMinutes = end.hour * 60 + end.minute

  while (formatDateParts(currentDay) <= endDayKey) {
    const dayKey = formatDateParts(currentDay)
    const isStart = dayKey === startDayKey
    const isEnd = dayKey === endDayKey
    const segmentStartMinutes = isStart ? start.hour * 60 + start.minute : 0
    const segmentEndMinutes = isEnd ? endMinutes : 24 * 60

    if (segmentEndMinutes > segmentStartMinutes) {
      segments.push({
        dayKey,
        segmentStartMinutes,
        segmentEndMinutes,
        durationMinutes: segmentEndMinutes - segmentStartMinutes,
        isRange: true,
        isStart,
        isEnd,
        todo,
      })
    }

    if (isEnd) break
    currentDay = addDays(currentDay, 1)
  }

  return segments.length ? segments : buildSingleDaySegment(todo)
}

export function getTodoSegmentDisplayTime(segment) {
  if (!segment?.todo) return ''

  if (!segment.isRange) {
    return getTodoDisplayTime(segment.todo)
  }

  return `${formatMinutesLabel(segment.segmentStartMinutes)} - ${formatMinutesLabel(segment.segmentEndMinutes)}`
}

export function getTodoDisplayTime(todo) {
  if (todo?.start_time && todo?.end_time) {
    return `${getTimeLabel(todo.start_time)} - ${getTimeLabel(todo.end_time)}`
  }
  if (todo?.deadline) {
    return `截止 ${getTimeLabel(todo.deadline)}`
  }
  return ''
}

export function getTodoTimingSummary(todo) {
  if (todo?.start_time && todo?.end_time) {
    return `${formatDisplayLocalDateTime(todo.start_time)} - ${formatDisplayLocalDateTime(todo.end_time)}`
  }
  if (todo?.deadline) {
    return formatDisplayLocalDateTime(todo.deadline)
  }
  return ''
}
