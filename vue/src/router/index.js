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
    path: '/rag',
    name: 'rag',
    component: () => import('@/views/Rag.vue'),
  },
  {
    path: '/todo',
    name: 'todo',
    component: () => import('@/views/Todo.vue'),
  },
  {
    path: '/user',
    name: 'user',
    component: () => import('@/views/User.vue'),
  },
  {
    path: '/files',
    name: 'files',
    component: () => import('@/views/FileManager.vue'),
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
