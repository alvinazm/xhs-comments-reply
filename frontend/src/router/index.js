import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import ExportHistory from '../views/ExportHistory.vue'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home,
  },
  {
    path: '/export-history',
    name: 'ExportHistory',
    component: ExportHistory,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router