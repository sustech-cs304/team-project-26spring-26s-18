
<template>
  <div class="rag-upload-container">
    <h2>RAG 文件上传</h2>
    <div class="upload-area">
      <input type="file" ref="fileInput" multiple @change="handleFileChange" style="display: none;" />
      <button class="select-btn" @click="triggerFileInput">选择文件</button>
      <button class="upload-btn" :disabled="selectedFiles.length === 0 || loading" @click="uploadFiles">上传</button>
    </div>
    <div style="color:#888; font-size:13px; margin-bottom:8px;">只支持后缀为 txt、md、pdf、docx、pptx 的文件,且只能提取其中的文字内容</div>
    <div v-if="selectedFiles.length > 0" class="file-list">
      <div v-for="(file, idx) in selectedFiles" :key="idx" class="file-item">
        <span>{{ file.name }}</span>
        <button class="remove-btn" @click="removeFile(idx)">×</button>
      </div>
    </div>
    <div v-if="loading" class="loading-msg">正在上传...</div>
    <div v-if="successMsg" class="success-msg">{{ successMsg }}</div>
    <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
  </div>
</template>


<script setup>
import { ref } from 'vue'

const fileInput = ref(null)
const selectedFiles = ref([])
const loading = ref(false)
const successMsg = ref('')
const errorMsg = ref('')

function triggerFileInput() {
  fileInput.value.click()
}

function handleFileChange(e) {
  const files = e.target.files
  if (files.length > 0) {
    // 检查文件格式是否一致（可选，或允许多种格式）
    // 这里允许多种格式
    selectedFiles.value = [...selectedFiles.value, ...Array.from(files)]
  }
}

function removeFile(idx) {
  selectedFiles.value.splice(idx, 1)
}

function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.onerror = err => reject(err)
    reader.readAsDataURL(file)
  })
}

async function uploadFiles() {
  if (selectedFiles.value.length === 0) return
  loading.value = true
  successMsg.value = ''
  errorMsg.value = ''
  try {
    const filesBase64 = await Promise.all(selectedFiles.value.map(file => fileToBase64(file)))
    const fileTypes = selectedFiles.value.map(file => file.type)
    const fileNames = selectedFiles.value.map(file => file.name)
    const body = {
      files: filesBase64,
      file_types: fileTypes,
      file_names: fileNames
    }
    const resp = await fetch('http://localhost:8000/rag/upload', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    })
    if (resp.ok) {
      successMsg.value = '上传成功！'
      selectedFiles.value = []
    } else {
      const err = await resp.text()
      errorMsg.value = '上传失败: ' + err
    }
  } catch (e) {
    errorMsg.value = '上传异常: ' + e.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.rag-upload-container {
  max-width: 500px;
  margin: 40px auto;
  padding: 32px 24px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.08);
}
.upload-area {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}
.select-btn, .upload-btn {
  padding: 8px 20px;
  border: none;
  border-radius: 6px;
  background: #2196f3;
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  transition: background 0.2s;
}
.select-btn:hover, .upload-btn:hover {
  background: #1976d2;
}
.upload-btn:disabled {
  background: #bdbdbd;
  cursor: not-allowed;
}
.file-list {
  margin-bottom: 16px;
}
.file-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #e3f2fd;
  border-radius: 8px;
  padding: 8px 14px;
  margin-bottom: 8px;
  font-size: 14px;
}
.remove-btn {
  background: none;
  border: none;
  color: #888;
  font-size: 18px;
  cursor: pointer;
  border-radius: 50%;
  transition: background 0.2s;
}
.remove-btn:hover {
  background: #bbdefb;
  color: #333;
}
.loading-msg {
  color: #1976d2;
  margin-top: 10px;
}
.success-msg {
  color: #388e3c;
  margin-top: 10px;
}
.error-msg {
  color: #d32f2f;
  margin-top: 10px;
}
</style>