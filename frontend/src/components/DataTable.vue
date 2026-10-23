<template>
  <el-table :data="data" v-loading="loading" border stripe style="width: 100%">
    <slot />
    <template #empty><el-empty description="暂无数据" /></template>
  </el-table>
  <el-pagination
    class="pager"
    background
    layout="total, prev, pager, next"
    :total="total"
    :current-page="page"
    :page-size="pageSize"
    @current-change="$emit('page-change', $event)"
  />
</template>

<script setup lang="ts">
defineProps<{
  data: any[]
  total: number
  page: number
  pageSize: number
  loading?: boolean
}>()
defineEmits<{ (e: 'page-change', page: number): void }>()
</script>

<style scoped>
.pager { margin-top: 12px; justify-content: flex-end; display: flex; }
</style>
