<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import ForceGraph3D from '3d-force-graph'
import * as THREE from 'three'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, InfoFilled } from '@element-plus/icons-vue'

const graphContainer = ref<HTMLElement | null>(null)
let Graph: any = null

const nodes = ref<any[]>([])
const links = ref<any[]>([])

// Selection state for Info Panel
const selectedNode = ref<any>(null)
const selectedEdge = ref<any>(null)
const connectedNeighbors = ref<any[]>([])

const fetchGraphData = async () => {
  try {
    const res = await axios.get('/api/graph')

    // Filter out invalid/empty nodes
    const validNodes = (res.data.nodes || []).filter((n: any) => n && n.id && n.id.trim() !== '')
    const validNodeIds = new Set(validNodes.map((n: any) => n.id))

    // Filter out edges connecting to invalid nodes
    const validLinks = (res.data.links || []).filter((l: any) => {
       const sourceId = typeof l.source === 'object' ? l.source.id : l.source
       const targetId = typeof l.target === 'object' ? l.target.id : l.target
       return validNodeIds.has(sourceId) && validNodeIds.has(targetId)
    })

    // Compute node weights (number of connected edges)
    const weights: Record<string, number> = {}
    validNodes.forEach((n: any) => weights[n.id] = 0)
    validLinks.forEach((l: any) => {
       const sourceId = typeof l.source === 'object' ? l.source.id : l.source
       const targetId = typeof l.target === 'object' ? l.target.id : l.target
       if (weights[sourceId] !== undefined) weights[sourceId]++
       if (weights[targetId] !== undefined) weights[targetId]++
    })

    validNodes.forEach((n: any) => {
      n.val = weights[n.id] || 0
    })

    nodes.value = validNodes
    links.value = validLinks

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

// Auto-rotation state
const idleTimeout = ref<number | null>(null)
const isIdle = ref(false)
let rotationAngle = 0
let animationFrameId: number | null = null
const STANDARD_DISTANCE = 300
const highlightedNodes = ref<string[]>([])

const highlightNodes = (nodeIds: string[]) => {
  highlightedNodes.value = nodeIds
  resetIdleTimer()
}

const resetIdleTimer = (e?: Event) => {
  if (e && e.type === 'mousemove') return; // Ignore passive mousemove to avoid interrupting rotation

  isIdle.value = false
  if (idleTimeout.value) clearTimeout(idleTimeout.value)

  idleTimeout.value = window.setTimeout(() => {
    isIdle.value = true
    highlightedNodes.value = [] // clear breathing effect when idle starts

    // Smoothly start rotation from the camera's CURRENT relative angle to the target
    if (Graph) {
      const controls = Graph.controls()
      const cameraPos = Graph.cameraPosition()
      const target = controls.target || {x:0, y:0, z:0}

      const relX = cameraPos.x - target.x
      const relZ = cameraPos.z - target.z
      rotationAngle = Math.atan2(relX, relZ || 1)
    }
  }, 15000)
}

const animateRotation = () => {
  if (Graph) {
    // 1. Idle Rotation & Zoom
    if (isIdle.value) {
      const controls = Graph.controls()
      const cameraPos = Graph.cameraPosition()
      const target = controls.target || {x:0, y:0, z:0}

      // Calculate current relative distance from target
      const relX = cameraPos.x - target.x
      const relZ = cameraPos.z - target.z
      const currentDistance = Math.hypot(relX, relZ) || STANDARD_DISTANCE

      // Smoothly interpolate towards standard distance
      const distanceDiff = STANDARD_DISTANCE - currentDistance
      const newDistance = Math.abs(distanceDiff) > 1 ? currentDistance + (distanceDiff * 0.02) : STANDARD_DISTANCE

      // Interpolate Y position towards 0
      const currentY = cameraPos.y || 0
      const newY = Math.abs(currentY) > 1 ? currentY - (currentY * 0.02) : 0

      // Interpolate the lookAt target slowly back to center (0,0,0)
      const targetX = Math.abs(target.x) > 0.5 ? target.x - (target.x * 0.02) : 0
      const targetY = Math.abs(target.y) > 0.5 ? target.y - (target.y * 0.02) : 0
      const targetZ = Math.abs(target.z) > 0.5 ? target.z - (target.z * 0.02) : 0
      const newTarget = { x: targetX, y: targetY, z: targetZ }

      Graph.cameraPosition({
        x: newTarget.x + newDistance * Math.sin(rotationAngle),
        y: newY,
        z: newTarget.z + newDistance * Math.cos(rotationAngle)
      }, newTarget, 0)

      rotationAngle += Math.PI / 1000 // Slow rotation
    }

    // 2. Node Breathing Effect
    const sceneNodes = Graph.scene().children.filter((c: any) => c.__data && c.__data.id)
    if (highlightedNodes.value.length > 0) {
      const time = Date.now() / 300 // breathing speed
      const emissiveIntensity = (Math.sin(time) + 1) / 2 // bounds 0.0 to 1.0

      sceneNodes.forEach((mesh: any) => {
        const nodeId = mesh.__data.id
        if (highlightedNodes.value.includes(nodeId) && mesh.material) {
          if (!mesh.userData.originalColor) {
            mesh.userData.originalColor = mesh.material.color.clone()
            mesh.material.emissive = new THREE.Color(0x4ade80)
          }
          mesh.material.emissiveIntensity = emissiveIntensity
        } else if (mesh.material && mesh.userData.originalColor) {
          mesh.material.emissiveIntensity = 0
        }
      })
    } else {
      // Clear if not highlighted
      sceneNodes.forEach((mesh: any) => {
        if (mesh.material && mesh.userData.originalColor) {
          mesh.material.emissiveIntensity = 0
        }
      })
    }
  }
  animationFrameId = requestAnimationFrame(animateRotation)
}

// Helpers for 3D Geometries
const getNodeColor = (type: string) => {
  const t = (type || '').toLowerCase()
  if (t.includes('申报条件') || t.includes('requirement') || t.includes('condition')) return '#e74c3c'
  if (t.includes('概念') || t.includes('concept')) return '#3498db'
  if (t.includes('组织') || t.includes('organization') || t.includes('company')) return '#9b59b6'
  if (t.includes('技术') || t.includes('technology')) return '#2ecc71'
  if (t.includes('人物') || t.includes('person')) return '#f1c40f'
  return '#95a5a6' // Default grey
}

const initGraph = () => {
  if (!graphContainer.value) return

  Graph = (ForceGraph3D as any)()(graphContainer.value)
    .width(graphContainer.value.clientWidth)
    .height(graphContainer.value.clientHeight)
    .graphData({ nodes: nodes.value, links: links.value })
    .nodeLabel('label')
    .nodeThreeObject((node: any) => {
      // Base size calculation derived from weight (number of edges)
      const baseSize = 4
      const weightBonus = Math.min((node.val || 0) * 1.5, 12) // Cap maximum size
      const size = baseSize + weightBonus

      const color = getNodeColor(node.type)
      const t = (node.type || '').toLowerCase()

      let geometry
      if (t.includes('申报条件') || t.includes('requirement')) {
        // Box for conditions
        geometry = new THREE.BoxGeometry(size, size, size)
      } else if (t.includes('组织') || t.includes('organization')) {
        // Cylinder for organizations
        geometry = new THREE.CylinderGeometry(size/1.5, size/1.5, size*1.5, 16)
      } else {
        // Default sphere
        geometry = new THREE.SphereGeometry(size, 16, 16)
      }

      const material = new THREE.MeshLambertMaterial({
        color: color,
        transparent: true,
        opacity: 0.85
      })
      const mesh = new THREE.Mesh(geometry, material)
      return mesh
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

  // Set up lights for 3D objects
  Graph.scene().add(new THREE.AmbientLight(0xbbbbbb))
  const directionalLight = new THREE.DirectionalLight(0xffffff, 0.6)
  directionalLight.position.set(1, 1, 1)
  Graph.scene().add(directionalLight)
}

onMounted(() => {
  window.addEventListener('mousemove', resetIdleTimer)
  window.addEventListener('keydown', resetIdleTimer)
  window.addEventListener('mousedown', resetIdleTimer)
  window.addEventListener('wheel', resetIdleTimer)
  resetIdleTimer()
  animateRotation()

  initGraph()
  fetchGraphData()

  const resizeObserver = new ResizeObserver(() => {
    if (Graph && graphContainer.value) {
      Graph.width(graphContainer.value.clientWidth)
      Graph.height(graphContainer.value.clientHeight)
    }
  })

  if (graphContainer.value) {
    resizeObserver.observe(graphContainer.value)
  }

  // Store the observer to disconnect later if needed, though unmount clears dom
  (window as any).__graphResizeObserver = resizeObserver
})

onBeforeUnmount(() => {
  if ((window as any).__graphResizeObserver) {
    (window as any).__graphResizeObserver.disconnect()
  }
  window.removeEventListener('mousemove', resetIdleTimer)
  window.removeEventListener('keydown', resetIdleTimer)
  window.removeEventListener('mousedown', resetIdleTimer)
  window.removeEventListener('wheel', resetIdleTimer)
  if (idleTimeout.value) clearTimeout(idleTimeout.value)
  if (animationFrameId !== null) cancelAnimationFrame(animationFrameId)

  if (Graph) Graph._destructor()
})

const handleDeleteNode = async () => {
  if (!selectedNode.value) return
  try {
    await ElMessageBox.confirm('确定要删除此知识节点及其关联边吗？', '警告', { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' })
    await axios.delete(`/api/nodes/${selectedNode.value.id}`)
    ElMessage.success('节点已删除')
    selectedNode.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除节点失败')
  }
}

const handleDeleteEdge = async () => {
  if (!selectedEdge.value) return
  try {
    await ElMessageBox.confirm('确定要删除此逻辑关联吗？', '警告', { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' })
    const edgeId = selectedEdge.value.id
    await axios.delete(`/api/edges/${edgeId}`)
    ElMessage.success('关联已删除')
    selectedEdge.value = null
    fetchGraphData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除关联失败')
  }
}

defineExpose({ fetchGraphData, highlightNodes })
</script>

<template>
  <div class="graph-wrapper">
    <div ref="graphContainer" class="graph-canvas"></div>

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
