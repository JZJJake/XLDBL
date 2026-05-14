<script setup lang="ts">
import { ref, nextTick } from 'vue'
import axios from 'axios'
import { Position } from '@element-plus/icons-vue'

const emit = defineEmits(['reply'])

const messages = ref<{role: string, content: string}[]>([
  { role: 'assistant', content: '您好！我是 DeepSeek 知识库助手。您可以向我提问，也可以要求我对知识库进行管理和组织，我会结合图谱、文档内容及Wiki百科为您解答和操作。' }
])
const inputMessage = ref('')
const isLoading = ref(false)
const chatMode = ref('query') // 'query' or 'manage'
const chatBodyRef = ref<HTMLElement | null>(null)

const scrollToBottom = () => {
  nextTick(() => {
    if (chatBodyRef.value) {
      chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    }
  })
}

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isLoading.value) return

  const userMsg = inputMessage.value
  messages.value.push({ role: 'user', content: userMsg })
  inputMessage.value = ''
  isLoading.value = true
  emit('reply', [])
  scrollToBottom()

  try {
    const endpoint = chatMode.value === 'query' ? '/api/chat' : '/api/wiki/chat_manage'
    const res = await axios.post(endpoint, { message: userMsg })
    messages.value.push({ role: 'assistant', content: res.data.reply })
  } catch (error) {
    messages.value.push({ role: 'assistant', content: '错误：无法连接到服务器或大模型接口。' })
  } finally {
    isLoading.value = false
    scrollToBottom()
  }
}
</script>

<template>
  <div class="chat-panel">
    <div class="header-row">
      <h3>DeepSeek 深度交流与管理</h3>
      <el-radio-group v-model="chatMode" size="small">
        <el-radio-button label="query">知识查询</el-radio-button>
        <el-radio-button label="manage">管理维护</el-radio-button>
      </el-radio-group>
    </div>
    <div class="chat-body" ref="chatBodyRef">
      <div
        v-for="(msg, index) in messages"
        :key="index"
        :class="['message', msg.role]"
      >
        <div class="msg-content">{{ msg.content }}</div>
      </div>
      <div v-if="isLoading" class="message assistant loading">
        <span class="dot"></span><span class="dot"></span><span class="dot"></span>
      </div>
    </div>
    <div class="chat-input">
      <el-input
        v-model="inputMessage"
        placeholder="向知识库提问或下达管理指令(如：整理某个知识点，生成新词条)..."
        @keyup.enter="sendMessage"
        :disabled="isLoading"
      >
        <template #append>
          <el-button :icon="Position" @click="sendMessage" :disabled="isLoading"></el-button>
        </template>
      </el-input>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #3b82f6;
  padding-bottom: 10px;
  margin-bottom: 10px;
}
.header-row h3 {
  margin: 0;
  color: #f3f4f6;
  font-size: 16px;
}
.chat-body {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
  background: #0b0f19;
  border-radius: 8px;
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.message {
  max-width: 85%;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.6;
  word-wrap: break-word;
  white-space: pre-wrap;
}
.message.user {
  align-self: flex-end;
  background-color: #3b82f6;
  color: white;
  border-bottom-right-radius: 2px;
}
.message.assistant {
  align-self: flex-start;
  background-color: #1e293b;
  color: #cbd5e1;
  border: 1px solid #334155;
  border-bottom-left-radius: 2px;
}
.loading .dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background-color: #909399;
  margin: 0 2px;
  animation: pulse 1.4s infinite ease-in-out both;
}
.loading .dot:nth-child(1) { animation-delay: -0.32s; }
.loading .dot:nth-child(2) { animation-delay: -0.16s; }

@keyframes pulse {
  0%, 80%, 100% { transform: scale(0); }
  40% { transform: scale(1); }
}
</style>
