import { onUnmounted, ref } from 'vue'

const SpeechRecognitionConstructor = typeof window !== 'undefined'
  ? window.SpeechRecognition || window.webkitSpeechRecognition
  : null

const errorMessages = {
  'not-allowed': '麦克风权限被拒绝，请在 Chrome 中允许麦克风访问。',
  'service-not-allowed': '浏览器阻止了语音识别服务，请检查 Chrome 权限设置。',
  'no-speech': '没有检测到语音，请重试。',
  'audio-capture': '没有检测到可用麦克风，请检查设备。',
  network: '语音识别网络连接失败，请稍后重试。',
}

function getErrorMessage(error) {
  return errorMessages[error] || '语音识别失败，请稍后重试。'
}

export function useSpeechRecognition() {
  const isSupported = ref(Boolean(SpeechRecognitionConstructor))
  const isListening = ref(false)
  const interimTranscript = ref('')
  const finalTranscript = ref('')
  const errorMessage = ref('')

  let recognition = null

  function createRecognition() {
    if (!SpeechRecognitionConstructor) {
      errorMessage.value = '当前浏览器不支持语音识别，请使用 Chrome。'
      return null
    }

    if (recognition) {
      return recognition
    }

    recognition = new SpeechRecognitionConstructor()
    recognition.lang = 'zh-CN'
    recognition.continuous = true
    recognition.interimResults = true
    recognition.maxAlternatives = 1

    recognition.onstart = () => {
      isListening.value = true
      errorMessage.value = ''
    }

    recognition.onresult = (event) => {
      let interimText = ''
      let finalText = ''

      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        const result = event.results[index]
        const transcript = result[0]?.transcript || ''

        if (result.isFinal) {
          finalText += transcript
        } else {
          interimText += transcript
        }
      }

      interimTranscript.value = interimText.trim()

      const committedText = finalText.trim()
      if (committedText) {
        finalTranscript.value = finalTranscript.value
          ? `${finalTranscript.value} ${committedText}`
          : committedText
      }
    }

    recognition.onerror = (event) => {
      isListening.value = false
      interimTranscript.value = ''
      errorMessage.value = getErrorMessage(event.error)
    }

    recognition.onend = () => {
      isListening.value = false
      interimTranscript.value = ''
    }

    return recognition
  }

  function start() {
    const speechRecognition = createRecognition()
    if (!speechRecognition || isListening.value) return

    errorMessage.value = ''
    interimTranscript.value = ''

    try {
      speechRecognition.start()
    } catch (error) {
      isListening.value = false
      errorMessage.value = '语音识别启动失败，请稍后重试。'
    }
  }

  function stop() {
    if (!recognition) return

    try {
      recognition.stop()
    } catch (error) {
      isListening.value = false
    }
  }

  function reset() {
    stop()
    interimTranscript.value = ''
    finalTranscript.value = ''
    errorMessage.value = ''
  }

  function cleanup() {
    if (!recognition) return

    recognition.onstart = null
    recognition.onresult = null
    recognition.onerror = null
    recognition.onend = null

    try {
      recognition.abort()
    } catch (error) {
      // Ignore abort errors during component teardown.
    }

    recognition = null
    isListening.value = false
    interimTranscript.value = ''
  }

  onUnmounted(cleanup)

  return {
    isSupported,
    isListening,
    interimTranscript,
    finalTranscript,
    errorMessage,
    start,
    stop,
    reset,
  }
}
