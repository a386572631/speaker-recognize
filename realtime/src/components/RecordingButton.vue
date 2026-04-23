<template>
  <button 
    class="recording-button"
    :class="{ 'recording': isRecording && !isPaused, 'paused': isPaused, 'processing': isProcessing }"
    :disabled="isProcessing"
    @click="handleClick"
  >
    <span v-if="isProcessing" class="loading-icon">
      <LoadingOutlined />
    </span>
    <span v-else-if="isRecording" class="stop-icon">
      <svg viewBox="0 0 24 24" width="24" height="24">
        <rect x="6" y="6" width="12" height="12" fill="currentColor" rx="2" />
      </svg>
    </span>
    <span v-else class="mic-icon">
      <svg viewBox="0 0 24 24" width="24" height="24">
        <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z" fill="currentColor"/>
        <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z" fill="currentColor"/>
      </svg>
    </span>
  </button>
</template>

<script setup>
import { LoadingOutlined } from '@ant-design/icons-vue'

defineProps({
  isRecording: { type: Boolean, default: false },
  isPaused: { type: Boolean, default: false },
  isProcessing: { type: Boolean, default: false }
})

const emit = defineEmits(['click'])

const handleClick = () => {
  emit('click')
}
</script>

<style scoped>
.recording-button {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
  background: var(--primary-color);
  color: var(--text-on-primary);
  box-shadow: var(--shadow-primary);
}

.recording-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.recording {
  background: #EF4444;
  animation: recording-pulse 1s ease-in-out infinite;
}

.paused {
  background: #F59E0B;
}

.processing {
  background: var(--primary-color);
}

.mic-icon, .stop-icon, .loading-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.loading-icon {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>