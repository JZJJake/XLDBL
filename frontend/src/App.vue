<script setup lang="ts">
import { ref, onMounted } from 'vue'
import GraphView from './components/GraphView.vue'
import UploadPanel from './components/UploadPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import DocumentExplorer from './components/DocumentExplorer.vue'
import { Download, ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import axios from 'axios'

const graphViewRef = ref()
const docExplorerRef = ref()

const graphStats = ref<any>(null)
const leftPanelOpen = ref(true)
const rightPanelOpen = ref(true)

const toggleLeftPanel = () => leftPanelOpen.value = !leftPanelOpen.value
const toggleRightPanel = () => rightPanelOpen.value = !rightPanelOpen.value

const fetchStats = async () => {
  try {
    const res = await axios.get('/api/graph')
    if (res.data && res.data.stats) {
      graphStats.value = res.data.stats
    }
  } catch (error) {
    console.error("Failed to load stats", error)
  }
}

onMounted(() => {
  fetchStats()
})

const handleUploadSuccess = () => {
  if (graphViewRef.value) {
    graphViewRef.value.fetchGraphData()
  }
  if (docExplorerRef.value) {
    docExplorerRef.value.fetchDocuments()
  }
  fetchStats()
}

const handleExport = () => {
  window.open('/api/export', '_blank')
}
</script>

<template>
  <div class="app-container">
    <el-header class="header">
      <div class="header-left">
        <div class="logo">
          <h2>智能知识图谱与向量搜索系统</h2>
        </div>
        <span class="version-tag">版本号: YJ2026 | 开发者: YJ</span>
      </div>
      <div class="header-actions">
        <el-button type="success" :icon="Download" @click="handleExport">导出大模型外挂知识库 (JSON)</el-button>
      </div>
    </el-header>

    <div class="main-layout">
      <!-- 左侧：文件管理与上传 -->
      <div class="panel-wrapper left-wrapper" :class="{ 'is-collapsed': !leftPanelOpen }">
        <div class="panel left-panel">
          <div class="panel-title">
            数据管理库
          </div>
          <div class="stats-panel" v-if="graphStats">
            <div class="stat-item">
              <span class="stat-value">{{ graphStats.node_count || 0 }}</span>
              <span class="stat-label">节点量</span>
            </div>
            <div class="stat-item">
              <span class="stat-value">{{ graphStats.edge_count || 0 }}</span>
              <span class="stat-label">神经连接量</span>
            </div>
          </div>
          <UploadPanel @success="handleUploadSuccess" />
          <DocumentExplorer ref="docExplorerRef" />
        </div>
        <div class="toggle-btn left-toggle sidebar-toggle-left" @click="toggleLeftPanel">
          <el-icon><ArrowLeft v-if="leftPanelOpen" /><ArrowRight v-else /></el-icon>
        </div>
      </div>

      <!-- 中间：3D 知识图谱 -->
      <div class="graph-container">
        <GraphView ref="graphViewRef" />
      </div>

      <!-- 右侧：AI 交流区 -->
      <div class="panel-wrapper right-wrapper" :class="{ 'is-collapsed': !rightPanelOpen }">
        <div class="toggle-btn right-toggle sidebar-toggle-right" @click="toggleRightPanel">
          <el-icon><ArrowRight v-if="rightPanelOpen" /><ArrowLeft v-else /></el-icon>
        </div>
        <div class="panel right-panel">
          <ChatPanel />
        </div>
      </div>
    </div>
  </div>
</template>

<style>
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #0b0f19;
  color: #e0e0e0;
}
.app-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
}
.header {
  background-color: #121826;
  border-bottom: 1px solid #1f2937;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  height: 60px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}
.logo h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #f3f4f6;
}
.version-tag {
  font-size: 12px;
  color: #4ade80;
  background: rgba(74, 222, 128, 0.1);
  padding: 4px 8px;
  border-radius: 4px;
  border: 1px solid rgba(74, 222, 128, 0.2);
}
.main-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.panel-wrapper {
  position: relative;
  display: flex;
  height: 100%;
  transition: transform 0.3s ease, margin 0.3s ease;
  z-index: 10;
  flex-shrink: 0;
}

.left-wrapper {
  transform: translateX(0);
  margin-right: 0;
  width: 380px;
}
.left-wrapper.is-collapsed {
  transform: translateX(-100%);
  margin-right: -380px;
}

.right-wrapper {
  transform: translateX(0);
  margin-left: 0;
  width: 400px;
}
.right-wrapper.is-collapsed {
  transform: translateX(100%);
  margin-left: -400px;
}

.panel {
  background-color: #121826;
  display: flex;
  flex-direction: column;
  padding: 15px;
  color: #e0e0e0;
  height: 100%;
  width: 100%;
  box-sizing: border-box;
  overflow: hidden;
}

.left-panel {
  border-right: 1px solid #1f2937;
}
.right-panel {
  border-left: 1px solid #1f2937;
}

.toggle-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 60px;
  background-color: #1f2937;
  color: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border: 1px solid #374151;
  z-index: 20;
}
.toggle-btn:hover {
  background-color: #374151;
  color: #4ade80;
}

.left-toggle {
  right: -20px;
  border-radius: 0 8px 8px 0;
  border-left: none;
}
.right-toggle {
  left: -20px;
  border-radius: 8px 0 0 8px;
  border-right: none;
}
.panel-title {
  font-size: 16px;
  font-weight: bold;
  color: #f3f4f6;
  margin-bottom: 10px;
  border-bottom: 2px solid #67C23A;
  padding-bottom: 10px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Stats styling */
.stats-panel {
  display: flex;
  justify-content: space-between;
  background: #1e293b;
  border-radius: 8px;
  padding: 10px;
  margin-bottom: 15px;
}
.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-value {
  font-size: 16px;
  font-weight: bold;
  color: #38bdf8;
}
.stat-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 4px;
}

.graph-container {
  flex: 1;
  position: relative;
  background-color: #0b0f19; /* starry sky feel */
}
</style>
