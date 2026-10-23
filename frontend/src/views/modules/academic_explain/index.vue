<template>
  <AcademicTool
    code="academic_explain"
    tool="explain"
    label="概念讲解"
    desc="通俗 + 严谨地讲解专业概念或公式"
    placeholder="输入一个专业概念或公式，例如：Transformer 的自注意力机制"
  />
</template>

<script setup lang="ts">
import AcademicTool from '@/components/academic/AcademicTool.vue'
</script>
