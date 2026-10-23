<template>
  <el-drawer :model-value="modelValue" :title="`模块配置 - ${module?.name || ''}`" size="460px" @update:model-value="$emit('update:modelValue', $event)">
    <el-form label-width="120px">
      <el-form-item v-for="f in schema" :key="f.key" :label="f.label">
        <el-input v-if="f.type === 'string' || f.type === 'textarea'" v-model="values[f.key]" :type="f.type === 'textarea' ? 'textarea' : 'text'" />
        <el-input-number v-else-if="f.type === 'number'" v-model="values[f.key]" />
        <el-switch v-else-if="f.type === 'boolean'" v-model="values[f.key]" />
        <el-select v-else-if="f.type === 'select'" v-model="values[f.key]" style="width: 100%">
          <el-option v-for="o in f.options" :key="o" :label="o" :value="o" />
        </el-select>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSave">保存</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api/modules'

const props = defineProps<{ modelValue: boolean; module?: any }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()

const schema = ref<any[]>([])
const values = ref<Record<string, any>>({})
const loading = ref(false)

function initSchema() {
  const s = (props.module?.config_schema as any[]) || []
  schema.value = s
  const v: Record<string, any> = {}
  for (const f of s) v[f.key] = f.default ?? (f.type === 'number' ? 0 : f.type === 'boolean' ? false : '')
  values.value = v
}

watch(() => props.modelValue, async (open) => {
  if (open && props.module) {
    initSchema()
    try {
      const res = await api.getConfig(props.module.code)
      for (const c of res.data.data) values.value[c.config_key] = c.config_value
    } catch { /* ignore */ }
  }
})

async function onSave() {
  loading.value = true
  try {
    const items = schema.value.map((f) => ({
      config_key: f.key,
      config_value: values.value[f.key],
      config_type: f.type || 'string',
      scope: 'global',
    }))
    await api.setConfig(props.module.code, items)
    ElMessage.success('已保存')
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    loading.value = false
  }
}
</script>
