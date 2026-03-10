import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

export default function ChatPanel({ onClose, onIngestStarted, onRefreshPending }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: 'Hello! I can help you explore Pakistani politicians. Ask me anything, or say "Add Imran Khan" to import a politician.' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const text = input.trim()
    if (!text || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setLoading(true)

    try {
      const res = await fetch('/api/v1/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const data = await res.json()

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.reply,
        intent: data.intent,
        thread_id: data.thread_id,
        pending_jobs: data.pending_jobs || [],
      }])

      if (data.intent === 'ingest') onIngestStarted?.()
      if (data.intent === 'pending' || data.pending_jobs?.length) onRefreshPending?.()
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'absolute', top: '48px', right: 0, bottom: 0, width: '380px',
      background: '#0f0f1a', borderLeft: '1px solid #222', zIndex: 15,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, color: '#a78bfa', fontSize: '14px' }}>Chat</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '18px' }}>✕</button>
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {messages.map((msg, i) => (
          <div key={i} style={{ display: 'flex', flexDirection: 'column', alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start' }}>
            <div style={{
              background: msg.role === 'user' ? '#4c1d95' : '#1e1e3a',
              borderRadius: msg.role === 'user' ? '14px 14px 2px 14px' : '14px 14px 14px 2px',
              padding: '9px 14px', maxWidth: '90%', fontSize: '13px', lineHeight: '1.6',
              color: '#e0e0e0', border: '1px solid ' + (msg.role === 'user' ? '#6d28d9' : '#2a2a4a'),
            }}>
              <ReactMarkdown>{msg.content}</ReactMarkdown>
            </div>
            {msg.intent === 'ingest' && msg.thread_id && (
              <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                ⏳ Ingestion running in background — check Approvals when ready
              </div>
            )}
            {msg.pending_jobs?.length > 0 && (
              <div style={{ fontSize: '11px', color: '#f59e0b', marginTop: '4px' }}>
                ⚠ Open the Approvals panel to review pending writes
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ display: 'flex', alignItems: 'flex-start' }}>
            <div style={{ background: '#1e1e3a', borderRadius: '14px 14px 14px 2px', padding: '9px 14px', border: '1px solid #2a2a4a' }}>
              <span style={{ animation: 'pulse 1s infinite', color: '#666' }}>●●●</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{ padding: '12px 16px', borderTop: '1px solid #222', display: 'flex', gap: '8px' }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
          placeholder="Ask about politicians or say 'Add Imran Khan'…"
          style={{
            flex: 1, background: '#1a1a2e', border: '1px solid #333', borderRadius: '8px',
            padding: '8px 12px', color: '#e0e0e0', fontSize: '13px', outline: 'none',
          }}
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          style={{
            background: input.trim() && !loading ? '#7c3aed' : '#2d2d4e',
            color: input.trim() && !loading ? '#fff' : '#555',
            border: 'none', borderRadius: '8px', padding: '8px 14px',
            cursor: input.trim() && !loading ? 'pointer' : 'default', fontSize: '14px',
          }}
        >→</button>
      </div>
    </div>
  )
}
