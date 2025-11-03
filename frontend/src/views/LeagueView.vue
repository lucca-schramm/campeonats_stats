<template>
  <div class="min-h-screen bg-gradient-to-b from-[#263FA3] to-[#0A175C]">
    <!-- Loading State -->
    <div v-if="loadingLeague" class="min-h-screen flex items-center justify-center">
      <div class="text-white text-xl">Carregando liga...</div>
    </div>

    <!-- Error State -->
    <div v-else-if="errorLeague" class="min-h-screen flex items-center justify-center">
      <div class="text-red-400 text-xl">{{ errorLeague }}</div>
    </div>

    <!-- League Content -->
    <div v-else-if="league">
      <!-- Banner Section -->
      <div class="w-full relative" id="hero-banner">
        <img
          v-if="league.image"
          :src="league.image"
          class="w-full h-auto object-cover object-center block banner-image"
          :alt="`${league.name} - Banner Principal`"
          loading="eager"
        />
        <div
          v-else
          class="w-full h-64 bg-gradient-to-r from-[#263FA3] to-[#0A175C] flex items-center justify-center"
        >
          <div class="text-white text-4xl font-bold">{{ league.name }}</div>
        </div>
        <div
          id="copy-bannet-text"
          class="absolute bottom-2 sm:bottom-4 md:bottom-5 lg:bottom-6 xl:bottom-1 left-0 right-0 px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20"
        >
          <div class="flex flex-col justify-start mt-2 items-start gap-1 sm:gap-2 w-full max-w-4xl">
            <div class="text-[#AAF53A] text-4xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-5xl font-extrabold font-sans uppercase leading-tight">
              {{ league.name }}
            </div>
            <div class="text-white sm:text-4xl sm:text-base md:text-lg lg:text-xl xl:text-2xl font-medium font-sans leading-relaxed max-w-3xl lg:max-w-none">
              Temporada {{ league.season_year }}
            </div>
          </div>
        </div>
      </div>

      <!-- Animated Banner -->
      <div class="w-full bg-[#AAF53A] py-4 overflow-hidden">
        <div id="slider-motion" class="flex whitespace-nowrap">
          <div class="flex items-center justify-start text-[#070300] text-base font-bold font-sans uppercase leading-relaxed whitespace-nowrap animate-scroll">
            <span class="text-[#070300]">TUDO SOBRE {{ league.name.toUpperCase() }}</span>
            <div class="w-2 h-2 mx-4"></div>
            <span class="text-[#070300]">*</span>
            <div class="w-2 h-2 mx-4"></div>
            <span class="text-[#070300]">INFORMAÇÃO QUE VIRA PALPITE</span>
            <div class="w-2 h-2 mx-4"></div>
            <span class="text-[#070300]">*</span>
            <div class="w-2 h-2 mx-4"></div>
          </div>
        </div>
      </div>

      <!-- Statistics Section -->
      <div class="w-full py-14 bg-gradient-to-b from-[#263FA3] to-[#0A175C]">
        <div class="w-full px-4 sm:px-6 md:px-20">
          <div class="w-full flex flex-col justify-start items-start gap-3 pb-6">
            <div class="text-[#AAF53A] text-3xl sm:text-3xl md:text-3xl font-semibold font-sans text-left">
              Central de Estatísticas
            </div>
            <div class="text-white sm:text-xs md:text-base font-sans text-left font-normal">
              Fique por dentro de {{ league.name }}! Informação em tempo real e diversão em um só lugar.
            </div>

            <!-- Tab Buttons -->
            <div class="flex gap-2 mt-4 overflow-x-auto w-full">
              <button
                @click="activeTab = 'estatisticas'"
                :class="['px-4 py-2 font-semibold rounded-lg transition-all duration-300', activeTab === 'estatisticas' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                DESEMPENHO
              </button>
              <button
                @click="activeTab = 'tabela'"
                :class="['px-4 py-2 font-semibold rounded-lg transition-all duration-300', activeTab === 'tabela' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                TABELA
              </button>
              <button
                @click="activeTab = 'artilheiros'"
                :class="['px-4 py-2 font-semibold rounded-lg transition-all duration-300', activeTab === 'artilheiros' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                ARTILHEIROS
              </button>
            </div>

            <!-- Filter Buttons (only for stats) -->
            <div v-if="activeTab === 'estatisticas'" id="stats-filter-buttons" class="flex gap-2 mt-2">
              <button
                @click="statsFilter = 'geral'"
                :class="['px-3 py-1 text-sm font-semibold rounded-lg transition-all duration-300', statsFilter === 'geral' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                GERAL
              </button>
              <button
                @click="statsFilter = 'casa'"
                :class="['px-3 py-1 text-sm font-semibold rounded-lg transition-all duration-300', statsFilter === 'casa' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                CASA
              </button>
              <button
                @click="statsFilter = 'fora'"
                :class="['px-3 py-1 text-sm font-semibold rounded-lg transition-all duration-300', statsFilter === 'fora' ? 'bg-[#AAF53A] text-black' : 'bg-gray-700 text-white opacity-80']"
              >
                FORA
              </button>
            </div>
          </div>

          <!-- Components -->
          <BrasileiraoStats v-if="activeTab === 'estatisticas'" :leagueId="parsedLeagueId" :filter="statsFilter" />
          <BrasileiraoTable v-if="activeTab === 'tabela'" :leagueId="parsedLeagueId" />
          <BrasileiraoTopScorers v-if="activeTab === 'artilheiros'" :leagueId="parsedLeagueId" />
        </div>
      </div>

      <!-- Responsible Gaming Section -->
      <div class="self-stretch py-14 bg-contentMain flex flex-col gap-8">
        <div class="self-stretch px-4 sm:px-6 md:px-20 flex flex-col gap-3">
          <div class="text-2xl sm:text-3xl md:text-4xl font-extrabold font-sans text-left">
            Jogue com responsabilidade!
          </div>
          <div class="self-stretch text-sm sm:text-base md:text-lg font-normal font-sans text-left max-w-3xl">
            A emoção de {{ league.name }} começa aqui! Acompanhe todos os jogos, confira estatísticas e aproveite odds turbinadas, tudo em um só lugar!
          </div>
        </div>
      </div>

      <!-- Back to Top Button -->
      <div class="fixed bottom-12 right-8 z-50 flex flex-row gap-3 items-center sm:bottom-18 sm:right-6">
        <a
          href="#hero-banner"
          class="w-10 h-12 bg-gray-800 hover:bg-gray-700 rounded-t-[244px] rounded-[244px] outline outline-2 outline-offset-[-2px] outline-white flex justify-center items-center transition-all duration-300 hover:-translate-y-1 hover:shadow-lg shadow-md"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path fill-rule="evenodd" clip-rule="evenodd" d="M12 3C12.2652 3 12.5196 3.10536 12.7071 3.29289L19.7071 10.2929C20.0976 10.6834 20.0976 11.3166 19.7071 11.7071C19.3166 12.0976 18.6834 12.0976 18.2929 11.7071L13 6.41421V20C13 20.5523 12.5523 21 12 21C11.4477 21 11 20.5523 11 20V6.41421L5.70711 11.7071C5.31658 12.0976 4.68342 12.0976 4.29289 11.7071C3.90237 11.3166 3.90237 10.6834 4.29289 10.2929L11.2929 3.29289C11.4804 3.10536 11.7348 3 12 3Z" fill="#f0efef"/>
          </svg>
        </a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import BrasileiraoStats from '@/components/BrasileiraoStats.vue'
import BrasileiraoTable from '@/components/BrasileiraoTable.vue'
import BrasileiraoTopScorers from '@/components/BrasileiraoTopScorers.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref('estatisticas')
const statsFilter = ref('geral')
const loadingLeague = ref(true)
const errorLeague = ref(null)
const league = ref(null)

const parsedLeagueId = computed(() => {
  const id = parseInt(route.params.leagueId)
  return isNaN(id) ? 1 : id
})

const fetchLeague = async () => {
  loadingLeague.value = true
  errorLeague.value = null
  
  try {
    const response = await axios.get(`/api/v1/leagues/${parsedLeagueId.value}`)
    league.value = response.data
  } catch (err) {
    if (err.response?.status === 404) {
      errorLeague.value = 'Liga não encontrada'
    } else {
      errorLeague.value = 'Erro ao carregar informações da liga'
    }
    console.error(err)
  } finally {
    loadingLeague.value = false
  }
}

watch(() => route.params.leagueId, fetchLeague, { immediate: true })

onMounted(() => {
  fetchLeague()
})
</script>

<style scoped>
.banner-image {
  width: 100%;
  height: auto;
  object-fit: cover;
  object-position: center center;
}

@media (max-width: 1024px) {
  .banner-image {
    height: 250px;
    object-position: center 30%;
  }
}

@media (min-width: 641px) and (max-width: 1024px) {
  .banner-image {
    height: 350px;
    object-position: center 35%;
  }
}

@media (max-width: 480px) {
  .banner-image {
    height: 200px;
    object-position: center 25%;
  }
}

.animate-scroll {
  animation: scroll-left 80s linear infinite;
}

@keyframes scroll-left {
  0% { transform: translateX(0%); }
  100% { transform: translateX(-50%); }
}
</style>

