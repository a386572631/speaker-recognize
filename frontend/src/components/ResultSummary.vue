<template>
  <a-card v-if="summary.visible" class="function-card summary-card">
    <template #title>
      <div class="result-title">
        <span>识别汇总</span>
      </div>
    </template>
    <div class="summary-content">
      <div class="summary-grid">
        <div class="summary-item">
          <span class="label">识别结果条数</span>
          <span class="value">{{ summary.totalCount }} 条</span>
        </div>
        <div class="summary-item">
          <span class="label">说话人数</span>
          <span class="value">{{ summary.speakerCount }} 人</span>
        </div>
        <div class="summary-item">
          <span class="label">总时长</span>
          <span class="value">{{ summary.totalDuration }} 秒</span>
        </div>
      </div>
      <div class="speaker-stats">
        <div v-for="(count, speaker) in summary.speakerStats" :key="speaker" class="speaker-stat-item">
          <a-tag color="blue">{{ formatSpeaker(speaker) }}</a-tag>
          <a-tag color="blue">{{ count }} 次</a-tag>
        </div>
      </div>
    </div>
  </a-card>
</template>

<script setup>
defineProps({
  summary: {
    type: Object,
    default: () => ({})
  }
})

function formatSpeaker(speaker) {
  if (!speaker) return '说话人'
  return speaker.replace('SPEAKER_', '说话人')
}
</script>

<style scoped>
.summary-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
}

.summary-item .label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 4px;
}

.summary-item .value {
  font-size: 16px;
  font-weight: 500;
  color: #262626;
}

.speaker-stats {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.speaker-stat-item {
  display: flex;
  gap: 4px;
}
</style>