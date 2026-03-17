import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid
} from 'recharts';
import PageContainer from '../layout/PageContainer';
import caseService from '../services/caseService';
import './CasesPage.css';

const STATUS_OPTIONS = ['Open', 'Under Investigation', 'Closed'];
const PRIORITY_OPTIONS = ['Low', 'Medium', 'High', 'Critical'];
const CRIME_TYPES = ['Homicide', 'Robbery', 'Fraud', 'Assault', 'Kidnapping', 'Cybercrime', 'Trafficking', 'Other'];
const INITIAL_FORM = { title: '', description: '', status: 'Open', priority: 'Medium', crime_type: '', location: '', incident_date: '' };

const DUMMY_CASES = [
  { id: 1, case_number: 'FF-2024-001', title: 'Downtown Bank Robbery', status: 'Under Investigation', priority: 'Critical', crime_type: 'Robbery', location: 'Downtown', incident_date: '2024-01-15', created_at: '2024-01-16T10:00:00Z' },
  { id: 2, case_number: 'FF-2024-002', title: 'Harbor District Homicide', status: 'Open', priority: 'High', crime_type: 'Homicide', location: 'Harbor District', incident_date: '2024-01-20', created_at: '2024-01-21T08:30:00Z' },
  { id: 3, case_number: 'FF-2024-003', title: 'Corporate Fraud Investigation', status: 'Closed', priority: 'Medium', crime_type: 'Fraud', location: 'Financial District', incident_date: '2023-12-10', created_at: '2023-12-11T14:00:00Z' },
  { id: 4, case_number: 'FF-2024-004', title: 'Westside Assault Series', status: 'Open', priority: 'High', crime_type: 'Assault', location: 'Westside', incident_date: '2024-01-25', created_at: '2024-01-26T09:00:00Z' },
  { id: 5, case_number: 'FF-2024-005', title: 'Missing Person — Jane Doe', status: 'Under Investigation', priority: 'Critical', crime_type: 'Kidnapping', location: 'Northgate', incident_date: '2024-01-28', created_at: '2024-01-28T16:00:00Z' },
  { id: 6, case_number: 'FF-2024-006', title: 'Cybercrime Network Breach', status: 'Open', priority: 'Medium', crime_type: 'Cybercrime', location: 'Online', incident_date: '2024-02-01', created_at: '2024-02-02T11:00:00Z' },
  { id: 7, case_number: 'FF-2024-007', title: 'Eastport Drug Trafficking', status: 'Closed', priority: 'High', crime_type: 'Trafficking', location: 'Eastport', incident_date: '2023-11-05', created_at: '2023-11-06T07:00:00Z' },
];

const PIE_COLORS = { 'Open': '#22c55e', 'Under Investigation': '#f59e0b', 'Closed': '#64748b' };

const PieTooltip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  return <div className="cp-tooltip"><span>{payload[0].name}</span><strong style={{color:'#06b6d4',marginLeft:8}}>{payload[0].value}</strong></div>;
};
const BarTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return <div className="cp-tooltip"><span>{label}</span><strong style={{color:'#06b6d4',marginLeft:8}}>{payload[0].value}</strong></div>;
};

// Stat card — inline SVG size set directly on the element
const StatCard = React.memo(({ label, value, colorClass, svgPath }) => (
  <div className={`cp-stat ${colorClass}`}>
    <div className="cp-stat-icon">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d={svgPath} />
      </svg>
    </div>
    <div>
      <div className="cp-stat-num">{value}</div>
      <div className="cp-stat-lbl">{label}</div>
    </div>
  </div>
));

const STATS_CONFIG = [
  { label: 'Total Cases',   colorClass: 'cp-stat-cyan',   key: 'total',        svgPath: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 3c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm7 13H5v-.23c0-.62.28-1.2.76-1.58C7.47 15.82 9.64 15 12 15s4.53.82 6.24 2.19c.48.38.76.97.76 1.58V19z' },
  { label: 'Open',          colorClass: 'cp-stat-green',  key: 'open',         svgPath: 'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z' },
  { label: 'Investigating', colorClass: 'cp-stat-yellow', key: 'investigating', svgPath: 'M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z' },
  { label: 'Closed',        colorClass: 'cp-stat-slate',  key: 'closed',       svgPath: 'M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z' },
  { label: 'Critical',      colorClass: 'cp-stat-red',    key: 'critical',     svgPath: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z' },
];

const CaseCharts = React.memo(({ cases }) => {
  const pieData = useMemo(() => {
    const c = {};
    cases.forEach(x => { c[x.status] = (c[x.status] || 0) + 1; });
    return Object.entries(c).map(([name, value]) => ({ name, value }));
  }, [cases]);

  const barData = useMemo(() => {
    const c = {};
    cases.forEach(x => { const t = x.crime_type || 'Unknown'; c[t] = (c[t] || 0) + 1; });
    return Object.entries(c).sort((a,b) => b[1]-a[1]).slice(0,7).map(([name,value]) => ({ name, value }));
  }, [cases]);

  return (
    <div className="cp-charts-grid">
      <div className="cp-chart-card">
        <div className="cp-chart-head">
          <span className="cp-chart-title">Status Distribution</span>
          <span className="cp-chart-sub">{cases.length} total</span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={78} paddingAngle={3} dataKey="value">
              {pieData.map(e => <Cell key={e.name} fill={PIE_COLORS[e.name] || '#94a3b8'} />)}
            </Pie>
            <Tooltip content={<PieTooltip />} />
          </PieChart>
        </ResponsiveContainer>
        <div className="cp-pie-legend">
          {pieData.map(e => (
            <div key={e.name} className="cp-pie-row">
              <span className="cp-pie-dot" style={{ background: PIE_COLORS[e.name] || '#94a3b8' }} />
              <span className="cp-pie-name">{e.name}</span>
              <span className="cp-pie-val">{e.value}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="cp-chart-card">
        <div className="cp-chart-head">
          <span className="cp-chart-title">Cases by Crime Type</span>
          <span className="cp-chart-sub">Top {barData.length}</span>
        </div>
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={barData} margin={{ top: 4, right: 8, left: -22, bottom: 36 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fill: '#64748b', fontSize: 11 }} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={{ fill: '#64748b', fontSize: 11 }} allowDecimals={false} />
            <Tooltip content={<BarTooltip />} cursor={{ fill: 'rgba(6,182,212,0.07)' }} />
            <Bar dataKey="value" fill="#06b6d4" radius={[4,4,0,0]} maxBarSize={38} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
});

const statusBadgeClass = s => s === 'Open' ? 'cp-badge-open' : s === 'Under Investigation' ? 'cp-badge-inv' : 'cp-badge-closed';
const priorityBadgeClass = p => ({ low:'cp-pri-low', medium:'cp-pri-med', high:'cp-pri-high', critical:'cp-pri-crit' })[(p||'medium').toLowerCase()] || 'cp-pri-med';

const CasesPage = () => {
  const navigate = useNavigate();
  const [cases, setCases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCase, setEditingCase] = useState(null);
  const [formData, setFormData] = useState(INITIAL_FORM);
  const [saving, setSaving] = useState(false);
  const [filterStatus, setFilterStatus] = useState('All');
  const [filterPriority, setFilterPriority] = useState('All');
  const [filterCrimeType, setFilterCrimeType] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortDir, setSortDir] = useState('desc');

  const fetchCases = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await caseService.getAllCases();
      const fetched = res.cases || [];
      setCases(fetched.length > 0 ? fetched : DUMMY_CASES);
    } catch (err) {
      setCases(DUMMY_CASES);
      if (!err.response) setError('Cannot connect to server — showing sample data.');
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchCases(); }, [fetchCases]);

  const handleSort = useCallback((field) => {
    setSortBy(prev => {
      if (prev === field) { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); return field; }
      setSortDir('desc'); return field;
    });
  }, []);

  const stats = useMemo(() => ({
    total: cases.length,
    open: cases.filter(c => c.status === 'Open').length,
    investigating: cases.filter(c => c.status === 'Under Investigation').length,
    closed: cases.filter(c => c.status === 'Closed').length,
    critical: cases.filter(c => c.priority === 'Critical').length,
  }), [cases]);

  const filteredCases = useMemo(() => cases
    .filter(c => {
      const q = searchQuery.toLowerCase();
      // Use logical OR with empty string to prevent null pointer exceptions
      return (filterStatus === 'All' || c.status === filterStatus)
        && (filterPriority === 'All' || c.priority === filterPriority)
        && (filterCrimeType === 'All' || c.crime_type === filterCrimeType)
        && (!q || (c.title || '').toLowerCase().includes(q) || (c.case_number || '').toLowerCase().includes(q) || (c.crime_type || '').toLowerCase().includes(q));
    })
    .sort((a, b) => {
      let vA = a[sortBy] || '', vB = b[sortBy] || '';
      if (sortBy === 'created_at' || sortBy === 'incident_date') {
        vA = vA ? new Date(vA).getTime() : 0; vB = vB ? new Date(vB).getTime() : 0;
      } else { vA = String(vA).toLowerCase(); vB = String(vB).toLowerCase(); }
      return vA < vB ? (sortDir === 'asc' ? -1 : 1) : vA > vB ? (sortDir === 'asc' ? 1 : -1) : 0;
    }), [cases, filterStatus, filterPriority, filterCrimeType, searchQuery, sortBy, sortDir]);

  const openNew = useCallback(() => { setEditingCase(null); setFormData(INITIAL_FORM); setIsModalOpen(true); }, []);
  const openEdit = useCallback((c) => {
    setEditingCase(c);
    setFormData({ title: c.title, description: c.description || '', status: c.status, priority: c.priority,
      crime_type: c.crime_type || '', location: c.location || '',
      incident_date: c.incident_date ? c.incident_date.split('T')[0] : '' });
    setIsModalOpen(true);
  }, []);

  const handleCloseCase = useCallback(async (c) => {
    if (!window.confirm(`Close case "${c.title}"?`)) return;
    try { await caseService.updateCase(c.id, { status: 'Closed' }); fetchCases(); }
    catch { setError('Failed to close case.'); }
  }, [fetchCases]);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      if (editingCase) await caseService.updateCase(editingCase.id, formData);
      else await caseService.createCase(formData);
      setIsModalOpen(false); setFormData(INITIAL_FORM); fetchCases();
    } catch { setError(editingCase ? 'Failed to update.' : 'Failed to create.'); }
    finally { setSaving(false); }
  };

  const clearFilters = useCallback(() => {
    setFilterStatus('All'); setFilterPriority('All'); setFilterCrimeType('All'); setSearchQuery('');
  }, []);

  const SortIcon = ({ field }) => (
    <span style={{ marginLeft: 3, fontSize: '0.7rem', opacity: sortBy === field ? 1 : 0.3, color: sortBy === field ? '#06b6d4' : 'inherit' }}>
      {sortBy === field ? (sortDir === 'asc' ? '↑' : '↓') : '↕'}
    </span>
  );

  return (
    <>
      <PageContainer variant="default">
        <div className="cp-wrap">

          {/* ── Header ── */}
          <div className="cp-header">
            <div>
              <h2 className="cp-title">Investigation Control Center</h2>
              <p className="cp-subtitle">Manage forensic investigations, track progress, and link evidence.</p>
            </div>
          </div>

          {/* ── Stats ── */}
          <div className="cp-stats-grid">
            {STATS_CONFIG.map(s => (
              <StatCard key={s.key} label={s.label} value={stats[s.key]} colorClass={s.colorClass} svgPath={s.svgPath} />
            ))}
          </div>

          {/* ── Charts ── */}
          {cases.length > 0 && <CaseCharts cases={cases} />}

          {/* ── Toolbar ── */}
          <div className="cp-toolbar">
            <div className="cp-search-box">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="#64748b" style={{position:'absolute',left:'0.7rem',top:'50%',transform:'translateY(-50%)',pointerEvents:'none',flexShrink:0}}>
                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
              </svg>
              <input className="cp-search-input" type="text" placeholder="Search by title, case #, crime type..."
                value={searchQuery} onChange={e => setSearchQuery(e.target.value)} />
              {searchQuery && <button className="cp-search-clear" onClick={() => setSearchQuery('')}>×</button>}
            </div>
            <div className="cp-filters">
              <select className="cp-select" value={filterStatus} onChange={e => setFilterStatus(e.target.value)}>
                <option value="All">All Statuses</option>
                {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <select className="cp-select" value={filterPriority} onChange={e => setFilterPriority(e.target.value)}>
                <option value="All">All Priorities</option>
                {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
              <select className="cp-select" value={filterCrimeType} onChange={e => setFilterCrimeType(e.target.value)}>
                <option value="All">All Crime Types</option>
                {CRIME_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <button className="cp-new-btn" onClick={openNew}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M19,13H13V19H11V13H5V11H11V5H13V11H19V13Z"/></svg>
              New Case
            </button>
          </div>

          {error && (
            <div className="cp-alert">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor" style={{flexShrink:0}}><path d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/></svg>
              <span>{error}</span>
              <button className="cp-alert-retry" onClick={fetchCases}>Retry</button>
            </div>
          )}

          {/* ── Table ── */}
          <div className="cp-table-card">
            <div className="cp-table-bar">
              <span className="cp-table-title">Active Cases</span>
              <span className="cp-table-sub">· Click a row to open details</span>
            </div>

            {loading ? (
              <div className="cp-loading"><div className="cp-spinner" /><span>Loading cases...</span></div>
            ) : filteredCases.length === 0 ? (
              <div className="cp-empty">
                <div style={{fontSize:'2.5rem',marginBottom:'0.75rem',opacity:0.5}}>📁</div>
                <h3 style={{margin:'0 0 0.4rem',fontSize:'1.1rem',color:'#f1f5f9'}}>{cases.length === 0 ? 'No Cases Found' : 'No Matching Cases'}</h3>
                <p style={{color:'#64748b',marginBottom:'1.25rem',fontSize:'0.875rem'}}>{cases.length === 0 ? "You haven't created any cases yet." : 'Try adjusting your filters.'}</p>
                <button className="cp-btn-outline" onClick={cases.length === 0 ? openNew : clearFilters}>
                  {cases.length === 0 ? 'Create First Case' : 'Clear Filters'}
                </button>
              </div>
            ) : (
              <>
                <div className="cp-count-bar">Showing <strong>{filteredCases.length}</strong> of <strong>{cases.length}</strong> cases</div>
                <div style={{overflowX:'auto'}}>
                  <table className="cp-table">
                    <thead>
                      <tr>
                        <th onClick={() => handleSort('case_number')} style={{cursor:'pointer'}}>Case # <SortIcon field="case_number" /></th>
                        <th onClick={() => handleSort('title')} style={{cursor:'pointer'}}>Title <SortIcon field="title" /></th>
                        <th onClick={() => handleSort('status')} style={{cursor:'pointer'}}>Status <SortIcon field="status" /></th>
                        <th onClick={() => handleSort('priority')} style={{cursor:'pointer'}}>Priority <SortIcon field="priority" /></th>
                        <th>Crime Type</th>
                        <th onClick={() => handleSort('incident_date')} style={{cursor:'pointer'}}>Date <SortIcon field="incident_date" /></th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredCases.map(c => (
                        <tr key={c.id} className="cp-row" onClick={() => navigate(`/cases/${c.id}`)}>
                          <td style={{fontFamily:'monospace',fontSize:'0.8rem',color:'#06b6d4',fontWeight:600,whiteSpace:'nowrap'}}>{c.case_number}</td>
                          <td style={{fontWeight:600,color:'#f8fafc',maxWidth:220}}>{c.title}</td>
                          <td><span className={`cp-badge ${statusBadgeClass(c.status)}`}>{c.status}</span></td>
                          <td><span className={`cp-priority ${priorityBadgeClass(c.priority)}`}>{c.priority || 'Medium'}</span></td>
                          <td style={{color:'#cbd5e1'}}>{c.crime_type || <span style={{color:'#334155'}}>—</span>}</td>
                          <td style={{color:'#64748b',fontSize:'0.8rem',whiteSpace:'nowrap'}}>{c.incident_date ? new Date(c.incident_date).toLocaleDateString() : <span style={{color:'#334155'}}>—</span>}</td>
                          <td onClick={e => e.stopPropagation()}>
                            <div style={{display:'flex',gap:'0.3rem',alignItems:'center'}}>
                              <button className="cp-act cp-act-view" title="View" onClick={() => navigate(`/cases/${c.id}`)}>
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>
                              </button>
                              <button className="cp-act cp-act-edit" title="Edit" onClick={() => openEdit(c)}>
                                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                              </button>
                              {c.status !== 'Closed' && (
                                <button className="cp-act cp-act-close" title="Close" onClick={() => handleCloseCase(c)}>
                                  <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z"/></svg>
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>

        </div>
      </PageContainer>

      {/* ── Modal ── */}
      {isModalOpen && (
        <div className="cp-modal-overlay" onClick={() => setIsModalOpen(false)}>
          <div className="cp-modal-box" onClick={e => e.stopPropagation()}>
            <div className="cp-modal-header">
              <h2 style={{margin:0,fontSize:'1.2rem',color:'#f8fafc'}}>{editingCase ? 'Edit Case' : 'Create New Case'}</h2>
              <button className="cp-modal-close" onClick={() => setIsModalOpen(false)}>×</button>
            </div>
            <form onSubmit={handleSubmit} style={{display:'flex',flexDirection:'column',gap:'1rem'}}>
              <div className="cp-fg">
                <label className="cp-label">Case Title *</label>
                <input type="text" name="title" className="cp-input" value={formData.title} onChange={handleChange} placeholder="e.g. Downtown Bank Robbery" required />
              </div>
              <div style={{display:'flex',gap:'1rem'}}>
                <div className="cp-fg" style={{flex:1}}>
                  <label className="cp-label">Status</label>
                  <select name="status" className="cp-input" value={formData.status} onChange={handleChange}>
                    {STATUS_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="cp-fg" style={{flex:1}}>
                  <label className="cp-label">Priority</label>
                  <select name="priority" className="cp-input" value={formData.priority} onChange={handleChange}>
                    {PRIORITY_OPTIONS.map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                </div>
              </div>
              <div style={{display:'flex',gap:'1rem'}}>
                <div className="cp-fg" style={{flex:1}}>
                  <label className="cp-label">Crime Type</label>
                  <input type="text" name="crime_type" className="cp-input" value={formData.crime_type} onChange={handleChange} placeholder="e.g. Homicide" />
                </div>
                <div className="cp-fg" style={{flex:1}}>
                  <label className="cp-label">Incident Date</label>
                  <input type="date" name="incident_date" className="cp-input" value={formData.incident_date} onChange={handleChange} />
                </div>
              </div>
              <div className="cp-fg">
                <label className="cp-label">Location</label>
                <input type="text" name="location" className="cp-input" value={formData.location} onChange={handleChange} placeholder="City, Area" />
              </div>
              <div className="cp-fg">
                <label className="cp-label">Description</label>
                <textarea name="description" className="cp-input" value={formData.description} onChange={handleChange} rows="3" placeholder="Background details..." style={{resize:'vertical',minHeight:75}} />
              </div>
              <div style={{display:'flex',justifyContent:'flex-end',gap:'0.75rem',paddingTop:'1rem',borderTop:'1px solid rgba(255,255,255,0.08)'}}>
                <button type="button" className="cp-btn-outline" onClick={() => setIsModalOpen(false)}>Cancel</button>
                <button type="submit" className="cp-new-btn" disabled={saving}>
                  {saving ? (editingCase ? 'Saving...' : 'Creating...') : (editingCase ? 'Save Changes' : 'Create Case')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};

export default CasesPage;
