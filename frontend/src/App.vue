<script setup lang="ts">
import { ref } from 'vue'
import GraphView from './components/GraphView.vue'
import UploadPanel from './components/UploadPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import { Download } from '@element-plus/icons-vue'

const graphViewRef = ref()

const handleUploadSuccess = () => {
  if (graphViewRef.value) {
    graphViewRef.value.fetchGraphData()
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
        <h2>KnowledgeGraph 3D VectorDB</h2>
      </div>
      <div class="header-actions">
        <el-button type="success" :icon="Download" @click="handleExport">Export Vector DB (JSON)</el-button>
      </div>
    </el-header>

    <el-container class="main-layout">
      <el-aside width="350px" class="sidebar">
        <UploadPanel @success="handleUploadSuccess" />
        <el-divider />
        <ChatPanel />
      </el-aside>

      <el-main class="graph-container">
        <GraphView ref="graphViewRef" />
      </el-main>
    </el-container>
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
.logo {
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #303133;
}
.main-layout {
  flex: 1;
  overflow: hidden;
}
.sidebar {
  background-color: #ffffff;
  border-right: 1px solid #e4e7ed;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}
.graph-container {
  padding: 0;
  position: relative;
  background-color: #000;
}
</style>
