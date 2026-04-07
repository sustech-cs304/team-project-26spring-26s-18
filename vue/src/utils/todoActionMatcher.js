import {
  formatDateParts,
  getWeekStartDateParts,
  getTodoPrimaryStart,
  parseLocalDateTimeString,
  resolveChineseDateText,
  resolveChineseTimeText,
} from '@/utils/todoTime'

function normalizeText(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/\s+/g, '')
    .replace(/[，。、“”"'！？!?,.；：:（）()【】\-[\]{}]/g, '')
}

function buildSearchTexts(draft) {
  return [
    draft.targetHint,
    draft.title,
    draft.content,
  ]
    .map((item) => String(item || '').trim())
    .filter(Boolean)
}

function scoreTextMatch(source, query) {
  const normalizedSource = normalizeText(source)
  const normalizedQuery = normalizeText(query)
  if (!normalizedSource || !normalizedQuery) return 0
  if (normalizedSource === normalizedQuery) return 120
  if (normalizedSource.includes(normalizedQuery) || normalizedQuery.includes(normalizedSource)) return 90

  const queryChars = [...new Set(normalizedQuery.split(''))]
  const overlap = queryChars.filter((char) => normalizedSource.includes(char)).length
  if (!overlap) return 0

  const ratio = overlap / queryChars.length
  if (ratio >= 0.8) return 40
  if (ratio >= 0.55) return 20
  return 0
}

function sameWeek(todoDeadline, resolvedDate) {
  const parsed = parseLocalDateTimeString(todoDeadline)
  if (!parsed || !resolvedDate) return false

  const todoWeek = getWeekStartDateParts(parsed)
  const targetWeek = getWeekStartDateParts(resolvedDate)
  return formatDateParts(todoWeek) === formatDateParts(targetWeek)
}

export function matchTodoActionTarget(draft, todos, nowParts) {
  const searchTexts = buildSearchTexts(draft)
  const resolvedDate = draft.dateText ? resolveChineseDateText(draft.dateText, nowParts) : null
  const resolvedTime = draft.timeText ? resolveChineseTimeText(draft.timeText) : null

  const scored = (Array.isArray(todos) ? todos : [])
    .map((todo) => {
      let score = 0

      searchTexts.forEach((text) => {
        score += scoreTextMatch(todo.title, text)
        score += Math.floor(scoreTextMatch(todo.content || '', text) * 0.45)
      })

      const referenceTime = getTodoPrimaryStart(todo)
      const parsedDeadline = parseLocalDateTimeString(referenceTime)
      if (parsedDeadline && resolvedDate?.ok) {
        const todoDate = formatDateParts(parsedDeadline)
        const targetDate = formatDateParts(resolvedDate.dateParts)
        if (todoDate === targetDate) {
          score += 40
        } else if (sameWeek(referenceTime, resolvedDate.dateParts)) {
          score += 12
        }
      }

      if (parsedDeadline && resolvedTime?.ok) {
        if (parsedDeadline.hour === resolvedTime.hour && parsedDeadline.minute === resolvedTime.minute) {
          score += 30
        } else if (parsedDeadline.hour === resolvedTime.hour) {
          score += 10
        }
      }

      return { todo, score }
    })
    .filter((item) => item.score > 0)
    .sort((a, b) => b.score - a.score)

  if (!scored.length) {
    return {
      status: 'none',
      message: '我没有准确定位到要修改/删除的事项，请补充更具体的标题或时间。',
      candidates: [],
    }
  }

  const top = scored[0]
  const second = scored[1]
  const hasLowConfidence = top.score < 90
  const isAmbiguous = second && top.score - second.score < 20

  if (hasLowConfidence) {
    return {
      status: 'none',
      message: '我没有准确定位到要修改/删除的事项，请补充更具体的标题或时间。',
      candidates: scored.slice(0, 3).map((item) => item.todo),
    }
  }

  if (isAmbiguous) {
    return {
      status: 'multiple',
      message: '我找到了多个可能匹配的事项，请补充更具体的标题或时间。',
      candidates: scored.slice(0, 3).map((item) => item.todo),
    }
  }

  return {
    status: 'matched',
    todo: top.todo,
    candidates: [top.todo],
  }
}
