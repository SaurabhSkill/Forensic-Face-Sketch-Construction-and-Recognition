import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import PageContainer from '../layout/PageContainer';
import caseService from '../services/caseService';
import './CaseDetailsPage.css';

const STATUS_OPTIONS = ['Open', 'Under Investigation', 'Closed'];
const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical'];

/* ── dummy data shown when API is unavailable ─────────────────── */
const DUMMY_CASE = {
  id: 1, case_number: 'FF-2024-001', title: 'Downtown Bank Robbery',
  status: 'Under Investigation', priority: 'Critical', crime_type: 'Robbery',
  location: 'Downtown Financial District', incident_date: '2024-01-15',
  description: 'Armed robbery at First National Bank. Three suspects entered at 10:15 AM. CCTV footage recovered. Partial facial match found via AI system.',
  officer_id: 'OFF-042', created_at: '2024-01-16T10:00:00Z', updated_at: '2024-01-20T14:30:00Z',
};
const DUMMY_NOTES = [
  { id: 1, author_name: 'Officer Chen', content: 'Suspect seen near ATM on 3rd Ave at 09:45 AM. Matches partial description from witness.', created_at: '2024-01-16T10:30:00Z', type: 'officer' },
  { id: 2, author_name: 'AI System', content: 'Facial match found — 87% similarity with Arjun Mehta (Criminal ID: CR-0042). Confidence: HIGH.', created_at: '2024-01-16T11:00:00Z', type: 'system' },
  { id: 3, author_name: 'Officer Chen', content: 'CCTV footage uploaded. Timestamp 10:12–10:28 AM. Three individuals visible. Requesting forensic analysis.', created_at: '2024-01-16T12:15:00Z', type: 'officer' },
  { id: 4, author_name: 'Officer Patel', content: 'Witness interview completed. Suspect described as male, 5\'10", dark jacket. Consistent with CCTV.', created_at: '2024-01-17T09:00:00Z', type: 'officer' },
];
const DUMMY_SUSPECTS = [
  { id: 1, name: 'Arjun Mehta', match: 87, status: 'AI Match', image: null },
  { id: 2, name: 'Unknown Subject', match: 62, status: 'Partial', image: null },
];
const DUMMY_EVIDENCE = [
  { id: 1, name: 'CCTV_footage_10AM.mp4', type: 'video', size: '142 MB', uploaded_at: '2024-01-16T12:15:00Z' },
  { id: 2, name: 'witness_statement.pdf', type: 'document', size: '84 KB', uploaded_at: '2024-01-17T09:30:00Z' },
  { id: 3, name: 'crime_scene_photo_01.jpg', type: 'image', size: '3.2 MB', uploaded_at: '2024-01-16T14:00:00Z' },
];

/* ── helpers ──────────────────────────────────────────────────── */
const statusCls = s => s === 'Open' ? 'cd-badge-open' : s === 'Under Investigation' ? 'cd-badge-inv' : 'cd-badge-closed';
const priorityCls = p => ({ low:'cd-pri-low', medium:'cd-pri-med', high:'cd-pri-high', critical:'cd-pri-crit' })[(p||'medium').toLowerCase()] || 'cd-pri-med';
const fmtDate = d => d ? new Date(d).toLocaleDateString('en-US', { month:'short', day:'numeric', year:'numeric' }) : '—';
const fmtDateTime = d => d ? new Date(d).toLocaleString('en-US', { month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : '—';

const fileIcon = type => {
  if (type === 'image') return 'M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z';
  if (type === 'video') return 'M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z';
  return 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z';
};

/* ── SuspectCard ──────────────────────────────────────────────── */
const SuspectCard = ({ suspect, onView }) => (
  <div className="cd-suspect-card">
    <div className="cd-suspect-avatar">
      {suspect.image
        ? <img src={suspect.image} alt={suspect.name} />
        : <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>
      }
    </div>
    <div className="cd-suspect-info">
      <div className="cd-suspect-name">{suspect.name}</div>
      <div className="cd-suspect-meta">
        {suspect.match && (
          <span className="cd-match-badge">
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            {suspect.match}% match
          </span>
        )}
        <span className={`cd-suspect-status ${suspect.status === 'AI Match' ? 'cd-suspect-ai' : 'cd-suspect-partial'}`}>
          {suspect.status}
        </span>
      </div>
    </div>
    <button className="cd-view-btn" onClick={() => onView(suspect.id)}>View</button>
  </div>
);

/* ── EvidenceItem ─────────────────────────────────────────────── */
const EvidenceItem = ({ item }) => (
  <div className="cd-evidence-item">
    <div className="cd-evidence-icon">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d={fileIcon(item.type)} /></svg>
    </div>
    <div className="cd-evidence-info">
      <div className="cd-evidence-name">{item.name}</div>
      <div className="cd-evidence-meta">{item.size} · {fmtDate(item.uploaded_at)}</div>
    </div>
    <button className="cd-evidence-dl" title="Download">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
    </button>
  </div>
);

/* ── TimelineItem ─────────────────────────────────────────────── */
const TimelineItem = ({ note, isLast }) => {
  const isSystem = note.type === 'system' || (note.author_name || '').toLowerCase().includes('system') || (note.author_name || '').toLowerCase().includes('ai');
  return (
    <div className="cd-tl-item">
      <div className="cd-tl-left">
        <div className={`cd-tl-dot ${isSystem ? 'cd-tl-dot-system' : 'cd-tl-dot-officer'}`}>
          {isSystem
            ? <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
            : <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/></svg>
          }
        </div>
        {!isLast && <div className="cd-tl-line" />}
      </div>
      <div className="cd-tl-body">
        <div className="cd-tl-meta">
          <span className={`cd-tl-author ${isSystem ? 'cd-tl-author-system' : ''}`}>{note.author_name}</span>
          <span className="cd-tl-time">{fmtDateTime(note.created_at)}</span>
        </div>
        <div className={`cd-tl-content ${isSystem ? 'cd-tl-content-system' : ''}`}>{note.content}</div>
      </div>
    </div>
  );
};

/* ── Main Page ────────────────────────────────────────────────── */
const CaseDetailsPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [caseDetails, setCaseDetails] = useState(null);
  const [notes, setNotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isEditing, setIsEditing] = useState(false);
  const [editData, setEditData] = useState({});
  const [saving, setSaving] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const fetchAll = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [caseRes, notesRes] = await Promise.all([
        caseService.getCaseById(id),
        caseService.getCaseNotes(id),
      ]);
      setCaseDetails(caseRes.case);
      setEditData(caseRes.case);
      setNotes(notesRes.notes || []);
    } catch (err) {
      // fall back to dummy data so UI is always visible
      setCaseDetails(DUMMY_CASE);
      setEditData(DUMMY_CASE);
      setNotes(DUMMY_NOTES);
      if (!err.response) setError('Backend offline — showing sample data.');
    } finally { setLoading(false); }
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleChange = e => setEditData(prev => ({ ...prev, [e.target.name]: e.target.value }));

  const handleUpdate = async () => {
    setSaving(true);
    try { await caseService.updateCase(id, editData); setIsEditing(false); fetchAll(); }
    catch { alert('Failed to update case.'); }
    finally { setSaving(false); }
  };

  const handleDelete = async () => {
    if (!window.confirm('Permanently delete this case?')) return;
    try { await caseService.deleteCase(id); navigate('/cases'); }
    catch { alert('Failed to delete case.'); }
  };

  const handleCloseCase = async () => {
    if (!window.confirm('Mark this case as Closed?')) return;
    try { await caseService.updateCase(id, { status: 'Closed' }); fetchAll(); }
    catch { alert('Failed to close case.'); }
  };

  const handleAddNote = async e => {
    e.preventDefault();
    if (!noteText.trim()) return;
    setSubmitting(true);
    try {
      await caseService.createCaseNote(id, { content: noteText });
      setNoteText('');
      const res = await caseService.getCaseNotes(id);
      setNotes(res.notes || []);
    } catch {
      // optimistic local add for demo
      setNotes(prev => [...prev, { id: Date.now(), author_name: 'Officer', content: noteText, created_at: new Date().toISOString(), type: 'officer' }]);
      setNoteText('');
    } finally { setSubmitting(false); }
  };

  /* ── loading / error states ── */
  if (loading) return (
    <div className="cd-fullscreen-state">
      <div className="cd-spinner" />
      <p>Loading case...</p>
    </div>
  );

  if (!caseDetails) return (
    <div className="cd-fullscreen-state">
      <svg width="40" height="40" viewBox="0 0 24 24" fill="#ef4444"><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
      <p style={{color:'#f87171'}}>{error || 'Case not found'}</p>
      <button className="cd-btn-outline" onClick={() => navigate('/cases')}>← Back to Cases</button>
    </div>
  );

  const c = caseDetails;

  return (
    <PageContainer variant="default">
      <div className="cd-wrap">

        {/* ── HEADER ── */}
        <div className="cd-header">
          <div className="cd-header-left">
            <button className="cd-back-btn" onClick={() => navigate('/cases')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
              Cases
            </button>
            <div className="cd-case-num">{c.case_number}</div>
            <h1 className="cd-title">{c.title}</h1>
            <div className="cd-header-badges">
              <span className={`cd-badge ${statusCls(c.status)}`}>{c.status}</span>
              <span className={`cd-priority ${priorityCls(c.priority)}`}>{c.priority || 'Medium'}</span>
              {c.crime_type && <span className="cd-crime-badge">{c.crime_type}</span>}
            </div>
          </div>
          <div className="cd-header-actions">
            {!isEditing ? (
              <>
                {c.status !== 'Closed' && (
                  <button className="cd-btn-danger" onClick={handleCloseCase}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>
                    Close Case
                  </button>
                )}
                <button className="cd-btn-outline" onClick={() => setIsEditing(true)}>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                  Edit
                </button>
                <button className="cd-btn-ghost" onClick={handleDelete}>Delete</button>
              </>
            ) : (
              <>
                <button className="cd-btn-primary" onClick={handleUpdate} disabled={saving}>{saving ? 'Saving...' : 'Save Changes'}</button>
                <button className="cd-btn-outline" onClick={() => { setIsEditing(false); setEditData(c); }}>Cancel</button>
              </>
            )}
          </div>
        </div>

        {error && <div className="cd-error-banner">{error}</div>}

        {/* ── SPLIT LAYOUT ── */}
        <div className="cd-layout">

          {/* ── LEFT PANEL ── */}
          <aside className="cd-left">

            {/* Case Summary */}
            <div className="cd-card">
              <div className="cd-card-title">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>
                Case Summary
              </div>
              <div className="cd-meta-list">
                {[
                  { label: 'Crime Type', value: c.crime_type || '—' },
                  { label: 'Location',   value: c.location   || '—' },
                  { label: 'Incident',   value: fmtDate(c.incident_date) },
                  { label: 'Officer ID', value: c.officer_id, mono: true },
                  { label: 'Opened',     value: fmtDate(c.created_at), muted: true },
                  { label: 'Updated',    value: fmtDate(c.updated_at), muted: true },
                ].map(row => (
                  <div key={row.label} className="cd-meta-row">
                    <span className="cd-meta-lbl">{row.label}</span>
                    <span className={`cd-meta-val${row.mono ? ' cd-mono' : row.muted ? ' cd-muted' : ''}`}>{row.value}</span>
                  </div>
                ))}
              </div>
              {isEditing && (
                <div className="cd-edit-fields">
                  <div className="cd-fg">
                    <label className="cd-lbl">Status</label>
                    <select name="status" className="cd-input" value={editData.status} onChange={handleChange}>
                      {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="cd-fg">
                    <label className="cd-lbl">Priority</label>
                    <select name="priority" className="cd-input" value={editData.priority || 'Medium'} onChange={handleChange}>
                      {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="cd-fg">
                    <label className="cd-lbl">Crime Type</label>
                    <input type="text" name="crime_type" className="cd-input" value={editData.crime_type || ''} onChange={handleChange} placeholder="e.g. Homicide" />
                  </div>
                  <div className="cd-fg">
                    <label className="cd-lbl">Location</label>
                    <input type="text" name="location" className="cd-input" value={editData.location || ''} onChange={handleChange} />
                  </div>
                  <div className="cd-fg">
                    <label className="cd-lbl">Incident Date</label>
                    <input type="date" name="incident_date" className="cd-input" value={editData.incident_date ? editData.incident_date.split('T')[0] : ''} onChange={handleChange} />
                  </div>
                  <div className="cd-fg">
                    <label className="cd-lbl">Description</label>
                    <textarea name="description" className="cd-input" rows="4" value={editData.description || ''} onChange={handleChange} style={{resize:'vertical'}} />
                  </div>
                </div>
              )}
            </div>

            {/* Linked Suspects */}
            <div className="cd-card">
              <div className="cd-card-title">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/></svg>
                Linked Suspects
                <span className="cd-count">{DUMMY_SUSPECTS.length}</span>
              </div>
              <div className="cd-suspects-list">
                {DUMMY_SUSPECTS.map(s => (
                  <SuspectCard key={s.id} suspect={s} onView={() => navigate('/database')} />
                ))}
              </div>
              <button className="cd-link-btn" onClick={() => navigate('/database')}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/></svg>
                Link from Database
              </button>
            </div>

            {/* Evidence */}
            <div className="cd-card">
              <div className="cd-card-title">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M20 6h-2.18c.07-.44.18-.88.18-1.36C18 2.06 15.96 0 13.36 0c-1.4 0-2.72.6-3.64 1.64L8 3.5 6.28 1.64C5.36.6 4.04 0 2.64 0 1.04 0 0 1.04 0 2.64c0 .48.11.92.18 1.36H0v2h20v-2zM8 18c0 1.1-.9 2-2 2s-2-.9-2-2V8H2v10c0 2.21 1.79 4 4 4s4-1.79 4-4V8H8v10zm8 0c0 1.1-.9 2-2 2s-2-.9-2-2V8h-2v10c0 2.21 1.79 4 4 4s4-1.79 4-4V8h-2v10z"/></svg>
                Evidence
                <span className="cd-count">{DUMMY_EVIDENCE.length}</span>
              </div>
              <div className="cd-evidence-list">
                {DUMMY_EVIDENCE.map(e => <EvidenceItem key={e.id} item={e} />)}
              </div>
              <button className="cd-link-btn">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></svg>
                Upload Evidence
              </button>
            </div>

            {/* Quick Actions */}
            <div className="cd-card">
              <div className="cd-card-title">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2.05v2.02c3.95.49 7 3.85 7 7.93 0 3.21-1.81 6-4.72 7.28L13 17v5l5-3-1.22-1.22C19.91 16.26 22 13.27 22 12c0-5.18-3.95-9.45-9-9.95zM11 2.05C5.95 2.55 2 6.82 2 12c0 3.27 2.09 6.26 5.22 7.78L6 21l5 3v-5l-2.28 2.28C6.81 20 5 17.21 5 14c0-4.08 3.05-7.44 7-7.93V2.05z"/></svg>
                Quick Actions
              </div>
              <div className="cd-quick-list">
                {[
                  { label: 'Run Sketch Search', path: '/search', icon: 'M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z' },
                  { label: 'Face Comparison',   path: '/compare', icon: 'M12,2A10,10 0 0,0 2,12A10,10 0 0,0 12,22A10,10 0 0,0 22,12A10,10 0 0,0 12,2M12,4A8,8 0 0,1 20,12A8,8 0 0,1 12,20A8,8 0 0,1 4,12A8,8 0 0,1 12,4M12,6A6,6 0 0,0 6,12A6,6 0 0,0 12,18A6,6 0 0,0 18,12A6,6 0 0,0 12,6Z' },
                  { label: 'Create Sketch',     path: '/sketch',  icon: 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z' },
                  { label: 'Criminal Database', path: '/database', icon: 'M12,3C7.58,3 4,4.79 4,7C4,9.21 7.58,11 12,11C16.42,11 20,9.21 20,7C20,4.79 16.42,3 12,3M4,9V12C4,14.21 7.58,16 12,16C16.42,16 20,14.21 20,12V9C20,11.21 16.42,13 12,13C7.58,13 4,11.21 4,9M4,14V17C4,19.21 7.58,21 12,21C16.42,21 20,19.21 20,17V14C20,16.21 16.42,18 12,18C7.58,18 4,16.21 4,14Z' },
                ].map(a => (
                  <button key={a.label} className="cd-quick-btn" onClick={() => navigate(a.path)}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d={a.icon}/></svg>
                    {a.label}
                  </button>
                ))}
              </div>
            </div>

          </aside>

          {/* ── RIGHT PANEL — TIMELINE ── */}
          <main className="cd-right">
            <div className="cd-card cd-timeline-card">
              <div className="cd-card-title cd-timeline-head">
                <div style={{display:'flex',alignItems:'center',gap:'0.5rem'}}>
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor"><path d="M13 2.05v2.02c3.95.49 7 3.85 7 7.93 0 3.21-1.81 6-4.72 7.28L13 17v5l5-3-1.22-1.22C19.91 16.26 22 13.27 22 12c0-5.18-3.95-9.45-9-9.95zM11 2.05C5.95 2.55 2 6.82 2 12c0 3.27 2.09 6.26 5.22 7.78L6 21l5 3v-5l-2.28 2.28C6.81 20 5 17.21 5 14c0-4.08 3.05-7.44 7-7.93V2.05z"/></svg>
                  Investigation Timeline
                </div>
                <span className="cd-count">{notes.length} entries</span>
              </div>

              {/* Description strip */}
              {c.description && (
                <div className="cd-desc-strip">
                  <span className="cd-desc-label">Overview</span>
                  <p className="cd-desc-text">{c.description}</p>
                </div>
              )}

              {/* Timeline entries */}
              <div className="cd-timeline">
                {notes.length === 0 ? (
                  <div className="cd-tl-empty">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2z"/></svg>
                    <p>No timeline entries yet. Add the first note below.</p>
                  </div>
                ) : (
                  notes.map((note, i) => (
                    <TimelineItem key={note.id} note={note} isLast={i === notes.length - 1} />
                  ))
                )}
              </div>

              {/* Add note form */}
              <div className="cd-note-form-wrap">
                <div className="cd-note-form-title">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/></svg>
                  Add Investigation Note
                </div>
                <form onSubmit={handleAddNote} className="cd-note-form">
                  <textarea
                    className="cd-note-input"
                    placeholder="Write an update, observation, lead, or AI finding..."
                    rows="3"
                    value={noteText}
                    onChange={e => setNoteText(e.target.value)}
                  />
                  <div className="cd-note-actions">
                    <button type="button" className="cd-btn-outline cd-btn-sm">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z"/></svg>
                      Upload Evidence
                    </button>
                    <button type="submit" className="cd-btn-primary cd-btn-sm" disabled={submitting || !noteText.trim()}>
                      {submitting ? 'Adding...' : 'Add Note'}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          </main>

        </div>
      </div>
    </PageContainer>
  );
};

export default CaseDetailsPage;
