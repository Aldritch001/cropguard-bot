// Image quality check running client side before any upload
function checkImageQuality(file) {
  return new Promise((resolve) => {
    const img = new Image()
    const url = URL.createObjectURL(file)
    img.onload = () => {
      const canvas = document.createElement("canvas")
      canvas.width = img.width
      canvas.height = img.height
      const ctx = canvas.getContext("2d")
      ctx.drawImage(img, 0, 0)

      const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height)
      const data = imageData.data

      // Brightness check
      let totalBrightness = 0
      for (let i = 0; i < data.length; i += 4) {
        totalBrightness += (data[i] + data[i + 1] + data[i + 2]) / 3
      }
      const avgBrightness = totalBrightness / (data.length / 4)

      // Blur check using variance of pixel differences
      let variance = 0
      for (let i = 0; i < data.length - 4; i += 4) {
        const diff = Math.abs(data[i] - data[i + 4])
        variance += diff * diff
      }
      variance = variance / (data.length / 4)

      URL.revokeObjectURL(url)

      if (avgBrightness < 30) {
        resolve({ ok: false, reason: "Image is too dark. Please take the photo in natural daylight." })
      } else if (avgBrightness > 230) {
        resolve({ ok: false, reason: "Image is overexposed. Move out of direct sunlight and try again." })
      } else if (variance < 50) {
        resolve({ ok: false, reason: "Image appears blurry. Hold the camera steady and make sure the leaf is in focus." })
      } else {
        resolve({ ok: true })
      }
    }
    img.src = url
  })
}

// Elements
const uploadArea = document.getElementById("upload-area")
const fileInput = document.getElementById("file-input")
const previewArea = document.getElementById("preview-area")
const previewImg = document.getElementById("preview-img")
const clearBtn = document.getElementById("clear-btn")
const diagnoseBtn = document.getElementById("diagnose-btn")
const qualityWarning = document.getElementById("quality-warning")
const warningText = document.getElementById("warning-text")
const uploadCard = document.getElementById("upload-card")
const resultCard = document.getElementById("result-card")
const loadingCard = document.getElementById("loading-card")
const diagnoseAgainBtn = document.getElementById("diagnose-again-btn")
const askBtn = document.getElementById("ask-btn")
const questionInput = document.getElementById("question-input")
const answerArea = document.getElementById("answer-area")
const answerLoading = document.getElementById("answer-loading")
const answerText = document.getElementById("answer-text")

let selectedFile = null

// Handle file selection
fileInput.addEventListener("change", async (e) => {
  const file = e.target.files[0]
  if (!file) return

  selectedFile = file

  // Show preview immediately
  const reader = new FileReader()
  reader.onload = (ev) => {
    previewImg.src = ev.target.result
    previewArea.style.display = "flex"
    uploadArea.style.display = "none"
    qualityWarning.style.display = "none"
  }
  reader.readAsDataURL(file)

  // Run quality check
  const quality = await checkImageQuality(file)
  if (!quality.ok) {
    warningText.textContent = quality.reason
    qualityWarning.style.display = "flex"
    diagnoseBtn.style.display = "none"
  } else {
    qualityWarning.style.display = "none"
    diagnoseBtn.style.display = "block"
  }
})

// Clear photo
clearBtn.addEventListener("click", () => {
  selectedFile = null
  fileInput.value = ""
  previewImg.src = ""
  previewArea.style.display = "none"
  uploadArea.style.display = "block"
  diagnoseBtn.style.display = "none"
  qualityWarning.style.display = "none"
})

// Diagnose
diagnoseBtn.addEventListener("click", async () => {
  if (!selectedFile) return

  uploadCard.style.display = "none"
  loadingCard.style.display = "block"
  resultCard.style.display = "none"

  const formData = new FormData()
  formData.append("image", selectedFile)

  try {
    const response = await fetch("/diagnose", {
      method: "POST",
      body: formData
    })

    const data = await response.json()

    loadingCard.style.display = "none"
    resultCard.style.display = "block"

    // Populate result
    const isHealthy = data.disease.toLowerCase().includes("healthy")
    document.getElementById("result-badge").textContent = isHealthy ? "Healthy" : "Disease detected"
    document.getElementById("result-badge").style.background = isHealthy
      ? "rgba(255,255,255,0.3)"
      : "rgba(255,80,80,0.3)"

    document.getElementById("result-disease").textContent = data.disease
    document.getElementById("result-treatment").textContent = data.treatment
    document.getElementById("result-sponsor").textContent = data.recommendation

    const confidenceBar = document.getElementById("confidence-bar")
    const confidenceLabel = document.getElementById("confidence-label")
    confidenceBar.style.width = data.confidence + "%"
    confidenceLabel.textContent = "Confidence: " + data.confidence.toFixed(1) + "%"

    // Scroll to result
    resultCard.scrollIntoView({ behavior: "smooth", block: "start" })

  } catch (err) {
    loadingCard.style.display = "none"
    uploadCard.style.display = "block"
    alert("Something went wrong. Please try again.")
  }
})

// Diagnose again
diagnoseAgainBtn.addEventListener("click", () => {
  selectedFile = null
  fileInput.value = ""
  previewImg.src = ""
  previewArea.style.display = "none"
  uploadArea.style.display = "block"
  diagnoseBtn.style.display = "none"
  qualityWarning.style.display = "none"
  resultCard.style.display = "none"
  uploadCard.style.display = "block"
  uploadCard.scrollIntoView({ behavior: "smooth", block: "start" })
})

// Ask a question
askBtn.addEventListener("click", async () => {
  const question = questionInput.value.trim()
  if (!question) return

  answerArea.style.display = "block"
  answerLoading.style.display = "flex"
  answerText.textContent = ""

  try {
    const response = await fetch("/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    })

    const data = await response.json()
    answerLoading.style.display = "none"
    answerText.textContent = data.answer.replace(/\*\*/g, "").replace(/---/g, "").trim()  

  } catch (err) {
    answerLoading.style.display = "none"
    answerText.textContent = "Could not get an answer right now. Please try again."
  }
})

// PWA install prompt
let deferredPrompt = null
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault()
  deferredPrompt = e
})

// Register service worker for offline support
if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/static/sw.js").catch(() => {})
  })
}