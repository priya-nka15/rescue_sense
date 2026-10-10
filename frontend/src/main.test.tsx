import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { App } from './main'

const result = { analysis_id: 'job-1', modality: 'text', verdict: 'INSUFFICIENT_EVIDENCE', explanation: 'No evidence.', claims: [{ text: 'Bridge collapsed', modality: 'text' }], observations: [], limitations: ['Confidence not calibrated.'], supporting_evidence: [], contradicting_evidence: [], context_evidence: [], methods: ['sentence_heuristic'] }

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(status === 204 ? null : JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
}

afterEach(() => { cleanup(); vi.unstubAllGlobals() })

describe('CrisisSense frontend', () => {
  it('submits text and renders the actual completed result', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/status') return response({ tools: { tesseract: false, ffmpeg: false }, resources: { disk_free_bytes: 10_000_000_000 } })
      if (url === '/api/history') return response([])
      if (url === '/api/verify/text') return response({ job_id: 'job-1', status: 'queued' }, 202)
      if (url === '/api/jobs/job-1') return response({ job_id: 'job-1', status: 'completed', stage: 'completed', result })
      return response({})
    }))
    render(<App />)
    await userEvent.type(screen.getByLabelText('Claim or report'), 'Bridge collapsed near river')
    await userEvent.click(screen.getByRole('button', { name: 'Assess text' }))
    await waitFor(() => expect(screen.getByText('INSUFFICIENT EVIDENCE')).toBeTruthy())
    expect(screen.getByText('Bridge collapsed')).toBeTruthy()
  })

  it('shows a request error for an image upload', async () => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/status') return response({ tools: { tesseract: false, ffmpeg: false }, resources: { disk_free_bytes: 10_000_000_000 } })
      if (url === '/api/history') return response([])
      if (url === '/api/verify/image') return Promise.resolve(new Response('Upload exceeds the configured size limit.', { status: 413 }))
      return response({})
    }))
    render(<App />)
    await userEvent.click(screen.getByRole('button', { name: 'image' }))
    await userEvent.upload(screen.getByLabelText('image file'), new File(['image'], 'test.png', { type: 'image/png' }))
    fireEvent.submit(screen.getByRole('button', { name: 'Assess image' }).closest('form')!)
    await waitFor(() => expect(screen.getByRole('alert').textContent).toContain('Upload exceeds'))
  })

  it('deletes a history entry using the backend response', async () => {
    let present = true
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)
      if (url === '/api/status') return response({ tools: { tesseract: false, ffmpeg: false }, resources: { disk_free_bytes: 10_000_000_000 } })
      if (url === '/api/history' && !init?.method) return response(present ? [{ analysis_id: 'old-1', modality: 'text', verdict: 'INSUFFICIENT_EVIDENCE', created_at: '2026-01-01T00:00:00Z' }] : [])
      if (url === '/api/history/old-1' && init?.method === 'DELETE') { present = false; return response(null, 204) }
      return response({})
    }))
    render(<App />)
    await waitFor(() => expect(screen.getByText('INSUFFICIENT_EVIDENCE')).toBeTruthy())
    await userEvent.click(screen.getByRole('button', { name: 'Delete analysis' }))
    await waitFor(() => expect(screen.queryByText('INSUFFICIENT_EVIDENCE')).toBeNull())
  })

  it('renders reviewer-scoped evidence and processing rationale', async () => {
    const reviewed = {
      ...result,
      verdict: 'SUPPORTED',
      processing_status: 'complete',
      stages: { evidence_retrieval: 'complete', comparison: 'reviewer_scoped' },
      supporting_evidence: [{ title: 'Controlled source', claim_text: 'Bridge collapsed', url: 'https://example.com/report', category: 'user_provided', excerpt: 'The bridge is closed.', relation: 'supports', reviewer: 'Test reviewer', source_note: 'Synthetic fixture' }],
      claim_assessments: [{ claim: 'Bridge collapsed', verdict: 'SUPPORTED' }],
      evidence_gaps: [],
    }
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input)
      if (url === '/api/status') return response({ tools: { tesseract: false, ffmpeg: false }, resources: { disk_free_bytes: 10_000_000_000 } })
      if (url === '/api/history' || url === '/api/evidence') return response([])
      if (url === '/api/verify/text') return response({ job_id: 'job-1', status: 'queued' }, 202)
      if (url === '/api/jobs/job-1') return response({ job_id: 'job-1', status: 'completed', stage: 'completed', result: reviewed })
      return response({})
    }))
    render(<App />)
    await userEvent.type(screen.getByLabelText('Claim or report'), 'Bridge collapsed')
    await userEvent.click(screen.getByRole('button', { name: 'Assess text' }))
    await waitFor(() => expect(screen.getByText('SUPPORTED')).toBeTruthy())
    expect(screen.getByText('Controlled source')).toBeTruthy()
    expect(screen.getByText(/Reviewed by Test reviewer/)).toBeTruthy()
    expect(screen.getByText('comparison: reviewer_scoped')).toBeTruthy()
    expect(screen.getByText('Controlled source: evidence for "Bridge collapsed" (supports)')).toBeTruthy()
    expect(screen.getByRole('link', { name: 'Open source' }).getAttribute('href')).toBe('https://example.com/report')
  })
})
