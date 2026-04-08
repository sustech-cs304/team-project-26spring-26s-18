<template>
  <section class="course-timetable">
    <div class="timetable-top">
      <div>
        <div class="eyebrow">Course Schedule</div>
        <h2>本周课表视图</h2>
        <p>导入课程已按学期周次展开，可按周查看真实课程实例。</p>
      </div>

      <div class="timetable-actions">
        <div class="week-nav">
          <button class="week-nav-btn" @click="weekOffset -= 1">上一周</button>
          <span class="week-range">{{ currentWeekLabel }}</span>
          <button class="week-nav-btn" @click="weekOffset += 1">下一周</button>
        </div>
        <button class="import-btn" @click="$emit('import-course-schedule')">导入课程表</button>
      </div>
    </div>

    <div v-if="filteredCourses.length" class="timetable-summary">
      当前周显示 {{ filteredCourses.length }} 条课程安排
    </div>

    <div v-if="filteredCourses.length" class="timetable-grid-wrap">
      <div class="timetable-grid">
        <div class="corner-cell">节次</div>
        <div
          v-for="day in weekdayColumns"
          :key="day.value"
          class="weekday-header"
        >
          {{ day.label }}
        </div>

        <template v-for="section in sectionBlocks" :key="section.key">
          <div class="section-label">
            <strong>{{ section.label }}</strong>
            <span>{{ section.timeLabel }}</span>
          </div>

          <div
            v-for="day in weekdayColumns"
            :key="`${section.key}-${day.value}`"
            class="timetable-cell"
            :class="{
              'has-course': getCellCourses(day.value, section.key).length > 0,
              'has-single-course': getCellCourses(day.value, section.key).length === 1,
            }"
          >
            <div
              v-if="getCellCourses(day.value, section.key).length"
              class="course-stack"
              :class="{ 'is-single-course': getCellCourses(day.value, section.key).length === 1 }"
            >
              <article
                v-for="course in getCellCourses(day.value, section.key)"
                :key="course.id"
                class="course-card"
                :class="weekTypeClass(course)"
              >
                <strong class="course-title">{{ getDisplayTitle(course) }}</strong>
                <div v-if="getDisplayInstructor(course)" class="course-meta course-instructor">
                  {{ getDisplayInstructor(course) }}
                </div>
                <div v-if="getDisplayLocation(course)" class="course-meta course-location">
                  {{ getDisplayLocation(course) }}
                </div>
              </article>
            </div>
            <div v-else class="empty-slot">-</div>
          </div>
        </template>
      </div>
    </div>

    <div v-else class="empty-state">
      当前周暂无课程表数据。请先导入课程表，或切换到其他周查看。
    </div>
  </section>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  courses: {
    type: Array,
    default: () => [],
  },
})

defineEmits(['import-course-schedule'])

const weekOffset = ref(0)

const weekdayColumns = [
  { label: '星期一', value: 1 },
  { label: '星期二', value: 2 },
  { label: '星期三', value: 3 },
  { label: '星期四', value: 4 },
  { label: '星期五', value: 5 },
  { label: '星期六', value: 6 },
  { label: '星期日', value: 7 },
]

const sectionBlocks = [
  { key: '1-2', label: '第1-2节', timeLabel: '08:00 - 09:50', startMinutes: 8 * 60, endMinutes: 9 * 60 + 50 },
  { key: '3-4', label: '第3-4节', timeLabel: '10:20 - 12:10', startMinutes: 10 * 60 + 20, endMinutes: 12 * 60 + 10 },
  { key: '5-6', label: '第5-6节', timeLabel: '14:00 - 15:50', startMinutes: 14 * 60, endMinutes: 15 * 60 + 50 },
  { key: '7-8', label: '第7-8节', timeLabel: '16:20 - 18:10', startMinutes: 16 * 60 + 20, endMinutes: 18 * 60 + 10 },
  { key: '9-10', label: '第9-10节', timeLabel: '19:00 - 20:50', startMinutes: 19 * 60, endMinutes: 20 * 60 + 50 },
]

const validGridWeekdays = new Set(weekdayColumns.map((day) => day.value))
const validGridSectionKeys = new Set(sectionBlocks.map((section) => section.key))
const sectionKeyPattern = /第?\s*(\d+)\s*[-－—~至]\s*(\d+)\s*节?/u

const normalizedCourses = computed(() => {
  const courses = props.courses.map((course) => {
    const sectionKeyCandidate = getSectionKeyFromCourse(course)
    const gridWeekday = normalizeGridWeekday(course.weekday, course.start_time)
    const gridSectionKey = normalizeGridSectionKey(sectionKeyCandidate)
    return {
      ...course,
      debugSectionKeyCandidate: sectionKeyCandidate,
      gridWeekday,
      gridSectionKey,
    }
  })
  console.debug('[CourseTimetable] props.courses.length =', props.courses.length)
  console.debug('[CourseTimetable] normalizedCourses.length =', courses.length)
  courses.forEach((course) => {
    console.debug('[CourseTimetable] normalized course', {
      id: course.id,
      title: course.title || course.course_name,
      start_time: course.start_time,
      end_time: course.end_time,
      originalWeekday: course.weekday,
      section_text: course.section_text,
      derivedSectionKeyCandidate: course.debugSectionKeyCandidate,
      normalizedGridWeekday: course.gridWeekday,
      normalizedGridSectionKey: course.gridSectionKey,
    })
  })
  return courses
})

const currentWeekRange = computed(() => {
  const start = getMondayOfWeek(new Date())
  start.setDate(start.getDate() + weekOffset.value * 7)
  const end = new Date(start)
  end.setDate(end.getDate() + 7)
  return { start, end }
})

const currentWeekLabel = computed(() => {
  const start = currentWeekRange.value.start
  const end = new Date(currentWeekRange.value.end)
  end.setDate(end.getDate() - 1)
  return `${start.getMonth() + 1}月${start.getDate()}日 - ${end.getMonth() + 1}月${end.getDate()}日`
})

const filteredCourses = computed(() => {
  const invalidGridWeekdayCount = normalizedCourses.value.filter((course) => !course.gridWeekday).length
  const invalidGridSectionKeyCount = normalizedCourses.value.filter((course) => !course.gridSectionKey).length
  const outsideCurrentWeekCount = normalizedCourses.value.filter((course) => !isCourseInCurrentWeek(course)).length

  console.debug('[CourseTimetable] current visible week range =', formatWeekRange(currentWeekRange.value))

  const courses = normalizedCourses.value.filter((course) => {
    const inCurrentWeek = isCourseInCurrentWeek(course)
    const passed = Boolean(course.gridWeekday && course.gridSectionKey && inCurrentWeek)

    console.debug('[CourseTimetable] filter decision', {
      id: course.id,
      title: course.title || course.course_name,
      start_time: course.start_time,
      end_time: course.end_time,
      originalWeekday: course.weekday,
      section_text: course.section_text,
      derivedSectionKeyCandidate: course.debugSectionKeyCandidate,
      normalizedGridWeekday: course.gridWeekday,
      normalizedGridSectionKey: course.gridSectionKey,
      inCurrentWeek,
      finalPass: passed,
    })

    return passed
  })
  console.debug('[CourseTimetable] filteredCourses.length =', courses.length)
  console.debug('[CourseTimetable] invalid gridWeekday count =', invalidGridWeekdayCount)
  console.debug('[CourseTimetable] invalid gridSectionKey count =', invalidGridSectionKeyCount)
  console.debug('[CourseTimetable] outside current week count =', outsideCurrentWeekCount)
  return courses
})

const courseMap = computed(() => {
  const map = new Map()
  filteredCourses.value.forEach((course) => {
    const key = `${course.gridWeekday}-${course.gridSectionKey}`
    if (!map.has(key)) {
      map.set(key, [])
    }
    map.get(key).push(course)
  })

  map.forEach((items) => {
    items.sort((a, b) => String(a.course_name || a.title || '').localeCompare(String(b.course_name || b.title || ''), 'zh-Hans-CN'))
  })

  console.debug('[CourseTimetable] courseMap keys =', Array.from(map.keys()))

  return map
})

function getCellCourses(weekday, sectionKey) {
  return courseMap.value.get(`${weekday}-${sectionKey}`) || []
}

function getMondayOfWeek(value) {
  const date = new Date(value)
  date.setHours(0, 0, 0, 0)
  const day = date.getDay() || 7
  date.setDate(date.getDate() - day + 1)
  return date
}

function formatWeekRange(range) {
  return {
    start: formatDateTime(range.start),
    end: formatDateTime(range.end),
  }
}

function formatDateTime(value) {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) return value
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  const hours = String(value.getHours()).padStart(2, '0')
  const minutes = String(value.getMinutes()).padStart(2, '0')
  const seconds = String(value.getSeconds()).padStart(2, '0')
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function parseCourseDate(value) {
  const text = String(value || '')
  const matched = text.match(/^(\d{4})-(\d{2})-(\d{2})/)
  if (!matched) return null
  return new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]))
}

function isCourseInCurrentWeek(course) {
  const courseDate = parseCourseDate(course.start_time)
  if (!courseDate) return true
  return courseDate >= currentWeekRange.value.start && courseDate < currentWeekRange.value.end
}

function getWeekdayValue(value) {
  const datePart = String(value || '').slice(0, 10)
  const matched = datePart.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!matched) return null

  const [, year, month, day] = matched
  const date = new Date(Number(year), Number(month) - 1, Number(day))
  const dayValue = date.getDay()
  return dayValue === 0 ? 7 : dayValue
}

function normalizeGridWeekday(rawWeekday, startTime) {
  const numericWeekday = Number(rawWeekday)
  const derivedWeekday = Number.isInteger(numericWeekday) && validGridWeekdays.has(numericWeekday)
    ? numericWeekday
    : getWeekdayValue(startTime)
  return validGridWeekdays.has(derivedWeekday) ? derivedWeekday : null
}

function getMinutes(value, fallback) {
  const timePart = String(value || '').match(/T?(\d{2}):(\d{2})/)
  if (!timePart) return fallback
  return Number(timePart[1]) * 60 + Number(timePart[2])
}

function getSectionKey(startTime, endTime) {
  const startMinutes = getMinutes(startTime, 0)
  const endMinutes = getMinutes(endTime, startMinutes + 50)

  let bestSection = null
  let bestOverlap = -1

  sectionBlocks.forEach((section) => {
    const overlap = Math.min(endMinutes, section.endMinutes) - Math.max(startMinutes, section.startMinutes)
    if (overlap > bestOverlap) {
      bestOverlap = overlap
      bestSection = section.key
    }
  })

  return bestSection
}

function getSectionKeyFromCourse(course) {
  const rawText = String(course.section_text || '')
    .trim()
    .replace(/[－—~至]/g, '-')
    .replace(/第/g, '')
    .replace(/节/g, '')

  const matched = rawText.match(/(\d+)\s*-\s*(\d+)/)
  if (matched) {
    const canonicalKey = `${Number(matched[1])}-${Number(matched[2])}`
    if (validGridSectionKeys.has(canonicalKey)) {
      return canonicalKey
    }
  }

  return getSectionKey(course.start_time, course.end_time)
}

function normalizeGridSectionKey(sectionKey) {
  const key = String(sectionKey || '')
  return validGridSectionKeys.has(key) ? key : null
}

function normalizeWeekType(course) {
  const explicitType = String(course.week_type || '').trim().toLowerCase()
  if (['odd', 'single', '单周'].includes(explicitType)) {
    return 'odd'
  }
  if (['even', 'double', '双周'].includes(explicitType)) {
    return 'even'
  }
  if (['all', 'every', '全周', '每周'].includes(explicitType)) {
    return 'all'
  }

  const weekText = [
    course.week_info,
    course.week_text,
    course.description,
  ]
    .filter(Boolean)
    .join(' ')

  if (/单周/.test(weekText) && !/双周/.test(weekText)) {
    return 'odd'
  }
  if (/双周/.test(weekText) && !/单周/.test(weekText)) {
    return 'even'
  }

  return 'all'
}

function formatDisplayText(value) {
  return String(value || '')
    .trim()
    .replace(/^\[+|\]+$/g, '')
    .replace(/^(教师|老师|授课教师|地点|教室|位置)\s*[:：]\s*/u, '')
    .trim()
}

function normalizeCompareText(value) {
  return formatDisplayText(value)
    .replace(/[\s()[\]【】（）:：,，/／·._-]+/gu, '')
    .toLowerCase()
}

function getDisplayTitle(course) {
  return formatDisplayText(course.course_name || course.title)
}

function getDisplayInstructor(course) {
  return formatDisplayText(course.instructor)
}

function isUselessLocationText(locationText, course) {
  const locationKey = normalizeCompareText(locationText)
  const titleKey = normalizeCompareText(course.course_name || course.title)
  const instructorKey = normalizeCompareText(course.instructor)

  if (!locationKey) return true
  if (titleKey && (locationKey === titleKey || locationKey.includes(titleKey) || titleKey.includes(locationKey))) return true
  if (instructorKey && locationKey === instructorKey) return true
  if (/(第?\d+\s*[-－—~至]\s*\d+\s*节|周[一二三四五六日天]|单周|双周|全周|教学班|班级|行政班|专业|学院|[(（]英[)）]|英语|英文班)/u.test(locationText)) {
    return true
  }
  return false
}

function getDisplayLocation(course) {
  const cleanedLocation = formatDisplayText(course.location)
  return isUselessLocationText(cleanedLocation, course) ? '' : cleanedLocation
}

function weekTypeClass(course) {
  const weekType = normalizeWeekType(course)
  if (weekType === 'odd') return 'is-odd-week'
  if (weekType === 'even') return 'is-even-week'
  return 'is-all-week'
}

</script>

<style scoped>
.course-timetable {
  margin-top: 18px;
  padding: 24px;
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(251, 253, 255, 0.98), rgba(241, 247, 255, 0.98)),
    linear-gradient(135deg, rgba(21, 62, 143, 0.06), rgba(38, 124, 137, 0.04));
  border: 1px solid rgba(107, 135, 181, 0.16);
  box-shadow: 0 18px 40px rgba(79, 103, 137, 0.12);
}

.timetable-top {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.eyebrow {
  color: #56739c;
  font-size: 12px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.timetable-top h2 {
  margin: 6px 0 8px;
  color: #1e3047;
}

.timetable-top p {
  margin: 0;
  color: #58708f;
}

.timetable-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.week-nav {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}

.week-nav-btn {
  border: 1px solid rgba(87, 109, 148, 0.18);
  border-radius: 999px;
  padding: 10px 14px;
  background: #fff;
  color: #365179;
  font-weight: 700;
  cursor: pointer;
}

.week-range {
  color: #47607f;
  font-size: 13px;
  font-weight: 700;
}

.import-btn {
  border: none;
  border-radius: 999px;
  padding: 10px 16px;
  font-weight: 700;
  cursor: pointer;
}

.import-btn {
  background: linear-gradient(135deg, #1745a3, #2f73d9);
  color: #fff;
}

.timetable-summary {
  margin-top: 18px;
  padding: 12px 14px;
  border-radius: 14px;
  background: #eef5ff;
  color: #274166;
}

.timetable-grid-wrap {
  margin-top: 18px;
  overflow-x: auto;
}

.timetable-grid {
  min-width: 980px;
  display: grid;
  grid-template-columns: 110px repeat(7, minmax(120px, 1fr));
  grid-template-rows: 56px repeat(5, 156px);
  gap: 10px;
  align-items: stretch;
}

.corner-cell,
.weekday-header,
.section-label,
.timetable-cell {
  border-radius: 18px;
}

.corner-cell,
.weekday-header {
  padding: 14px 12px;
  background: #dde8f8;
  color: #294568;
  text-align: center;
  font-weight: 700;
}

.section-label {
  padding: 16px 12px;
  background: #f1f6fd;
  color: #37506f;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 6px;
  min-height: 0;
}

.section-label span {
  font-size: 12px;
  color: #69809d;
}

.timetable-cell {
  min-height: 0;
  height: 100%;
  padding: 5px;
  display: flex;
  border-radius: 18px;
  overflow: hidden;
}

.timetable-cell.has-course {
  padding: 2px;
  background: transparent;
  border: none;
}

.course-stack {
  display: flex;
  width: 100%;
  height: 100%;
  min-height: 0;
  box-sizing: border-box;
  flex-direction: column;
  gap: 4px;
  overflow: hidden;
}

.course-stack.is-single-course {
  flex: 1 1 auto;
  min-height: 100%;
}

.course-stack:not(.is-single-course) > .course-card {
  flex: 1 1 0;
}

.course-card {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 11px;
  min-height: 0;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
  border-radius: 16px;
  color: #1f3350;
  border: 1px solid rgba(76, 115, 177, 0.12);
  box-shadow: none;
  background-clip: padding-box;
  overflow: hidden;
}

.course-stack.is-single-course > .course-card:only-child {
  flex: 1 1 auto;
  min-height: 0;
}

.course-title {
  display: -webkit-box;
  overflow: hidden;
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  letter-spacing: 0.01em;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.course-stack.is-single-course .course-title {
  -webkit-line-clamp: 3;
  line-clamp: 3;
}

.course-card.is-all-week {
  background: linear-gradient(135deg, #dcecff 0%, #d2e4ff 100%);
  border-color: rgba(53, 104, 173, 0.16);
}

.course-card.is-odd-week {
  background: linear-gradient(135deg, #ffe2dc 0%, #ffd0d8 100%);
  border-color: rgba(197, 76, 92, 0.18);
}

.course-card.is-even-week {
  background: linear-gradient(135deg, #def7ea 0%, #d7f2e4 100%);
  border-color: rgba(46, 136, 98, 0.16);
}

.course-meta {
  margin-top: 4px;
  display: block;
  font-size: 13px;
  color: #506783;
  line-height: 1.3;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.course-stack:not(.is-single-course) .course-meta {
  display: -webkit-box;
  overflow: hidden;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
}

.course-instructor {
  color: #415a78;
}

.course-location {
  color: #59708c;
}

.empty-slot {
  width: 100%;
  height: 100%;
  min-height: 0;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: #9aaabd;
  background:
    linear-gradient(180deg, rgba(247, 250, 253, 0.75), rgba(242, 246, 251, 0.72));
  border: 1px dashed rgba(145, 164, 192, 0.24);
}

.empty-state {
  margin-top: 18px;
  padding: 18px;
  border-radius: 16px;
  background: #f5f8fc;
  color: #647991;
}

@media (max-width: 900px) {
  .course-timetable {
    padding: 18px;
  }
}
</style>
