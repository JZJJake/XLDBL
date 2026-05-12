<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import ForceGraph3D from '3d-force-graph'

import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus } from '@element-plus/icons-vue'

const graphContainer = ref<HTMLElement | null>(null)
let Graph: any = null

const nodes = ref<any[]>([])
const links = ref<any[]>([])

// Dialogs state
const nodeDialogVisible = ref(false)
const edgeDialogVisible = ref(false)


const nodeForm = ref({ id: '', label: '', type: 'Entity' })
const edgeForm = ref({ id: '', source: '', target: '', relation: '' })

// Actions panel state
const selectedNode = ref<any>(null)
const selectedEdge = ref<any>(null)

const fetchGraphData = async () => {
  try {
    const res = await axios.get('http://localhost:8000/api/graph')
    nodes.value = res.data.nodes || []
    links.value = res.data.links || []

    if (Graph) {
      Graph.graphData({ nodes: nodes.value, links: links.value })
    }
  } catch (error) {
    ElMessage.error('Failed to load knowledge graph data')
  }
}

const initGraph = () => {
  if (!graphContainer.value) return

  Graph = (ForceGraph3D as any)()(graphContainer.value)
    .graphData({ nodes: nodes.value, links: links.value })
    .nodeLabel('label')
    .nodeAutoColorBy('type')
    .linkDirectionalArrowLength(3.5)
    .linkDirectionalArrowRelPos(1)
    .linkLabel('relation')
    .onNodeClick((node: any) => {
      selectedNode.value = node
      selectedEdge.value = null

      // Aim at node
      const distance = 40;
      const distRatio = 1 + distance/Math.hypot(node.x, node.y, node.z);
      Graph.cameraPosition(
        { x: node.x * distRatio, y: node.y * distRatio, z: node.z * distRatio },
        node,
        3000
      );
    })
    .onLinkClick((link: any) => {
      selectedEdge.value = link
      selectedNode.value = null
    })
}

onMounted(() => {
  initGraph()
  fetchGraphData()

  // Handle resize
  window.addEventListener('resize', () => {
    if (Graph && graphContainer.value) {
      Graph.width(graphContainer.value.clientWidth)
      Graph.height(graphContainer.value.clientHeight)
    }
  })
})

onBeforeUnmount(() => {
  if (Graph) {
    Graph._destructor()
  }
})

// Add Node
const openAddNode = () => {
  nodeForm.value = { id: 'node_' + Date.now(), label: '', type: 'Entity' }
  nodeDialogVisible.value = true
}

const submitNode = async () => {
  try {
    await axios.post('http://localhost:8000/api/nodes', nodeForm.value)
    ElMessage.success('Node added')
    nodeDialogVisible.value = false
    fetchGraphData()
  } catch (error) {
    ElMessage.error('Failed to add node')
  }
}

// Delete Node
const handleDeleteNode = async () => {
  if (!selectedNode.value) return

  try {
    await ElMessageBox.confirm('Are you sure you want to delete this node and its related edges?', 'Warning', { type: 'warning' })
    await axios.delete(`http://localhost:8000/api/nodes/${selectedNode.value.id}`)
    ElMessage.success('Node deleted')
    selectedNode.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete node')
  }
}

// Add Edge
const openAddEdge = () => {
  edgeForm.value = { id: 'edge_' + Date.now(), source: '', target: '', relation: '' }
  edgeDialogVisible.value = true
}

const submitEdge = async () => {
  try {
    await axios.post('http://localhost:8000/api/edges', edgeForm.value)
    ElMessage.success('Edge added')
    edgeDialogVisible.value = false
    fetchGraphData()
  } catch (error) {
    ElMessage.error('Failed to add edge')
  }
}

// Delete Edge
const handleDeleteEdge = async () => {
  if (!selectedEdge.value) return
  try {
    await ElMessageBox.confirm('Are you sure you want to delete this edge?', 'Warning', { type: 'warning' })
    // In 3d-force-graph links get populated with source/target objects, use the string id if available
    const edgeId = selectedEdge.value.id
    await axios.delete(`http://localhost:8000/api/edges/${edgeId}`)
    ElMessage.success('Edge deleted')
    selectedEdge.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('Failed to delete edge')
  }
}

// Expose fetchGraphData for parent component (App.vue)
defineExpose({
  fetchGraphData
})
</script>

<template>
  <div class="graph-wrapper">
    <div ref="graphContainer" class="graph-canvas"></div>

    <!-- Maintenance Toolbar Overlay -->
    <div class="toolbar">
      <el-button type="primary" :icon="Plus" @click="openAddNode">Add Node</el-button>
      <el-button type="primary" :icon="Plus" @click="openAddEdge">Add Edge</el-button>

      <div v-if="selectedNode" class="selection-panel">
        <p><strong>Selected Node:</strong> {{ selectedNode.label }} ({{ selectedNode.type }})</p>
        <el-button type="danger" size="small" :icon="Delete" @click="handleDeleteNode">Delete Node</el-button>
      </div>

      <div v-if="selectedEdge" class="selection-panel">
        <p><strong>Selected Edge:</strong> {{ selectedEdge.relation }}</p>
        <el-button type="danger" size="small" :icon="Delete" @click="handleDeleteEdge">Delete Edge</el-button>
      </div>
    </div>

    <!-- Node Dialog -->
    <el-dialog v-model="nodeDialogVisible" title="Add Node" width="400px">
      <el-form :model="nodeForm" label-width="80px">
        <el-form-item label="ID">
          <el-input v-model="nodeForm.id" />
        </el-form-item>
        <el-form-item label="Label">
          <el-input v-model="nodeForm.label" />
        </el-form-item>
        <el-form-item label="Type">
          <el-input v-model="nodeForm.type" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="nodeDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitNode">Submit</el-button>
      </template>
    </el-dialog>

    <!-- Edge Dialog -->
    <el-dialog v-model="edgeDialogVisible" title="Add Edge" width="400px">
      <el-form :model="edgeForm" label-width="80px">
        <el-form-item label="ID">
          <el-input v-model="edgeForm.id" />
        </el-form-item>
        <el-form-item label="Source">
          <el-select v-model="edgeForm.source" placeholder="Select Source Node" style="width: 100%">
            <el-option v-for="n in nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Target">
          <el-select v-model="edgeForm.target" placeholder="Select Target Node" style="width: 100%">
            <el-option v-for="n in nodes" :key="n.id" :label="n.label" :value="n.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="Relation">
          <el-input v-model="edgeForm.relation" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="edgeDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="submitEdge">Submit</el-button>
      </template>
    </el-dialog>

  </div>
</template>

<style scoped>
.graph-wrapper {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  overflow: hidden;
}
.graph-canvas {
  width: 100%;
  height: 100%;
}
.toolbar {
  position: absolute;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.9);
  padding: 15px;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0,0,0,0.1);
  display: flex;
  flex-direction: column;
  gap: 10px;
  z-index: 10;
}
.selection-panel {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
.selection-panel p {
  margin: 0 0 10px 0;
  font-size: 14px;
  color: #606266;
}
</style>
