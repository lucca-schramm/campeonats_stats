<template>
  <div class="min-h-screen bg-gradient-to-b from-[#263FA3] to-[#0A175C]">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 md:px-20 py-12">
      <!-- Header -->
      <div class="text-center mb-12">
        <h1 class="text-4xl sm:text-5xl font-bold text-[#AAF53A] mb-4">Ligas Disponíveis</h1>
        <p class="text-white/70 text-lg">Explore todas as ligas e suas estatísticas</p>
      </div>

      <!-- Search and Filter -->
      <div class="mb-8">
        <div class="flex flex-col sm:flex-row gap-4">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Buscar liga..."
            class="flex-1 px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-[#AAF53A]"
          />
          <select
            v-model="selectedCountry"
            class="px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-[#AAF53A]"
          >
            <option value="">Todos os países</option>
            <option v-for="country in countries" :key="country" :value="country">
              {{ country }}
            </option>
          </select>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-20">
        <div class="text-white text-xl">Carregando ligas...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="text-center py-20">
        <div class="text-red-400 text-xl">{{ error }}</div>
        <button
          @click="fetchLeagues"
          class="mt-4 px-6 py-2 bg-[#AAF53A] text-black font-semibold rounded-lg hover:bg-[#9ae430] transition-colors"
        >
          Tentar Novamente
        </button>
      </div>

      <!-- Leagues Grid -->
      <div v-else-if="filteredLeagues.length === 0" class="text-center py-20">
        <div class="text-white/50 text-lg">Nenhuma liga encontrada</div>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
        <div
          v-for="league in filteredLeagues"
          :key="league.id"
          @click="goToLeague(league.id)"
          class="bg-gray-800/50 rounded-lg p-6 cursor-pointer hover:bg-gray-700/70 transition-all duration-300 hover:scale-105 hover:shadow-xl border border-gray-700 hover:border-[#AAF53A]"
        >
          <!-- League Image -->
          <div class="mb-4 h-32 bg-gradient-to-br from-[#263FA3] to-[#0A175C] rounded-lg flex items-center justify-center overflow-hidden">
            <img
              v-if="league.image"
              :src="league.image"
              :alt="league.name"
              class="w-full h-full object-cover"
            />
            <div v-else class="text-white text-4xl font-bold">
              {{ league.name.charAt(0) }}
            </div>
          </div>

          <!-- League Info -->
          <h3 class="text-xl font-bold text-white mb-2 truncate">{{ league.name }}</h3>
          <div class="flex items-center gap-2 text-white/70 text-sm mb-4">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span>{{ league.country }}</span>
          </div>
          <div class="text-[#AAF53A] text-sm font-semibold">
            Temporada {{ league.season_year }}
          </div>

          <!-- Action Button -->
          <button
            class="mt-4 w-full px-4 py-2 bg-[#AAF53A] text-black font-semibold rounded-lg hover:bg-[#9ae430] transition-colors"
            @click.stop="goToLeague(league.id)"
          >
            Ver Estatísticas
          </button>
        </div>
      </div>

      <!-- Navigation to Chatbot -->
      <div class="mt-12 text-center">
        <router-link
          to="/chatbot"
          class="inline-block px-8 py-3 bg-[#AAF53A] text-black font-semibold rounded-lg hover:bg-[#9ae430] transition-colors"
        >
          💬 Chat com Assistente de Futebol
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

const leagues = ref([])
const loading = ref(true)
const error = ref(null)
const searchQuery = ref('')
const selectedCountry = ref('')

const countries = computed(() => {
  const uniqueCountries = [...new Set(leagues.value.map(l => l.country))]
  return uniqueCountries.sort()
})

const filteredLeagues = computed(() => {
  let filtered = leagues.value

  // Filter by search query
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(league =>
      league.name.toLowerCase().includes(query) ||
      league.country.toLowerCase().includes(query)
    )
  }

  // Filter by country
  if (selectedCountry.value) {
    filtered = filtered.filter(league => league.country === selectedCountry.value)
  }

  return filtered
})

const fetchLeagues = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await axios.get('/api/v1/leagues?limit=1000')
    leagues.value = response.data || []
  } catch (err) {
    error.value = 'Erro ao carregar ligas'
    console.error(err)
  } finally {
    loading.value = false
  }
}

const goToLeague = (leagueId) => {
  router.push({ name: 'league', params: { leagueId } })
}

onMounted(() => {
  fetchLeagues()
})
</script>

