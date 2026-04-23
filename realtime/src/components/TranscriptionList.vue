<template>
  <div class="transcription-list">
    <Empty v-if="segments.length === 0 && !processing" description="点击下方按钮开始录音" />
    <div v-else class="list-content">
      <TranscriptionCard
        v-for="(segment, index) in segments"
        :key="index"
        :segment="segment"
        :processing="false"
      />
      <div v-if="processing" class="processing-indicator">
        <SpeakerTag :speaker="lastSpeaker" :processing="true" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { Empty } from 'ant-design-vue'
import TranscriptionCard from './TranscriptionCard.vue'
import SpeakerTag from './SpeakerTag.vue'

defineProps({
  segments: { type: Array, default: () => [] },
  lastSpeaker: { type: String, default: '' },
  processing: { type: Boolean, default: false }
})
</script>

<style scoped>
.transcription-list {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.list-content {
  display: flex;
  flex-direction: column;
}

.processing-indicator {
  display: flex;
  justify-content: center;
  padding: 16px;
}
</style>