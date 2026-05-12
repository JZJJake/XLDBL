<script setup lang="ts">
import { ref } from 'vue'
import { UploadFilled } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['success'])

const isUploading = ref(false)

const handleSuccess: UploadProps['onSuccess'] = (response) => {
  isUploading.value = false
  ElMessage.success(`File processed! Added ${response.chunks} chunks, ${response.nodes_added} nodes.`)
  emit('success')
}

const handleError: UploadProps['onError'] = () => {
  isUploading.value = false
  ElMessage.error('Upload or processing failed.')
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (!file.name.endsWith('.md')) {
    ElMessage.error('Please upload Markdown (.md) files only.')
    return false
  }
  isUploading.value = true
  return true
}
</script>

<template>
  <div class="upload-panel">
    <h3>Add Knowledge (.md)</h3>
    <el-upload
      class="upload-demo"
      drag
      action="http://localhost:8000/api/upload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :before-upload="beforeUpload"
      accept=".md"
      :show-file-list="false"
    >
      <div v-if="isUploading" class="upload-loading">
        <el-icon class="is-loading" :size="40"><UploadFilled /></el-icon>
        <div class="el-upload__text">Processing chunks & generating Graph...</div>
      </div>
      <div v-else>
        <el-icon class="el-icon--upload"><upload-filled /></el-icon>
        <div class="el-upload__text">
          Drop .md file here or <em>click to upload</em>
        </div>
      </div>
    </el-upload>
  </div>
</template>

<style scoped>
.upload-panel h3 {
  margin-top: 0;
  color: #303133;
}
.upload-loading {
  padding: 20px 0;
  color: #409EFC;
}
</style>
