import { ref, onUnmounted, toValue } from 'vue'
import axios from 'axios'
import { MicVAD } from '@ricky0123/vad-web'

const API_KEY = import.meta.env.VITE_API_KEY
const WS_HOST = import.meta.env.VITE_WS_HOST || 'wss://wsyy.wzhospital.cn:8443'
const API_HOST = import.meta.env.VITE_API_HOST || 'https://wsyy.wzhospital.cn:8443'

const apiClient = axios.create({
  baseURL: import.meta.env.MODE === 'development' ? '/api' : API_HOST,
  timeout: 30000,
  headers: { 'Authorization': `Bearer ${API_KEY}` }
})

export function useAudioRecorder(numSpeaker) {
  const isRecording = ref(false)
  const isPaused = ref(false)
  const isProcessing = ref(false)
  const isListening = ref(false)
  const recordingTime = ref(0)
  const lastSpeaker = ref('')
  const transcriptionResults = ref([])
  const pendingTranscripts = ref([])
  const ws = ref(null)
  const wsConnected = ref(false)
  const vad = ref(null)
  const vadLoading = ref(false)
  const timer = ref(null)
  const audioBuffers = ref([])
  const pendingAudioChunks = ref([])
  const combinedAudioChunks = ref([])
  const currentSpeechTime = ref({ start: null, end: null })
  const recordingStartTime = ref(null)

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  const formatSpeaker = (speaker) => {
    if (!speaker) return '说话人'
    return speaker.replace('SPEAKER_', '说话人')
  }

  const formatSpeakerClass = (speaker) => {
    if (!speaker) return 'speaker-1'
    const num = speaker.replace('SPEAKER_', '')
    return `speaker-${num}`
  }

  const createWavBlob = (audioFloat32) => {
    const sampleRate = 16000
    const numSamples = audioFloat32.length
    
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
    
    const wavData = new Uint8Array(44 + numSamples * 2)
    for (let i = 0; i < 44; i++) {
      wavData[i] = new Uint8Array(buffer)[i]
    }
    
    let offset = 44
    for (let i = 0; i < audioFloat32.length; i++) {
      const sample = Math.max(-1, Math.min(1, audioFloat32[i]))
      const intSample = sample < 0 ? sample * 32768 : sample * 32767
      wavData[offset] = intSample & 0xff
      wavData[offset + 1] = (intSample >> 8) & 0xff
      offset += 2
    }
    
    return new Blob([wavData], { type: 'audio/wav' })
  }

  const startTimer = () => {
    recordingTime.value = 0
    timer.value = setInterval(() => {
      if (!isPaused.value) {
        recordingTime.value++
      }
    }, 1000)
  }

  const stopTimer = () => {
    if (timer.value) {
      clearInterval(timer.value)
      timer.value = null
    }
  }

  const connectWebSocket = () => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      return ws.value
    }
    
    const wsUrl = `${WS_HOST}/stt/speaker/ws/transcribe`
    ws.value = new WebSocket(wsUrl)

    ws.value.onopen = () => {
      console.log('WebSocket connected')
      ws.value.send(`Authorization: Bearer ${API_KEY}`)
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        console.log('WebSocket message:', data)
        if (data.status === 'connected') {
          isListening.value = true
          wsConnected.value = true
        } else if (data.result && typeof data.result === 'string') {
          const newResult = {
            text: data.result,
            start: currentSpeechTime.value.start,
            end: currentSpeechTime.value.end,
            speaker: '识别中',
            speakerLoading: true
          }
          transcriptionResults.value.push(newResult)
          
          identifySpeaker(transcriptionResults.value.length - 1)
        } else if (data.error) {
          console.error('WebSocket error:', data.error)
        }
      } catch (e) {
        console.log('WebSocket text:', event.data)
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.value.onclose = () => {
      console.log('WebSocket closed')
      wsConnected.value = false
      ws.value = null
    }

    return ws.value
  }

  const identifySpeaker = async (index) => {
    if (index < 0 || index >= transcriptionResults.value.length) return
    
    if (combinedAudioChunks.value.length === 0) {
      transcriptionResults.value[index].speakerLoading = false
      transcriptionResults.value[index].speaker = '说话人1'
      return
    }
    
    const combinedLength = combinedAudioChunks.value.reduce((sum, chunk) => sum + chunk.length, 0)
    const combinedAudio = new Float32Array(combinedLength)
    let offset = 0
    for (const chunk of combinedAudioChunks.value) {
      combinedAudio.set(chunk, offset)
      offset += chunk.length
    }
    
    const fullRecordedBlob = createWavBlob(combinedAudio)
    if (!fullRecordedBlob || fullRecordedBlob.size === 0) {
      transcriptionResults.value[index].speakerLoading = false
      transcriptionResults.value[index].speaker = '说话人1'
      return
    }
    
    try {
      const formData = new FormData()
      formData.append('file', fullRecordedBlob, 'audio.wav')
      formData.append('num_speaker', toValue(numSpeaker))
      
      const response = await apiClient.post('/stt/speaker/transcribe', formData)
      
      const data = response.data
      
      if (data && data.last_speaker) {
        transcriptionResults.value[index].speaker = data.last_speaker.replace('SPEAKER_', '说话人')

        transcriptionResults.value[index].start_time = currentSpeechTime.value.start - recordingStartTime.value
        transcriptionResults.value[index].end_time = (currentSpeechTime.value.end || Date.now()) - recordingStartTime.value
        transcriptionResults.value[index].speakerLoading = false
      } else {
        transcriptionResults.value[index].speaker = '说话人1'
      }
    } catch (error) {
      console.error('Speaker identification error:', error)
      transcriptionResults.value[index].speakerLoading = false
      transcriptionResults.value[index].speaker = 'UNKNOW'
    } finally {
      isProcessing.value = false
    }
  }

  const arrayBufferToBase64 = (buffer) => {
    return new Promise((resolve) => {
      const reader = new FileReader()
      reader.onload = () => {
        resolve(reader.result.split(',')[1])
      }
      reader.readAsDataURL(new Blob([buffer]))
    })
  }

  const sendAudioToWs = async (audioFloat32) => {
    if (!ws.value || ws.value.readyState !== WebSocket.OPEN || !wsConnected.value) return
    if (!audioFloat32 || audioFloat32.length === 0) return
    
    const wavBlob = createWavBlob(audioFloat32)
    const base64Audio = await arrayBufferToBase64(await wavBlob.arrayBuffer())
    ws.value.send(JSON.stringify({
      type: 'transcribe',
      audio: base64Audio,
      isFinal: false
    }))
  }

  const loadVAD = async () => {
    if (vad.value || vadLoading.value) return vad.value

    vadLoading.value = true
    audioBuffers.value = []
    try {
      const vadInstance = await MicVAD.new({
        onSpeechStart: () => {
          console.log('Speech started')
          isListening.value = true
          currentSpeechTime.value.start = Date.now()
        },
        onSpeechEnd: async (audio) => {
          console.log('Speech ended')
          isListening.value = false
          currentSpeechTime.value.end = Date.now()
          
          if (audio && audio.length > 0) {
            const wavBlob = createWavBlob(audio)
            audioBuffers.value.push(wavBlob)
            pendingAudioChunks.value.push(audio)
            combinedAudioChunks.value.push(audio)
            await sendAudioToWs(audio)
          }
        },
        baseAssetPath: 'https://cdn.jsdelivr.net/npm/@ricky0123/vad-web@0.0.30/dist/',
        onnxWASMBasePath: 'https://cdn.jsdelivr.net/npm/onnxruntime-web@1.22.0/dist/'
      })
      vad.value = vadInstance
      console.log('VAD loaded')
      return vadInstance
    } catch (error) {
      console.error('Failed to load VAD:', error)
      return null
    } finally {
      vadLoading.value = false
    }
  }

  const downloadAudio = () => {
    if (combinedAudioChunks.value.length === 0) return
    
    const combinedLength = combinedAudioChunks.value.reduce((sum, chunk) => sum + chunk.length, 0)
    const combinedAudio = new Float32Array(combinedLength)
    let offset = 0
    for (const chunk of combinedAudioChunks.value) {
      combinedAudio.set(chunk, offset)
      offset += chunk.length
    }
    
    const blob = createWavBlob(combinedAudio)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `recording_${Date.now()}.wav`
    a.click()
    URL.revokeObjectURL(url)
  }

  const transcribeAudio = async () => {
    if (pendingAudioChunks.value.length === 0) return

    isProcessing.value = true
    try {
      const combinedLength = pendingAudioChunks.value.reduce((sum, chunk) => sum + chunk.length, 0)
      const combinedAudio = new Float32Array(combinedLength)
      let offset = 0
      for (const chunk of pendingAudioChunks.value) {
        combinedAudio.set(chunk, offset)
        offset += chunk.length
      }

      const blob = createWavBlob(combinedAudio)
      
      const formData = new FormData()
      formData.append('file', blob, 'audio.wav')
      formData.append('num_speaker', toValue(numSpeaker))

      const response = await axios.post(`${API_PREFIX}/stt/speaker/transcribe`, formData, {
        headers: { 
          'Content-Type': 'multipart/form-data',
          'Authorization': `Bearer ${API_KEY}`
        },
        timeout: 30000
      })

if (response.data && response.data.last_speaker) {
        lastSpeaker.value = response.data.last_speaker.replace('SPEAKER_', '说话人')
      }
      
      pendingAudioChunks.value = []
      return response.data
    } catch (error) {
      console.error('Failed to transcribe audio:', error)
      return null
    } finally {
      isProcessing.value = false
    }
  }

  const startRecording = async () => {
    audioBuffers.value = []
    combinedAudioChunks.value = []
    recordingStartTime.value = Date.now()
    
    try {
      let vadInstance = vad.value
      if (!vadInstance) {
        vadInstance = await loadVAD()
        vad.value = vadInstance
      }
      if (!vadInstance) {
        throw new Error('Failed to load VAD')
      }

      await vadInstance.start()
      connectWebSocket()
      startTimer()
      isRecording.value = true
      isPaused.value = false
    } catch (error) {
      console.error('Failed to start recording:', error)
    }
  }

  const pauseRecording = () => {
    isPaused.value = true
    if (vad.value) {
      vad.value.pause()
    }
  }

  const resumeRecording = () => {
    isPaused.value = false
    if (vad.value) {
      vad.value.start()
    }
  }

  const stopRecording = async () => {
    stopTimer()
    isRecording.value = false
    isPaused.value = false
    isListening.value = false
    
    try {
      if (vad.value) {
        await vad.value.destroy()
        vad.value = null
      }
      if (ws.value) {
        wsConnected.value = false
        ws.value.close()
        ws.value = null
      }
    } catch (e) {
      console.error('Error stopping:', e)
      vad.value = null
    }
    
    pendingAudioChunks.value = []
  }

  const clearResults = () => {
    transcriptionResults.value = []
    pendingTranscripts.value = []
    recordingTime.value = 0
  }

  onUnmounted(() => {
    stopTimer()
    if (vad.value) {
      vad.value.destroy().catch(() => {})
    }
    if (ws.value) {
      ws.value.close()
    }
  })

  return {
    isRecording,
    isPaused,
    isProcessing,
    isListening,
    recordingTime,
    transcriptionResults,
    vadLoading,
    audioBuffers,
    lastSpeaker,
    loadVAD,
    downloadAudio,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    clearResults,
    formatTime,
    formatSpeaker,
    formatSpeakerClass
  }
}