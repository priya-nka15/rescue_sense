import { useEffect, useState } from 'react'

type EvidenceRecord = { id: string; title: string; relation?: string; publisher?: string; ingested_at?: string }

export function EvidencePanel({ request }: { request: (path: string, init?: RequestInit) => Promise<any> }) {
  const [items, setItems] = useState<EvidenceRecord[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [relation, setRelation] = useState('context')

  async function refresh() {
    const data = await request('/api/evidence')
    setItems(Array.isArray(data) ? data : [])
  }

  useEffect(() => {
    refresh().catch(() => setError('Evidence collection could not be loaded.'))
  }, [])

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setBusy(true)
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form))
    try {
      await request('/api/evidence', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...values, url: values.url || null, relation }),
      })
      form.reset()
      setRelation('context')
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evidence could not be saved.')
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    try {
      await request(`/api/evidence/${id}`, { method: 'DELETE' })
      await refresh()
    } catch {
      setError('Evidence could not be deleted.')
    }
  }

  const relationMeta: Record<string, { label: string; desc: string }> = {
    context:     { label: 'Context only', desc: 'Passage is retrieved as background context, never as support/contradiction.' },
    supports:    { label: 'Supports an exact claim', desc: 'Requires exact claim text, quoted passage, and reviewer name.' },
    contradicts: { label: 'Contradicts an exact claim', desc: 'Requires exact claim text, quoted passage, and reviewer name.' },
  }

  return (
    <section className="evidence-collection-section" id="evidence-collection">
      <div className="card">
        <div className="card-title">Local Evidence Collection</div>
        <p className="muted" style={{ marginBottom: 20, lineHeight: 1.6 }}>
          Add source passages or public HTTP(S) URLs to build the local evidence base.
          Fetched URLs are treated as contextual unless a reviewer explicitly annotates the relationship.
          Source credibility is not independently verified.
        </p>
        <div className="evidence-collection-grid">
          {/* ADD FORM */}
          <div>
            <p className="eyebrow" style={{ marginBottom: 12 }}>Add new source</p>
            <form onSubmit={save}>
              <div className="field">
                <label htmlFor="ev-title">Source title</label>
                <input id="ev-title" name="title" type="text" required maxLength={200} placeholder="e.g. Reuters report on the incident" />
              </div>
              <div className="field">
                <label htmlFor="ev-publisher">Publisher or author</label>
                <input id="ev-publisher" name="publisher" type="text" maxLength={200} placeholder="e.g. Reuters, BBC, @username" />
              </div>
              <div className="field">
                <label htmlFor="ev-url">Source URL <span className="muted">(optional)</span></label>
                <input id="ev-url" name="url" type="url" maxLength={2048} placeholder="https://example.com/article" />
                <p className="field-hint">If provided, the page is fetched during verification with safety checks. No search providers are configured.</p>
              </div>
              <div className="field">
                <label htmlFor="ev-body">Evidence text <span className="muted">(optional if URL provided)</span></label>
                <textarea id="ev-body" name="body" minLength={0} maxLength={20000} placeholder="Paste the relevant text here…" style={{ minHeight: 90 }} />
              </div>
              <div className="field">
                <label htmlFor="ev-source-note">Provenance note</label>
                <input id="ev-source-note" name="source_note" type="text" required minLength={3} maxLength={1000} placeholder="Where and when you obtained this text" />
              </div>
              <div className="field">
                <label htmlFor="ev-relation">Reviewer relationship</label>
                <select id="ev-relation" aria-label="Reviewer relationship" value={relation} onChange={e => setRelation(e.target.value)}>
                  <option value="context">Context only</option>
                  <option value="supports">Supports an exact claim</option>
                  <option value="contradicts">Contradicts an exact claim</option>
                </select>
                <p className="field-hint">{relationMeta[relation]?.desc}</p>
              </div>

              {relation !== 'context' && (
                <>
                  <div className="field">
                    <label htmlFor="ev-reviewed-claim">Exact reviewed claim</label>
                    <textarea id="ev-reviewed-claim" name="reviewed_claim" required maxLength={12000} placeholder="Copy the claim text exactly as it appears in an analysis." style={{ minHeight: 70 }} />
                  </div>
                  <div className="field">
                    <label htmlFor="ev-passage">Quoted passage (verbatim from evidence text)</label>
                    <textarea id="ev-passage" name="passage" required maxLength={2000} style={{ minHeight: 70 }} />
                    <p className="field-hint">The passage must appear verbatim in the evidence text above.</p>
                  </div>
                  <div className="field">
                    <label htmlFor="ev-reviewer">Reviewer name</label>
                    <input id="ev-reviewer" name="reviewer" type="text" required maxLength={200} />
                  </div>
                </>
              )}

              <button id="ev-save-btn" className="btn-primary" disabled={busy} type="submit">
                {busy ? 'Saving…' : '＋ Save evidence'}
              </button>
            </form>
            {error && <p role="alert" className="alert alert-error" style={{ marginTop: 12 }}>{error}</p>}
          </div>

          {/* SAVED LIST */}
          <div>
            <p className="eyebrow" style={{ marginBottom: 12 }}>
              Saved ({items.length})
            </p>
            {items.length === 0 ? (
              <div className="evidence-none">No sources added yet.</div>
            ) : (
              <div className="saved-evidence-list">
                {items.map(item => (
                  <div className="saved-item" key={item.id}>
                    <div className="saved-item-info">
                      <div className="saved-item-title">{item.title}</div>
                      <div className="saved-item-meta">
                        {item.publisher && <>{item.publisher} · </>}
                        <span className={`relation-pill ${item.relation || 'context'}`}>
                          {item.relation || 'context'}
                        </span>
                      </div>
                    </div>
                    <button
                      className="btn-danger"
                      onClick={() => remove(item.id)}
                      aria-label={`Delete evidence ${item.title}`}
                    >
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
