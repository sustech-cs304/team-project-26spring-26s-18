<template>
  <el-dialog
    :model-value="modelValue"
    title="导入日程来源"
    width="720px"
    destroy-on-close
    @close="emit('update:modelValue', false)"
  >
    <div class="import-dialog">
      <el-alert
        type="info"
        :closable="false"
        show-icon
        :title="infoTitle"
      />

      <el-form label-width="96px" class="import-form">
        <el-form-item label="导入来源">
          <el-radio-group :model-value="form.sourceType" @update:model-value="updateField('sourceType', $event)">
            <el-radio-button label="official-calendar">官方校历</el-radio-button>
            <el-radio-button label="course-schedule">课程表</el-radio-button>
            <el-radio-button label="blackboard">Blackboard</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="内容格式">
          <el-select :model-value="form.contentType" @update:model-value="updateField('contentType', $event)">
            <el-option label="自动识别" value="auto" />
            <el-option label="JSON" value="json" />
            <el-option label="CSV" value="csv" />
            <el-option label="制表符表格" value="table" />
            <el-option label="ICS" value="ics" />
            <el-option label="XLSX" value="xlsx" />
          </el-select>
        </el-form-item>

        <el-form-item label="导入模式">
          <el-radio-group :model-value="form.inputMode" @update:model-value="updateField('inputMode', $event)">
            <el-radio-button label="paste">粘贴文本</el-radio-button>
            <el-radio-button label="file">上传文件</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="替换旧数据">
          <el-switch :model-value="form.replaceExisting" @update:model-value="updateField('replaceExisting', $event)" />
          <span class="hint-text">
            {{
              form.sourceType === 'official-calendar'
                ? '覆盖当前共享官方校历数据'
                : form.sourceType === 'blackboard'
                  ? '仅覆盖当前账号下已导入的 Blackboard 事项'
                  : '覆盖当前账号下的课程表数据'
            }}
          </span>
        </el-form-item>

        <template v-if="showTermControls">
          <el-form-item label="学期">
            <el-select :model-value="form.term" @update:model-value="updateField('term', $event)">
              <el-option label="春季学期" value="spring" />
              <el-option label="秋季学期" value="fall" />
            </el-select>
          </el-form-item>

          <el-form-item label="年份">
            <el-input-number
              :model-value="form.year"
              :min="2000"
              :max="2100"
              :step="1"
              controls-position="right"
              @update:model-value="updateField('year', $event)"
            />
          </el-form-item>
        </template>

        <el-form-item v-if="form.inputMode === 'file'" label="选择文件">
          <div class="file-pick">
            <input ref="fileInputRef" class="file-input" type="file" :accept="fileAccept" @change="handleFileChange" />
            <el-button @click="triggerFilePick">选择文件</el-button>
            <span class="file-name">{{ form.fileName || '未选择文件' }}</span>
          </div>
        </el-form-item>

        <el-form-item v-if="showContentInput" label="导入内容">
          <el-input
            :model-value="form.content"
            type="textarea"
            :rows="12"
            :placeholder="contentPlaceholder"
            @update:model-value="updateField('content', $event)"
          />
        </el-form-item>
      </el-form>

      <div class="sample-block">
        <div class="sample-title">字段提示</div>
        <div class="sample-text">
          {{ sampleHint }}
        </div>
        <pre class="sample-code">{{ sampleContent }}</pre>
      </div>
    </div>

    <template #footer>
      <span class="dialog-footer">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">开始导入</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
  form: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue', 'update:form', 'submit'])
const fileInputRef = ref(null)

const infoTitle = computed(() => {
  if (props.form.sourceType === 'official-calendar') {
    return '官方校历使用开发者/管理员预处理后的共享结构化数据导入，本轮不做 PDF 解析。'
  }
  if (props.form.sourceType === 'blackboard') {
    return 'Blackboard ICS 按当前用户导入，并优先映射为截止型待办，不会作为共享数据。'
  }
  return '课程表导入后仅作为独立来源保存和预览，本轮不会并入个人周视图。'
})

const contentPlaceholder = computed(() => {
  if (props.form.sourceType === 'official-calendar') {
    return '粘贴开发者/管理员预处理后的官方校历 JSON / CSV / 表格文本。'
  }
  if (props.form.sourceType === 'blackboard') {
    return '粘贴 Blackboard 导出的 .ics 原始内容，或上传 .ics 文件。'
  }
  return '支持传统课表 .xlsx 上传，也兼容 JSON 数组、CSV，或制表符分隔的课程表文本。'
})

const sampleHint = computed(() => {
  if (props.form.sourceType === 'official-calendar') {
    return '官方校历至少需要 `title + display_mode + source_year + start_time + end_time`。display_mode 只允许 `background` 或 `event`。'
  }
  if (props.form.sourceType === 'blackboard') {
    return 'Blackboard ICS 将读取 `SUMMARY / DTSTART / DTEND / UID / DESCRIPTION / LOCATION`，并优先映射为 deadline-style Todo。'
  }
  return '课程表优先支持传统周课表 .xlsx，按星期列和节次行解析课程单元格。'
})

const sampleContent = computed(() => {
  if (props.form.sourceType === 'blackboard') {
    return `BEGIN:VEVENT
DTSTART;TZID=Asia/Shanghai:20260315T235900
DTEND;TZID=Asia/Shanghai:20260315T235900
SUMMARY:Programming Assignment 1
UID:blackboard-assignment-1
DESCRIPTION:Submit on Blackboard
END:VEVENT`
  }
  if (props.form.sourceType === 'course-schedule') {
    return `高等数学
1-16周
张老师
教学楼A-201`
  }

  return `title,display_mode,source_year,event_type,start_time,end_time,location
Mid-term Exams,background,2026,exam_period,2026-04-20 00:00,2026-04-24 23:59,Campus
Sports Day,event,2026,activity,2026-05-15 09:00,2026-05-15 17:00,Main Stadium`
})

const fileAccept = computed(() => {
  if (props.form.sourceType === 'course-schedule') {
    return '.xlsx,.json,.csv,.txt,.tsv'
  }
  if (props.form.sourceType === 'blackboard') {
    return '.ics,.txt'
  }
  return '.json,.csv,.txt,.tsv'
})

const showContentInput = computed(() => {
  return !(props.form.sourceType === 'course-schedule' && props.form.inputMode === 'file' && props.form.contentType === 'xlsx')
})

const showTermControls = computed(() => {
  return props.form.sourceType === 'course-schedule'
})

function updateField(field, value) {
  if (field === 'sourceType') {
    let nextContentType = props.form.contentType
    if (value === 'blackboard') {
      nextContentType = 'ics'
    } else if (value === 'course-schedule' && props.form.inputMode === 'file') {
      nextContentType = 'xlsx'
    } else if (props.form.contentType === 'ics' || props.form.contentType === 'xlsx') {
      nextContentType = 'auto'
    }
    emit('update:form', {
      ...props.form,
      sourceType: value,
      contentType: nextContentType,
      file: null,
      fileName: '',
    })
    return
  }

  if (field === 'inputMode') {
    const nextContentType = value === 'file' && props.form.sourceType === 'course-schedule'
      ? 'xlsx'
      : value === 'file' && props.form.sourceType === 'blackboard'
        ? 'ics'
        : props.form.contentType === 'xlsx' || props.form.contentType === 'ics'
          ? 'auto'
          : props.form.contentType
    emit('update:form', {
      ...props.form,
      inputMode: value,
      contentType: nextContentType,
      file: null,
      fileName: '',
      content: value === 'file' && props.form.sourceType === 'course-schedule' ? '' : props.form.content,
    })
    return
  }

  emit('update:form', {
    ...props.form,
    [field]: value,
  })
}

function triggerFilePick() {
  fileInputRef.value?.click()
}

function handleFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return

  if (props.form.sourceType === 'course-schedule' && file.name.toLowerCase().endsWith('.xlsx')) {
    emit('update:form', {
      ...props.form,
      file,
      fileName: file.name,
      contentType: 'xlsx',
      content: '',
    })
    return
  }

  const reader = new FileReader()
  reader.onload = () => {
    emit('update:form', {
      ...props.form,
      file,
      fileName: file.name,
      content: typeof reader.result === 'string' ? reader.result : '',
    })
  }
  reader.readAsText(file)
}

function handleSubmit() {
  emit('submit')
}
</script>

<style scoped>
.import-dialog {
  display: grid;
  gap: 16px;
}

.import-form {
  margin-top: 4px;
}

.file-pick {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}

.file-input {
  display: none;
}

.file-name {
  color: #5c6b82;
  font-size: 13px;
}

.hint-text {
  margin-left: 12px;
  color: #5c6b82;
  font-size: 13px;
}

.el-form-item :deep(.el-textarea__inner) {
  font-family: inherit;
}

.sample-block {
  border-radius: 14px;
  padding: 14px 16px;
  background: #f5f8fc;
  border: 1px solid rgba(107, 135, 181, 0.16);
}

.sample-title {
  font-weight: 600;
  color: #24364d;
}

.sample-text {
  margin-top: 6px;
  color: #5c6b82;
  font-size: 13px;
}

.sample-code {
  margin: 12px 0 0;
  padding: 12px;
  border-radius: 10px;
  background: #0e1726;
  color: #e8eef8;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
}
</style>
