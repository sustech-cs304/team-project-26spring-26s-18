<script setup>
import { RouterView, useRoute } from 'vue-router'
import Navbar from './views/Navbar.vue'

const route = useRoute()
</script>

<template>
  <div>
    <!-- 只有不是 studio 页面时才显示导航栏 -->
    <Navbar v-if="route.path !== '/studio'" />
    <RouterView />
  </div>
</template>