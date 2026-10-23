<template>
  <span class="bz-logo" :class="`bz-logo--${variant}`">
    <!-- 内联矢量：任意 DPI / 缩放均清晰，且随主题变量渲染 -->
    <svg
      class="bz-mark"
      :width="size"
      :height="size"
      viewBox="0 0 64 64"
      role="img"
      :aria-label="title || '白泽'"
    >
      <template v-if="variant === 'mono'">
        <!-- 单色：继承 currentColor -->
        <g fill="none" stroke="currentColor" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M29 10.5 L22.3 17" />
          <rect x="20.6" y="16.8" width="22.8" height="25.2" rx="5.2" />
          <path d="M20.6 29.4 L43.4 29.4" />
        </g>
        <circle cx="32" cy="35.6" r="3.5" fill="currentColor" />
      </template>
      <template v-else>
        <defs>
          <linearGradient :id="gid" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="#34d399" />
            <stop offset="0.48" stop-color="#10b981" />
            <stop offset="1" stop-color="#06b6d4" />
          </linearGradient>
          <linearGradient :id="sid" x1="0.1" y1="0" x2="0.7" y2="1">
            <stop offset="0" stop-color="#ffffff" stop-opacity="0.30" />
            <stop offset="0.55" stop-color="#ffffff" stop-opacity="0" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="60" height="60" rx="18" :fill="`url(#${gid})`" />
        <rect x="2" y="2" width="60" height="60" rx="18" :fill="`url(#${sid})`" />
        <g fill="none" stroke="#ffffff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M29 10.5 L22.3 17" />
          <rect x="20.6" y="16.8" width="22.8" height="25.2" rx="5.2" />
          <path d="M20.6 29.4 L43.4 29.4" />
        </g>
        <circle cx="32" cy="35.6" r="3.5" fill="#ffffff" />
        <!-- 泽之水波：仅较大尺寸呈现，避免小图标糊化 -->
        <path
          v-if="size >= 30"
          d="M13 49.6 C20 45.8 26 53.2 32 49.6 C38 46 44 53.2 51 49.6"
          fill="none"
          stroke="#ffffff"
          stroke-opacity="0.4"
          stroke-width="2"
          stroke-linecap="round"
        />
      </template>
    </svg>

    <span v-if="variant === 'full' && title" class="bz-text">
      <span class="bz-title gradient-text" :style="{ fontSize: titleSize + 'px' }">{{ title }}</span>
      <span v-if="subtitle" class="bz-sub" :style="{ fontSize: Math.max(10, Math.round(titleSize * 0.58)) + 'px' }">
        {{ subtitle }}
      </span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

let seq = 0

const props = withDefaults(
  defineProps<{
    /** 标记尺寸（px） */
    size?: number
    /** mark=仅图形 / full=图形+字标 / mono=单色图形 */
    variant?: 'mark' | 'full' | 'mono'
    /** 字标主标题 */
    title?: string
    /** 字标副标题 */
    subtitle?: string
    /** 主标题字号（px），默认按 size 推导 */
    titleSize?: number
  }>(),
  { size: 38, variant: 'full', title: '白泽', subtitle: '', titleSize: 0 },
)

// 每个实例唯一 id，避免同页多实例的渐变 id 冲突
const uid = `bz${(seq++).toString(36)}${Math.random().toString(36).slice(2, 6)}`
const gid = computed(() => `bzGrad-${uid}`)
const sid = computed(() => `bzSheen-${uid}`)
const titleSize = computed(() => props.titleSize || Math.max(13, Math.round(props.size * 0.42)))
</script>

<style scoped>
.bz-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  line-height: 1.15;
  user-select: none;
}
.bz-mark {
  display: block;
  flex: none;
  filter: drop-shadow(0 6px 16px rgba(16, 185, 129, 0.32));
}
.bz-logo--mono .bz-mark {
  filter: none;
}
.bz-text {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.bz-title {
  font-weight: 700;
  letter-spacing: 1px;
  white-space: nowrap;
}
.bz-sub {
  letter-spacing: 1.2px;
  color: var(--c-text-3, #8aab9f);
  font-weight: 600;
  white-space: nowrap;
}
</style>
