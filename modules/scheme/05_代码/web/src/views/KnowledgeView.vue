<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { searchKnowledge, type SearchHit } from '@/api'

const query = ref('')
const domain = ref('')
const applicable = ref('')
const hits = ref<SearchHit[]>([])
const loading = ref(false)

async function run() {
  if (!query.value.trim()) {
    ElMessage.warning('请输入检索内容')
    return
  }
  loading.value = true
  try {
    const res = await searchKnowledge({
      query: query.value,
      domain: domain.value || undefined,
      applicable_template: applicable.value || undefined,
      top_k: 10,
    })
    hits.value = res.hits
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2>知识库检索（混合：FTS + 向量 + 分面）</h2>
    <el-input v-model="query" placeholder="输入要检索的知识点，如：项目总体架构" @keyup.enter="run">
      <template #prepend>查询</template>
      <template #append>
        <el-button @click="run" icon="Search">检索</el-button>
      </template>
    </el-input>
    <div style="margin: 12px 0; display: flex; gap: 12px">
      <el-select v-model="applicable" placeholder="适用模板类型" clearable style="width: 180px">
        <el-option label="投标" value="投标" />
        <el-option label="技术" value="技术" />
        <el-option label="实施" value="实施" />
      </el-select>
      <el-input v-model="domain" placeholder="领域(domain) 过滤" clearable style="width: 200px" />
    </div>

    <el-empty v-if="!hits.length && !loading" description="暂无结果" />
    <el-card v-for="h in hits" :key="h.chunk_id" style="margin-bottom: 12px" v-loading="loading">
      <template #header>
        <div style="display: flex; justify-content: space-between">
          <span>{{ h.document_title }} <el-tag size="small">{{ h.heading_path || '全文' }}</el-tag></span>
          <span style="color: #999">得分 {{ h.score }}</span>
        </div>
      </template>
      <p style="white-space: pre-wrap">{{ h.content }}</p>
      <div>
        <el-tag v-for="k in h.keywords" :key="k" size="small" style="margin-right: 6px">{{ k }}</el-tag>
      </div>
    </el-card>
  </div>
</template>
