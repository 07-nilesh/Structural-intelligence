import { useState } from 'react'

export default function ExplanationPanel({ explanations }) {
  const [expanded, setExpanded] = useState(new Set([0]))

  const toggle = (idx) => {
    setExpanded(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }

  if (!explanations || explanations.length === 0) {
    return (
      <div className="section-card slide-up">
        <div className="section-header">
          <h2>💬 Engineering Explanations</h2>
        </div>
        <div className="section-body">
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>
            No explanations generated.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="section-card slide-up">
      <div className="section-header">
        <h2>💬 Engineering Explanations</h2>
        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
          {explanations.length} elements explained
        </span>
      </div>
      <div className="section-body">
        {explanations.map((exp, idx) => (
          <div key={idx} className="explanation-item">
            <div
              onClick={() => toggle(idx)}
              style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }}
            >
              <span style={{
                fontSize: '0.7rem', transition: 'transform 0.2s',
                transform: expanded.has(idx) ? 'rotate(90deg)' : 'rotate(0deg)',
                display: 'inline-block',
              }}>
                ▶
              </span>
              <div style={{ flex: 1 }}>
                <div className="element-name">{exp.element_label}</div>
                <div className="material-name">
                  Recommended: {exp.recommended_material}
                </div>
              </div>
            </div>

            {expanded.has(idx) && (
              <div className="text fade-in" style={{ marginTop: '8px', paddingLeft: '20px' }}>
                {exp.explanation}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
