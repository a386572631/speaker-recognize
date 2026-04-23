<template>
  <div v-if="active || listening" class="wave-visualizer">
    <span 
      v-for="i in 5" 
      :key="i" 
      class="wave-bar"
      :class="{ listening: listening }"
      :style="{ animationDelay: `${i * 0.1}s` }"
    ></span>
  </div>
</template>

<script setup>
defineProps({
  active: { type: Boolean, default: false },
  listening: { type: Boolean, default: false }
})
</script>

<style scoped>
.wave-visualizer {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 32px;
}

.wave-bar {
  width: 4px;
  height: 4px;
  background: var(--primary-color);
  border-radius: 2px;
  animation: wave 0.8s ease-in-out infinite;
}

.wave-bar.listening {
  background: #10B981;
}

@keyframes wave {
  0%, 100% { 
    height: 4px; 
    opacity: 0.4;
  }
  50% { 
    height: 24px; 
    opacity: 1;
  }
}
</style>