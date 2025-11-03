<template>
  <div class="min-h-screen">
    <!-- Navigation Bar -->
    <nav class="bg-gray-900/90 border-b border-gray-700 sticky top-0 z-50 backdrop-blur-sm">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div class="flex items-center justify-between h-16">
          <!-- Logo / Title -->
          <div class="flex items-center">
            <router-link to="/" class="text-[#AAF53A] text-xl font-bold">
              ⚽ Campeonatos Stats
            </router-link>
          </div>

          <!-- Navigation Links -->
          <div class="flex items-center gap-4">
            <router-link
              to="/ligas"
              class="text-white/70 hover:text-[#AAF53A] transition-colors px-3 py-2 rounded-md text-sm font-medium"
              active-class="text-[#AAF53A] bg-gray-800"
            >
              Ligas
            </router-link>
            <router-link
              to="/chatbot"
              class="text-white/70 hover:text-[#AAF53A] transition-colors px-3 py-2 rounded-md text-sm font-medium"
              active-class="text-[#AAF53A] bg-gray-800"
            >
              Chatbot
            </router-link>
          </div>
        </div>
      </div>
    </nav>

    <!-- Main Content -->
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
/* Global styles */
body {
  margin: 0;
  padding: 0;
}
</style>
