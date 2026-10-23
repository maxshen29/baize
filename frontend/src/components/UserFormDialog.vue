<template>
  <el-dialog :model-value="modelValue" :title="edit ? '编辑用户' : '新建用户'" @update:model-value="$emit('update:modelValue', $event)" @open="sync">
    <el-form :model="form" label-width="80px">
      <el-form-item label="用户名">
        <el-input v-model="form.username" :disabled="!!edit" />
      </el-form-item>
      <el-form-item label="昵称">
        <el-input v-model="form.display_name" />
      </el-form-item>
      <el-form-item label="邮箱">
        <el-input v-model="form.email" />
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="form.password" type="password" placeholder="留空则不修改" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="$emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" :loading="loading" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import * as api from '@/api/users'

const props = defineProps<{ modelValue: boolean; edit?: any }>()
const emit = defineEmits<{ (e: 'update:modelValue', v: boolean): void; (e: 'saved'): void }>()
const form = reactive({ username: '', display_name: '', email: '', password: '' })
const loading = ref(false)

function sync() {
  if (props.edit) {
    form.username = props.edit.username
    form.display_name = props.edit.display_name || ''
    form.email = props.edit.email || ''
    form.password = ''
  } else {
    form.username = ''
    form.display_name = ''
    form.email = ''
    form.password = ''
  }
}
async function onSave() {
  loading.value = true
  try {
    if (props.edit) {
      const body: any = { display_name: form.display_name, email: form.email }
      if (form.password) body.password = form.password
      await api.updateUser(props.edit.id, body)
    } else {
      await api.createUser({ username: form.username, display_name: form.display_name, email: form.email, password: form.password })
    }
    ElMessage.success('已保存')
    emit('update:modelValue', false)
    emit('saved')
  } finally {
    loading.value = false
  }
}
</script>
