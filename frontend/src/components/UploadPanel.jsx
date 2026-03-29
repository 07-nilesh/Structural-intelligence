import { useRef, useState, useCallback } from 'react'

export default function UploadPanel({ onAnalyze, loading }) {
  const fileInputRef = useRef(null)
  const [dragOver, setDragOver] = useState(false)
  const [preview, setPreview] = useState(null)

  const handleFile = useCallback((file) => {
    if (!file) return
    setPreview(URL.createObjectURL(file))
    onAnalyze(file)
  }, [onAnalyze])

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.type === 'image/png' || file.type === 'image/jpeg')) {
      handleFile(file)
    }
  }, [handleFile])

  const handleDragOver = useCallback((e) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => {
    setDragOver(false)
  }, [])

  const handleSamplePlan = useCallback(async (planName) => {
    try {
      const response = await fetch(`/sample_inputs/${planName}.png`)
      const blob = await response.blob()
      const file = new File([blob], `${planName}.png`, { type: 'image/png' })
      handleFile(file)
    } catch (err) {
      console.error('Failed to load sample plan:', err)
    }
  }, [handleFile])

  if (loading) {
    return (
      <div className="loading-overlay fade-in">
        <div className="spinner" />
        <p style={{ fontSize: '1.1rem', fontWeight: 600 }}>Analyzing Floor Plan...</p>
        <div className="loading-stages">
          <span className="done">✓ Stage 1: Parsing floor plan (OpenCV)</span>
          <span className="done">✓ Stage 2: Reconstructing geometry graph</span>
          <span className="active">⟳ Stage 3: Generating 3D model segments</span>
          <span>○ Stage 4: Optimizing materials (cost-strength tradeoff)</span>
          <span>○ Stage 5: Generating explanations</span>
          <span>○ Web3: Logging to Stellar blockchain</span>
        </div>
      </div>
    )
  }

  return (
    <div className="slide-up">
      <div
        className={`upload-zone ${dragOver ? 'drag-over' : ''}`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg"
          onChange={(e) => handleFile(e.target.files[0])}
        />
        {preview ? (
          <img src={preview} alt="Floor plan preview" style={{
            maxWidth: '300px', maxHeight: '200px', borderRadius: '8px',
            border: '2px solid var(--border-color)', marginBottom: '12px'
          }} />
        ) : (
          <div className="icon">🏗️</div>
        )}
        <p style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 4px' }}>
          Drop a floor plan image here
        </p>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', margin: 0 }}>
          or click to browse • PNG / JPG supported
        </p>
      </div>

      <div style={{ textAlign: 'center', marginTop: '16px' }}>
        <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '10px' }}>
          Or try a sample floor plan:
        </p>
        <div className="sample-buttons">
          <button className="sample-btn" onClick={(e) => { e.stopPropagation(); handleSamplePlan('plan_a') }}>
            📐 Plan A — 2BR Simple
          </button>
          <button className="sample-btn" onClick={(e) => { e.stopPropagation(); handleSamplePlan('plan_b') }}>
            📐 Plan B — 3BR Complex
          </button>
          <button className="sample-btn" onClick={(e) => { e.stopPropagation(); handleSamplePlan('plan_c') }}>
            📐 Plan C — 4BR Large
          </button>
        </div>
      </div>
    </div>
  )
}
