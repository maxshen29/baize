<template>
  <AcademicTool
    code="academic_grammar"
    tool="grammar"
    label="语法纠错"
    desc="拼写 / 语法 / 标点校对，给出修改对照"
    placeholder="粘贴需要校对的文本（英文 / 中文）…"
  />
</template>

<script setup lang="ts">
import AcademicTool from '@/components/academic/AcademicTool.vue'
</script>
