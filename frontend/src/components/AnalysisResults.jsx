export default function AnalysisResults({ result }) {
  const summary = result.summary
  const geometry = result.geometry
  const concerns = geometry?.structural_concerns || []

  return (
    <div className="slide-up">
      {/* Stats Bar */}
      <div className="stats-bar">
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-blue)' }}>
            {summary.rooms_detected}
          </div>
          <div className="stat-label">Rooms</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--text-primary)' }}>
            {summary.walls_detected}
          </div>
          <div className="stat-label">Walls</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#3b82f6' }}>
            {summary.load_bearing_walls}
          </div>
          <div className="stat-label">Load-Bearing</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: '#10b981' }}>
            {summary.partition_walls}
          </div>
          <div className="stat-label">Partition</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-amber)' }}>
            {summary.openings_detected}
          </div>
          <div className="stat-label">Openings</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: summary.structural_warnings_count > 0 ? 'var(--accent-red)' : 'var(--accent-green)' }}>
            {summary.structural_warnings_count}
          </div>
          <div className="stat-label">Warnings</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--accent-amber)' }}>
            {summary.columns_required}
          </div>
          <div className="stat-label">Columns</div>
        </div>
      </div>

      {/* Fallback Notice */}
      {result.fallback_used && (
        <div style={{
          padding: '10px 16px', borderRadius: '8px', marginBottom: '16px',
          background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)',
          fontSize: '0.8rem', color: 'var(--accent-amber)',
        }}>
          ⚠️ CV parsing used fallback coordinates — {result.fallback_reason}
        </div>
      )}

      {/* Structural Warnings */}
      {concerns.length > 0 && (
        <div className="section-card" style={{ marginBottom: '20px' }}>
          <div className="section-header">
            <h2>⚠️ Structural Warnings</h2>
          </div>
          <div className="section-body">
            {concerns.map((c, i) => (
              <div key={i} style={{
                padding: '10px 14px', borderRadius: '8px', marginBottom: '8px',
                background: c.severity === 'critical'
                  ? 'rgba(239, 68, 68, 0.08)' : 'rgba(245, 158, 11, 0.08)',
                border: `1px solid ${c.severity === 'critical'
                  ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)'}`,
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <span className={`warning-badge warning-${c.severity}`}>
                    {c.severity === 'critical' ? '🔴' : '🟡'} {c.severity.toUpperCase()}
                  </span>
                  <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
                    {c.room_label}
                  </span>
                </div>
                <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  {c.concern}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Wall Classification Table */}
      <div className="section-card">
        <div className="section-header">
          <h2>🧱 Wall Classification</h2>
        </div>
        <div className="section-body" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color)' }}>
                <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Wall</th>
                <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Type</th>
                <th style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)' }}>Reason</th>
              </tr>
            </thead>
            <tbody>
              {geometry?.classified_walls?.map((cw, i) => (
                <tr key={i} style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.5)' }}>
                  <td style={{ padding: '8px 12px', fontWeight: 600 }}>{cw.wall_id}</td>
                  <td style={{ padding: '8px 12px' }}>
                    <span style={{
                      padding: '2px 8px', borderRadius: '4px', fontSize: '0.75rem', fontWeight: 600,
                      background: cw.type === 'load-bearing' ? 'rgba(59, 130, 246, 0.15)' : 'rgba(16, 185, 129, 0.15)',
                      color: cw.type === 'load-bearing' ? '#3b82f6' : '#10b981',
                    }}>
                      {cw.type}
                    </span>
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', fontSize: '0.75rem' }}>
                    {cw.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
