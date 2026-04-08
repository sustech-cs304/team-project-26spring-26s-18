<template>
  <el-dialog
    :model-value="modelValue"
    width="520px"
    :title="isEditing ? '编辑 Todo' : 'Todo 详情'"
    @close="handleClose"
  >
    <template v-if="todo">
      <div v-if="!isEditing" class="detail-view" :class="{ 'is-done-view': todo.status === 'done' }">
        <div class="detail-header">
          <div>
            <div class="status-chip" :class="statusClass(todo.status)">{{ statusText(todo.status) }}</div>
            <h3>{{ todo.title }}</h3>
          </div>
          <div class="priority-chip" :class="priorityClass(todo.priority)">{{ priorityText(todo.priority) }}</div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <span>{{ todo.start_time && todo.end_time ? '时间段' : '截止时间' }}</span>
            <strong>{{ timingSummary }}</strong>
          </div>
          <div class="detail-item">
            <span>状态</span>
            <strong>{{ statusText(todo.status) }}</strong>
          </div>
          <div class="detail-item">
            <span>优先级</span>
            <strong>{{ priorityText(todo.priority) }}</strong>
          </div>
          <div class="detail-item">
            <span>类型</span>
            <strong>{{ todo.start_time && todo.end_time ? '日程时间块' : '截止型待办' }}</strong>
          </div>
          <div v-if="todo.import_source === 'blackboard'" class="detail-item">
            <span>来源</span>
            <strong>Blackboard</strong>
          </div>
        </div>

        <div class="detail-content" :class="{ 'is-done-content': todo.status === 'done' }">
          <div class="content-label">详细说明</div>
          <div class="content-box">{{ todo.content || '暂无详细描述' }}</div>
        </div>

        <div class="quick-actions">
          <el-button
            v-if="todo.status !== 'done'"
            type="success"
            :loading="statusLoading"
            @click="emitStatus('done')"
          >
            标记完成
          </el-button>
          <el-button
            v-if="todo.status !== 'pending'"
            :loading="statusLoading"
            @click="emitStatus('pending')"
          >
            标记待办
          </el-button>
          <el-button type="primary" @click="isEditing = true">编辑</el-button>
          <el-button type="danger" :loading="deleteLoading" @click="emitDelete">删除</el-button>
        </div>
      </div>

      <el-form v-else label-position="top" :model="form">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="100" />
        </el-form-item>

        <el-form-item label="内容">
          <el-input v-model="form.content" type="textarea" :rows="4" maxlength="300" />
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
              style="width: 100%;"
            />
          </el-form-item>

          <el-form-item label="结束时间" required>
            <el-date-picker
              v-model="form.endTime"
              type="datetime"
              value-format="YYYY-MM-DDTHH:mm:ss"
              format="YYYY-MM-DD HH:mm"
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

        <el-form-item label="状态">
          <el-select v-model="form.status" style="width: 100%;">
            <el-option label="待办" value="pending" />
            <el-option label="完成" value="done" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
        </el-form-item>
      </el-form>
    </template>

    <template #footer>
      <div class="dialog-footer">
        <template v-if="isEditing">
          <el-button @click="cancelEdit">取消</el-button>
          <el-button type="primary" :loading="saveLoading" @click="emitSave">保存</el-button>
        </template>
        <el-button v-else @click="handleClose">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { compareLocalDateTime, getTodoTimingSummary } from '@/utils/todoTime'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false,
  },
  todo: {
    type: Object,
    default: null,
  },
  saveLoading: {
    type: Boolean,
    default: false,
  },
  deleteLoading: {
    type: Boolean,
    default: false,
  },
  statusLoading: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'save', 'delete', 'update-status'])

const isEditing = ref(false)
const form = reactive({
  title: '',
  content: '',
  timeMode: 'deadline',
  deadline: '',
  startTime: '',
  endTime: '',
  priority: 2,
  status: 'pending',
})

const timingSummary = computed(() => getTodoTimingSummary(props.todo))

function applyTodoToForm(todo) {
  Object.assign(form, {
    title: todo.title || '',
    content: todo.content || '',
    timeMode: todo.start_time && todo.end_time ? 'range' : 'deadline',
    deadline: todo.deadline || '',
    startTime: todo.start_time || '',
    endTime: todo.end_time || '',
    priority: todo.priority ?? 2,
    status: todo.status || 'pending',
  })
}

watch(
  () => [props.modelValue, props.todo],
  ([visible, todo]) => {
    if (visible && todo) {
      isEditing.value = false
      applyTodoToForm(todo)
    }
  },
  { immediate: true }
)

function handleClose() {
  emit('update:modelValue', false)
}

function cancelEdit() {
  isEditing.value = false
  if (props.todo) {
    applyTodoToForm(props.todo)
  }
}

function emitSave() {
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

  emit('save', {
    title: form.title.trim(),
    content: form.content.trim() || null,
    deadline: form.timeMode === 'deadline' ? form.deadline : null,
    start_time: form.timeMode === 'range' ? form.startTime : null,
    end_time: form.timeMode === 'range' ? form.endTime : null,
    priority: form.priority,
    status: form.status,
  })
}

async function emitDelete() {
  try {
    await ElMessageBox.confirm('确定要删除这个 Todo 吗？', '删除确认', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    emit('delete')
  } catch {
  }
}

function emitStatus(status) {
  emit('update-status', status)
}

function priorityText(priority) {
  if (priority === 3) return '高'
  if (priority === 1) return '低'
  return '中'
}

function priorityClass(priority) {
  if (priority === 3) return 'is-high'
  if (priority === 1) return 'is-low'
  return 'is-medium'
}

function statusText(status) {
  if (status === 'done') return '已完成'
  if (status === 'cancelled') return '已取消'
  return '待办中'
}

function statusClass(status) {
  if (status === 'done') return 'is-done'
  if (status === 'cancelled') return 'is-cancelled'
  return 'is-pending'
}
</script>

<style scoped>
.detail-view {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.detail-view.is-done-view {
  color: #516071;
}

.detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-header h3 {
  margin: 10px 0 0;
  font-size: 24px;
  color: #1f304a;
}

.detail-view.is-done-view .detail-header h3 {
  color: #5d6b7b;
  opacity: 0.92;
  text-decoration: line-through;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-item {
  padding: 14px;
  border-radius: 14px;
  background: #f6f9fc;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.detail-view.is-done-view .detail-item {
  background: #f4f6f8;
}

.detail-item span,
.content-label {
  font-size: 12px;
  color: #7b8ca4;
}

.content-box {
  min-height: 92px;
  padding: 14px;
  border-radius: 14px;
  background: #f6f9fc;
  color: #24384f;
  line-height: 1.6;
  white-space: pre-wrap;
}

.detail-content.is-done-content .content-box {
  background: #f4f6f8;
  color: #5f6d7d;
  text-decoration: line-through;
}

.detail-content.is-done-content .content-label,
.detail-view.is-done-view .detail-item span {
  color: #8895a4;
}

.quick-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.status-chip,
.priority-chip {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.is-pending {
  background: #e7f1ff;
  color: #255ea2;
}

.is-done {
  background: #ebeff3;
  color: #5c6877;
}

.is-cancelled {
  background: #f7e3e3;
  color: #994646;
}
</style>
