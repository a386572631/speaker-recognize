<template>
  <span 
    class="speaker-tag"
    :class="{ 'speaker-tag-processing': processing }"
  >
    <slot>{{ displayText }}</slot>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  speaker: { type: String, default: '' },
  processing: { type: Boolean, default: false },
  numSpeaker: { type: Number, default: 2 }
})

const displayText = computed(() => {
  if (props.processing) return '识别中'
  if (!props.speaker) return '等待说话'
  return props.speaker
})

const getSpeakerNum = () => {
  if (!props.speaker) return 0
  const match = props.speaker.match(/说话人(\d+)/)
  return match ? parseInt(match[1]) : 0
}
</script>

<style scoped>
.speaker-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.speaker-tag-processing {
  color: var(--primary-color);
  border-color: var(--primary-color);
}
</style>