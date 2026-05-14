<script setup lang="ts">
import { ref } from 'vue'
import { Upload, Link } from '@element-plus/icons-vue'
import type { UploadProps } from 'element-plus'
import { ElMessage } from 'element-plus'
import axios from 'axios'

const emit = defineEmits(['success'])
const isUploading = ref(false)
const inputUrl = ref('')

const handleSuccess: UploadProps['onSuccess'] = (response) => {
  isUploading.value = false
  ElMessage.success(`解析完成！添加了 ${response.chunks} 个数据块，${response.nodes_added} 个节点。`)
  emit('success')
}

const handleError: UploadProps['onError'] = () => {
  isUploading.value = false
  ElMessage.error('上传或处理失败，请重试。')
}

const beforeUpload: UploadProps['beforeUpload'] = (_file) => {
  isUploading.value = true
  return true
}

const handleUrlUpload = async () => {
  if (!inputUrl.value.trim()) {
    ElMessage.warning('请输入有效的网页URL')
    return
  }
  isUploading.value = true
  try {
    const formData = new FormData()
    formData.append('url', inputUrl.value.trim())
    const res = await axios.post('/api/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    handleSuccess(res.data, null as any, [])
    inputUrl.value = ''
  } catch (err) {
    handleError(err as any, null as any, [])
  }
}
</script>

<template>
  <div class="upload-panel">
    <el-tabs type="border-card">
      <el-tab-pane label="文件上传">
        <el-upload
          action="/api/upload"
          :on-success="handleSuccess"
          :on-error="handleError"
          :before-upload="beforeUpload"
          accept="*"
          :show-file-list="false"
        >
          <el-button type="primary" :loading="isUploading" :icon="Upload" class="full-width">
            {{ isUploading ? '大模型正在解析分析中...' : '追加上传知识文档' }}
          </el-button>
        </el-upload>
      </el-tab-pane>
      <el-tab-pane label="网页URL抓取">
        <div class="url-upload-container">
          <el-input v-model="inputUrl" placeholder="输入网页地址 (https://...)" clearable />
          <el-button type="success" :loading="isUploading" :icon="Link" @click="handleUrlUpload">
            抓取
          </el-button>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.upload-panel {
  margin-bottom: 15px;
}
.full-width {
  width: 100%;
}
.url-upload-container {
  display: flex;
  gap: 10px;
}
</style>
