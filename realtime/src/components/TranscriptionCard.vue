<template>
  <div class="transcription-card">
    <div class="card-header">
      <SpeakerTag 
        :speaker="segment.speaker" 
        :processing="processing"
      />
      <span class="time-range">
        {{ formatTime(segment.start_time) }} - {{ formatTime(segment.end_time) }}
      </span>
    </div>
    <div class="card-content">
      {{ segment.text || '...' }}
    </div>
    <div v-if="segment.similarity" class="similarity">
      相似度: {{ (segment.similarity * 100).toFixed(1) }}%
    </div>
  </div>
</template>

<script setup>
import SpeakerTag from './SpeakerTag.vue'

defineProps({
  segment: { type: Object, required: true },
  processing: { type: Boolean, default: false }
})

const formatTime = (ms) => {
  if (!ms && ms !== 0) return '--:--'
  const totalSeconds = Math.floor(ms / 1000)
  const mins = Math.floor(totalSeconds / 60)
  const secs = totalSeconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.transcription-card {
  background: var(--ai-bubble-bg);
  border: 1px solid var(--ai-bubble-border);
  border-radius: var(--radius-md);
  padding: 12px;
  margin-bottom: 8px;
  animation: fadeIn 0.3s ease;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.time-range {
  font-size: 12px;
  color: var(--text-tertiary);
}

.card-content {
  font-size: 15px;
  color: var(--text-primary);
  line-height: 1.6;
}

.similarity {
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-secondary);
}
</style>