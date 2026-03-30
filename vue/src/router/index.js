import { createRouter, createWebHashHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
  },
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/Chat.vue'),
  },
  {
    path: '/page1',
    name: 'page1',
    component: () => import('@/views/Page1.vue'),
  },
  {
    path: '/page2',
    name: 'page2',
    component: () => import('@/views/Page2.vue'),
  },
  {
    path: '/user',
    name: 'user',
    component: () => import('@/views/User.vue'),
  },
  {
    path: '/',
    redirect: '/chat',
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes,
})

export default router
