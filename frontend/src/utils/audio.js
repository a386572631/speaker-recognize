const SILENCE_THRESHOLD = 0.01
const SILENCE_DURATION = 0.5

export class AudioBufferManager {
  constructor() {
    this.chunks = []
    this.sampleRate = 16000
    this.channels = 1
  }

  addChunk(audioBuffer) {
    this.chunks.push(audioBuffer)
  }

  mergeChunks() {
    if (this.chunks.length === 0) return null

    const totalLength = this.chunks.reduce((sum, chunk) => sum + chunk.length, 0)
    const merged = new Float32Array(totalLength)

    let offset = 0
    for (const chunk of this.chunks) {
      merged.set(chunk, offset)
      offset += chunk.length
    }

    return merged
  }

  clear() {
    this.chunks = []
  }

  get length() {
    return this.chunks.length
  }

  get totalSamples() {
    return this.chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  }
}

export function float32ToWav(audioData, sampleRate = 16000) {
  const numChannels = 1
  const bitsPerSample = 16
  const bytesPerSample = bitsPerSample / 8
  const blockAlign = numChannels * bytesPerSample
  const byteRate = sampleRate * blockAlign
  const dataSize = audioData.length * bytesPerSample
  const bufferSize = 44 + dataSize

  const buffer = new ArrayBuffer(bufferSize)
  const view = new DataView(buffer.buffer)

  const writeString = (offset, string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i))
    }
  }

  writeString(0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(8, 'WAVE')
  writeString(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, numChannels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, byteRate, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bitsPerSample, true)
  writeString(36, 'data')
  view.setUint32(40, dataSize, true)

  let offset = 44
  for (let i = 0; i < audioData.length; i++) {
    const sample = Math.max(-1, Math.min(1, audioData[i]))
    view.setInt16(offset, sample * 0x7fff, true)
    offset += 2
  }

  return buffer
}

export function audioBufferToWavBlob(audioBuffer) {
  const wavBuffer = float32ToWav(audioBuffer)
  return new Blob([wavBuffer], { type: 'audio/wav' })
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export function float32ArrayToWav(float32Array, sampleRate = 16000) {
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

export function mergeAudioSegments(segments) {
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