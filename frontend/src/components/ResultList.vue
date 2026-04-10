<template>
  <a-card v-if="results.length > 0" class="function-card" style="margin-top: 16px;">
    <template #title>
      <div class="result-title">
        <span>识别结果</span>
        <a-tag color="green">{{ results.length }} 条</a-tag>
      </div>
    </template>
    <div class="result-list">
      <ResultItem v-for="(item, index) in results" :key="index" :item="item" />
    </div>
  </a-card>
</template>

<script setup>
import ResultItem from './ResultItem.vue'

defineProps({
  results: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}
</style>