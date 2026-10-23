<template>
  <div class="dash tech-bg">
    <!-- 背景微光球 -->
    <span class="orb orb--mint orb--slow" style="width: 240px; height: 240px; top: -70px; right: 8%"></span>
    <span class="orb orb--emerald orb--slower" style="width: 200px; height: 200px; bottom: 8%; left: 4%"></span>

    <!-- 欢迎条 -->
    <div class="welcome rise-in">
      <div>
        <h2 class="welcome-title">
          欢迎回来，<span class="gradient-text">{{ userStore.displayName }}</span>
        </h2>
        <p class="welcome-sub">白泽 AI 应用平台 · 控制台总览</p>
      </div>
      <div class="welcome-badge glass">
        <span class="spark"></span> 系统运行中
      </div>
    </div>

    <!-- 加载骨架 -->
    <template v-if="loading">
      <el-row :gutter="16">
        <el-col :span="8" v-for="i in 3" :key="i">
          <div class="tech-card" style="padding: 22px">
            <div class="skeleton" style="width: 40%; height: 14px; margin-bottom: 16px"></div>
            <div class="skeleton" style="width: 60%; height: 34px"></div>
          </div>
        </el-col>
      </el-row>
      <div class="tech-card mt" style="padding: 22px">
        <div class="skeleton" style="width: 30%; height: 16px; margin-bottom: 16px"></div>
        <div class="skeleton" style="width: 100%; height: 14px; margin-bottom: 10px"></div>
        <div class="skeleton" style="width: 86%; height: 14px"></div>
      </div>
    </template>

    <!-- 内容 -->
    <template v-else>
      <!-- 统计卡片 -->
      <el-row :gutter="16">
        <el-col :span="8" v-for="(c, i) in cards" :key="c.title">
          <div class="tech-card stat rise-in" :class="'delay-' + (i + 1)" @mousemove="tilt" @mouseleave="untilt">
            <div class="stat-ico" :style="{ background: c.grad }">
              <el-icon><component :is="c.icon" /></el-icon>
            </div>
            <div class="stat-body">
              <div class="stat-title">{{ c.title }}</div>
              <div class="stat-value gradient-text">{{ display[i] }}<small v-if="c.suffix"> {{ c.suffix }}</small></div>
            </div>
            <div class="stat-ring" :style="{ background: c.grad }"></div>
          </div>
        </el-col>
      </el-row>

      <!-- AI 应用市场快捷入口 -->
      <h3 class="section-title rise-in delay-2">AI 应用市场</h3>
      <el-row :gutter="16">
        <el-col :span="8" v-for="(a, i) in apps" :key="a.code">
          <div class="tech-card app-card rise-in cursor" :class="'delay-' + (i + 2)" @click="openApp(a)">
            <div class="app-ico" :style="{ background: 'var(--brand-grad)' }">
              <el-icon><component :is="iconOf(a.icon)" /></el-icon>
            </div>
            <div class="app-body">
              <div class="app-name">{{ a.name }}</div>
              <div class="app-desc">{{ a.description || 'AI 应用' }}</div>
            </div>
            <el-icon class="app-arrow"><ArrowRight /></el-icon>
          </div>
        </el-col>
        <el-col :span="8" v-if="!apps.length">
          <div class="tech-card app-empty rise-in delay-3">
            <el-icon><Shop /></el-icon>
            <span>暂无可用应用</span>
            <small>需在「应用市场管理」启用并授予使用权限</small>
          </div>
        </el-col>
      </el-row>

      <!-- 平台能力 -->
      <h3 class="section-title rise-in delay-3">平台能力</h3>
      <el-row :gutter="16">
        <el-col :span="8" v-for="(f, i) in features" :key="f.title">
          <div
            class="flip-card rise-in"
            :class="['delay-' + (i + 2), { 'is-flipped': flipped[i] }]"
            style="height: 168px"
            @click="flipped[i] = !flipped[i]"
          >
            <div class="flip-card__inner">
              <div class="flip-card__face flip-card__face--front">
                <div class="feat-ico" :style="{ background: f.grad }">
                  <el-icon><component :is="f.icon" /></el-icon>
                </div>
                <h4 class="feat-title">{{ f.title }}</h4>
                <p class="feat-tip">点击 / 悬停查看详情</p>
              </div>
              <div class="flip-card__face flip-card__face--back">
                <h4 style="margin: 0 0 8px">{{ f.title }}</h4>
                <p style="font-size: 13px; line-height: 1.7; opacity: 0.92">{{ f.desc }}</p>
              </div>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- 权限标签 -->
      <div class="tech-card mt rise-in delay-3">
        <div class="perm-head">
          <span class="perm-title">我的权限</span>
          <span class="perm-count">{{ userStore.permissions.length }} 项</span>
        </div>
        <div class="perm-tags">
          <el-tag
            v-for="p in userStore.permissions"
            :key="p"
            class="perm-tag"
            effect="light"
          >{{ p }}</el-tag>
          <el-empty v-if="!userStore.permissions.length" description="暂无权限" :image-size="60" />
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/store/user'
import { useModuleStore } from '@/store/modules'
import {
  User, Key, Shop, Lock, Connection, ArrowRight,
  DataAnalysis, Coin, MagicStick, Cpu,
} from '@element-plus/icons-vue'

const router = useRouter()
const userStore = useUserStore()
const moduleStore = useModuleStore()

const loading = ref(true)
const display = reactive<number[]>([0, 0, 0])
const flipped = reactive<boolean[]>([false, false, false])
// 组件定义不可被响应式代理：用 markRaw 包裹，避免 Vue 将其转为 reactive（性能开销 + 警告）
const cards = ref<any[]>([
  { title: '我的角色', value: 0, icon: markRaw(User), grad: 'linear-gradient(135deg,#34d399,#10b981)', suffix: '' },
  { title: '权限点', value: 0, icon: markRaw(Key), grad: 'linear-gradient(135deg,#10b981,#06b6d4)', suffix: '' },
  { title: '可用应用', value: 0, icon: markRaw(Shop), grad: 'linear-gradient(135deg,#06b6d4,#34d399)', suffix: '' },
])

const apps = computed(() => moduleStore.visibleList)

const features = [
  { title: '角色权限', icon: markRaw(Lock), grad: 'linear-gradient(135deg,#34d399,#10b981)', desc: '基于 RBAC 的细粒度权限控制，支持角色继承与权限点动态分配。' },
  { title: '应用市场', icon: markRaw(Shop), grad: 'linear-gradient(135deg,#10b981,#06b6d4)', desc: 'AI 应用即插即用，按使用权限开放；后端 frontend 分离部署，热插拔加载。' },
  { title: '操作审计', icon: markRaw(Connection), grad: 'linear-gradient(135deg,#06b6d4,#34d399)', desc: '全量操作日志留痕，可追溯每一次关键行为与系统变更。' },
]

const iconMap: Record<string, any> = { DataAnalysis, Coin, MagicStick }
function iconOf(name?: string) {
  return (name && iconMap[name]) || Cpu
}

function openApp(a: any) {
  router.push(a.entry || `/apps/${a.code}`)
}

// 数字滚动动画
function countUp(idx: number, target: number, dur = 900) {
  const start = performance.now()
  const step = (now: number) => {
    const t = Math.min(1, (now - start) / dur)
    const eased = 1 - Math.pow(1 - t, 3)
    display[idx] = Math.round(eased * target)
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

// 卡片悬浮 3D 倾斜
function tilt(e: MouseEvent) {
  const el = e.currentTarget as HTMLElement
  const r = el.getBoundingClientRect()
  const rx = ((e.clientY - r.top) / r.height - 0.5) * -8
  const ry = ((e.clientX - r.left) / r.width - 0.5) * 8
  el.style.transform = `translateY(-6px) perspective(800px) rotateX(${rx}deg) rotateY(${ry}deg)`
}
function untilt(e: MouseEvent) {
  ;(e.currentTarget as HTMLElement).style.transform = ''
}

onMounted(async () => {
  await moduleStore.fetchModules()
  cards.value = [
    { title: '我的角色', value: userStore.roles.length, icon: markRaw(User), grad: 'linear-gradient(135deg,#34d399,#10b981)', suffix: '' },
    { title: '权限点', value: userStore.permissions.length, icon: markRaw(Key), grad: 'linear-gradient(135deg,#10b981,#06b6d4)', suffix: '' },
    { title: '可用应用', value: moduleStore.visibleList.length, icon: markRaw(Shop), grad: 'linear-gradient(135deg,#06b6d4,#34d399)', suffix: '' },
  ]
  setTimeout(() => {
    loading.value = false
    cards.value.forEach((c, i) => countUp(i, c.value))
  }, 500)
})
</script>

<style scoped>
.dash { position: relative; padding: 4px 2px 8px; }

.welcome {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 18px;
}
.welcome-title { font-size: 24px; font-weight: 700; }
.welcome-sub { margin: 4px 0 0; font-size: 13px; color: var(--c-text-3); letter-spacing: 1px; }
.welcome-badge {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px; border-radius: 999px;
  font-size: 12px; color: var(--c-text-2);
  box-shadow: var(--shadow-sm);
}

.mt { margin-top: 16px; }

/* 统计卡 */
.stat {
  position: relative;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 22px;
  transition:
    transform var(--dur) var(--ease-out),
    box-shadow var(--dur) var(--ease-out),
    border-color var(--dur) var(--ease);
}
.stat-ico {
  display: grid; place-items: center;
  width: 54px; height: 54px;
  border-radius: 14px;
  color: #fff; font-size: 24px;
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35);
}
.stat-title { color: var(--c-text-2); font-size: 13px; }
.stat-value { font-size: 30px; font-weight: 800; margin-top: 4px; letter-spacing: 0.5px; }
.stat-value small { font-size: 14px; font-weight: 600; }
.stat-ring {
  position: absolute;
  right: -20px; top: -20px;
  width: 90px; height: 90px;
  border-radius: 50%;
  opacity: 0.12;
  filter: blur(6px);
  pointer-events: none;
}

/* 区块标题 */
.section-title {
  margin: 24px 0 14px;
  font-size: 16px;
  padding-left: 12px;
  border-left: 3px solid transparent;
  border-image: var(--brand-grad) 1;
}

/* AI 应用卡 */
.app-card { display: flex; align-items: center; gap: 14px; padding: 18px; cursor: pointer; }
.cursor { cursor: pointer; }
.app-ico {
  flex: none; display: grid; place-items: center;
  width: 46px; height: 46px; border-radius: 13px;
  color: #fff; font-size: 22px;
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.3);
}
.app-body { flex: 1; min-width: 0; }
.app-name { font-weight: 600; color: var(--c-text-1); }
.app-desc {
  margin-top: 3px; font-size: 12px; color: var(--c-text-3);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.app-arrow { color: var(--brand-emerald); font-size: 18px; transition: transform var(--dur-fast) var(--ease); }
.app-card:hover .app-arrow { transform: translateX(4px); }

.app-empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 22px; color: var(--c-text-3); text-align: center;
}
.app-empty .el-icon { font-size: 28px; color: var(--brand-mint); }
.app-empty small { font-size: 11px; color: var(--c-text-3); }

/* 翻转卡正面 */
.flip-card__face--front {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 22px;
}
.feat-ico {
  display: grid; place-items: center;
  width: 50px; height: 50px;
  border-radius: 14px;
  color: #fff; font-size: 22px;
  margin-bottom: 12px;
  box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35);
}
.feat-title { font-size: 16px; margin: 0; }
.feat-tip { margin: 8px 0 0; font-size: 12px; color: var(--c-text-3); }

/* 权限区 */
.perm-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.perm-title { font-size: 15px; font-weight: 600; }
.perm-count {
  font-size: 12px; color: var(--brand-emerald);
  background: var(--brand-grad-soft);
  padding: 2px 10px; border-radius: 999px;
}
.perm-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.perm-tag {
  border-radius: 8px;
  border-color: transparent;
  background: var(--brand-grad-soft);
  color: var(--brand-emerald);
  font-family: var(--font-mono);
  transition: transform var(--dur-fast) var(--ease), box-shadow var(--dur-fast) var(--ease);
}
.perm-tag:hover { transform: translateY(-2px); box-shadow: var(--shadow-sm); }
</style>
