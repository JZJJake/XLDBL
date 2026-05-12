<script setup lang="ts">
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { Document, Files } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const treeData = ref<any[]>([])
const loading = ref(false)
const selectedContent = ref('')
const contentDialogVisible = ref(false)

const fetchDocuments = async () => {
  loading.value = true
  try {
    const res = await axios.get('http://localhost:8000/api/documents')
    treeData.value = res.data || []
  } catch (error) {
    ElMessage.error('无法加载文档列表')
  } finally {
    loading.value = false
  }
}

const handleNodeClick = (data: any) => {
  if (data.content) {
    selectedContent.value = data.content
    contentDialogVisible.value = true
  }
}

onMounted(() => {
  fetchDocuments()
})

defineExpose({ fetchDocuments })
</script>

<template>
  <div class="explorer-panel" v-loading="loading">
    <el-tree
      :data="treeData"
      :props="{ children: 'children', label: 'label' }"
      @node-click="handleNodeClick"
      class="custom-tree"
      empty-text="暂无文档"
    >
      <template #default="{ node, data }">
        <span class="custom-tree-node">
          <el-icon v-if="data.children"><Files /></el-icon>
          <el-icon v-else><Document /></el-icon>
          <span>{{ node.label }}</span>
        </span>
      </template>
    </el-tree>

    <el-dialog v-model="contentDialogVisible" title="原始内容" width="50%">
      <div class="raw-content">{{ selectedContent }}</div>
    </el-dialog>
  </div>
</template>

<style scoped>
.explorer-panel {
  flex: 1;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 10px;
  background-color: #f9fafc;
}
.custom-tree {
  background: transparent;
}
.custom-tree-node {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #606266;
}
.raw-content {
  white-space: pre-wrap;
  background: #f5f7fa;
  padding: 15px;
  border-radius: 6px;
  font-family: monospace;
  line-height: 1.5;
  color: #303133;
}
</style>
