import { useState, useCallback } from 'react'
import './App.css'
import UploadPanel from './components/UploadPanel'
import FloorPlanView from './components/FloorPlanView'
import ModelViewer from './components/ModelViewer'
import AnalysisResults from './components/AnalysisResults'
import MaterialReport from './components/MaterialReport'
import ExplanationPanel from './components/ExplanationPanel'

function App() {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleAnalyze = useCallback(async (file) => {
    setLoading(true)
    setError(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await fetch('/analyze', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error(`Server error: ${response.status} ${response.statusText}`)
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      console.error('Analysis failed:', err)
      setError(err.message || 'Analysis failed. Is the backend running on port 8000?')
    } finally {
      setLoading(false)
    }
  }, [])

  const handleReset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return (
    <>
      {/* Header */}
      <header className="app-header">
        <h1>
          🏗️ Autonomous Structural Intelligence
          <span className="badge">v1.0</span>
        </h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {result && (
            <button
              onClick={handleReset}
              style={{
                padding: '6px 14px', borderRadius: '6px', border: '1px solid rgba(255,255,255,0.2)',
                background: 'rgba(255,255,255,0.1)', color: 'white', cursor: 'pointer',
                fontSize: '0.8rem', fontWeight: 500,
              }}
            >
              ↻ New Analysis
            </button>
          )}
          <span style={{ fontSize: '0.7rem', opacity: 0.7 }}>
            5-Stage Pipeline • Gemini AI • Stellar Web3
          </span>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Error Display */}
        {error && (
          <div style={{
            padding: '14px 20px', borderRadius: '10px', marginBottom: '20px',
            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
            color: 'var(--accent-red)', fontSize: '0.85rem',
          }}>
            ❌ {error}
          </div>
        )}

        {/* Upload / Loading State */}
        {!result && (
          <UploadPanel onAnalyze={handleAnalyze} loading={loading} />
        )}

        {/* Results Dashboard */}
        {result && (
          <div className="fade-in">
            {/* Analysis ID & Timestamp */}
            <div style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginBottom: '16px', fontSize: '0.75rem', color: 'var(--text-muted)',
            }}>
              <span>Analysis ID: <strong style={{ color: 'var(--text-secondary)' }}>{result.analysis_id}</strong></span>
              <span>{new Date(result.timestamp).toLocaleString()}</span>
            </div>

            {/* Stats Summary */}
            <AnalysisResults result={result} />

            {/* 2D + 3D Views */}
            <div className="views-grid" style={{ marginTop: '20px' }}>
              <FloorPlanView result={result} />
              <ModelViewer modelData={result.model_3d} />
            </div>

            {/* Material Recommendations + Explanations */}
            <div className="details-grid">
              <MaterialReport result={result} />
              <ExplanationPanel explanations={result.explanations} />
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer style={{
        textAlign: 'center', padding: '16px', fontSize: '0.7rem',
        color: 'var(--text-muted)', borderTop: '1px solid var(--border-color)',
      }}>
        Autonomous Structural Intelligence System — IIIT NR
        {' '} • OpenCV • NetworkX • Three.js • Gemini AI • Stellar Soroban
      </footer>
    </>
  )
}

export default App
