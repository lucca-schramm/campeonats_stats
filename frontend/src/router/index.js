import { createRouter, createWebHistory } from 'vue-router'
import BrasileiraoView from '../views/BrasileiraoView.vue'
import LeagueView from '../views/LeagueView.vue'
import LeaguesView from '../views/LeaguesView.vue'
import ChatbotView from '../views/ChatbotView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      redirect: '/ligas'
    },
    {
      path: '/ligas',
      name: 'leagues',
      component: LeaguesView
    },
    {
      path: '/ligas/:leagueId',
      name: 'league',
      component: LeagueView,
      props: true
    },
    {
      path: '/brasileirao',
      name: 'brasileirao',
      component: BrasileiraoView
    },
    {
      path: '/chatbot',
      name: 'chatbot',
      component: ChatbotView
    }
  ]
})

export default router
