<script setup lang="ts">
import { ref } from 'vue'
import GraphView from './components/GraphView.vue'
import UploadPanel from './components/UploadPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import DocumentExplorer from './components/DocumentExplorer.vue'
import { Download } from '@element-plus/icons-vue'

const graphViewRef = ref()
const docExplorerRef = ref()

const handleUploadSuccess = () => {
  if (graphViewRef.value) {
    graphViewRef.value.fetchGraphData()
  }
  if (docExplorerRef.value) {
    docExplorerRef.value.fetchDocuments()
  }
}

const handleExport = () => {
  window.open('http://localhost:8000/api/export', '_blank')
}
</script>

<template>
  <div class="app-container">
    <el-header class="header">
      <div class="logo">
        <h2>智能知识图谱与向量搜索系统</h2>
      </div>
      <div class="header-actions">
        <el-button type="success" :icon="Download" @click="handleExport">导出大模型外挂知识库 (JSON)</el-button>
      </div>
    </el-header>

    <div class="main-layout">
      <!-- 左侧：文件管理与上传 -->
      <div class="panel left-panel">
        <div class="panel-title">数据管理库</div>
        <UploadPanel @success="handleUploadSuccess" />
        <DocumentExplorer ref="docExplorerRef" />
      </div>

      <!-- 中间：3D 知识图谱 -->
      <div class="graph-container">
        <GraphView ref="graphViewRef" />
      </div>

      <!-- 右侧：AI 交流区 -->
      <div class="panel right-panel">
        <ChatPanel />
      </div>
    </div>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #f5f7fa;
}
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background-color: #ffffff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}
.logo h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #303133;
}
.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.panel {
  background-color: #ffffff;
  display: flex;
  flex-direction: column;
  padding: 15px;
}
.left-panel {
  width: 300px;
  border-right: 1px solid #e4e7ed;
}
.right-panel {
  width: 350px;
  border-left: 1px solid #e4e7ed;
}
.panel-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 15px;
  border-bottom: 2px solid #67C23A;
  padding-bottom: 10px;
}
.graph-container {
  flex: 1;
  position: relative;
  background-color: #000;
}
</style>
