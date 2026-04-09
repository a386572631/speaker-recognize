import { ref } from 'vue'

const API_HOST = import.meta.env.VITE_API_HOST || '10.104.60.38'
const API_PORT = import.meta.env.VITE_API_PORT || '5062'
const WS_URL = `ws://${API_HOST}:${API_PORT}/ws`
const WSS_URL = `wss://${API_HOST}:${API_PORT}/ws`
const API_KEY = 'wfy-9CmPH8HQ1jtGxcAC5PJxF7N9Z6teRZTM'

export function useWebSocket() {
  const ws = ref(null)
  const isConnected = ref(false)
  const lastMessage = ref(null)
  const error = ref(null)

  const connect = () => {
    return new Promise((resolve, reject) => {
      const url = window.location.protocol === 'https:' ? WSS_URL : WS_URL
      const socket = new WebSocket(`${url}?Authorization=Bearer ${API_KEY}`)

      socket.onopen = () => {
        isConnected.value = true
        ws.value = socket
        resolve(socket)
      }

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          lastMessage.value = data
        } catch (e) {
          console.error('Failed to parse message:', e)
        }
      }

      socket.onerror = (e) => {
        error.value = e
        reject(e)
      }

      socket.onclose = () => {
        isConnected.value = false
        ws.value = null
      }
    })
  }

  const send = (data) => {
    if (ws.value && ws.value.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
      return true
    }
    return false
  }

  const close = () => {
    if (ws.value) {
      ws.value.close()
      ws.value = null
      isConnected.value = false
    }
  }

  return {
    ws,
    isConnected,
    lastMessage,
    error,
    connect,
    send,
    close
  }
}

export function base64ToArrayBuffer(base64) {
  const binaryString = atob(base64)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return bytes.buffer
}

export function arrayBufferToBase64(buffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i])
  }
  return btoa(binary)
}