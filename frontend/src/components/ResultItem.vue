<template>
  <div class="result-item">
    <span v-if="item.speakerLoading" class="speaker-tag">
      识别中...
      <LoadingOutlined spin />
    </span>
    <span v-else class="speaker-tag" :class="getSpeakerClass(item.speaker)">
      {{ formatSpeaker(item.speaker) }}
    </span>
    <span v-if="!item.speakerLoading" class="time">{{ formatTime(item.start_time) }} - {{ formatTime(item.end_time) }}秒</span>
    <span class="text">{{ item.text }}</span>
  </div>
</template>

<script setup>
import { LoadingOutlined } from '@ant-design/icons-vue'

const props = defineProps({
  item: {
    type: Object,
    required: true
  }
})

function formatSpeaker(speaker) {
  if (!speaker) return '说话人'
  return speaker.replace('SPEAKER_', '说话人')
}

function formatTime(seconds) {
  if (!seconds) return '0.0'
  return seconds.toFixed(1)
}

function getSpeakerClass(speaker) {
  if (!speaker) return 'speaker-1'
  const num = speaker.replace('SPEAKER_', '')
  return `speaker-${num}`
}
</script>

<style scoped>
.result-item {
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.speaker-tag {
  flex-shrink: 0;
  white-space: nowrap;
  font-size: 14px;
}

.time {
  flex-shrink: 0;
  white-space: nowrap;
  font-size: 12px;
  color: #8c8c8c;
}

.text {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}
</style>