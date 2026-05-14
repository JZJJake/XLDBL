<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Document, Reading, Notebook } from '@element-plus/icons-vue'
import axios from 'axios'

const rawDocs = ref<any[]>([])
const wikiPages = ref<string[]>([])
const currentMode = ref('wiki') // 'wiki' or 'raw'
const dialogVisible = ref(false)
const dialogContent = ref('')
const dialogTitle = ref('')

const fetchDocuments = async () => {
  try {
    const res = await axios.get('/api/documents')
    rawDocs.value = res.data
  } catch (error) {
    console.error("Failed to load documents", error)
  }
}

const fetchWikiPages = async () => {
  try {
    const res = await axios.get('/api/wiki')
    wikiPages.value = res.data.pages || []
  } catch (error) {
    console.error("Failed to load wiki pages", error)
  }
}

const viewContent = (content: string, title: string) => {
  dialogTitle.value = title
  dialogContent.value = content
  dialogVisible.value = true
}

const viewWikiPage = async (pageName: string) => {
  try {
    const res = await axios.get(`/api/wiki/${pageName}`)
    viewContent(res.data.content, pageName)
  } catch(e) {
    console.error(e)
  }
}

onMounted(() => {
  fetchDocuments()
  fetchWikiPages()
})

defineExpose({
  fetchDocuments,
  fetchWikiPages
})
</script>

<template>
  <div class="explorer-container">
    <div class="tabs">
      <div class="tab" :class="{ active: currentMode === 'wiki' }" @click="currentMode = 'wiki'; fetchWikiPages()">
        <el-icon><Notebook /></el-icon> Wiki 知识库
      </div>
      <div class="tab" :class="{ active: currentMode === 'raw' }" @click="currentMode = 'raw'; fetchDocuments()">
        <el-icon><Document /></el-icon> 原始数据
      </div>
    </div>

    <div class="content-list" v-if="currentMode === 'wiki'">
      <div v-if="wikiPages.length === 0" class="empty">暂无构建的Wiki知识</div>
      <div v-for="page in wikiPages" :key="page" class="wiki-item" @click="viewWikiPage(page)">
        <el-icon><Reading /></el-icon> {{ page }}
      </div>
    </div>

    <div class="content-list" v-if="currentMode === 'raw'">
      <el-tree
        :data="rawDocs"
        :props="{ children: 'children', label: 'label' }"
        @node-click="(data: any) => { if(!data.children) viewContent(data.content, data.label) }"
      >
        <template #default="{ node, data }">
          <span class="custom-tree-node">
            <el-icon v-if="data.children"><Document /></el-icon>
            <el-icon v-else><Reading /></el-icon>
            <span class="node-label">{{ node.label }}</span>
          </span>
        </template>
      </el-tree>
    </div>

    <!-- Content Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="70%"
      destroy-on-close
    >
      <div class="doc-content">
        <pre>{{ dialogContent }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<style scoped>
.explorer-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #1e293b;
  border-radius: 8px;
}
.tabs {
  display: flex;
  border-bottom: 1px solid #334155;
}
.tab {
  flex: 1;
  text-align: center;
  padding: 10px;
  cursor: pointer;
  color: #94a3b8;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
}
.tab.active {
  color: #38bdf8;
  border-bottom: 2px solid #38bdf8;
  background: #0f172a;
}
.content-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}
.empty {
  color: #64748b;
  text-align: center;
  margin-top: 20px;
}
.wiki-item {
  padding: 8px;
  margin-bottom: 5px;
  background: #334155;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
}
.wiki-item:hover {
  background: #475569;
}
.custom-tree-node {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
  overflow: hidden;
}
.node-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 250px;
}
:deep(.el-tree) {
  background: transparent;
  color: #e2e8f0;
}
:deep(.el-tree-node:focus > .el-tree-node__content) {
  background-color: #334155;
}
:deep(.el-tree-node__content:hover) {
  background-color: #334155;
}

.doc-content {
  background: #f8fafc;
  padding: 20px;
  border-radius: 8px;
  max-height: 60vh;
  overflow-y: auto;
  color: #334155;
  font-size: 14px;
  line-height: 1.6;
}
.doc-content pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: inherit;
  margin: 0;
}
</style>
