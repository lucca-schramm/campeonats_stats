<template>
  <div class="w-full flex flex-col text-white">
    <div class="text-center mb-4">
      <h3 class="text-lg font-bold text-[#AAF53A]">Tabela de Classificação</h3>
    </div>
    <div v-if="loading" class="text-center py-8 text-white/50">
      Carregando tabela...
    </div>
    <div v-else-if="error" class="text-center py-8 text-red-400">
      {{ error }}
    </div>
    <div v-else-if="!standings.length" class="text-center py-8 text-white/50">
      Nenhum dado disponível
    </div>
    <div v-else class="relative overflow-x-auto scrollbar-hide">
      <table class="min-w-full table-fixed">
        <thead>
          <tr class="sticky top-0 z-10 bg-[#0A175C]">
            <th class="sticky left-0 z-10 w-20 sm:w-64 px-4 py-4 text-left text-xs font-medium uppercase tracking-wider bg-[#0A175C]">
              <div class="flex items-center space-x-10 justify-around p-1">
                <span>Pos</span>
                <span class="w-full">Time</span>
              </div>
            </th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider text-[#AAF53A]">Pts</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">J</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">V</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">E</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">D</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">GP</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">GC</th>
            <th class="w-20 px-4 py-4 text-center text-xs font-medium uppercase tracking-wider">SG</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700/50">
          <tr v-for="team in standings" :key="team.team_id" class="hover:bg-gray-700/30 transition-colors text-white">
            <td class="sticky left-0 z-1 w-20 sm:w-64 px-4 py-4 bg-[#0A175C]">
              <div class="flex flex-row items-center justify-around">
                <span class="w-8 text-sm font-medium text-[#AAF53A]">{{ team.rank }}</span>
                <div class="flex flex-row gap-1 p-1 w-full">
                  <img v-if="team.logo" class="w-6 h-6 object-cover" :src="team.logo" :alt="team.name" />
                  <span class="font-medium truncate">{{ team.name }}</span>
                </div>
              </div>
            </td>
            <td class="px-4 py-4 text-center text-sm font-semibold text-[#AAF53A]">{{ team.points }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.matches_played }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.wins }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.draws }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.losses }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.goals_for }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.goals_against }}</td>
            <td class="px-4 py-4 text-center text-sm">{{ team.goals_diff }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <div class="w-full text-center py-3 text-white/50 text-sm">
      <div class="grid grid-cols-2 items-center font-bold justify-center gap-4 text-xs">
        <div class="w-full flex flex-col gap-1">
          <span><b>Pts:</b> Pontos acumulados</span>
          <span><b>J:</b> Jogos disputados</span>
          <span><b>V:</b> Vitórias</span>
          <span><b>E:</b> Empates</span>
        </div>
        <div class="w-full flex flex-col gap-1">
          <span><b>D:</b> Derrotas</span>
          <span><b>GP:</b> Gols pró</span>
          <span><b>GC:</b> Gols contra</span>
          <span><b>SG:</b> Saldo de gols</span>
        </div>
      </div>
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
const standings = ref([])

const fetchStandings = async () => {
  loading.value = true
  error.value = null
  
  try {
    const response = await axios.get(`/api/v1/leagues/${props.leagueId}/standings`)
    const data = response.data.standings || []
    
    standings.value = data.map(team => ({
      team_id: team.team_id,
      name: `Time ${team.team_id}`,
      logo: '',
      rank: team.rank,
      points: team.points || 0,
      matches_played: team.matches_played || 0,
      wins: team.wins || 0,
      draws: team.draws || 0,
      losses: team.losses || 0,
      goals_for: team.goals_for || 0,
      goals_against: team.goals_against || 0,
      goals_diff: team.goals_diff || 0
    }))
  } catch (err) {
    error.value = 'Erro ao carregar tabela'
    console.error(err)
  } finally {
    loading.value = false
  }
}

onMounted(fetchStandings)
watch(() => props.leagueId, fetchStandings)
</script>
