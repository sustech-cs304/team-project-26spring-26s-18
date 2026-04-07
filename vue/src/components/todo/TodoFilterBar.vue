<template>
  <div class="todo-filter-bar" role="tablist" aria-label="待办筛选">
    <button
      v-for="option in options"
      :key="option.value"
      type="button"
      class="filter-chip"
      :class="{ 'is-active': modelValue === option.value }"
      @click="emit('update:modelValue', option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  options: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue'])
</script>

<style scoped>
.todo-filter-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.filter-chip {
  height: 34px;
  padding: 0 14px;
  border: 1px solid #d9e4f0;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #5d738d;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
}

.filter-chip:hover {
  border-color: #b9cde3;
  color: #35506f;
}

.filter-chip.is-active {
  border-color: transparent;
  background: linear-gradient(135deg, #17395d 0%, #2560a1 100%);
  color: #fff;
  box-shadow: 0 10px 20px rgba(37, 96, 161, 0.18);
}
</style>
