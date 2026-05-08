import { useRef, useCallback, useMemo } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import { nodeColor } from '../App.jsx'

export default function GraphView({ graphData, onNodeClick }) {
  const fgRef = useRef()

  const data = useMemo(() => ({
    nodes: graphData.nodes.map(n => ({ ...n })),
    links: graphData.links.map(l => ({ ...l })),
  }), [graphData])

  const paintNode = useCallback((node, ctx, globalScale) => {
    const label = node.name || ''
    const fontSize = Math.max(10, 14 / globalScale)
    const r = node.type === 'Politician' ? 7 : node.type === 'Party' ? 6 : 5

    // Glow
    ctx.shadowColor = nodeColor(node.type)
    ctx.shadowBlur = 8
    ctx.beginPath()
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI)
    ctx.fillStyle = nodeColor(node.type)
    ctx.fill()
    ctx.shadowBlur = 0

    // Label (only at reasonable zoom)
    if (globalScale > 0.6) {
      ctx.font = `${fontSize}px Sans-Serif`
      ctx.fillStyle = 'rgba(220,220,220,0.9)'
      ctx.textAlign = 'center'
      ctx.fillText(label, node.x, node.y + r + fontSize)
    }
  }, [])

  if (!data.nodes.length) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '12px', color: '#555' }}>
        <div style={{ fontSize: '48px' }}>🕸</div>
        <div style={{ fontSize: '15px' }}>No politicians in the database yet.</div>
        <div style={{ fontSize: '13px', color: '#444' }}>Use the chat to add one — try "Add Imran Khan"</div>
      </div>
    )
  }

  return (
    <ForceGraph2D
      ref={fgRef}
      graphData={data}
      nodeCanvasObject={paintNode}
      nodeCanvasObjectMode={() => 'replace'}
      linkColor={() => '#334155'}
      linkWidth={1}
      linkDirectionalArrowLength={4}
      linkDirectionalArrowRelPos={1}
      linkLabel={link => link.type}
      backgroundColor="#0f0f1a"
      onNodeClick={(node) => onNodeClick(node)}
      nodeRelSize={6}
      cooldownTicks={120}
    />
  )
}
