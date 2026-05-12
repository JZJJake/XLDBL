<script setup lang="ts">
import { ref } from 'vue'
import { Upload } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import { ElMessage } from 'element-plus'

const emit = defineEmits(['success'])
const isUploading = ref(false)

const handleSuccess: UploadProps['onSuccess'] = (response) => {
  isUploading.value = false
  ElMessage.success(`解析完成！添加了 ${response.chunks} 个数据块，${response.nodes_added} 个节点。`)
  emit('success')
}

const handleError: UploadProps['onError'] = () => {
  isUploading.value = false
  ElMessage.error('上传或处理失败，请重试。')
}

const beforeUpload: UploadProps['beforeUpload'] = (file) => {
  if (!file.name.endsWith('.md')) {
    ElMessage.error('请上传 Markdown (.md) 格式的文件。')
    return false
  }
  isUploading.value = true
  return true
}
</script>

<template>
  <div class="upload-panel">
    <el-upload
      action="http://localhost:8000/api/upload"
      :on-success="handleSuccess"
      :on-error="handleError"
      :before-upload="beforeUpload"
      accept=".md"
      :show-file-list="false"
    >
      <el-button type="primary" :loading="isUploading" :icon="Upload">
        {{ isUploading ? '大模型正在解析分析中...' : '追加上传 MD 知识文档' }}
      </el-button>
    </el-upload>
  </div>
</template>

<style scoped>
.upload-panel {
  margin-bottom: 15px;
}
</style>
