<template>
  <div class="min-h-screen bg-gradient-to-b from-[#263FA3] to-[#0A175C]">
    <div class="w-full relative" id="hero-banner">
      <img
        src="https://next-minio-b2b.devcore.at/next-cms/rGDgR0Bv1imTH7wcpi8xSw.png"
        class="w-full h-auto object-cover object-center block banner-image"
        alt="Brasileirão 2025 - Banner Principal"
        loading="eager"
      />
      <div
        id="copy-bannet-text"
        class="absolute bottom-2 sm:bottom-4 md:bottom-5 lg:bottom-6 xl:bottom-1 left-0 right-0 px-4 sm:px-6 md:px-8 lg:px-12 xl:px-16 2xl:px-20"
      >
        <div class="flex flex-col justify-start mt-2 items-start gap-1 sm:gap-2 w-full max-w-4xl">
          <div class="text-[#AAF53A] text-4xl sm:text-3xl md:text-4xl lg:text-5xl xl:text-5xl font-extrabold font-sans uppercase leading-tight">
            Brasileirão
          </div>
          <div class="text-white sm:text-4xl sm:text-base md:text-lg lg:text-xl xl:text-2xl font-medium font-sans leading-relaxed max-w-3xl lg:max-w-none">
            Faça seu palpite na Casa!
          </div>
        </div>
      </div>
    </div>

    <div id="mercados-especiais" class="w-full px-4 sm:px-6 md:px-20 pb-14 xl:pt-10 bg-gradient-to-b from-[#263FA3] to-[#0D115B]">
      <div class="max-w-7xl">
        <div class="flex flex-col gap-8">
          <div class="flex flex-col gap-4">
            <div class="self-stretch pr-4 inline-flex flex-col justify-start items-start">
              <div class="flex items-center gap-2 pb-6">
                <div class="self-stretch inline-flex justify-center text-white text-[10px] sm:text-[14px] md:text-sm font-normal font-sans">
                  <svg width="16" height="16" class="sm:w-[18px] sm:h-[18px] md:w-[20px] md:h-[20px]" viewBox="0 0 20 20" fill="white" xmlns="http://www.w3.org/2000/svg">
                    <path d="M19.2162 13.1769C18.9234 13.1683 18.7137 12.9422 18.7055 12.6411C18.6134 8.99971 16.7384 6.30436 13.8923 5.24971L11.9423 10.6069C11.9255 10.6486 11.9337 10.6822 11.9755 10.699C12.0091 10.7158 12.0341 10.699 12.0595 10.674L13.047 9.60257C13.6916 8.90757 14.512 8.85757 15.148 9.39329C15.868 10.004 15.8766 10.9165 15.173 11.779L12.3691 15.169C10.2512 17.7304 7.76552 18.5254 4.98624 17.5126C1.66302 16.3072 0.248381 13.2604 1.58802 9.57721L2.21552 7.8615C2.86838 6.04507 4.11552 5.30007 5.58052 5.81079C5.9741 5.30007 6.57695 5.12436 7.22945 5.35864C7.46411 5.44836 7.68413 5.57246 7.88231 5.72686C8.30945 5.17436 8.97052 4.97329 9.65731 5.21614C9.84458 5.28786 10.0218 5.38354 10.1845 5.50079L11.1387 2.88936C11.4984 1.89293 12.4027 1.47471 13.3316 1.80936C14.2691 2.15257 14.6877 3.04864 14.328 4.04436L14.2609 4.22864C17.5002 5.44221 19.752 8.56436 19.752 12.6244C19.752 12.9254 19.5009 13.1851 19.2162 13.1769ZM5.34624 16.4161C7.5391 17.2197 9.59838 16.8094 11.532 14.474L14.3362 11.1008C14.6373 10.7494 14.6373 10.4061 14.3695 10.1715C14.1184 9.94579 13.7752 10.0211 13.4991 10.3054L11.5655 12.3061C11.2391 12.6411 10.9545 12.6744 10.678 12.574C10.3516 12.4569 10.2095 12.1054 10.3434 11.7454L13.3066 3.59257C13.432 3.25757 13.2816 2.93971 12.9634 2.82221C12.637 2.70507 12.3355 2.86436 12.2098 3.199L10.092 9.01686C9.99195 9.29293 9.68195 9.41829 9.40588 9.31793C9.13802 9.21757 8.99588 8.92436 9.09624 8.6565L9.85802 6.55579C9.74052 6.44686 9.5816 6.33793 9.42231 6.27936C9.02945 6.13721 8.70267 6.31293 8.55195 6.72293L7.88231 8.55614C7.78231 8.84079 7.47231 8.94971 7.20445 8.849C6.94481 8.75686 6.77767 8.48114 6.8866 8.18793L7.43052 6.70614C7.30664 6.58219 7.1584 6.48527 6.99517 6.4215C6.60159 6.27936 6.27517 6.45507 6.12445 6.86543L5.68088 8.08757C5.57231 8.38043 5.26231 8.48936 4.99445 8.38864C4.93 8.36636 4.87059 8.33153 4.81967 8.28617C4.76875 8.24081 4.72732 8.18581 4.69777 8.12434C4.66821 8.06288 4.65113 7.99618 4.64749 7.92807C4.64386 7.85997 4.65375 7.79183 4.6766 7.72757L5.01124 6.82329C4.30838 6.57221 3.64695 7.1415 3.19517 8.39721L2.66767 9.82864C1.52088 12.9926 2.56731 15.4033 5.34624 16.4161Z"/>
                  </svg>
                  <p style="padding-left: 0.5rem;" class="text-[12px] sm:text-[14px] xl:text-[18px] md:text-sm">
                    Deslize para o lado e explore mais mercados.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="w-full bg-[#AAF53A] py-4 overflow-hidden">
      <div id="slider-motion" class="flex whitespace-nowrap">
        <div class="flex items-center justify-start text-[#070300] text-base font-bold font-sans uppercase leading-relaxed whitespace-nowrap animate-scroll">
          <span class="text-[#070300]">TUDO SOBRE BRASILEIRÃO</span>
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

    <div class="w-full py-14 bg-gradient-to-b from-[#263FA3] to-[#0A175C]">
      <div class="w-full px-4 sm:px-6 md:px-20">
        <div class="w-full flex flex-col justify-start items-start gap-3 pb-6">
          <div class="text-[#AAF53A] text-3xl sm:text-3xl md:text-3xl font-semibold font-sans text-left">
            Central de Estatísticas
          </div>
          <div class="text-white sm:text-xs md:text-base font-sans text-left font-normal">
            Fique por dentro do Brasileirão! Informação em tempo real e diversão em um só lugar.
          </div>

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

        <BrasileiraoStats v-if="activeTab === 'estatisticas'" :leagueId="564922" :filter="statsFilter" />
        <BrasileiraoTable v-if="activeTab === 'tabela'" :leagueId="564922" />
        <BrasileiraoTopScorers v-if="activeTab === 'artilheiros'" :leagueId="564922" />
      </div>
    </div>

    <div class="self-stretch py-14 bg-contentMain flex flex-col gap-8 text-white">
      <div class="self-stretch px-4 sm:px-6 md:px-20 flex flex-col gap-3">
        <div class="text-2xl sm:text-3xl md:text-4xl font-extrabold font-sans text-left">
          Jogue com responsabilidade!
        </div>
        <div class="self-stretch text-sm sm:text-base md:text-lg font-normal font-sans text-left max-w-3xl">
          A emoção do Brasileirão começa aqui! Acompanhe todos os jogos, confira estatísticas e aproveite odds turbinadas, tudo em um só lugar!
        </div>
        <div class="flex flex-col justify-start items-start gap-1">
          <p class="text-sm sm:text-base md:text-lg font-normal font-sans text-left">
            Leia todas as informações disponíveis na nossa seção de
            <a href="https://casadeapostas.bet.br/br/jogo-responsavel" class="text-emerald-700 font-semibold underline hover:text-emerald-800 transition-colors">
              Jogo Responsável
            </a>
            e dos nossos
            <a href="https://casadeapostas.bet.br/br/terms-and-conditions" class="text-emerald-700 font-semibold underline hover:text-emerald-800 transition-colors">
              Termos e Condições
            </a>.
          </p>
        </div>
      </div>
    </div>

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
</template>

<script setup>
import { ref } from 'vue'
import BrasileiraoStats from '@/components/BrasileiraoStats.vue'
import BrasileiraoTable from '@/components/BrasileiraoTable.vue'
import BrasileiraoTopScorers from '@/components/BrasileiraoTopScorers.vue'

const activeTab = ref('estatisticas')
const statsFilter = ref('geral')
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
