<template>
  <AcademicTool
    code="academic_translate"
    tool="translate"
    label="中英互译"
    :needs-lang="true"
    desc="学术级中英互译，术语准确、保留格式"
    placeholder="粘贴需要翻译的英文或中文文本…"
  />
</template>

<script setup lang="ts">
import AcademicTool from '@/components/academic/AcademicTool.vue'
</script>
