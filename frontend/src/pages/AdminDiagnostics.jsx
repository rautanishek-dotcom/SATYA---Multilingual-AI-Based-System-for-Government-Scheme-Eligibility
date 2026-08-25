import React, { useEffect, useState } from 'react';
import { Activity, Server, FileText, Database, Shield, Zap, TrendingUp, AlertTriangle } from 'lucide-react';

const API_BASE = 'http://localhost:5000/api/vault';

export default function AdminDiagnostics() {
  const [health, setHealth] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // Auto-refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [healthRes, analyticsRes] = await Promise.all([
        fetch(`${API_BASE}/health`),
        fetch(`${API_BASE}/analytics`)
      ]);
      
      const healthData = await healthRes.json();
      const analyticsData = await analyticsRes.json();

      setHealth(healthData);
      setAnalytics(analyticsData);
      setError(null);
    } catch {
      console.error('Diagnostics fetch failed');
      setError('Could not connect to the backend server.');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <Activity className="spin" size={32} color="#3b82f6" />
        <div style={{ marginTop: 16, color: '#475569' }}>Loading Diagnostics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={styles.errorContainer}>
        <AlertTriangle size={48} color="#ef4444" />
        <h2 style={{ marginTop: 16, color: '#0f172a' }}>Connection Error</h2>
        <p style={{ color: '#475569' }}>{error}</p>
        <button onClick={fetchData} style={styles.btnPrimary}>Retry</button>
      </div>
    );
  }

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div>
          <h1 style={styles.title}>System Diagnostics</h1>
          <p style={styles.subtitle}>Real-time health, performance, and usage metrics</p>
        </div>
        <div style={styles.statusBadge(health?.status)}>
          <div style={styles.statusDot(health?.status)} />
          {health?.status || 'Unknown'}
        </div>
      </header>

      <div style={styles.grid}>
        {/* Health Panel */}
        <section style={styles.panel}>
          <div style={styles.panelHeader}>
            <Server size={20} color="#3b82f6" />
            <h2 style={styles.panelTitle}>Subsystem Health</h2>
          </div>
          <div style={styles.list}>
            {Object.entries(health?.subsystems || {}).map(([key, value]) => (
              <div key={key} style={styles.listItem}>
                <div style={{ textTransform: 'capitalize', fontWeight: 600, color: '#334155' }}>
                  {key.replace(/_/g, ' ')}
                </div>
                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {value.model_loaded !== undefined && (
                    <span style={{ fontSize: '11px', color: '#64748b' }}>
                      Model: {value.model_loaded ? 'Loaded' : 'Pending'}
                    </span>
                  )}
                  <span style={styles.pill(value.status)}>
                    {value.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Analytics Panel */}
        <section style={styles.panel}>
          <div style={styles.panelHeader}>
            <TrendingUp size={20} color="#10b981" />
            <h2 style={styles.panelTitle}>Performance & Quality</h2>
          </div>
          <div style={styles.metricsGrid}>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>OCR Success Rate</div>
              <div style={styles.metricValue}>{analytics?.ocr_success_rate || 0}%</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Avg Confidence</div>
              <div style={styles.metricValue}>{analytics?.average_confidence || 0}%</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Avg Processing Time</div>
              <div style={styles.metricValue}>{analytics?.average_processing_time || 0}s</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Verification Rate</div>
              <div style={styles.metricValue}>{analytics?.verification_success_rate || 0}%</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Avg Identity Score</div>
              <div style={styles.metricValue}>{analytics?.average_identity_match_score || 0}%</div>
            </div>
            <div style={styles.metricCard}>
              <div style={styles.metricLabel}>Duplicate Rate</div>
              <div style={styles.metricValue}>{analytics?.duplicate_rate || 0}%</div>
            </div>
          </div>
        </section>

        {/* Document Stats Panel */}
        <section style={styles.panel}>
          <div style={styles.panelHeader}>
            <FileText size={20} color="#8b5cf6" />
            <h2 style={styles.panelTitle}>Document Vault Usage</h2>
          </div>
          
          <div style={{ display: 'flex', gap: '20px', marginBottom: '24px' }}>
             <div style={styles.statBox}>
               <div style={styles.statBoxLabel}>Total Documents</div>
               <div style={styles.statBoxValue}>{analytics?.total_documents || 0}</div>
             </div>
             <div style={styles.statBox}>
               <div style={styles.statBoxLabel}>Awaiting Review</div>
               <div style={{ ...styles.statBoxValue, color: '#f59e0b' }}>{analytics?.awaiting_review || 0}</div>
             </div>
          </div>

          <h3 style={{ fontSize: '13px', textTransform: 'uppercase', color: '#64748b', letterSpacing: '0.05em', marginBottom: '12px' }}>
            Document Types
          </h3>
          <div style={styles.list}>
            {Object.entries(analytics?.document_type_distribution || {}).map(([type, count]) => (
              <div key={type} style={styles.listItem}>
                <div style={{ color: '#334155', fontWeight: 500 }}>
                  {type === 'other_document' ? 'Other' : type}
                </div>
                <div style={{ fontWeight: 700, color: '#0f172a' }}>{count}</div>
              </div>
            ))}
            {Object.keys(analytics?.document_type_distribution || {}).length === 0 && (
              <div style={{ color: '#94a3b8', fontStyle: 'italic', padding: '8px 0' }}>No documents stored yet.</div>
            )}
          </div>
        </section>

      </div>
      
      <style>{`
        .spin { animation: spin 1.5s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const styles = {
  page: {
    padding: '40px',
    maxWidth: '1200px',
    margin: '0 auto',
    fontFamily: 'Inter, system-ui, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '32px',
  },
  title: {
    margin: '0 0 8px 0',
    fontSize: '28px',
    fontWeight: 800,
    color: '#0f172a',
  },
  subtitle: {
    margin: 0,
    color: '#64748b',
    fontSize: '15px',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
    gap: '24px',
  },
  panel: {
    background: '#ffffff',
    borderRadius: '16px',
    padding: '24px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
    border: '1px solid #f1f5f9',
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '20px',
    borderBottom: '1px solid #f1f5f9',
    paddingBottom: '16px',
  },
  panelTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: 700,
    color: '#0f172a',
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  listItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px',
    background: '#f8fafc',
    borderRadius: '8px',
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  metricCard: {
    padding: '16px',
    background: '#f8fafc',
    borderRadius: '12px',
    border: '1px solid #f1f5f9',
  },
  metricLabel: {
    fontSize: '12px',
    color: '#64748b',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginBottom: '8px',
  },
  metricValue: {
    fontSize: '24px',
    fontWeight: 800,
    color: '#0f172a',
  },
  statBox: {
    flex: 1,
    padding: '20px',
    borderRadius: '12px',
    background: '#f8fafc',
    border: '1px solid #e2e8f0',
  },
  statBoxLabel: {
    fontSize: '13px',
    color: '#64748b',
    fontWeight: 600,
    marginBottom: '8px',
  },
  statBoxValue: {
    fontSize: '32px',
    fontWeight: 800,
    color: '#0f172a',
  },
  pill: (status) => ({
    padding: '4px 10px',
    borderRadius: '999px',
    fontSize: '12px',
    fontWeight: 700,
    background: status === 'Healthy' || status === 'Available' ? '#dcfce7' : status === 'Degraded' ? '#fef3c7' : '#fee2e2',
    color: status === 'Healthy' || status === 'Available' ? '#166534' : status === 'Degraded' ? '#92400e' : '#991b1b',
  }),
  statusBadge: (status) => ({
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    borderRadius: '999px',
    background: status === 'Healthy' ? '#ecfdf5' : status === 'Degraded' ? '#fffbeb' : '#fef2f2',
    color: status === 'Healthy' ? '#065f46' : status === 'Degraded' ? '#b45309' : '#991b1b',
    fontWeight: 700,
    border: `1px solid ${status === 'Healthy' ? '#a7f3d0' : status === 'Degraded' ? '#fde68a' : '#fecaca'}`,
  }),
  statusDot: (status) => ({
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: status === 'Healthy' ? '#10b981' : status === 'Degraded' ? '#f59e0b' : '#ef4444',
  }),
  loadingContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: '#f8fafc',
  },
  errorContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    height: '100vh',
    background: '#f8fafc',
  },
  btnPrimary: {
    marginTop: '20px',
    padding: '10px 24px',
    background: '#3b82f6',
    color: 'white',
    border: 'none',
    borderRadius: '8px',
    fontWeight: 600,
    cursor: 'pointer',
  }
};
