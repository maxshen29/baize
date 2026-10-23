<template>
  <el-drawer :model-value="modelValue" :title="`配置权限 - ${role?.name || ''}`" size="420px" @update:model-value="$emit('update:modelValue', $event)">
    <el-tree
      ref="treeRef"
      :data="treeData"
      show-checkbox
      node-key="id"
      :props="{ label: 'name', children: 'children' }"
      default-expand-all
    />
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSave">保存</el-button>
    </template>
  </el-drawer>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api/rbac'

const props = defineProps<{ modelValue: boolean; role?: any }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()

const treeRef = ref<any>(null)
const treeData = ref<any[]>([])
const allPerms = ref<any[]>([])
const loading = ref(false)

async function loadTree() {
  const res = await api.permissionTree()
  const flat: any[] = []
  const tree: any[] = []
  for (const [mod, perms] of Object.entries(res.data.data)) {
    const children = (perms as any[]).map((p) => ({ id: p.id, name: `${p.name} (${p.code})` }))
    tree.push({ id: `mod-${mod}`, name: mod, children })
    flat.push(...(perms as any[]))
  }
  treeData.value = tree
  allPerms.value = flat
}

watch(
  () => props.modelValue,
  async (open) => {
    if (open && props.role) {
      await loadTree()
      const res = await api.rolePermissions(props.role.id)
      const ids = (res.data.data as any[]).map((p) => p.id)
      treeRef.value?.setCheckedKeys(ids)
    }
  },
)

async function onSave() {
  loading.value = true
  try {
    const ids = treeRef.value?.getCheckedKeys().filter((k: string) => !k.startsWith('mod-')) || []
    await api.setRolePermissions(props.role.id, ids)
    ElMessage.success('已保存')
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    loading.value = false
  }
}
</script>
