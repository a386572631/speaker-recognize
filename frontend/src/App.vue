<template>
  <div class="app-container">
    <div class="header-setting">
      <SettingOutlined class="setting-icon" @click="showSettings = true" />
    </div>
    <div class="main-content">
      <a-card class="function-card transcribe-card">
        <div class="transcribe-section">
          <MicButton :is-recording="isRecording" :is-paused="isPaused" @click="handleMicClick" />
          
          <div class="record-hint">
            <span v-if="isPaused">已暂停，点击继续</span>
            <span v-else-if="isRecording">录音中...</span>
            <span v-else>点击开始录音</span>
          </div>
          
          <div class="vad-status" :class="statusClass" :style="{ opacity: vadStatus ? 1 : 0 }">
            {{ vadStatus }}
          </div>
          
          <div class="vad-status initializing" :style="{ opacity: isInitializing ? 1 : 0 }">
            <LoadingOutlined spin /> VAD初始化中...
          </div>
          
          <div class="button-row">
            <a-button 
              v-if="isRecording || isPaused"
              type="primary"
              danger
              size="large"
              @click="onStopRecording"
            >
              <StopOutlined /> 停止
            </a-button>
            <a-button 
              v-if="isRecording && !isPaused"
              size="large"
              @click="onPauseRecording"
            >
              <PauseOutlined /> 暂停
            </a-button>
            <a-button 
              v-if="isPaused"
              type="primary"
              size="large"
              @click="onResumeRecording"
            >
              <CaretRightOutlined /> 继续
            </a-button>
            <a-button 
              :disabled="!fullRecordedBlob"
              size="large"
              @click="downloadAudio"
            >
              <DownloadOutlined /> 录音下载
            </a-button>
          </div>
        </div>
      </a-card>

      <ResultList :results="results" />

      <ResultSummary :summary="summary" />
    </div>

    <div v-if="isRecognizing" class="recognizing-bar">
      识别中<span class="dots">...</span>
    </div>

    <a-modal
      v-model:open="showSettings"
      title="设置"
      :footer="null"
      @ok="showSettings = false"
    >
      <div class="setting-item">
        <span class="setting-label">说话人人数：</span>
        <a-slider v-model:value="numSpeakerSetting" :min="1" :max="5" :marks="{1:'1',2:'2',3:'3',4:'4',5:'5'}" />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { 
  DownloadOutlined,
  StopOutlined,
  PauseOutlined,
  CaretRightOutlined,
  LoadingOutlined,
  SettingOutlined
} from '@ant-design/icons-vue'
import MicButton from './components/MicButton.vue'
import ResultList from './components/ResultList.vue'
import ResultSummary from './components/ResultSummary.vue'
import { mergeAudioSegments, float32ArrayToWav } from './utils/audio'

const results = ref([])
const isRecording = ref(false)
const isPaused = ref(false)
const isInitializing = ref(false)
const vadStatus = ref('')
const statusClass = ref('')
const loading = ref(false)
const isRecognizing = ref(false)
const recordedBlob = ref(null)
const fullRecordedBlob = ref(null)
const audioSegments = ref([])
const fullAudioSegments = ref([])
const pendingTranscripts = ref([])
const transcriptTimer = ref(null)
const MAX_TRANSCRIPT_INTERVAL = 2000
const showSettings = ref(false)
const numSpeakerSetting = ref(2)

const summary = ref({
  visible: false,
  totalCount: 0,
  speakerCount: 0,
  totalDuration: 0,
  speakerStats: {}
})

const isDev = import.meta.env.MODE === 'development'
const API_KEY = 'wfy-9CmPH8HQ1jtGxcAC5PJxF7N9Z6teRZTM'
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const API_BASE_WS = import.meta.env.VITE_API_BASE_WS
const HTTPS_URL = isDev ? `/api/stt/speaker` : `${API_BASE_URL}/stt/speaker`
const WSS_URL = `${API_BASE_WS}/stt/speaker/ws`

let vadInstance = null
let ws = null

function getBaseUrl() {
  return HTTPS_URL
}

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

function startTranscriptTimer() {
  if (transcriptTimer.value) return
  
  transcriptTimer.value = setInterval(async () => {
    if (audioSegments.value.length === 0) return
    
    const mergedAudio = mergeAudioSegments(audioSegments.value)
    if (!mergedAudio || mergedAudio.length === 0) return
    
    const wavBlob = await float32ArrayToWav(mergedAudio)
    const arrayBuffer = await wavBlob.arrayBuffer()
    const base64Audio = btoa(
      new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    )
    
    try {
      const result = await sendViaWebSocket(base64Audio, false)
      if (Array.isArray(result) && result.length > 0) {
        pendingTranscripts.value.push(...result)
      }
    } catch (e) {
      console.error('Transcription error:', e)
    }
  }, MAX_TRANSCRIPT_INTERVAL)
}

function stopTranscriptTimer() {
  if (transcriptTimer.value) {
    clearInterval(transcriptTimer.value)
    transcriptTimer.value = null
  }
}

function createWebSocket() {
  return new Promise((resolve, reject) => {
    const socket = new WebSocket(WSS_URL)
    
    socket.onopen = () => {
      socket.send(`Authorization: Bearer ${API_KEY}`)
      resolve(socket)
    }
    
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWsMessage(data)
      } catch (e) {
        console.error('Parse error:', e)
      }
    }
    
    socket.onerror = (e) => {
      reject(e)
    }
    
    socket.onclose = () => {
      ws = null
    }
  })
}

function handleWsMessage(data) {
  if (data.status) {
    vadStatus.value = data.status
  }
  if (data.result) {
    loading.value = false
    const result = data.result
    if (Array.isArray(result) && result.length > 0) {
      const lastItem = result[result.length - 1]
      const newResult = {
        ...lastItem,
        speaker: '识别中',
        speakerLoading: true
      }
      results.value.push(newResult)
      identifySpeaker(results.value.length - 1)
    }
  }
  if (data.error) {
    loading.value = false
    isRecognizing.value = false
    vadStatus.value = '识别失败: ' + data.error
    statusClass.value = 'error'
    setTimeout(() => { vadStatus.value = '' }, 3000)
  }
}

async function identifySpeaker(index) {
  if (index < 0 || index >= results.value.length) return
  
  if (!fullRecordedBlob.value) {
    results.value[index].speakerLoading = false
    results.value[index].speaker = '说话人1'
    return
  }
  
  try {
    const formData = new FormData()
    formData.append('file', fullRecordedBlob.value, 'audio.wav')
    formData.append('num_speaker', numSpeakerSetting.value)
    
    const response = await fetch(`${getBaseUrl()}/transcribe`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`
      },
      body: formData
    })
    
    if (response.ok) {
      const data = await response.json()
      
      let httpTotalEndTime = 0
      if (data.segments && data.segments.length > 0) {
        httpTotalEndTime = data.segments[data.segments.length - 1].end_time
      }
      
      if (httpTotalEndTime > 0) {
        const wsStartTime = results.value[index].start_time ?? 0
        const wsEndTime = results.value[index].end_time ?? 0
        const wsDuration = wsEndTime - wsStartTime
        
        results.value[index].start_time = httpTotalEndTime - wsDuration
        results.value[index].end_time = httpTotalEndTime
      }
      
      if (data.last_speaker) {
        results.value[index].speaker = data.last_speaker
      }
    }
  } catch (error) {
    console.error('Speaker identification error:', error)
    vadStatus.value = '说话人识别失败'
    statusClass.value = 'error'
  } finally {
    results.value[index].speakerLoading = false
    isRecognizing.value = false
    vadStatus.value = ''
    statusClass.value = ''
  }
}

async function sendViaWebSocket(base64Audio, isFinal = false) {
  return new Promise((resolve, reject) => {
    let timeoutId = setTimeout(() => {
      if (ws) {
        ws.close()
        ws = null
      }
      reject(new Error('识别超时，服务端未响应'))
    }, 60000)
    
    createWebSocket().then(socket => {
      ws = socket
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          
          if (data.status === 'connected') {
            socket.send(JSON.stringify({
              type: 'transcribe',
              audio: base64Audio,
              isFinal: isFinal
            }))
            vadStatus.value = '正在识别...'
            statusClass.value = ''
          } else if (data.result) {
            clearTimeout(timeoutId)
            socket.close()
            resolve(data.result)
          } else if (data.error) {
            clearTimeout(timeoutId)
            socket.close()
            reject(new Error(data.error))
          } else if (data.status && data.status !== 'connected') {
            vadStatus.value = data.status
          }
        } catch (e) {
          console.error('Parse error:', e)
        }
      }
    }).catch(reject)
  })
}

async function initVAD() {
  try {
    isInitializing.value = true
    vadStatus.value = '初始化VAD...'
    statusClass.value = ''

    if (typeof window !== 'undefined' && !window.ort) {
      await new Promise((resolve, reject) => {
        const script = document.createElement('script')
        script.src = 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/ort.js'
        script.onload = () => resolve()
        script.onerror = () => reject(new Error('onnxruntime-web加载失败'))
        document.head.appendChild(script)
      })
    }

    const { MicVAD } = await import('@ricky0123/vad-web')
    
    vadInstance = await MicVAD.new({
      onSpeechStart: () => {
        vadStatus.value = '检测到语音'
        statusClass.value = 'info'
        startTranscriptTimer()
      },
      onSpeechEnd: async (audio) => {
        clearInterval(transcriptTimer.value)
        transcriptTimer.value = null
        
        vadStatus.value = '语音结束，正在识别...'
        statusClass.value = 'processing'
        isRecognizing.value = true
        
        if (audio && audio.length > 0) {
          audioSegments.value.push(audio)
          fullAudioSegments.value.push(audio)
          
          const mergedAudio = mergeAudioSegments(audioSegments.value)
          const fullMergedAudio = mergeAudioSegments(fullAudioSegments.value)
          
          if (mergedAudio && mergedAudio.length > 0) {
            const wavBlob = await float32ArrayToWav(mergedAudio)
            recordedBlob.value = wavBlob
            
            if (fullMergedAudio && fullMergedAudio.length > 0) {
              const fullWavBlob = await float32ArrayToWav(fullMergedAudio)
              fullRecordedBlob.value = fullWavBlob
            }
            
            await transcribeCurrentAudio()
            
            audioSegments.value = []
          }
        }
        
        setTimeout(() => {
          if (!isRecording.value) {
            vadStatus.value = ''
          }
        }, 2000)
      },
      onVADMisfire: () => {},
      positiveSpeechThreshold: 0.5,
      negativeSpeechThreshold: 0.3,
      redemptionFrames: 8,
      preSpeechPadFrames: 10,
      minSpeechFrames: 8,
      frameSamples: 512,
      onnxWASMBasePath: 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/',
      baseAssetPath: 'https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.30/dist/'
    })
    
    isInitializing.value = false
    vadStatus.value = ''
    message.success('VAD初始化成功')
    return true
  } catch (error) {
    console.error('VAD初始化失败:', error)
    isInitializing.value = false
    vadStatus.value = 'VAD初始化失败'
    statusClass.value = 'error'
    message.error('VAD初始化失败: ' + error.message)
    return false
  }
}

async function transcribeCurrentAudio() {
  let result = null
  let wsFinalResult = null

  if (recordedBlob.value) {
    const audioSize = recordedBlob.value.size
    if (audioSize < 1000) return

    loading.value = true
    const arrayBuffer = await recordedBlob.value.arrayBuffer()
    const base64Audio = btoa(
      new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    )
    wsFinalResult = await sendViaWebSocket(base64Audio, true)
    loading.value = false
  }

  if (pendingTranscripts.value.length > 0 && wsFinalResult?.length > 0) {
    result = [...pendingTranscripts.value, ...wsFinalResult]
    pendingTranscripts.value = []
  } else if (wsFinalResult?.length > 0) {
    result = wsFinalResult
  } else if (pendingTranscripts.value.length > 0) {
    result = pendingTranscripts.value
    pendingTranscripts.value = []
  }

  if (!result || result.length === 0) return

  try {
    const httpTotalEndTime = result[result.length - 1].end_time || 0

    const adjustedResult = result.map((r, idx) => {
      const startTime = r.start_time ?? 0
      const endTime = r.end_time ?? 0
      if (idx === result.length - 1) {
        return { ...r, start_time: startTime, end_time: httpTotalEndTime }
      }
      let nextResult = result[idx + 1]
      let nextStartTime = nextResult?.start_time ?? 0
      let nextEndTime = nextResult?.end_time ?? 0
      let nextDuration = nextEndTime - nextStartTime
      return {
        ...r,
        start_time: startTime,
        end_time: nextEndTime
      }
    })

    const mergedText = adjustedResult.map(r => r.text).join('')
    const mergedStartTime = adjustedResult[0]?.start_time ?? 0
    const mergedEndTime = adjustedResult[adjustedResult.length - 1]?.end_time ?? httpTotalEndTime

    const newItem = {
      text: mergedText,
      start_time: mergedStartTime,
      end_time: mergedEndTime,
      speaker: '识别中',
      speakerLoading: true
    }
    results.value.push(newItem)
    
    vadStatus.value = '识别完成正在识别说话人...'
    statusClass.value = 'success'
    
    identifySpeaker(results.value.length - 1)
  } catch (error) {
    vadStatus.value = '识别失败: ' + error.message
    statusClass.value = 'error'
    isRecognizing.value = false
  }
    loading.value = false
  }


async function handleMicClick() {
  if (!isRecording.value) {
    await onStartRecording()
  }
}

async function onStartRecording() {
  if (!vadInstance) {
    const vadSuccess = await initVAD()
    if (!vadSuccess) return
  }
  
  vadInstance.start()
  isRecording.value = true
  isPaused.value = false
  vadStatus.value = '录音中...'
  statusClass.value = 'info'
  results.value = []
  summary.value = { visible: false, totalCount: 0, speakerCount: 0, totalDuration: 0, speakerStats: {} }
  audioSegments.value = []
  fullAudioSegments.value = []
  recordedBlob.value = null
  fullRecordedBlob.value = null
  pendingTranscripts.value = []
  message.success('开始录音')
}

function onPauseRecording() {
  isPaused.value = true
  stopTranscriptTimer()
  
  if (vadInstance) {
    vadInstance.pause()
  }
  
  vadStatus.value = '已暂停'
  statusClass.value = ''
  message.info('录音已暂停')
}

async function onResumeRecording() {
  if (vadInstance) {
    vadInstance.start()
  }
  
  isPaused.value = false
  isRecording.value = true
  pendingTranscripts.value = []
  vadStatus.value = '录音中...'
  statusClass.value = 'info'
  startTranscriptTimer()
  message.success('继续录音')
}

function onStopRecording() {
  isRecording.value = false
  isPaused.value = false
  
  stopTranscriptTimer()
  
  if (vadInstance) {
    vadInstance.pause()
  }
  
  calculateSummary()
  
  audioSegments.value = []
  pendingTranscripts.value = []
  vadStatus.value = ''
  statusClass.value = ''
  message.success('录音已停止')
}

function calculateSummary() {
  if (results.value.length === 0) return
  
  const speakers = new Set(results.value.map(r => r.speaker))
  const speakerStats = {}
  
  for (const result of results.value) {
    const speaker = result.speaker
    speakerStats[speaker] = (speakerStats[speaker] || 0) + 1
  }
  
  let totalDuration = 0
  for (const result of results.value) {
    if (result.end_time && result.start_time) {
      totalDuration = Math.max(totalDuration, result.end_time)
    }
  }
  
  summary.value = {
    visible: true,
    totalCount: results.value.length,
    speakerCount: speakers.size,
    totalDuration: totalDuration.toFixed(1),
    speakerStats
  }
}

function downloadAudio() {
  if (!fullRecordedBlob.value) {
    message.warning('没有可下载的音频')
    return
  }
  
  const url = URL.createObjectURL(fullRecordedBlob.value)
  const a = document.createElement('a')
  a.href = url
  a.download = `recording_${Date.now()}.wav`
  a.click()
  URL.revokeObjectURL(url)
  message.success('音频已下载')
}

onUnmounted(() => {
  if (vadInstance) {
    vadInstance.pause()
    vadInstance.destroy()
    vadInstance = null
  }
  if (ws) {
    ws.close()
    ws = null
  }
  audioSegments.value = []
  fullAudioSegments.value = []
  isRecording.value = false
  isPaused.value = false
})
</script>

<style scoped>
.app-container {
  min-height: 100vh;
  background: #f0f2f5;
  padding: 20px;
}

.header-setting {
  max-width: 600px;
  margin: 0 auto 16px;
  display: flex;
  justify-content: flex-end;
}

.setting-icon {
  font-size: 20px;
  cursor: pointer;
  color: #595959;
  padding: 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.setting-icon:hover {
  color: #1890ff;
  background: #f0f0f0;
}

.setting-item {
  padding: 8px 0;
}

.setting-label {
  font-size: 14px;
  color: #595959;
}

.main-content {
  max-width: 600px;
  margin: 0 auto;
}

.function-card {
  background: #fff !important;
  border: 1px solid #f0f0f0 !important;
  border-radius: 12px !important;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.function-card :deep(.ant-card-head) {
  border-bottom: 1px solid #f0f0f0;
  color: #262626;
}

.function-card :deep(.ant-card-body) {
  color: #262626;
}

.transcribe-card :deep(.ant-card-body) {
  padding: 16px !important;
}

.transcribe-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  position: relative;
}

.mic-wrapper {
  position: relative;
}

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

.record-hint {
  font-size: 14px;
  color: #8c8c8c;
}

.vad-status {
  min-height: 37px;
  line-height: 20px;
  padding: 8px 16px;
  box-sizing: border-box;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
}

.vad-status.info {
  background: #e6f7ff;
  color: #1890ff;
  border-color: #91d5ff;
}

.vad-status.processing {
  background: #fffbe6;
  color: #faad14;
  border-color: #ffe58f;
}

.vad-status.success {
  background: #f6ffed;
  color: #52c41a;
  border-color: #b7eb8f;
}

.vad-status.error {
  background: #fff1f0;
  color: #ff4d4f;
  border-color: #ffccc7;
}

.vad-status.initializing {
  background: #fffbe6;
  color: #faad14;
  border-color: #ffe58f;
}

.button-row {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 0 0 8px 8px;
  margin: 0 -16px -16px -16px;
}

.button-row :deep(.ant-btn) {
  background: #fff;
  border: 1px solid #d9d9d9;
  color: #595959;
}

.button-row :deep(.ant-btn:hover) {
  background: #fff;
  border-color: #1890ff;
  color: #1890ff;
}

.button-row :deep(.ant-btn-primary) {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.button-row :deep(.ant-btn-danger) {
  background: #ff4d4f;
  border-color: #ff4d4f;
  color: #fff;
}

.function-card + .function-card {
  margin-top: 16px;
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

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
}

.text {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.result-item:first-child {
  margin-top: 12px;
}

.result-item.recognizing {
  background: #e6f7ff;
  border: 1px solid #91d5ff;
}

.result-item.recognizing .speaker-tag {
  background: #1890ff;
}

.result-item.recognizing .dots {
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}

.recognizing-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 12px;
  background: #e6f7ff;
  border-radius: 8px;
  margin-top: 16px;
  color: #1890ff;
  font-size: 14px;
}

.recognizing-bar .dots {
  display: inline-block;
  animation: dots 1.5s infinite;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}
</style>