import { useRef, useEffect } from 'react'

const COLORS = {
  'load-bearing': '#3b82f6',
  'partition': '#10b981',
  'door': '#f59e0b',
  'window': '#8b5cf6',
  'room-fill': 'rgba(59, 130, 246, 0.06)',
  'room-label': '#94a3b8',
  'column': '#f59e0b',
}

export default function FloorPlanView({ result }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    if (!result || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    const parsed = result.parsed_data
    const geometry = result.geometry
    const dims = parsed.image_dimensions || [800, 600]

    // Set canvas size
    const container = canvas.parentElement
    const maxW = container.clientWidth - 40
    const scaleFactor = Math.min(maxW / dims[0], 380 / dims[1])
    canvas.width = dims[0] * scaleFactor
    canvas.height = dims[1] * scaleFactor

    ctx.clearRect(0, 0, canvas.width, canvas.height)

    const sx = scaleFactor
    const sy = scaleFactor

    // Build classification lookup
    const wallTypes = {}
    if (geometry?.classified_walls) {
      geometry.classified_walls.forEach(cw => {
        wallTypes[cw.wall_id] = cw.type
      })
    }

    // Draw room fills
    parsed.rooms?.forEach(room => {
      if (room.polygon && room.polygon.length >= 3) {
        ctx.beginPath()
        ctx.moveTo(room.polygon[0][0] * sx, room.polygon[0][1] * sy)
        room.polygon.slice(1).forEach(pt => ctx.lineTo(pt[0] * sx, pt[1] * sy))
        ctx.closePath()
        ctx.fillStyle = COLORS['room-fill']
        ctx.fill()
      }
    })

    // Draw walls with classification colors
    parsed.walls?.forEach(wall => {
      const wtype = wallTypes[wall.id] || 'partition'
      ctx.beginPath()
      ctx.moveTo(wall.start[0] * sx, wall.start[1] * sy)
      ctx.lineTo(wall.end[0] * sx, wall.end[1] * sy)
      ctx.strokeStyle = COLORS[wtype]
      ctx.lineWidth = wtype === 'load-bearing' ? 4 : 2.5
      ctx.stroke()
    })

    // Draw openings
    parsed.openings?.forEach(op => {
      const px = op.position[0] * sx
      const py = op.position[1] * sy
      const hw = (op.width_px || 40) * sx / 2

      ctx.beginPath()
      if (op.type === 'door') {
        ctx.strokeStyle = COLORS.door
        ctx.lineWidth = 2
        ctx.arc(px - hw, py, hw * 2, -Math.PI / 2, 0)
        ctx.stroke()
      } else {
        ctx.strokeStyle = COLORS.window
        ctx.lineWidth = 3
        ctx.setLineDash([4, 3])
        // Find parent wall orientation
        const parentWall = parsed.walls?.find(w => w.id === op.wall_id)
        if (parentWall?.orientation === 'horizontal') {
          ctx.moveTo(px - hw, py)
          ctx.lineTo(px + hw, py)
        } else {
          ctx.moveTo(px, py - hw)
          ctx.lineTo(px, py + hw)
        }
        ctx.stroke()
        ctx.setLineDash([])
      }
    })

    // Draw room labels
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    parsed.rooms?.forEach(room => {
      const cx = room.centroid[0] * sx
      const cy = room.centroid[1] * sy

      ctx.fillStyle = COLORS['room-label']
      ctx.font = `bold ${Math.max(9, 11 * scaleFactor)}px Inter, sans-serif`
      ctx.fillText(room.label, cx, cy - 8)

      ctx.font = `${Math.max(8, 9 * scaleFactor)}px Inter, sans-serif`
      ctx.fillStyle = '#64748b'
      ctx.fillText(`${room.area_m2} m²`, cx, cy + 8)
    })

    // Draw columns
    geometry?.columns_required?.forEach(col => {
      const cx = col.position[0] * sx
      const cy = col.position[1] * sy
      ctx.beginPath()
      ctx.arc(cx, cy, 6, 0, Math.PI * 2)
      ctx.fillStyle = COLORS.column
      ctx.fill()
      ctx.strokeStyle = '#92400e'
      ctx.lineWidth = 1.5
      ctx.stroke()
    })

  }, [result])

  return (
    <div className="section-card">
      <div className="section-header">
        <h2>📋 2D Floor Plan</h2>
        <div className="legend">
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: COLORS['load-bearing'] }} />
            Load-bearing
          </span>
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: COLORS['partition'] }} />
            Partition
          </span>
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: COLORS['door'] }} />
            Door
          </span>
          <span className="legend-item">
            <span className="legend-swatch" style={{ background: COLORS['window'] }} />
            Window
          </span>
        </div>
      </div>
      <div className="section-body" style={{ display: 'flex', justifyContent: 'center' }}>
        <canvas ref={canvasRef} className="floor-plan-canvas" />
      </div>
    </div>
  )
}
