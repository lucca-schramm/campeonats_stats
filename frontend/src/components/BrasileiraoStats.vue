<template>
  <div class="w-full flex flex-col text-white">
    <div class="text-center mb-4">
      <h3 class="text-lg font-bold text-[#AAF53A]">{{ headerText }}</h3>
    </div>
    <div v-if="loading" class="text-center py-8 text-white/50">
      Carregando estatísticas...
    </div>
    <div v-else-if="error" class="text-center py-8 text-red-400">
      {{ error }}
    </div>
    <div v-else-if="!stats.length" class="text-center py-8 text-white/50">
      Nenhum dado disponível
    </div>
    <div v-else class="relative overflow-x-auto scrollbar-hide">
      <table class="min-w-full table-fixed">
        <thead>
          <tr class="sticky top-0 z-10 bg-[#0A175C]">
            <th class="sticky left-0 z-10 w-36 sm:w-64 px-4 py-4 text-left text-xs font-medium uppercase tracking-wider bg-[#0A175C]">
              <div class="flex items-center space-x-10 justify-around">
                <span>Time</span>
                <span>Jogos</span>
              </div>
            </th>
            <th class="w-24 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">Aprov(%)</th>
            <th class="w-24 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">+2,5 gols</th>
            <th class="w-32 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">Ambos marcam</th>
            <th class="w-32 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">Sem sofrer gol</th>
            <th class="w-28 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">+0,5 gol 1ºT</th>
            <th class="w-28 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">+0,5 gol 2ºT</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">Esc/J</th>
            <th class="w-32 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">Forma</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700/50">
          <tr v-for="team in stats" :key="team.team_id" class="hover:bg-gray-700/30 transition-colors text-white">
            <td class="sticky left-0 z-1 w-36 sm:w-64 px-4 py-4 bg-[#0A175C]">
              <div class="flex items-center justify-around">
                <div class="flex flex-row p-1 gap-1 w-full">
                  <img v-if="team.logo" class="w-6 h-6 object-cover hidden sm:block" :src="team.logo" :alt="team.name" />
                  <span class="font-medium truncate">{{ team.name }}</span>
                </div>
                <span class="w-8 text-sm font-medium text-[#AAF53A]">{{ team.matches_played }}</span>
              </div>
            </td>
            <td class="px-4 py-4 text-center text-sm font-medium">{{ team.aproveitamento }}%</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.over25Goals }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.btts }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.cleanSheets }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.over05HT }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.over05FT }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.avgCorners }}</td>
            <td class="px-4 py-4">
              <div class="flex justify-center space-x-1">
                <span v-for="(result, idx) in team.form" :key="idx" :class="getFormColor(result)" class="text-xs font-bold">
                  {{ result }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="w-full text-center py-3 text-white/50 text-sm">
      <div class="grid grid-cols-2 items-center justify-center text-start gap-4 text-xs">
        <div class="w-full flex flex-col gap-1">
          <span><b>Aprov (%):</b> Aproveitamento dos pontos disputados</span>
          <span><b>+2,5 gols:</b> Jogos em que houveram três ou mais gols</span>
          <span><b>Ambos marcam:</b> Jogos com ambos marcando gol</span>
          <span><b>Sem sofrer gol:</b> Jogos em que o time não sofreu gol</span>
        </div>
        <div class="w-full flex flex-col gap-1">
          <span><b>+0,5 gol 1ºT:</b> Jogos em que o time marcou no 1º Tempo</span>
          <span><b>+0,5 gol 2ºT:</b> Jogos em que o time marcou no 2º Tempo</span>
          <span><b>Esc/J:</b> Média de escanteios que o time produziu por jogo</span>
          <span><b>Forma:</b> Desempenho nos últimos 5 jogos</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  leagueId: {
    type: Number,
    required: true,
    default: 1
  },
  filter: {
    type: String,
    default: 'geral'
  }
})

const loading = ref(false)
const error = ref(null)
const stats = ref([])

const headerText = computed(() => {
  switch (props.filter) {
    case 'casa':
      return 'Desempenho como mandante'
    case 'fora':
      return 'Desempenho como visitante'
    default:
      return 'Desempenho Geral'
  }
})

const getFormColor = (result) => {
  if (result === 'V') return 'text-green-500'
  if (result === 'E') return 'text-yellow-500'
  if (result === 'D') return 'text-red-500'
  return 'text-gray-400'
}

const fetchStats = async () => {
  loading.value = true
  error.value = null
  
  try {
    const filterParam = props.filter === 'casa' ? 'casa' : props.filter === 'fora' ? 'fora' : 'geral'
    const response = await axios.get(`/api/v1/leagues/${props.leagueId}/standings`, {
      params: { filter_type: filterParam }
    })
    const standings = response.data.standings || []
    
    stats.value = standings.map((team, idx) => ({
      team_id: team.team_id,
      name: team.name || getTeamName(team.team_id),
      logo: team.logo || '',
      rank: team.rank || (idx + 1),
      matches_played: team.matches_played || 0,
      aproveitamento: calculateAproveitamento(team),
      over25Goals: team.over25Goals || 0,
      btts: team.btts || 0,
      cleanSheets: team.cleanSheets || 0,
      over05HT: team.over05HT || 0,
      over05FT: team.over05FT || 0,
      avgCorners: team.avgCorners || 0,
      form: team.form || '-----'.split('')
    }))
  } catch (err) {
    error.value = `Erro ao carregar estatísticas: ${err.message || 'Erro desconhecido'}`
  } finally {
    loading.value = false
  }
}

const getTeamName = (teamId) => {
  return `Time ${teamId}`
}

const calculateAproveitamento = (team) => {
  const points = team.points || 0
  const played = team.matches_played || 0
  if (played === 0) return 0
  return Math.round((points / (played * 3)) * 100)
}

watch(() => props.filter, fetchStats, { immediate: true })
watch(() => props.leagueId, fetchStats, { immediate: true })
</script>
