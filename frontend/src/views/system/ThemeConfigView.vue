<template>
  <div class="page">
    <el-card class="panel tech-card" shadow="never">
      <template #header>
        <div class="panel-head">
          <div>
            <h2 class="panel-title gradient-text">配色方案</h2>
            <p class="panel-sub">设定平台默认配色；用户在界面右上角可自由切换，其个人选择优先于平台默认。</p>
          </div>
          <el-button type="primary" :icon="Check" :loading="saving" @click="save">保存默认主题</el-button>
        </div>
      </template>

      <div class="grid">
        <div
          v-for="t in THEMES"
          :key="t.key"
          class="theme-card"
          :class="{ active: selected === t.key }"
          @click="selected = t.key"
        >
          <span class="swatch" :style="{ background: t.swatch }"></span>
          <div class="meta">
            <div class="name">{{ t.name }}</div>
            <div class="tag" v-if="selected === t.key">已选为默认</div>
            <div class="tag muted" v-else>点击选择</div>
          </div>
          <el-icon v-if="selected === t.key" class="check"><CircleCheck /></el-icon>
        </div>
      </div>

      <el-alert
        class="tip"
        type="info"
        :closable="false"
        title="提示"
        description="保存后，新登录且未手动切换主题的用户将使用此默认配色；已自选主题的用户不受影响。"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, CircleCheck } from '@element-plus/icons-vue'
import { THEMES, useAppStore } from '@/store/app'
import * as themeApi from '@/api/theme'

const appStore = useAppStore()
const selected = ref<string>('mint')
const saving = ref(false)

async function load() {
  try {
    const res = await themeApi.getDefault()
    const t = res.data?.data?.theme
    if (t) selected.value = t
  } catch {
    /* ignore */
  }
}

async function save() {
  saving.value = true
  try {
    await themeApi.setDefault(selected.value)
    appStore.defaultTheme = selected.value
    ElMessage.success('平台默认主题已更新')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page { padding: 4px; }
.panel-head { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.panel-title { font-size: 18px; font-weight: 700; margin: 0; }
.panel-sub { margin: 4px 0 0; font-size: 13px; color: var(--c-text-3); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 14px; }
.theme-card {
  display: flex; align-items: center; gap: 12px;
  padding: 14px; border-radius: var(--radius); cursor: pointer;
  border: 1px solid var(--c-border); background: var(--c-surface-2);
  transition: transform var(--dur-fast) var(--ease), border-color var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
  position: relative;
}
.theme-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.theme-card.active { border-color: var(--brand-emerald); box-shadow: var(--shadow-glow); }
.swatch { width: 38px; height: 38px; border-radius: 10px; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.08); }
.meta { flex: 1; }
.name { font-weight: 600; color: var(--c-text-1); }
.tag { font-size: 12px; color: var(--brand-emerald); }
.tag.muted { color: var(--c-text-3); }
.check { color: var(--brand-emerald); font-size: 18px; }
.tip { margin-top: 18px; }
.tech-card { border: 1px solid var(--c-border); border-radius: var(--radius-lg); background: var(--c-surface); }
</style>
