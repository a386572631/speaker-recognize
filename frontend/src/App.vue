<template>
  <div class="app-container">
    <div class="main-content">
      <a-card class="function-card transcribe-card">
        <div class="transcribe-section">
          <div class="mic-wrapper">
            <div 
              class="mic-button"
              :class="{ 
                recording: isRecording,
                paused: isPaused
              }"
              @click="handleMicClick"
            >
              <AudioOutlined v-if="!isRecording || isPaused" class="mic-icon" />
              <SoundOutlined v-else class="mic-icon recording-icon" />
            </div>
          </div>
          
          <div class="record-hint">
            <span v-if="isPaused">已暂停，点击继续</span>
            <span v-else-if="isRecording">录音中...</span>
            <span v-else>点击开始录音</span>
          </div>
          
          <div v-if="vadStatus" class="vad-status" :class="statusClass">
            {{ vadStatus }}
          </div>
          
          <div v-if="isInitializing" class="vad-status initializing">
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

      <a-card v-if="results.length > 0" class="function-card" style="margin-top: 16px;">
        <template #title>
          <div class="result-title">
            <span>识别结果</span>
            <a-tag color="green">{{ results.length }} 条</a-tag>
          </div>
        </template>
        <div class="result-list">
          <div 
            v-for="(item, index) in results" 
            :key="index"
            class="result-item"
          >
            <div class="result-header">
              <span class="speaker-tag" :class="getSpeakerClass(item.speaker)">
                {{ formatSpeaker(item.speaker) }}
                <span v-if="item.speakerLoading" class="speaker-loading">
                  <LoadingOutlined spin />
                </span>
              </span>
              <span class="time">{{ formatTime(item.start_time) }} - {{ formatTime(item.end_time) }}秒</span>
            </div>
            <div class="text">{{ item.text }}</div>
          </div>
          
          </div>
      </a-card>

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
            <div 
              v-for="(count, speaker) in summary.speakerStats" 
              :key="speaker" 
              class="speaker-stat-item"
            >
              <a-tag color="blue">{{ formatSpeaker(speaker) }}</a-tag>
              <a-tag color="blue">{{ count }} 次</a-tag>
            </div>
          </div>
        </div>
      </a-card>
    </div>

    <div v-if="isRecognizing" class="recognizing-bar">
      识别中<span class="dots">...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { 
  AudioOutlined, 
  SoundOutlined,
  DownloadOutlined,
  StopOutlined,
  PauseOutlined,
  CaretRightOutlined,
  LoadingOutlined
} from '@ant-design/icons-vue'

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

const summary = ref({
  visible: false,
  totalCount: 0,
  speakerCount: 0,
  totalDuration: 0,
  speakerStats: {}
})

const API_KEY = 'wfy-9CmPH8HQ1jtGxcAC5PJxF7N9Z6teRZTM'
const API_HOST = import.meta.env.VITE_API_HOST || '10.104.60.38'
const API_PORT = import.meta.env.VITE_API_PORT || '5062'
const WS_URL = `ws://${API_HOST}:${API_PORT}/ws`
const WSS_URL = `wss://${API_HOST}:${API_PORT}/ws`
const HTTP_URL = `http://${API_HOST}:${API_PORT}`
const HTTPS_URL = `https://${API_HOST}:${API_PORT}`

let vadInstance = null
let ws = null

function getBaseUrl() {
  const protocol = window.location.protocol
  return protocol === 'https:' ? HTTPS_URL : HTTP_URL
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

async function mergeAudioSegments(segments) {
  if (!segments || segments.length === 0) return null
  
  const totalLength = segments.reduce((sum, seg) => sum + seg.length, 0)
  const separatorLength = Math.floor(16000 * 0.5)
  const merged = new Float32Array(totalLength + separatorLength * (segments.length - 1))
  
  let offset = 0
  for (let i = 0; i < segments.length; i++) {
    merged.set(segments[i], offset)
    offset += segments[i].length
    if (i < segments.length - 1) {
      for (let j = 0; j < separatorLength; j++) {
        merged[offset + j] = 0
      }
      offset += separatorLength
    }
  }
  
  return merged
}

function createWebSocket() {
  return new Promise((resolve, reject) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${API_HOST}:${API_PORT}/ws`
    const socket = new WebSocket(wsUrl)
    
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
    
    const response = await fetch(`${getBaseUrl()}/transcribe`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${API_KEY}`
      },
      body: formData
    })
    
    if (response.ok) {
      const data = await response.json()
      if (data.results && data.results.length > 0) {
        results.value[index] = data.results[data.results.length - 1]
      } else if (data.last_speaker) {
        results.value[index].speaker = data.last_speaker
      }
    }
  } catch (error) {
    console.error('Speaker identification error:', error)
  } finally {
    results.value[index].speakerLoading = false
    isRecognizing.value = false
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

async function float32ArrayToWav(float32Array, sampleRate = 16000) {
  const wavHeader = createWavHeader(float32Array.length, sampleRate)
  const wavData = new Uint8Array(wavHeader.length + float32Array.length * 2)
  
  wavData.set(wavHeader, 0)
  
  let offset = wavHeader.length
  for (let i = 0; i < float32Array.length; i++) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]))
    const intSample = sample < 0 ? sample * 32768 : sample * 32767
    wavData[offset] = intSample & 0xff
    wavData[offset + 1] = (intSample >> 8) & 0xff
    offset += 2
  }
  
  return new Blob([wavData], { type: 'audio/wav' })
}

function createWavHeader(numSamples, sampleRate) {
  const buffer = new ArrayBuffer(44)
  const view = new DataView(buffer)
  
  view.setUint8(0, 0x52)
  view.setUint8(1, 0x49)
  view.setUint8(2, 0x46)
  view.setUint8(3, 0x46)
  view.setUint32(4, 36 + numSamples * 2, true)
  view.setUint8(8, 0x57)
  view.setUint8(9, 0x41)
  view.setUint8(10, 0x56)
  view.setUint8(11, 0x45)
  view.setUint8(12, 0x66)
  view.setUint8(13, 0x6D)
  view.setUint8(14, 0x74)
  view.setUint8(15, 0x20)
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  view.setUint8(36, 0x64)
  view.setUint8(37, 0x61)
  view.setUint8(38, 0x74)
  view.setUint8(39, 0x61)
  view.setUint32(40, numSamples * 2, true)
  
  return new Uint8Array(buffer)
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
      },
      onSpeechEnd: async (audio) => {
        vadStatus.value = '语音结束，正在识别...'
        statusClass.value = 'processing'
        isRecognizing.value = true
        
        if (audio && audio.length > 0) {
          audioSegments.value.push(audio)
          fullAudioSegments.value.push(audio)
          
          const mergedAudio = await mergeAudioSegments(audioSegments.value)
          const fullMergedAudio = await mergeAudioSegments(fullAudioSegments.value)
          
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
  if (!recordedBlob.value) return

  const audioSize = recordedBlob.value.size
  if (audioSize < 1000) return

  try {
    loading.value = true

    const arrayBuffer = await recordedBlob.value.arrayBuffer()
    const base64Audio = btoa(
      new Uint8Array(arrayBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    )

    const result = await sendViaWebSocket(base64Audio, false)
    
    if (Array.isArray(result) && result.length > 0) {
      const lastResult = result[result.length - 1]
      const newItem = {
        ...lastResult,
        speaker: '识别中',
        speakerLoading: true
      }
      results.value.push(newItem)
      
      vadStatus.value = '识别完成，正在识别说话人...'
      statusClass.value = 'success'
      
      identifySpeaker(results.value.length - 1)
    }
  } catch (error) {
    vadStatus.value = '识别失败: ' + error.message
    statusClass.value = 'error'
    isRecognizing.value = false
  } finally {
    loading.value = false
  }
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
  message.success('开始录音')
}

function onPauseRecording() {
  isPaused.value = true
  
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
  vadStatus.value = '录音中...'
  statusClass.value = 'info'
  message.success('继续录音')
}

function onStopRecording() {
  isRecording.value = false
  isPaused.value = false
  
  if (vadInstance) {
    vadInstance.pause()
  }
  
  calculateSummary()
  
  audioSegments.value = []
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
  padding: 40px 24px;
}

.transcribe-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  position: relative;
  padding-bottom: 60px;
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
  padding: 8px 16px;
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
  margin: 0 -24px -24px -24px;
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
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
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