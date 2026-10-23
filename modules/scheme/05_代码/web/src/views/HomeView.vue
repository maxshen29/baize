<script setup lang="ts">
const cards = [
  { title: '① 参考结构模板', desc: '可复用的标准章节骨架，零正文，跨项目复用。', to: '/templates' },
  { title: '② 参考文档导入', desc: 'Word/PDF/Markdown 解析、去重、版本管理。', to: '/documents' },
  { title: '③ 知识库检索', desc: '本地嵌入 + 混合检索（FTS + 向量 + 分面）。', to: '/knowledge' },
  { title: '④ 按需撰写', desc: '选模板 → 检索知识 → LLM 生成带引用正文 → 导出。', to: '/writing' },
]
</script>

<template>
  <div>
    <h2>方案撰写平台 · 总览</h2>
    <p style="color: #666">基于 OpenBidKit 成熟范式，固化为「模板 / 文档 / 知识库 / 撰写」四能力平台。</p>
    <el-row :gutter="16">
      <el-col v-for="c in cards" :key="c.to" :span="6">
        <el-card shadow="hover" @click="$router.push(c.to)" style="cursor: pointer">
          <h3>{{ c.title }}</h3>
          <p style="color: #888; min-height: 48px">{{ c.desc }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
