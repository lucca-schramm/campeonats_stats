<template>
  <div class="w-full flex flex-col">
    <div class="w-full h-8 sm:h-10 py-2 sm:py-2.5 border-t border-b border-[#AAF53A] flex justify-start items-center gap-2 sm:gap-4 px-4 sm:px-6 md:px-8">
      <div class="w-8 text-center shrink-0"></div>
      <div class="flex-1 text-left text-white text-sm sm:text-base font-normal uppercase">Ranking</div>
      <div class="w-16 text-center shrink-0 text-white text-sm sm:text-base font-normal uppercase">Gols</div>
    </div>
    <div v-if="loading" class="text-center py-8 text-white/50">
      Carregando artilheiros...
    </div>
    <div v-else-if="error" class="text-center py-8 text-red-400">
      {{ error }}
    </div>
    <div v-else-if="!scorers.length" class="text-center py-8 text-white/50">
      Nenhum dado disponível
    </div>
    <div v-else class="w-full flex-1 flex flex-col justify-start items-start overflow-y-auto max-h-[250px] sm:max-h-[calc(100vh-350px)] scrollbar-hide">
      <div class="w-full">
        <div
          v-for="(scorer, idx) in scorers"
          :key="idx"
          class="w-full py-2 sm:py-3.5 border-b border-[#AAF53A] flex justify-start items-center gap-2 sm:gap-4 transition-colors duration-200 px-4 sm:px-6 md:px-8"
        >
          <div class="w-8 text-center shrink-0 text-[#AAF53A] text-2xl sm:text-3xl font-['Open_Sans']" :class="{ 'opacity-50': scorer.pos > 3 }">
            {{ scorer.pos }}
          </div>
          
          <div class="flex-1 flex items-center gap-2 sm:gap-4 min-w-0">
            <img
              class="w-10 h-10 sm:w-12 sm:h-12 relative rounded-[80px] object-cover bg-white shrink-0"
              :class="scorer.pos <= 3 ? 'border-2 border-[#AAF53A]' : 'border border-[#AAF53A]'"
              :src="scorer.foto || 'https://next-minio-b2b.devcore.at/next-cms/sXB4jmygKl9Ug4-iafqoRQ.webp'"
              :alt="scorer.nome"
              @error="handleImageError"
            />
            <img
              v-if="scorer.escudo"
              class="w-5 h-5 sm:w-6 sm:h-6 relative object-cover rounded shrink-0"
              :src="scorer.escudo"
              alt="Escudo do time"
              @error="handleImageError"
            />
            <div class="flex-1 min-w-0 flex flex-col justify-start items-start">
              <div class="w-full text-white text-lg sm:text-xl font-normal truncate">{{ scorer.nome }}</div>
              <div class="w-full text-white/50 text-[9px] sm:text-[10px] font-bold uppercase truncate">{{ scorer.posicao }}</div>
            </div>
          </div>

          <div class="w-16 text-center shrink-0 text-[#AAF53A] text-xl sm:text-2xl font-bold leading-relaxed" :class="{ 'opacity-50': scorer.pos > 3 }">
            {{ scorer.gols }}
          </div>
        </div>
      </div>
    </div>
    <div class="w-full text-center py-2 text-white/50 text-sm block sm:hidden">
      <span class="flex items-center justify-center gap-1">
        <svg class="w-4 h-4" fill="var(--content-right-contrast)" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
        </svg>
        Deslize para ver mais
      </span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  leagueId: {
    type: Number,
    required: true,
    default: 1
  }
})

const loading = ref(false)
const error = ref(null)
const scorers = ref([])

const fetchScorers = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await axios.get(`/api/v1/leagues/${props.leagueId}/top-scorers?limit=50`)
    const data = response.data.top_scorers || []
    
    let lastGols = -1
    let posCounter = 0
    
    scorers.value = data
      .sort((a, b) => (b['jogador-gols'] || 0) - (a['jogador-gols'] || 0))
      .map(scorer => {
        const gols = parseInt(scorer['jogador-gols']) || 0
        if (gols !== lastGols) {
          posCounter++
        }
        lastGols = gols
        return {
          pos: posCounter,
          nome: scorer['jogador-nome'] || 'Nome não disponível',
          posicao: translatePosition(scorer['jogador-posicao']),
          gols: gols,
          foto: scorer['jogador-foto'] || '',
          escudo: scorer['jogador-escudo'] || ''
        }
      })
  } catch (err) {
    error.value = 'Erro ao carregar artilheiros'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const translatePosition = (posicao) => {
  switch ((posicao || '').toLowerCase()) {
    case 'attacker':
    case 'forward':
      return 'Atacante'
    case 'midfielder':
      return 'Meio-campo'
    case 'defender':
      return 'Defensor'
    default:
      return posicao || 'N/A'
  }
}

const handleImageError = (event) => {
  event.target.src = 'https://next-minio-b2b.devcore.at/next-cms/sXB4jmygKl9Ug4-iafqoRQ.webp'
}

onMounted(fetchScorers)
watch(() => props.leagueId, fetchScorers)
</script>
