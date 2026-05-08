import { useState } from 'react'

const METRIC_LABELS = {
  faithfulness: 'Faithfulness',
  answer_relevancy: 'Answer Relevancy',
  context_precision: 'Context Precision',
}

const METRIC_COLORS = {
  faithfulness: '#a78bfa',
  answer_relevancy: '#34d399',
  context_precision: '#f59e0b',
}

function ScoreBar({ label, value, color }) {
  const pct = Math.round((value ?? 0) * 100)
  return (
    <div style={{ marginBottom: '14px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
        <span style={{ fontSize: '12px', color: '#aaa' }}>{label}</span>
        <span style={{ fontSize: '13px', fontWeight: 700, color }}>{pct}%</span>
      </div>
      <div style={{ background: '#1a1a2e', borderRadius: '4px', height: '6px', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%', background: color,
          borderRadius: '4px', transition: 'width 0.6s ease',
        }} />
      </div>
    </div>
  )
}

function scoreColor(value) {
  if (value == null) return '#555'
  if (value >= 0.75) return '#34d399'
  if (value >= 0.5) return '#f59e0b'
  return '#ef4444'
}

export default function EvalPanel({ onClose }) {
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const runEval = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const res = await fetch('/api/v1/eval')
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `HTTP ${res.status}`)
      }
      setResult(await res.json())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'absolute', top: '48px', right: 0, bottom: 0, width: '440px',
      background: '#0f0f1a', borderLeft: '1px solid #222', zIndex: 15,
      display: 'flex', flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid #222',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      }}>
        <span style={{ fontWeight: 600, color: '#34d399', fontSize: '14px' }}>RAGAS Evaluation</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '18px' }}>✕</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {/* Run button */}
        <button
          onClick={runEval}
          disabled={loading}
          style={{
            width: '100%', padding: '10px', marginBottom: '20px',
            background: loading ? '#1a3a2e' : '#065f46',
            color: loading ? '#6ee7b7' : '#6ee7b7',
            border: '1px solid #10b981', borderRadius: '8px',
            cursor: loading ? 'default' : 'pointer', fontSize: '13px', fontWeight: 600,
          }}
        >
          {loading ? '⏳ Running evaluation… (this may take ~60s)' : '▶ Run Evaluation'}
        </button>

        {error && (
          <div style={{
            background: '#2d0a0a', border: '1px solid #7f1d1d', borderRadius: '8px',
            padding: '12px', marginBottom: '16px', color: '#fca5a5', fontSize: '13px',
          }}>
            {error}
          </div>
        )}

        {result && (
          <>
            {/* Aggregate scores */}
            <div style={{
              background: '#1a1a2e', border: '1px solid #2a2a4a', borderRadius: '10px',
              padding: '16px', marginBottom: '20px',
            }}>
              <div style={{ fontSize: '12px', color: '#666', marginBottom: '14px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Aggregate Scores
              </div>
              {Object.entries(METRIC_LABELS).map(([key, label]) => (
                <ScoreBar
                  key={key}
                  label={label}
                  value={result.aggregate?.[key]}
                  color={METRIC_COLORS[key]}
                />
              ))}
            </div>

            {/* Per-question breakdown */}
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Per-Question Breakdown
            </div>
            {(result.per_question ?? []).map((row, i) => (
              <div key={i} style={{
                background: '#1a1a2e', border: '1px solid #2a2a4a', borderRadius: '8px',
                padding: '12px', marginBottom: '10px',
              }}>
                <div style={{ fontSize: '13px', color: '#e0e0e0', marginBottom: '8px', lineHeight: 1.4 }}>
                  {row.question}
                </div>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {Object.keys(METRIC_LABELS).map(key => {
                    const val = row[key]
                    return (
                      <span key={key} style={{
                        fontSize: '11px', padding: '2px 8px', borderRadius: '4px',
                        background: '#0f0f1a', border: `1px solid ${scoreColor(val)}`,
                        color: scoreColor(val),
                      }}>
                        {METRIC_LABELS[key].split(' ')[0]}: {val != null ? Math.round(val * 100) + '%' : 'N/A'}
                      </span>
                    )
                  })}
                </div>
              </div>
            ))}
          </>
        )}

        {!loading && !result && !error && (
          <div style={{ color: '#444', textAlign: 'center', marginTop: '40px', fontSize: '13px', lineHeight: 1.8 }}>
            Run an evaluation to measure<br />
            faithfulness, answer relevancy,<br />
            and context precision of the RAG pipeline.
          </div>
        )}
      </div>
    </div>
  )
}
