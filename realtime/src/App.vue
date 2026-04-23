<template>
  <div id="app">
    <PageHeader 
      title="实时语音识别" 
      :subtitle="isRecording ? formatTime(recordingTime) : ''"
    >
      <template #extra>
        <Button type="text" size="small" @click="downloadAudio" title="下载音频" :disabled="audioBuffers.length === 0">
          <DownloadOutlined />
        </Button>
        <Button type="text" size="small" @click="showSettings = true">
          <SettingOutlined />
        </Button>
      </template>
    </PageHeader>

    <TranscriptionList
      :segments="displaySegments"
      :lastSpeaker="lastSpeaker"
      :processing="isProcessing"
    />

    <div class="control-panel">
      <WaveVisualizer :active="isRecording && !isPaused" :listening="isListening" />
      
      <div class="recording-status">
        <span v-if="vadLoading" class="status-text loading">
          模型加载中...
        </span>
        <span v-else-if="isListening" class="status-text listening">
          检测到声音...
        </span>
        <span v-else-if="isRecording && !isPaused" class="status-text recording">
          录音中 {{ formatTime(recordingTime) }}
        </span>
        <span v-else-if="isRecording && isPaused" class="status-text paused">
          已暂停 {{ formatTime(recordingTime) }}
        </span>
        <span v-else-if="isProcessing" class="status-text processing">
          识别中...
        </span>
        <span v-else class="status-text">
          点击开始录音
        </span>
      </div>

      <div class="button-group">
        <Button 
          v-if="isRecording && !isProcessing"
          class="pause-btn" 
          shape="circle"
          @click="togglePause"
        >
          <PauseOutlined v-if="!isPaused" />
          <StepForwardOutlined v-else />
        </Button>

        <RecordingButton
          :isRecording="isRecording"
          :isPaused="isPaused"
          :isProcessing="isProcessing || vadLoading"
          @click="toggleRecording"
        />
      </div>
    </div>

    <Modal
      v-model:open="showSettings"
      title="设置"
      :footer="null"
      :width="320"
    >
      <Form layout="vertical">
        <FormItem label="说话人数">
          <Slider 
            v-model:value="numSpeakerRef" 
            :min="1" 
            :max="5" 
            :marks="{ 1: '1', 2: '2', 3: '3', 4: '4', 5: '5' }"
          />
        </FormItem>
        <FormItem>
          <Button type="primary" block @click="saveSettings">
            确定
          </Button>
        </FormItem>
      </Form>
    </Modal>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { SettingOutlined, PauseOutlined, StepForwardOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { Button, Modal, Form, FormItem, Slider } from 'ant-design-vue'

import PageHeader from './components/PageHeader.vue'
import TranscriptionList from './components/TranscriptionList.vue'
import RecordingButton from './components/RecordingButton.vue'
import WaveVisualizer from './components/WaveVisualizer.vue'
import { useAudioRecorder } from './composables/useAudioRecorder'

const showSettings = ref(false)

const urlParams = new URLSearchParams(window.location.search)
const initialNumSpeaker = parseInt(urlParams.get('num_speaker')) || 2

const numSpeakerRef = ref(initialNumSpeaker)

const {
  isRecording,
  isPaused,
  isProcessing,
  isListening,
  recordingTime,
  transcriptionResults,
  vadLoading,
  audioBuffers,
  lastSpeaker,
  downloadAudio,
  startRecording,
  pauseRecording,
  resumeRecording,
  stopRecording,
  clearResults,
  formatTime,
  formatSpeaker,
  formatSpeakerClass
} = useAudioRecorder(numSpeakerRef)

const displaySegments = ref([])

watch(transcriptionResults, (newResults) => {
  if (newResults && newResults.length > 0) {
    displaySegments.value = newResults
  } else {
    displaySegments.value = []
  }
}, { deep: true })

const toggleRecording = async () => {
  if (isRecording.value) {
    await stopRecording()
  } else {
    displaySegments.value = []
    clearResults()
    await startRecording()
  }
}

const togglePause = () => {
  if (isPaused.value) {
    resumeRecording()
  } else {
    pauseRecording()
  }
}

const saveSettings = () => {
  showSettings.value = false
  const newUrl = `${window.location.pathname}?num_speaker=${numSpeakerRef.value}`
  window.history.replaceState({}, '', newUrl)
}

onMounted(() => {
  if (!urlParams.get('num_speaker')) {
    const newUrl = `${window.location.pathname}?num_speaker=${numSpeakerRef.value}`
    window.history.replaceState({}, '', newUrl)
  }
})
</script>

<style scoped>
#app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--bg-primary);
}

.control-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px 16px;
  background: var(--bg-secondary);
  border-top: 1px solid var(--border-color);
  gap: 16px;
}

.recording-status {
  height: 24px;
  display: flex;
  align-items: center;
}

.status-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.status-text.loading {
  color: #F59E0B;
  font-weight: 500;
}

.status-text.recording {
  color: #EF4444;
  font-weight: 500;
}

.status-text.listening {
  color: #10B981;
  font-weight: 500;
}

.status-text.paused {
  color: #F59E0B;
  font-weight: 500;
}

.status-text.processing {
  color: var(--primary-color);
  font-weight: 500;
}

.button-group {
  display: flex;
  align-items: center;
  gap: 24px;
}

.pause-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>