export default function MaterialReport({ result }) {
  const recommendations = result.recommendations?.recommendations || []
  const totalCost = result.recommendations?.total_cost_estimate_inr || 0
  const warnings = result.recommendations?.structural_warnings || []
  const stellarHash = result.stellar_tx_hash || ''

  return (
    <div className="section-card slide-up">
      <div className="section-header">
        <h2>🧪 Material Recommendations</h2>
        <span style={{ fontSize: '0.8rem', color: 'var(--accent-green)', fontWeight: 600 }}>
          Est. Cost: ₹{totalCost.toLocaleString('en-IN')}
        </span>
      </div>
      <div className="section-body">
        {/* Structural Warnings */}
        {warnings.length > 0 && (
          <div style={{ marginBottom: '16px' }}>
            {warnings.map((w, i) => (
              <div key={i} style={{
                padding: '8px 12px', borderRadius: '6px', marginBottom: '6px',
                background: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.2)',
                fontSize: '0.75rem', color: 'var(--accent-red)',
              }}>
                ⚠️ {w}
              </div>
            ))}
          </div>
        )}

        {/* Material Cards */}
        {recommendations.map((rec, idx) => (
          <div key={idx} className="material-item">
            <div className="element-name">{rec.element_label}</div>
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', marginBottom: '8px' }}>
              <span style={{
                fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px',
                background: rec.element_type.includes('load') || rec.element_type === 'column'
                  ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                color: rec.element_type.includes('load') || rec.element_type === 'column'
                  ? '#3b82f6' : '#10b981',
                fontWeight: 600,
              }}>
                {rec.element_type.replace(/_/g, ' ')}
              </span>
              {rec.span_m > 0 && (
                <span style={{
                  fontSize: '0.7rem', padding: '2px 8px', borderRadius: '4px',
                  background: 'rgba(148, 163, 184, 0.15)', color: 'var(--text-secondary)',
                }}>
                  Span: {rec.span_m}m
                </span>
              )}
            </div>

            {/* Top 3 Materials */}
            {rec.top_3_materials?.map((mat, mIdx) => (
              <div key={mIdx} style={{ marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span className={`material-rank rank-${mat.rank}`}>
                    #{mat.rank} {mat.material_name}
                  </span>
                  <span style={{
                    fontSize: '0.7rem', fontWeight: 700,
                    color: mat.score > 60 ? 'var(--accent-green)' : mat.score > 30 ? 'var(--accent-amber)' : 'var(--accent-red)',
                  }}>
                    {mat.score}/100
                  </span>
                  {!mat.eligible && (
                    <span style={{
                      fontSize: '0.6rem', padding: '1px 6px', borderRadius: '3px',
                      background: 'rgba(239, 68, 68, 0.15)', color: 'var(--accent-red)',
                    }}>
                      Ineligible
                    </span>
                  )}
                </div>

                <div className="score-bar">
                  <div className="score-bar-fill" style={{ width: `${mat.score}%` }} />
                </div>

                <div className="material-stats">
                  <div className="stat">
                    <span className="stat-val">{mat.strength_mpa} MPa</span>
                    <span className="stat-lbl">Strength</span>
                  </div>
                  <div className="stat">
                    <span className="stat-val">₹{mat.cost_per_m3_inr?.toLocaleString('en-IN')}</span>
                    <span className="stat-lbl">Cost/m³</span>
                  </div>
                  <div className="stat">
                    <span className="stat-val">{mat.durability_score}/10</span>
                    <span className="stat-lbl">Durability</span>
                  </div>
                </div>

                {mat.exclusion_reason && (
                  <p style={{
                    fontSize: '0.65rem', color: 'var(--accent-red)',
                    margin: '4px 0 0', fontStyle: 'italic',
                  }}>
                    {mat.exclusion_reason}
                  </p>
                )}
              </div>
            ))}

            {/* Structural Flags */}
            {rec.structural_flags?.length > 0 && (
              <div style={{ marginTop: '6px' }}>
                {rec.structural_flags.map((flag, fi) => (
                  <span key={fi} style={{
                    display: 'inline-block', fontSize: '0.65rem', padding: '2px 6px',
                    borderRadius: '3px', marginRight: '4px', marginBottom: '2px',
                    background: 'rgba(245, 158, 11, 0.1)', color: 'var(--accent-amber)',
                  }}>
                    {flag}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Stellar Badge */}
        <div className="stellar-badge">
          <div className="info">
            <h4>
              {stellarHash && !stellarHash.includes('error') && !stellarHash.includes('not_')
                ? '✓ Secured on Stellar Blockchain'
                : '○ Blockchain Audit Trail'}
            </h4>
            <p>
              {stellarHash && !stellarHash.includes('error') && !stellarHash.includes('not_')
                ? `Tx: ${stellarHash.slice(0, 16)}...`
                : stellarHash === 'stellar_not_configured'
                  ? 'Set STELLAR_SECRET_KEY to enable'
                  : stellarHash === 'stellar_sdk_not_installed'
                    ? 'Install stellar-sdk to enable'
                    : 'Immutable Structural Audit Trail'}
            </p>
          </div>
          {stellarHash && !stellarHash.includes('error') && !stellarHash.includes('not_') && (
            <a
              href={`https://stellar.expert/explorer/testnet/tx/${stellarHash}`}
              target="_blank"
              rel="noopener noreferrer"
              className="verify-btn"
            >
              Verify Ledger Entry
            </a>
          )}
        </div>
      </div>
    </div>
  )
}
