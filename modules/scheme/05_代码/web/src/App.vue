<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const active = computed(() => route.path)
</script>

<template>
  <el-container style="height: 100vh">
    <el-aside width="220px" style="background: #001529">
      <div style="color: #fff; font-weight: 700; padding: 16px; font-size: 16px">
        Baize 方案平台
      </div>
      <el-menu :default-active="active" router background-color="#001529" text-color="#fff"
        active-text-color="#409eff">
        <el-menu-item index="/"><el-icon><HomeFilled /></el-icon>总览</el-menu-item>
        <el-menu-item index="/templates"><el-icon><Files /></el-icon>参考模板</el-menu-item>
        <el-menu-item index="/documents"><el-icon><Document /></el-icon>参考文档</el-menu-item>
        <el-menu-item index="/knowledge"><el-icon><Search /></el-icon>知识库检索</el-menu-item>
        <el-menu-item index="/writing"><el-icon><Edit /></el-icon>撰写工作台</el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header style="display: flex; align-items: center; border-bottom: 1px solid #eee">
        <span style="font-size: 15px; color: #555">Vue3 + FastAPI + PostgreSQL(pgvector)</span>
      </el-header>
      <el-main>
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
