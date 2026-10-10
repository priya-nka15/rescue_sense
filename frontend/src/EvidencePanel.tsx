import { useEffect, useState } from 'react'

export function EvidencePanel({ request }: { request: (path: string, init?: RequestInit) => Promise<any> }) {
  const [items, setItems] = useState<any[]>([])
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [relation, setRelation] = useState('context')
  async function refresh() {
    const data = await request('/api/evidence')
    setItems(Array.isArray(data) ? data : [])
  }
  useEffect(() => { refresh().catch(() => setError('Evidence collection could not be loaded.')) }, [])
  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setBusy(true)
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form))
    try {
      await request('/api/evidence', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...values, url: values.url || null, relation }) })
      form.reset(); setRelation('context'); await refresh()
    } catch (error) { setError(error instanceof Error ? error.message : 'Evidence could not be saved.') }
    finally { setBusy(false) }
  }
  async function remove(id: string) {
    try { await request(`/api/evidence/${id}`, { method: 'DELETE' }); await refresh() }
    catch { setError('Evidence could not be deleted.') }
  }
  return <section className="evidence-input"><h2>Local evidence collection</h2>
    <p className="muted">Add source text or a public HTTP(S) URL. URLs are fetched with size, timeout, redirect, and private-network safeguards during verification; fetched passages remain contextual until reviewed.</p>
    <form onSubmit={save}>
      <label>Source title<input name="title" required maxLength={200} /></label>
      <label>Publisher or author<input name="publisher" maxLength={200} /></label>
      <label>Source URL (optional)<input name="url" type="url" maxLength={2048} /></label>
      <label>Evidence text (optional when a URL is provided)<textarea name="body" minLength={3} maxLength={20000} /></label>
      <label>Provenance note<input name="source_note" required minLength={3} maxLength={1000} placeholder="Where and when you obtained this text" /></label>
      <label>Reviewer relationship<select aria-label="Reviewer relationship" value={relation} onChange={e => setRelation(e.target.value)}>
        <option value="context">Context only</option><option value="supports">Supports an exact claim</option><option value="contradicts">Contradicts an exact claim</option>
      </select></label>
      {relation !== 'context' && <><label>Exact reviewed claim<textarea name="reviewed_claim" required maxLength={12000} /></label>
        <label>Quoted supporting or contradicting passage<textarea name="passage" required maxLength={2000} /></label>
        <label>Reviewer name<input name="reviewer" required maxLength={200} /></label></>}
      <button className="primary" disabled={busy} type="submit">{busy ? 'Saving evidence...' : 'Save evidence'}</button>
    </form>
    {error && <p role="alert" className="error">{error}</p>}
    <ul>{items.map(item => <li key={item.id}>{item.title} ({item.relation || 'context'}) <button onClick={() => remove(item.id)} aria-label={`Delete evidence ${item.title}`}>Delete</button></li>)}</ul>
  </section>
}
