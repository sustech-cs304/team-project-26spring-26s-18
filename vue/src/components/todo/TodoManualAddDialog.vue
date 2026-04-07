<template>
  <el-dialog
    :model-value="modelValue"
    title="手动添加 Todo"
    width="460px"
    @close="handleClose"
  >
    <el-form label-position="top" :model="form">
      <el-form-item label="标题" required>
        <el-input v-model="form.title" maxlength="100" placeholder="输入任务标题" />
      </el-form-item>

      <el-form-item label="内容">
        <el-input
          v-model="form.content"
          type="textarea"
          :rows="3"
          maxlength="300"
          placeholder="补充任务说明"
        />
      </el-form-item>

      <el-form-item label="时间类型" required>
        <el-radio-group v-model="form.timeMode">
          <el-radio-button label="deadline">截止型待办</el-radio-button>
          <el-radio-button label="range">日程时间块</el-radio-button>
        </el-radio-group>
      </el-form-item>

      <el-form-item v-if="form.timeMode === 'deadline'" label="截止时间" required>
        <el-date-picker
          v-model="form.deadline"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm:ss"
          format="YYYY-MM-DD HH:mm"
          placeholder="选择截止时间"
          style="width: 100%;"
        />
      </el-form-item>

      <template v-else>
        <el-form-item label="开始时间" required>
          <el-date-picker
            v-model="form.startTime"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            placeholder="选择开始时间"
            style="width: 100%;"
          />
        </el-form-item>

        <el-form-item label="结束时间" required>
          <el-date-picker
            v-model="form.endTime"
            type="datetime"
            value-format="YYYY-MM-DDTHH:mm:ss"
            format="YYYY-MM-DD HH:mm"
            placeholder="选择结束时间"
            style="width: 100%;"
          />
        </el-form-item>
      </template>

      <el-form-item label="优先级" required>
        <el-select v-model="form.priority" style="width: 100%;">
          <el-option label="低" :value="1" />
          <el-option label="中" :value="2" />
          <el-option label="高" :value="3" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">创建</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { compareLocalDateTime } from '@/utils/todoTime'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  initialValues: {
    type: Object,
    default: null,
  },
  submitting: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'submit'])

const createInitialForm = () => ({
  title: '',
  content: '',
  timeMode: 'deadline',
  deadline: '',
  startTime: '',
  endTime: '',
  priority: 2,
})

const form = reactive(createInitialForm())

watch(
  () => props.modelValue,
  (visible) => {
    if (visible) {
      Object.assign(form, createInitialForm(), props.initialValues || {})
    }
  }
)

function handleClose() {
  emit('update:modelValue', false)
}

function submitForm() {
  if (!form.title.trim()) {
    ElMessage.error('请输入标题')
    return
  }

  if (form.timeMode === 'deadline') {
    if (!form.deadline) {
      ElMessage.error('请选择截止时间')
      return
    }
  } else {
    if (!form.startTime || !form.endTime) {
      ElMessage.error('请选择开始和结束时间')
      return
    }
    if (compareLocalDateTime(form.endTime, form.startTime) < 0) {
      ElMessage.error('结束时间不能早于开始时间')
      return
    }
  }

  emit('submit', {
    title: form.title.trim(),
    content: form.content.trim() || null,
    priority: form.priority,
    deadline: form.timeMode === 'deadline' ? form.deadline : null,
    start_time: form.timeMode === 'range' ? form.startTime : null,
    end_time: form.timeMode === 'range' ? form.endTime : null,
  })
}
</script>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
}
</style>
