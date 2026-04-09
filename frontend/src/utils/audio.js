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