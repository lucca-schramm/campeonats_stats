<template>
  <div class="min-h-screen bg-gradient-to-b from-[#263FA3] to-[#0A175C] flex flex-col">
    <div class="flex-1 flex flex-col max-w-4xl mx-auto w-full px-4 py-8">
      <div class="text-center mb-8">
        <h1 class="text-4xl font-bold text-[#AAF53A] mb-2">Chatbot de Futebol</h1>
        <p class="text-white/70">Faça perguntas sobre ligas, times, estatísticas e muito mais!</p>
      </div>

      <div class="flex-1 flex flex-col bg-gray-900/50 rounded-lg border border-gray-700 overflow-hidden">
        <div ref="messagesContainer" class="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-hide">
          <div v-if="messages.length === 0" class="text-center text-white/50 py-8">
            <p>Comece uma conversa! Pergunte sobre:</p>
            <ul class="mt-4 space-y-2 text-sm">
              <li>• Tabela de classificação do Brasileirão</li>
              <li>• Top artilheiros</li>
              <li>• Estatísticas de times</li>
              <li>• Próximas partidas</li>
            </ul>
          </div>

          <div
            v-for="(message, idx) in messages"
            :key="idx"
            :class="['flex', message.role === 'user' ? 'justify-end' : 'justify-start']"
          >
            <div
              :class="[
                'max-w-[80%] rounded-lg px-4 py-3',
                message.role === 'user'
                  ? 'bg-[#AAF53A] text-black'
                  : 'bg-gray-800 text-white'
              ]"
            >
              <div class="whitespace-pre-wrap">{{ message.content }}</div>
              <div :class="['text-xs mt-1', message.role === 'user' ? 'text-black/70' : 'text-white/50']">
                {{ formatTime(message.timestamp) }}
              </div>
            </div>
          </div>

          <div v-if="loading" class="flex justify-start">
            <div class="bg-gray-800 text-white rounded-lg px-4 py-3">
              <div class="flex items-center gap-2">
                <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                <span>Pensando...</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="suggestions.length > 0" class="px-4 py-2 border-t border-gray-700">
          <div class="flex flex-wrap gap-2">
            <button
              v-for="(suggestion, idx) in suggestions"
              :key="idx"
              @click="sendMessage(suggestion)"
              class="px-3 py-1 text-sm bg-gray-800 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              {{ suggestion }}
            </button>
          </div>
        </div>

        <div class="p-4 border-t border-gray-700">
          <form @submit.prevent="sendMessage(userInput)" class="flex gap-2">
            <input
              v-model="userInput"
              type="text"
              placeholder="Digite sua pergunta..."
              class="flex-1 px-4 py-2 bg-gray-800 text-white rounded-lg border border-gray-700 focus:outline-none focus:border-[#AAF53A]"
              :disabled="loading"
            />
            <button
              type="submit"
              :disabled="loading || !userInput.trim()"
              class="px-6 py-2 bg-[#AAF53A] text-black font-semibold rounded-lg hover:bg-[#9ae430] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Enviar
            </button>
          </form>
        </div>
      </div>

      <div class="mt-4 text-center text-white/50 text-sm">
        <p>Chatbot alimentado por IA • Dados atualizados a cada 2 minutos</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import axios from 'axios'

const messages = ref([])
const userInput = ref('')
const loading = ref(false)
const suggestions = ref([])
const messagesContainer = ref(null)
const sessionId = ref(null)

const sendMessage = async (text) => {
  if (!text.trim() || loading.value) return

  const messageText = text.trim()
  userInput.value = ''
  
  messages.value.push({
    role: 'user',
    content: messageText,
    timestamp: new Date()
  })

  loading.value = true
  suggestions.value = []

  try {
    const response = await axios.post('/api/v1/chatbot/chat', {
      message: messageText,
      session_id: sessionId.value,
      chatbot_type: 'rag'  // Usa RAG com DeepSeek para respostas mais inteligentes
    })

    sessionId.value = response.data.session_id

    messages.value.push({
      role: 'assistant',
      content: response.data.response,
      timestamp: new Date()
    })

    if (response.data.suggestions && response.data.suggestions.length > 0) {
      suggestions.value = response.data.suggestions
    }
  } catch (error) {
    console.error('Erro ao enviar mensagem:', error)
    const errorMessage = error.response?.data?.detail || error.message || 'Desculpe, ocorreu um erro ao processar sua mensagem. Tente novamente.'
    messages.value.push({
      role: 'assistant',
      content: `❌ Erro: ${errorMessage}`,
      timestamp: new Date()
    })
  } finally {
    loading.value = false
    await nextTick()
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

const formatTime = (date) => {
  return new Date(date).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  messages.value.push({
    role: 'assistant',
    content: 'Olá! Eu sou seu assistente de futebol. Posso ajudar você com informações sobre ligas, times, estatísticas e muito mais. Como posso ajudá-lo hoje?',
    timestamp: new Date()
  })
})
</script>

<style scoped>
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
</style>
