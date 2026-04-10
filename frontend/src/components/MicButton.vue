<template>
  <div class="mic-button" :class="{ recording: isRecording, paused: isPaused }" @click="$emit('click')">
    <AudioOutlined v-if="!isRecording || isPaused" class="mic-icon" />
    <SoundOutlined v-else class="mic-icon recording-icon" />
  </div>
</template>

<script setup>
import { AudioOutlined, SoundOutlined } from '@ant-design/icons-vue'

defineProps({
  isRecording: Boolean,
  isPaused: Boolean
})

defineEmits(['click'])
</script>

<style scoped>
.mic-button {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1890ff 0%, #096dd9 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 16px rgba(24, 144, 255, 0.3);
}

.mic-button:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 20px rgba(24, 144, 255, 0.4);
}

.mic-button.recording {
  background: linear-gradient(135deg, #ff4d4f 0%, #cf1322 100%);
  box-shadow: 0 4px 16px rgba(255, 77, 79, 0.3);
  animation: pulse 2s infinite;
}

.mic-button.paused {
  background: linear-gradient(135deg, #8c8c8c 0%, #595959 100%);
  box-shadow: 0 4px 16px rgba(140, 140, 140, 0.3);
}

@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.5); }
  50% { box-shadow: 0 0 0 20px rgba(255, 77, 79, 0); }
}

.mic-icon {
  font-size: 48px;
  color: white;
}

.recording-icon {
  animation: blink 1s infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>