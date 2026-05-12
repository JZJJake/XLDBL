<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import ForceGraph3D from '3d-force-graph'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, InfoFilled } from '@element-plus/icons-vue'

const graphContainer = ref<HTMLElement | null>(null)
let Graph: any = null

const nodes = ref<any[]>([])
const links = ref<any[]>([])

// Dialogs state
const nodeDialogVisible = ref(false)
const edgeDialogVisible = ref(false)

const nodeForm = ref({ id: '', label: '', type: 'Entity', description: '' })
const edgeForm = ref({ id: '', source: '', target: '', relation: '', description: '' })

// Selection state for Info Panel
const selectedNode = ref<any>(null)
const selectedEdge = ref<any>(null)
const connectedNeighbors = ref<any[]>([])

const fetchGraphData = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/graph')
    nodes.value = res.data.nodes || []
    links.value = res.data.links || []

    if (Graph) {
      Graph.graphData({ nodes: nodes.value, links: links.value })
    }
  } catch (error) {
    ElMessage.error('无法加载图谱数据')
  }
}

const updateNeighbors = (node: any) => {
  if (!node) {
    connectedNeighbors.value = []
    return
  }
  const relatedLinks = links.value.filter(l =>
    (l.source.id || l.source) === node.id || (l.target.id || l.target) === node.id
  )

  const neighbors = relatedLinks.map(l => {
    const isSource = (l.source.id || l.source) === node.id
    const targetNodeId = isSource ? (l.target.id || l.target) : (l.source.id || l.source)
    const targetNode = nodes.value.find(n => n.id === targetNodeId)

    return {
      relation: l.relation,
      direction: isSource ? 'outgoing' : 'incoming',
      node: targetNode
    }
  }).filter(item => item.node)

  connectedNeighbors.value = neighbors
}

const initGraph = () => {
  if (!graphContainer.value) return

  Graph = (ForceGraph3D as any)()(graphContainer.value)
    .graphData({ nodes: nodes.value, links: links.value })
    .nodeLabel('label')
    .nodeAutoColorBy('type')
    .nodeVal((node: any) => {
      const base = 5;
      const bonus = node.description ? Math.min(node.description.length / 50, 15) : 0;
      return base + bonus;
    })
    .linkDirectionalArrowLength(4)
    .linkDirectionalArrowRelPos(1)
    .linkDirectionalParticles(2)
    .linkDirectionalParticleSpeed(0.005)
    .linkLabel('relation')
    .onNodeClick((node: any) => {
      selectedNode.value = node
      selectedEdge.value = null
      updateNeighbors(node)

      const distance = 80;
      const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
      Graph.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        node,
        2000
      );
    })
    .onLinkClick((link: any) => {
      selectedEdge.value = link
      selectedNode.value = null
      connectedNeighbors.value = []
    })
    .onBackgroundClick(() => {
      selectedNode.value = null
      selectedEdge.value = null
      connectedNeighbors.value = []
    })
}

onMounted(() => {
  initGraph()
  fetchGraphData()

  window.addEventListener('resize', () => {
    if (Graph && graphContainer.value) {
      Graph.width(graphContainer.value.clientWidth)
      Graph.height(graphContainer.value.clientHeight)
    }
  })
})

onBeforeUnmount(() => {
  if (Graph) Graph._destructor()
})

const openAddNode = () => {
  nodeForm.value = { id: 'node_' + Date.now(), label: '', type: 'Entity', description: '' }
  nodeDialogVisible.value = true
}

const submitNode = async () => {
  try {
    await axios.post('http://localhost:8000/api/nodes', nodeForm.value)
    ElMessage.success('节点添加成功')
    nodeDialogVisible.value = false
    fetchGraphData()
  } catch (error) {
    ElMessage.error('添加节点失败')
  }
}

const handleDeleteNode = async () => {
  if (!selectedNode.value) return
  try {
    await ElMessageBox.confirm('确定要删除此知识节点及其关联边吗？', '警告', { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' })
    await axios.delete(`http://localhost:8000/api/nodes/${selectedNode.value.id}`)
    ElMessage.success('节点已删除')
    selectedNode.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除节点失败')
  }
}

const openAddEdge = () => {
  edgeForm.value = { id: 'edge_' + Date.now(), source: '', target: '', relation: '', description: '' }
  edgeDialogVisible.value = true
}

const submitEdge = async () => {
  try {
    await axios.post('http://localhost:8000/api/edges', edgeForm.value)
    ElMessage.success('关联添加成功')
    edgeDialogVisible.value = false
    fetchGraphData()
  } catch (error) {
    ElMessage.error('添加关联失败')
  }
}

const handleDeleteEdge = async () => {
  if (!selectedEdge.value) return
  try {
    await ElMessageBox.confirm('确定要删除此逻辑关联吗？', '警告', { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' })
    const edgeId = selectedEdge.value.id
    await axios.delete(`http://localhost:8000/api/edges/${edgeId}`)
    ElMessage.success('关联已删除')
    selectedEdge.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除关联失败')
  }
}

defineExpose({ fetchGraphData })
</script>

<template>
  <div class="graph-wrapper">
    <div ref="graphContainer" class="graph-canvas"></div>

    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openAddNode">新增知识点</el-button>
      <el-button type="primary" :icon="Plus" @click="openAddEdge">新增逻辑边</el-button>
    </div>

    <transition name="el-zoom-in-right">
      <div v-if="selectedNode || selectedEdge" class="info-panel">
        <div class="panel-header">
          <h3>
            <el-icon><InfoFilled /></el-icon>
            {{ selectedNode ? '知识点详情' : '逻辑关联详情' }}
          </h3>
        </div>

        <div class="panel-body">
          <template v-if="selectedNode">
            <h2 class="title">{{ selectedNode.label }}</h2>
            <el-tag size="small" type="success" class="mb-3">{{ selectedNode.type || 'Entity' }}</el-tag>

            <div class="section">
              <h4>背景描述</h4>
              <p class="desc-text">{{ selectedNode.description || '暂无详细描述。' }}</p>
            </div>

            <div class="section" v-if="connectedNeighbors.length > 0">
              <h4>关联知识网 ({{ connectedNeighbors.length }})</h4>
              <ul class="neighbor-list">
                <li v-for="(nb, idx) in connectedNeighbors" :key="idx">
                  <span class="relation-badge" :class="nb.direction">{{ nb.relation }}</span>
                  <strong>{{ nb.node.label }}</strong>
                </li>
              </ul>
            </div>

            <div class="actions">
              <el-button type="danger" size="small" :icon="Delete" @click="handleDeleteNode">删除知识点</el-button>
            </div>
          </template>

          <template v-if="selectedEdge">
            <h2 class="title">逻辑：{{ selectedEdge.relation }}</h2>

            <div class="section">
              <h4>关联方向</h4>
              <div class="connection-logic">
                 <strong>{{ selectedEdge.source.label || selectedEdge.source }}</strong>
                 <span class="arrow">→</span>
                 <strong>{{ selectedEdge.target.label || selectedEdge.target }}</strong>
              </div>
            </div>

            <div class="section">
              <h4>逻辑说明</h4>
              <p class="desc-text">{{ selectedEdge.description || '暂无详细描述。' }}</p>
            </div>

            <div class="actions">
              <el-button type="danger" size="small" :icon="Delete" @click="handleDeleteEdge">删除关联边</el-button>
            </div>
          </template>
        </div>
      </div>
    </transition>

    <el-dialog v-model="nodeDialogVisible" title="新增知识节点" width="500px">
      <el-form :model="nodeForm" label-width="90px">
        <el-form-item label="标识ID"><el-input v-model="nodeForm.id" placeholder="唯一英文字母或数字组合" /></el-form-item>
        <el-form-item label="知识点名称"><el-input v-model="nodeForm.label" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="nodeForm.type" placeholder="如：概念、人物、技术、组织" /></el-form-item>
        <el-form-item label="描述">
          <el-input type="textarea" :rows="4" v-model="nodeForm.description" placeholder="在此输入有关该知识点的详细上下文内容..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nodeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitNode">保存节点</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="edgeDialogVisible" title="新增逻辑关联边" width="500px">
      <el-form :model="edgeForm" label-width="90px">
        <el-form-item label="标识ID"><el-input v-model="edgeForm.id" /></el-form-item>
        <el-form-item label="源节点">
          <el-select filterable v-model="edgeForm.source" placeholder="请选择来源节点" style="width: 100%">
            <el-option v-for="n in nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标节点">
          <el-select filterable v-model="edgeForm.target" placeholder="请选择目标节点" style="width: 100%">
            <el-option v-for="n in nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="关系定义"><el-input v-model="edgeForm.relation" placeholder="如：包含、发明了、属于" /></el-form-item>
        <el-form-item label="逻辑说明">
          <el-input type="textarea" :rows="4" v-model="edgeForm.description" placeholder="解释这两者产生这种逻辑关系的原因或背景..." />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="edgeDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdge">保存关联</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.graph-wrapper {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  overflow: hidden;
  background-color: #111;
}
.graph-canvas { width: 100%; height: 100%; }

.toolbar {
  position: absolute;
  top: 20px; right: 20px;
  display: flex; gap: 10px;
  z-index: 10;
}

.info-panel {
  position: absolute;
  top: 70px;
  right: 20px;
  width: 320px;
  max-height: calc(100vh - 180px);
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.2);
  display: flex;
  flex-direction: column;
  z-index: 10;
  overflow-y: auto;
  border: 1px solid rgba(255,255,255,0.2);
}
.panel-header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background: #f8f9fa;
  border-radius: 12px 12px 0 0;
}
.panel-header h3 {
  margin: 0;
  font-size: 14px;
  color: #606266;
  display: flex; align-items: center; gap: 8px;
}
.panel-body {
  padding: 20px;
}
.title {
  margin: 0 0 10px 0;
  font-size: 20px;
  color: #303133;
}
.mb-3 { margin-bottom: 15px; }

.section {
  margin-bottom: 20px;
}
.section h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  text-transform: uppercase;
  color: #909399;
  letter-spacing: 0.5px;
}
.desc-text {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #404142;
  background: #f4f4f5;
  padding: 10px;
  border-radius: 6px;
  border-left: 3px solid #409EFC;
}

.connection-logic {
  background: #ecf5ff;
  padding: 10px;
  border-radius: 6px;
  text-align: center;
  color: #409EFC;
}
.connection-logic .arrow { margin: 0 10px; color: #909399; }

.neighbor-list {
  list-style: none;
  padding: 0; margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.neighbor-list li {
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.relation-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 10px;
  background: #e1f3d8;
  color: #67c23a;
}
.relation-badge.incoming {
  background: #fdf6ec;
  color: #e6a23c;
}

.actions {
  margin-top: 25px;
  padding-top: 15px;
  border-top: 1px solid #ebeef5;
  text-align: right;
}
</style>
