import { useState, useEffect } from 'react'

export default function PendingPanel({ onClose, onApproved }) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(false)
  const [expandedJob, setExpandedJob] = useState(null)

  const fetchJobs = async () => {
    const res = await fetch('/api/v1/pending')
    setJobs(await res.json())
  }

  useEffect(() => { fetchJobs() }, [])

  const approve = async (jobId) => {
    setLoading(true)
    await fetch(`/api/v1/approve/${jobId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) })
    await fetchJobs()
    onApproved?.()
    setLoading(false)
  }

  const reject = async (jobId) => {
    setLoading(true)
    await fetch(`/api/v1/reject/${jobId}`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feedback: 'Rejected via UI' }) })
    await fetchJobs()
    setLoading(false)
  }

  return (
    <div style={{
      position: 'absolute', top: '48px', right: 0, bottom: 0, width: '420px',
      background: '#0f0f1a', borderLeft: '1px solid #222', zIndex: 15,
      display: 'flex', flexDirection: 'column',
    }}>
      <div style={{ padding: '12px 16px', borderBottom: '1px solid #222', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontWeight: 600, color: '#f59e0b', fontSize: '14px' }}>Pending Approvals ({jobs.length})</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: '#666', cursor: 'pointer', fontSize: '18px' }}>✕</button>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '12px' }}>
        {jobs.length === 0 ? (
          <div style={{ color: '#555', textAlign: 'center', marginTop: '40px', fontSize: '14px' }}>
            No pending approvals
          </div>
        ) : jobs.map(job => (
          <div key={job.job_id} style={{
            background: '#1a1a2e', border: '1px solid #2a2a4a', borderRadius: '10px',
            padding: '14px', marginBottom: '12px',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
              <span style={{ fontWeight: 600, color: '#a78bfa', fontSize: '14px' }}>{job.politician_name}</span>
              <span style={{ fontSize: '11px', color: '#666' }}>{new Date(job.created_at).toLocaleTimeString()}</span>
            </div>

            <button
              onClick={() => setExpandedJob(expandedJob === job.job_id ? null : job.job_id)}
              style={{ background: 'none', border: '1px solid #333', borderRadius: '4px', color: '#888', cursor: 'pointer', fontSize: '11px', padding: '2px 8px', marginBottom: '10px' }}
            >
              {expandedJob === job.job_id ? 'Hide' : 'Show'} Cypher Query
            </button>

            {expandedJob === job.job_id && (
              <pre style={{
                background: '#0a0a18', borderRadius: '6px', padding: '10px',
                fontSize: '11px', color: '#86efac', overflow: 'auto',
                maxHeight: '200px', marginBottom: '10px', border: '1px solid #1a3a1a',
              }}>{job.cypher_query}</pre>
            )}

            <div style={{ display: 'flex', gap: '8px' }}>
              <button
                onClick={() => approve(job.job_id)}
                disabled={loading}
                style={{ flex: 1, background: '#065f46', color: '#6ee7b7', border: '1px solid #10b981', borderRadius: '6px', padding: '7px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
              >✓ Approve</button>
              <button
                onClick={() => reject(job.job_id)}
                disabled={loading}
                style={{ flex: 1, background: '#7f1d1d', color: '#fca5a5', border: '1px solid #ef4444', borderRadius: '6px', padding: '7px', cursor: 'pointer', fontSize: '13px', fontWeight: 600 }}
              >✕ Reject</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
