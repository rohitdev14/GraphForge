import { useEffect, useRef, useState } from 'react';
import cytoscape from 'cytoscape';

type Node = { id: number; type: string; key: string; attributes: Record<string, unknown> };
type Proposal = { id: number; dataset_id: number; source_record_id: number; source_node_id: number; target_node_id: number; relation_type: string; status: string; origin: string; evidence: { record_order?: number; source_fields?: Record<string, unknown> } };
type Graph = { dataset_id: number; nodes: Node[]; edges: Proposal[] };
type EntitySpec = { entity_type: string; key_field: string };

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) {
    let message = response.statusText;
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); } catch { /* ignore */ }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}
const jsonPost = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });

function GraphCanvas({ graph }: { graph: Graph }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!container.current) return;
    const instance = cytoscape({
      container: container.current,
      elements: [
        ...graph.nodes.map(n => ({ data: { id: String(n.id), label: n.key, type: n.type } })),
        ...graph.edges.map(e => ({ data: { id: 'e' + e.id, source: String(e.source_node_id), target: String(e.target_node_id), label: e.relation_type } }))
      ],
      style: [
        { selector: 'node', style: { 'background-color': '#2864b4', label: 'data(label)', color: '#1a2940', 'font-size': 12, 'text-valign': 'bottom', 'text-margin-y': 8, width: 34, height: 34 } },
        { selector: 'edge', style: { width: 2, 'line-color': '#8ea7c4', 'target-arrow-color': '#8ea7c4', 'target-arrow-shape': 'triangle', 'curve-style': 'bezier', label: 'data(label)', 'font-size': 9, color: '#475569', 'text-background-color': '#fff', 'text-background-opacity': 1 } }
      ],
      layout: { name: 'cose', animate: false },
      wheelSensitivity: 0.25
    });
    return () => instance.destroy();
  }, [graph]);
  return <div className="graph" ref={container} aria-label="Approved knowledge graph visualization" />;
}

export default function App() {
  const [datasetId, setDatasetId] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [entities, setEntities] = useState<EntitySpec[]>([{ entity_type: 'equipment', key_field: 'equipment_id' }, { entity_type: 'fault', key_field: 'fault' }]);
  const [sourceType, setSourceType] = useState('equipment');
  const [targetType, setTargetType] = useState('fault');
  const [relationType, setRelationType] = useState('HAS_FAULT');
  const [reviewer, setReviewer] = useState('operator');
  const [proposals, setProposals] = useState<Proposal[]>([]);
  const [graph, setGraph] = useState<Graph | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const id = Number(datasetId);
  const validId = Number.isInteger(id) && id > 0;

  async function run(task: () => Promise<void>) {
    setBusy(true); setMessage('');
    try { await task(); } catch (error) { setMessage(error instanceof Error ? error.message : String(error)); }
    finally { setBusy(false); }
  }
  async function refresh() {
    if (!validId) throw new Error('Enter a valid dataset ID');
    const [p, g] = await Promise.all([
      request<Proposal[]>(`/api/proposals?dataset_id=${id}`),
      request<Graph>(`/api/graph/${id}`)
    ]);
    setProposals(p); setGraph(g);
  }
  async function upload() {
    if (!file) throw new Error('Choose a CSV or JSON file');
    const data = new FormData(); data.append('file', file);
    const result = await request<{ dataset_id: number }>('/upload', { method: 'POST', body: data });
    setDatasetId(String(result.dataset_id)); setProposals([]); setGraph(null);
    setMessage(`Dataset ${result.dataset_id} uploaded. Configure and apply mapping next.`);
  }
  async function map() {
    if (!validId) throw new Error('Enter a valid dataset ID');
    await request('/api/mappings', jsonPost({ dataset_id: id, entities, relations: [{ source_type: sourceType, target_type: targetType, relation_type: relationType }] }));
    await refresh();
  }
  async function suggest() {
    if (!validId) throw new Error('Enter a valid dataset ID');
    await request('/api/ai/suggest', jsonPost({ dataset_id: id, relation_types: [relationType], max_records: 20 }));
    await refresh();
  }
  async function review(proposal: Proposal, action: 'approved' | 'rejected') {
    await request(`/api/proposals/${proposal.id}/review`, jsonPost({ action, reviewer }));
    await refresh();
  }
  function exportGraph() {
    if (!graph) return;
    const blob = new Blob([JSON.stringify(graph, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a'); link.href = url; link.download = `graphforge-${id}.json`; link.click();
    URL.revokeObjectURL(url);
  }
  return <main className="layout">
    <header><div><h1>GraphForge <span>V0.1</span></h1><p>Evidence-backed knowledge graphs. Human-approved by design.</p></div><span className="local">Local-first</span></header>
    <section className="panel">
      <h2>1 · Import dataset</h2>
      <div className="controls"><input aria-label="Dataset file" type="file" accept=".csv,.json,text/csv,application/json" onChange={e => setFile(e.target.files?.[0] || null)} /><button disabled={busy || !file} onClick={() => void run(upload)}>Upload</button><label>Dataset ID <input type="number" min="1" value={datasetId} onChange={e => setDatasetId(e.target.value)} /></label><button disabled={busy || !validId} onClick={() => void run(refresh)}>Load</button></div>
    </section>
    <section className="panel">
      <h2>2 · Define entity mapping</h2>
      {entities.map((entity, index) => <div className="controls" key={index}>
        <input aria-label={`Entity type ${index + 1}`} value={entity.entity_type} onChange={e => setEntities(old => old.map((v, i) => i === index ? { ...v, entity_type: e.target.value } : v))} placeholder="Entity type" />
        <input aria-label={`Key field ${index + 1}`} value={entity.key_field} onChange={e => setEntities(old => old.map((v, i) => i === index ? { ...v, key_field: e.target.value } : v))} placeholder="CSV/JSON field" />
        <button className="secondary" disabled={entities.length <= 1} onClick={() => setEntities(old => old.filter((_, i) => i !== index))}>Remove</button>
      </div>)}
      <button className="secondary" onClick={() => setEntities(old => [...old, { entity_type: '', key_field: '' }])}>Add entity type</button>
      <div className="controls mapping">
        <label>From <select value={sourceType} onChange={e => setSourceType(e.target.value)}>{entities.map((v,i) => <option key={i} value={v.entity_type}>{v.entity_type}</option>)}</select></label>
        <label>Relationship <input value={relationType} onChange={e => setRelationType(e.target.value)} /></label>
        <label>To <select value={targetType} onChange={e => setTargetType(e.target.value)}>{entities.map((v,i) => <option key={i} value={v.entity_type}>{v.entity_type}</option>)}</select></label>
        <button disabled={busy || !validId} onClick={() => void run(map)}>Generate proposals</button>
        <button className="secondary" disabled={busy || !validId} onClick={() => void run(suggest)}>Ask local AI</button>
      </div>
    </section>
    <section className="panel">
      <h2>3 · Review proposals <span className="count">{proposals.filter(p => p.status === 'pending').length} pending</span></h2>
      <label>Reviewer <input value={reviewer} onChange={e => setReviewer(e.target.value)} /></label>
      <div className="proposals">{proposals.length === 0 ? <p className="muted">No proposals loaded.</p> : proposals.map(p => <article key={p.id} className="proposal">
        <div><strong>#{p.id} · {p.relation_type}</strong><p>Node {p.source_node_id} → Node {p.target_node_id} · {p.origin} · {p.status}</p><details><summary>Evidence · source record #{p.source_record_id}</summary><pre>{JSON.stringify(p.evidence, null, 2)}</pre></details></div>
        {p.status === 'pending' && <div className="controls"><button disabled={busy || !reviewer.trim()} onClick={() => void run(() => review(p, 'approved'))}>Approve</button><button className="danger" disabled={busy || !reviewer.trim()} onClick={() => void run(() => review(p, 'rejected'))}>Reject</button></div>}
      </article>)}</div>
    </section>
    <section className="panel"><div className="section-head"><h2>4 · Approved graph</h2><button disabled={!graph} onClick={exportGraph}>Export JSON</button></div>{graph ? <GraphCanvas graph={graph} /> : <p className="muted">Load a dataset to display approved relationships.</p>}</section>
    {message && <div className="notice" role="status">{message}</div>}
  </main>;
}
