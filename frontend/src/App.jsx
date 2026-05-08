import { useState, useEffect, useCallback } from 'react'
import GraphView from './components/GraphView.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import PendingPanel from './components/PendingPanel.jsx'
import EvalPanel from './components/EvalPanel.jsx'

export default function App() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] })
  const [chatOpen, setChatOpen] = useState(true)
  const [pendingOpen, setPendingOpen] = useState(false)
  const [evalOpen, setEvalOpen] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const [selectedNode, setSelectedNode] = useState(null)

  const fetchGraph = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/graph')
      const data = await res.json()
      setGraphData(data)
    } catch (e) {
      console.error('Graph fetch failed:', e)
    }
  }, [])

  const fetchPendingCount = useCallback(async () => {
    try {
      const res = await fetch('/api/v1/pending')
      const data = await res.json()
      setPendingCount(data.length)
    } catch (e) {}
  }, [])

  useEffect(() => {
    fetchGraph()
    fetchPendingCount()
    const interval = setInterval(() => {
      fetchGraph()
      fetchPendingCount()
    }, 10000)
    return () => clearInterval(interval)
  }, [fetchGraph, fetchPendingCount])

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw', position: 'relative' }}>
      {/* Top bar */}
      <div style={{
        position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10,
        background: 'rgba(26,26,46,0.9)', backdropFilter: 'blur(8px)',
        borderBottom: '1px solid #333', padding: '10px 20px',
        display: 'flex', alignItems: 'center', gap: '16px'
      }}>
        <span style={{ fontSize: '18px', fontWeight: 700, color: '#a78bfa', letterSpacing: '0.05em' }}>
          ﺗاریخ نیٹ
        </span>
        <span style={{ color: '#666', fontSize: '13px' }}>Pakistani Politicians Knowledge Graph</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: '10px' }}>
          <button onClick={() => { setPendingOpen(o => !o); setChatOpen(false); setEvalOpen(false) }} style={btnStyle(pendingOpen)}>
            Approvals {pendingCount > 0 && <span style={{ background: '#ef4444', borderRadius: '50%', padding: '1px 6px', fontSize: '11px', marginLeft: '4px' }}>{pendingCount}</span>}
          </button>
          <button onClick={() => { setChatOpen(o => !o); setPendingOpen(false); setEvalOpen(false) }} style={btnStyle(chatOpen)}>
            Chat
          </button>
          <button onClick={() => { setEvalOpen(o => !o); setChatOpen(false); setPendingOpen(false) }} style={btnStyle(evalOpen)}>
            Eval
          </button>
          <button onClick={fetchGraph} style={btnStyle(false)}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Graph */}
      <div style={{ flex: 1, paddingTop: '48px' }}>
        <GraphView
          graphData={graphData}
          onNodeClick={setSelectedNode}
        />
      </div>

      {/* Node info tooltip */}
      {selectedNode && (
        <div style={{
          position: 'absolute', bottom: '20px', left: '20px', zIndex: 20,
          background: '#16213e', border: '1px solid #444', borderRadius: '10px',
          padding: '14px 18px', maxWidth: '320px', fontSize: '13px'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
            <span style={{ fontWeight: 600, color: nodeColor(selectedNode.type), fontSize: '15px' }}>{selectedNode.name}</span>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: '16px' }}>✕</button>
          </div>
          <div style={{ color: '#888', fontSize: '11px', marginBottom: '6px' }}>{selectedNode.type}</div>
          {selectedNode.bio && <p style={{ color: '#ccc', lineHeight: 1.5 }}>{selectedNode.bio}</p>}
          {selectedNode.born && <p style={{ color: '#888', marginTop: '4px', fontSize: '12px' }}>Born: {selectedNode.born}</p>}
        </div>
      )}

      {/* Chat panel */}
      {chatOpen && (
        <ChatPanel
          onClose={() => setChatOpen(false)}
          onIngestStarted={fetchGraph}
          onRefreshPending={fetchPendingCount}
        />
      )}

      {/* Pending approvals panel */}
      {pendingOpen && (
        <PendingPanel
          onClose={() => setPendingOpen(false)}
          onApproved={() => { fetchGraph(); fetchPendingCount() }}
        />
      )}

      {/* Eval panel */}
      {evalOpen && (
        <EvalPanel onClose={() => setEvalOpen(false)} />
      )}
    </div>
  )
}

function btnStyle(active) {
  return {
    background: active ? '#7c3aed' : '#2d2d4e',
    color: active ? '#fff' : '#aaa',
    border: '1px solid ' + (active ? '#7c3aed' : '#444'),
    borderRadius: '6px',
    padding: '5px 14px',
    cursor: 'pointer',
    fontSize: '13px',
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  }
}

export function nodeColor(type) {
  const colors = { Politician: '#7c3aed', Party: '#f59e0b', Position: '#10b981', default: '#6b7280' }
  return colors[type] || colors.default
}
