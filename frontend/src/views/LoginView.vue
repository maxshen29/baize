<template>
  <div
    class="login-page tech-bg"
    :style="{ '--px': px, '--py': py }"
    @mousemove="onMove"
    @mouseleave="onLeave"
  >
    <!-- 背景悬浮微光球（视差） -->
    <span class="orb orb--mint orb--slow par par-1" aria-hidden="true"></span>
    <span class="orb orb--cyan orb--slower par par-2" aria-hidden="true"></span>
    <span class="orb orb--emerald par par-3" aria-hidden="true"></span>

    <!-- 玻璃登录卡片 -->
    <el-card class="box glass" shadow="never">
      <div class="scanline" aria-hidden="true"></div>

      <div class="brand">
        <BrandLogo :size="46" title="白泽 AI 应用平台" subtitle="Baize AI Platform" :title-size="23" />
      </div>

      <el-form class="login-form" :model="form" @submit.prevent="onSubmit">
        <el-form-item>
          <el-input v-model="form.account" size="large" placeholder="用户名或邮箱" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" size="large" type="password" placeholder="密码" show-password :prefix-icon="Lock" />
        </el-form-item>
        <el-button
          class="login-btn"
          type="primary"
          size="large"
          :loading="loading"
          @click="onSubmit"
        >
          <template #loading><span class="tech-spinner tech-spinner--sm"></span></template>
          {{ loading ? '登录中' : '登 录' }}
        </el-button>
      </el-form>

      <p class="hint">
        <span class="spark"></span>
        默认管理员：<code>admin</code> / <code>Admin@123456</code>
      </p>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/store/user'
import BrandLogo from '@/components/BrandLogo.vue'

const router = useRouter()
const userStore = useUserStore()
const form = reactive({ account: '', password: '' })
const loading = ref(false)

// 鼠标视差
const px = ref(0)
const py = ref(0)
function onMove(e: MouseEvent) {
  const r = (e.currentTarget as HTMLElement).getBoundingClientRect()
  px.value = ((e.clientX - r.left) / r.width - 0.5) * 2
  py.value = ((e.clientY - r.top) / r.height - 0.5) * 2
}
function onLeave() {
  px.value = 0
  py.value = 0
}

async function onSubmit() {
  if (!form.account || !form.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    await userStore.login(form.account, form.password)
    ElMessage.success('登录成功')
    router.push('/dashboard')
  } catch {
    /* 错误已在拦截器提示 */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
  overflow: hidden;
}

/* 视差：卡片与微光球随鼠标位移 */
.box { transform: translate(calc(var(--px) * 12px), calc(var(--py) * 12px)); transition: transform 0.25s var(--ease-out); }
.par { transform: translate(calc(var(--px) * var(--k, 20px)), calc(var(--py) * var(--k, 20px))); transition: transform 0.4s var(--ease-out); }
.par-1 { --k: 34px; width: 300px; height: 300px; top: -80px; left: -60px; }
.par-2 { --k: 26px; width: 240px; height: 240px; bottom: -70px; right: -40px; }
.par-3 { --k: 18px; width: 160px; height: 160px; top: 30%; right: 18%; }

.box {
  position: relative;
  width: 380px;
  padding: 14px 26px 22px;
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
  animation: rise-in 0.7s var(--ease-out) both;
}
.box :deep(.el-card__body) { padding: 6px 4px 0; }

/* 顶部扫描线 */
.scanline {
  position: absolute;
  left: 0; right: 0; top: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, var(--brand-cyan), transparent);
  box-shadow: 0 0 12px 2px var(--brand-cyan);
  animation: scan 4.5s linear infinite;
  opacity: 0.7;
}

.brand { display: flex; align-items: center; margin: 20px 0 24px; }

.login-form { margin-top: 6px; }
.login-form :deep(.el-input__wrapper) {
  border-radius: var(--radius);
  background: rgba(255, 255, 255, 0.85);
  transition: box-shadow var(--dur-fast) var(--ease);
}
.login-form :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--brand-emerald), 0 0 16px rgba(16, 185, 129, 0.28);
}

.login-btn {
  width: 100%;
  margin-top: 6px;
  border: none;
  border-radius: var(--radius);
  background: var(--brand-grad) !important;
  box-shadow: 0 10px 26px rgba(16, 185, 129, 0.4);
  letter-spacing: 4px;
  font-weight: 600;
  transition: transform var(--dur) var(--ease-out), box-shadow var(--dur) var(--ease-out), filter var(--dur) var(--ease);
}
.login-btn:hover {
  transform: translateY(-2px);
  filter: brightness(1.05);
  box-shadow: 0 14px 34px rgba(6, 182, 212, 0.45);
}
.login-btn:active { transform: translateY(0); }
.login-btn .tech-spinner { display: inline-block; }

.hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  margin: 16px 0 4px;
  color: var(--c-text-3);
  font-size: 12px;
}
.hint code {
  font-family: var(--font-mono);
  color: var(--brand-emerald);
  background: var(--brand-grad-soft);
  padding: 1px 6px;
  border-radius: 6px;
}
</style>
