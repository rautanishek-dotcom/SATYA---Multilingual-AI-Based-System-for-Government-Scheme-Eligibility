import React, { useCallback, useEffect, useMemo, useDeferredValue, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Shield, Upload, Search, RefreshCw, ShieldCheck, Lock,
  AlertTriangle, CheckCircle2, XCircle, Clock3, Sparkles, Trash2,
  ChevronRight, BadgeInfo, BadgeAlert, BadgeCheck, Loader2, FileSearch,
  Fingerprint, UserRound, CalendarDays, VenetianMask
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import DocumentReviewModal from '../components/DocumentReviewModal';
import OTPVerificationModal from '../components/OTPVerificationModal';

const API_BASE = 'http://localhost:5000/api/vault';
const SUPPORTS = [
  'Aadhaar Card',
  'Aadhaar Offline e-KYC',
  'PAN Card',
  'Passport',
  'Driving Licence',
  'Voter ID',
  'Ration Card',
  'Certificates',
];

const formatDate = (value) => {
  if (!value) return 'Not Available';
  try {
    return new Date(value).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
  } catch {
    return 'Not Available';
  }
};

const displayValue = (value) => {
  if (value === null || value === undefined || value === '') return 'Not Available';
  if (typeof value === 'object') {
    const candidate = value.value ?? value.Value ?? value.text ?? value.Text ?? value.display ?? value.Display;
    return candidate ? String(candidate) : 'Not Available';
  }
  return String(value);
};

const normalizeIdentityProfile = (profile = {}) => ({
  user_id: displayValue(profile.user_id || profile.userId || ''),
  full_name: displayValue(profile.full_name || profile.fullName || ''),
  dob: displayValue(profile.dob || ''),
  gender: displayValue(profile.gender || ''),
  masked_aadhaar: displayValue(profile.masked_aadhaar || profile.maskedAadhaar || ''),
  aadhaar_reference_id: displayValue(profile.aadhaar_reference_id || profile.aadhaarReferenceId || ''),
  identity_locked: Boolean(profile.identity_locked ?? profile.identityLocked),
  verification_status: displayValue(profile.verification_status || profile.verificationStatus || (profile.identity_locked || profile.identityLocked ? 'Verified' : '')),
  confidence: Number(profile.confidence ?? 0) || 0,
  verified_at: displayValue(profile.verified_at || profile.verifiedAt || ''),
  document_type: displayValue(profile.document_type || profile.documentType || ''),
  verification_method: displayValue(profile.verification_method || profile.verificationMethod || ''),
  last_reset_at: displayValue(profile.last_reset_at || profile.lastResetAt || ''),
});

const summarizeLogResult = (step, result) => {
  if (result === null || result === undefined || result === '') {
    return 'No details available';
  }
  if (typeof result === 'string') {
    return result.length > 180 ? `${result.slice(0, 177)}...` : result;
  }
  if (Array.isArray(result)) {
    if (!result.length) return 'No details available';
    const top = result.slice(0, 3).map((item) => {
      if (typeof item === 'string') return item;
      const engine = item.engine || item.verification_engine || item.step || 'item';
      const confidence = item.confidence !== undefined ? `${Math.round(Number(item.confidence) || 0)}%` : '';
      const text = item.text || item.value || item.label || item.message || '';
      return [engine, confidence, text].filter(Boolean).join(': ');
    });
    return top.join(' | ');
  }
  if (typeof result === 'object') {
    if (step === 'quality') {
      const score = result.quality_score !== undefined ? `${Math.round(Number(result.quality_score) || 0)}%` : 'n/a';
      const issues = Array.isArray(result.issues) && result.issues.length ? `Issues: ${result.issues.slice(0, 2).join(', ')}` : 'No quality issues';
      return `Quality ${score} - ${issues}`;
    }
    if (step === 'classification') {
      return `${displayValue(result.document_label || result.document_type || 'Document')} (${displayValue(result.confidence || 'n/a')} confidence)`;
    }
    if (step === 'identity') {
      return `Identity match score ${displayValue(result.score || result.identityMatchScore || 'n/a')} - ${displayValue(result.message || 'Reviewed')}`;
    }
    if (step === 'qr') {
      return `${result.available ? 'QR available' : 'QR unavailable'}${result.passed === false ? ', mismatch detected' : ''}`;
    }
    if (step === 'ocr') {
      const first = result[0] || {};
      return `${displayValue(first.engine || 'OCR')} ${first.confidence !== undefined ? `${Math.round(Number(first.confidence) || 0)}%` : ''}`.trim();
    }
    const entries = Object.entries(result)
      .filter(([key]) => !['raw_text', 'raw_xml', 'candidates', 'sealed_payload'].includes(key))
      .slice(0, 3)
      .map(([key, value]) => `${key.replace(/_/g, ' ')}: ${displayValue(value)}`);
    return entries.length ? entries.join(' | ') : 'Structured result available';
  }
  return String(result);
};

const getUser = () => {
  try {
    const raw = localStorage.getItem('satya_user');
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const apiFetch = async (path, options = {}) => {
  const token = localStorage.getItem('satya_token');
  const headers = { ...(options.headers || {}) };
  if (token) headers.Authorization = `Bearer ${token}`;
  return fetch(`${API_BASE}${path}`, { ...options, headers });
};

function Badge({ children, tone = 'slate' }) {
  const colors = {
    slate: { bg: '#e2e8f0', fg: '#334155' },
    blue: { bg: '#dbeafe', fg: '#1d4ed8' },
    green: { bg: '#dcfce7', fg: '#166534' },
    amber: { bg: '#fef3c7', fg: '#92400e' },
    red: { bg: '#fee2e2', fg: '#991b1b' },
    purple: { bg: '#ede9fe', fg: '#6d28d9' },
  }[tone];

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 6,
      padding: '6px 10px',
      borderRadius: 999,
      fontSize: 12,
      fontWeight: 700,
      background: colors.bg,
      color: colors.fg,
      letterSpacing: '0.01em',
    }}>
      {children}
    </span>
  );
}

function StatCard({ icon: Icon, label, value, accent, subtext }) {
  return (
    <div style={{
      background: 'rgba(255,255,255,0.85)',
      border: '1px solid rgba(148,163,184,0.15)',
      borderRadius: 24,
      padding: '20px 22px',
      display: 'flex',
      alignItems: 'center',
      gap: 16,
      boxShadow: '0 18px 50px rgba(15,23,42,0.07)',
      backdropFilter: 'blur(16px)',
    }}>
      <div style={{
        width: 52,
        height: 52,
        borderRadius: 18,
        background: `${accent}18`,
        display: 'grid',
        placeItems: 'center',
        color: accent,
        flexShrink: 0,
      }}>
        {Icon && <Icon size={24} />}
      </div>
      <div>
        <div style={{ color: '#64748b', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{label}</div>
        <div style={{ color: '#0f172a', fontSize: 26, fontWeight: 900, lineHeight: 1.1, marginTop: 2 }}>{value}</div>
        {subtext && <div style={{ color: '#94a3b8', fontSize: 12, marginTop: 2 }}>{subtext}</div>}
      </div>
    </div>
  );
}

function LockRow({ icon: Icon, label, value }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0' }}>
      {Icon && <Icon size={15} style={{ color: '#64748b', flexShrink: 0 }} />}
      <span style={{ color: '#64748b', fontSize: 13, minWidth: 130 }}>{label}</span>
      <span style={{ color: '#0f172a', fontSize: 13, fontWeight: 700 }}>{value || 'Not Available'}</span>
    </div>
  );
}


function DocumentCard({ doc, onDelete, onDownload, onPreview }) {
  const status = (doc.document_status || doc.verification_status || '').toUpperCase();
  const matchScore = Math.round(doc.identity_match_score || 0);
  const confidence = Math.round(doc.confidence || 0);
  const risk = doc.document_summary?.risk || 'low';
  
  const isAccepted = status === 'ACCEPTED';
  const isRejected = status === 'REJECTED';
  const isReview = status === 'AWAITING REVIEW' || status === 'AWAITING_REVIEW';
  
  const tone = isAccepted ? 'green' : isRejected ? 'red' : isReview ? 'amber' : 'slate';
  const statusLabel = isAccepted ? 'Accepted' : isRejected ? 'Rejected' : isReview ? 'Awaiting Review' : status || 'Pending';

  return (
    <div
      style={{
        background: 'rgba(255,255,255,0.9)',
        border: '1px solid rgba(148,163,184,0.14)',
        borderRadius: 24,
        padding: 18,
        boxShadow: '0 18px 45px rgba(15,23,42,0.08)',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 10 }}>
            <Badge tone={tone}>{statusLabel}</Badge>
            <Badge tone="blue">{doc.document_label || doc.document_type || 'Document'}</Badge>
            <Badge tone={risk === 'high' ? 'red' : risk === 'medium' ? 'amber' : 'green'}>{risk} risk</Badge>
          </div>
          <h3 style={{ margin: 0, color: '#0f172a', fontSize: 18, fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {doc.document_name || doc.document_label || doc.document_type || 'Vault Document'}
          </h3>
          <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>
            Verified on {formatDate(doc.created_at)}
          </div>
        </div>
        <div style={{
          width: 70,
          height: 70,
          borderRadius: '50%',
          border: '8px solid rgba(59,130,246,0.12)',
          display: 'grid',
          placeItems: 'center',
          color: '#0f172a',
          fontWeight: 800,
          fontSize: 16,
          background: 'linear-gradient(135deg, rgba(14,165,233,0.08), rgba(16,185,129,0.08))',
        }}>
          {confidence}%
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: 10, marginTop: 16 }}>
        <MiniStat label="Match" value={`${matchScore}%`} />
        <MiniStat label="Confidence" value={`${confidence}%`} />
        <MiniStat label="Quality" value={doc.quality_score ? `${Math.round(doc.quality_score)}%` : 'n/a'} />
      </div>

      <div style={{ marginTop: 14, color: '#334155', fontSize: 13, lineHeight: 1.6 }}>
        {doc.document_summary ? (
          <div>{doc.document_summary.missingFields?.length ? `Missing fields: ${doc.document_summary.missingFields.join(', ')}` : 'All required fields were extracted.'}</div>
        ) : (
          <div>{doc.verification_status === 'REJECTED' ? 'Rejected by the identity and fraud checks.' : 'Stored in the secure vault.'}</div>
        )}
      </div>

      {Array.isArray(doc.verification_logs) && doc.verification_logs.length > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary style={{ cursor: 'pointer', color: '#2563eb', fontSize: 13, fontWeight: 700 }}>
            View verification trail
          </summary>
          <div style={{ marginTop: 10, display: 'grid', gap: 8 }}>
            {doc.verification_logs.slice(0, 4).map((log, idx) => (
              <div key={idx} style={{ background: '#f8fafc', borderRadius: 12, padding: 10, fontSize: 12, color: '#334155' }}>
                <strong>{log.step}:</strong> {summarizeLogResult(log.step, log.result)}
              </div>
            ))}
          </div>
        </details>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 16 }}>
        <div style={{ color: '#64748b', fontSize: 12 }}>
          Hash {doc.hash ? `${String(doc.hash).slice(0, 10)}...` : 'n/a'}
        </div>
        <div style={{ display: 'flex', gap: 12 }}>
          <button type="button" onClick={() => onPreview(doc._id)} style={{ border: 'none', background: 'transparent', color: '#2563eb', fontWeight: 700, cursor: 'pointer' }}>Preview</button>
          <button type="button" onClick={() => onDownload(doc._id)} style={{ border: 'none', background: 'transparent', color: '#2563eb', fontWeight: 700, cursor: 'pointer' }}>Download</button>
          <button
            type="button"
            onClick={() => onDelete(doc._id)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 8,
              border: 'none',
              background: 'transparent',
              color: '#dc2626',
              fontWeight: 700,
              cursor: 'pointer',
            }}
          >
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>
    </div>
  );
}

function MiniStat({ label, value }) {
  return (
    <div style={{
      background: '#f8fafc',
      borderRadius: 16,
      padding: '12px 14px',
      border: '1px solid rgba(148,163,184,0.12)',
    }}>
      <div style={{ color: '#64748b', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
        {label}
      </div>
      <div style={{ color: '#0f172a', fontSize: 16, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}

function IdentityLockCard({ identity, resetAvailable, onReset }) {
  const locked = identity?.identityLocked;
  const verificationLabel = identity?.verification_method
    ? identity.verification_method
    : locked
      ? 'Aadhaar Verification'
      : 'Not Available';
  const statusLabel = identity?.verification_status || (locked ? 'Verified' : 'Not Available');
  const documentTypeLabel = identity?.document_type || (locked ? 'Aadhaar Card' : 'Not Available');
  return (
    <div style={{
      background: locked
        ? 'linear-gradient(135deg, rgba(34,197,94,0.12), rgba(14,165,233,0.10))'
        : 'linear-gradient(135deg, rgba(245,158,11,0.14), rgba(239,68,68,0.08))',
      border: `1px solid ${locked ? 'rgba(34,197,94,0.18)' : 'rgba(245,158,11,0.2)'}`,
      borderRadius: 28,
      padding: 24,
      backdropFilter: 'blur(16px)',
      boxShadow: '0 24px 60px rgba(15,23,42,0.10)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 46,
              height: 46,
              borderRadius: 16,
              background: locked ? '#16a34a' : '#d97706',
              color: '#fff',
              display: 'grid',
              placeItems: 'center',
            }}>
              <ShieldCheck size={22} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>Identity Lock</div>
              <div style={{ color: '#334155', fontSize: 13 }}>
                {locked ? 'Verified identity is locked to this account' : 'Aadhaar verification is required to unlock the vault'}
              </div>
            </div>
          </div>
          {locked ? (
            <div style={{ display: 'grid', gap: 8, color: '#0f172a' }}>
              <LockRow icon={UserRound} label="Full Name" value={displayValue(identity?.full_name)} />
              <LockRow icon={Fingerprint} label="Masked Aadhaar" value={displayValue(identity?.masked_aadhaar)} />
              <LockRow icon={CalendarDays} label="Date of Birth" value={displayValue(identity?.dob)} />
              <LockRow icon={VenetianMask} label="Gender" value={displayValue(identity?.gender)} />
              <LockRow icon={Shield} label="Verification Status" value={statusLabel} />
              <LockRow icon={Sparkles} label="Confidence" value={identity?.confidence ? `${Math.round(identity.confidence)}%` : 'Not Available'} />
              <LockRow icon={Clock3} label="Verification Date" value={formatDate(identity?.verified_at)} />
              <LockRow icon={FileSearch} label="Document Type" value={documentTypeLabel} />
              <LockRow icon={BadgeCheck} label="Verification Method" value={verificationLabel} />
            </div>
          ) : (
            <div style={{ marginTop: 10, maxWidth: 680 }}>
              <p style={{ color: '#1f2937', margin: 0, lineHeight: 1.7 }}>
                Upload and verify your Aadhaar first. SATYA will then create a permanent Identity Lock for this account.
              </p>
              <p style={{ color: '#7c2d12', marginTop: 12, lineHeight: 1.7, fontSize: 13 }}>
                SATYA is not affiliated with any government agency and does not replace official government verification.
              </p>
            </div>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 10 }}>
          <Badge tone={locked ? 'green' : 'amber'}>
            {locked ? 'Identity verified' : 'Verification pending'}
          </Badge>
          <button
            type="button"
            disabled={!locked || !resetAvailable}
            onClick={onReset}
            style={{
              border: 'none',
              borderRadius: 14,
              padding: '12px 16px',
              cursor: !locked || !resetAvailable ? 'not-allowed' : 'pointer',
              background: !locked || !resetAvailable ? '#cbd5e1' : '#0f172a',
              color: '#fff',
              fontWeight: 800,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
            }}
          >
            Reset Identity
            <ChevronRight size={16} />
          </button>
          {!resetAvailable && <div style={{ color: '#7c2d12', fontSize: 12 }}>Reset cooldown is active.</div>}
        </div>
      </div>
    </div>
  );
}

function Modal({ title, subtitle, children, onClose, width = 620 }) {
  return (
    <div style={styles.modalOverlay} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} style={{ ...styles.modalCard, width, maxWidth: 'calc(100vw - 32px)' }}>
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{ width: 42, height: 42, borderRadius: 14, background: '#fee2e2', color: '#dc2626', display: 'grid', placeItems: 'center' }}>
              <AlertTriangle size={20} />
            </div>
            <div>
              <div style={{ fontSize: 20, fontWeight: 900, color: '#0f172a' }}>{title}</div>
              {subtitle && <div style={{ color: '#64748b', fontSize: 13, marginTop: 4 }}>{subtitle}</div>}
            </div>
          </div>
        </div>
        {children}
      </div>
    </div>
  );
}

export default function DocumentVault() {
  const user = useMemo(() => getUser(), []);
  const userId = user?.id || user?._id || '';
  const navigate = useNavigate();

  const [documents, setDocuments] = useState([]);
  const [identity, setIdentity] = useState({ identityLocked: false });
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [stage, setStage] = useState('idle');
  const [query, setQuery] = useState('');
  const deferredQuery = useDeferredValue(query);
  const [pendingUpload, setPendingUpload] = useState(null);
  const [confirmation, setConfirmation] = useState(null);
  const [reviewDoc, setReviewDoc] = useState(null); // New state for review modal
  
  // OTP State for document review confirmation
  const [showOTPModal, setShowOTPModal] = useState(false);
  const [pendingReviewData, setPendingReviewData] = useState(null);
  const [banner, setBanner] = useState(null);
  const [error, setError] = useState(null);
  const [resetOpen, setResetOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState('');
  const [resetBusy, setResetBusy] = useState(false);

  const fetchIdentity = useCallback(async () => {
    if (!userId) return;
    const res = await apiFetch(`/identity?user_id=${encodeURIComponent(userId)}`);
    const data = await res.json();
    if (res.ok) {
      setIdentity(normalizeIdentityProfile({
        ...(data.identityProfile || {}),
        identityLocked: data.identityLocked,
        resetAvailable: data.resetAvailable,
        lastResetAt: data.lastResetAt,
        nextResetAllowedAt: data.nextResetAllowedAt,
      }));
    }
  }, [userId]);

  const fetchVault = useCallback(async (search = '') => {
    if (!userId) return;
    setLoading(true);
    const path = search ? `/search?user_id=${encodeURIComponent(userId)}&q=${encodeURIComponent(search)}` : `/?user_id=${encodeURIComponent(userId)}`;
    const res = await apiFetch(path);
    const data = await res.json();
    if (res.ok) {
      setDocuments(data.documents || []);
      if (data.identity_profile || data.identity_locked !== undefined) {
        setIdentity((prev) => normalizeIdentityProfile({
          ...prev,
          ...(data.identity_profile || {}),
          identityLocked: data.identity_locked ?? prev.identityLocked,
        }));
      }
    } else {
      setError({ title: 'Vault load failed', message: data.error || 'Could not load your vault.' });
    }
    setLoading(false);
  }, [userId]);

  useEffect(() => {
    let active = true;
    const boot = async () => {
      if (!userId) {
        setLoading(false);
        return;
      }
      await Promise.all([fetchIdentity(), fetchVault()]);
      if (!active) return;
    };
    boot();
    return () => {
      active = false;
    };
  }, [userId, fetchIdentity, fetchVault]);

  useEffect(() => {
    if (!userId) return undefined;
    const timer = setTimeout(() => {
      fetchVault(deferredQuery.trim());
    }, 300);
    return () => clearTimeout(timer);
  }, [deferredQuery, userId, fetchVault]);

  const handleUpload = async (file, confirm_match = false) => {
    if (!file || uploading) return;
    setUploading(true);
    setError(null);
    setBanner(null);
    const timeline = ['uploading', 'ocr', 'matching', 'fraud', 'saving'];
    let idx = 0;
    const interval = setInterval(() => {
      idx = Math.min(idx + 1, timeline.length - 1);
      setStage(timeline[idx]);
    }, 600);

    try {
      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('file', file);
      if (confirm_match) formData.append('confirm_match', 'true');

      const res = await apiFetch('/upload', { method: 'POST', body: formData });
      const data = await res.json();
      clearInterval(interval);

      if (data.status === 'CONFIRMATION_REQUIRED') {
        setPendingUpload({ file });
        setConfirmation({
          title: 'Confirm Document Ownership',
          message: data.message || 'Please confirm the extracted details to continue.',
          details: data.extracted || {},
          score: data.identityMatchScore || 0,
        });
        setUploading(false);
        setStage('idle');
        return;
      }

      if (data.status === 'AWAITING_REVIEW') {
        // Pop the review modal
        setReviewDoc(data);
        setUploading(false);
        setStage('idle');
        return;
      }

      if (!res.ok || data.status === 'FAILED' || data.status === 'REJECTED') {
        setError({
          title: data.reason === 'Identity Mismatch' ? 'Identity Verification Failed' : 'Document Rejected',
          message: data.message || data.error || 'The uploaded document could not be verified.',
        });
        setUploading(false);
        setStage('idle');
        return;
      }

      setBanner({
        tone: 'green',
        title: 'Document Accepted',
        message: `${data.document?.document_label || data.classification?.document_label || 'Document'} added to your secure vault.`,
      });
      await Promise.all([fetchVault(query), fetchIdentity()]);
      setUploading(false);
      setStage('idle');
    } catch (err) {
      clearInterval(interval);
      setUploading(false);
      setStage('idle');
      setError({
        title: 'Upload failed',
        message: err.message?.includes('fetch') ? 'The backend server is not reachable.' : err.message || 'Something went wrong.',
      });
    }
  };

  const confirmPendingUpload = async () => {
    if (!pendingUpload) return;
    const file = pendingUpload.file;
    setPendingUpload(null);
    setConfirmation(null);
    await handleUpload(file, true);
  };

  const handleReviewConfirm = async (verifiedData, corrections) => {
    if (!reviewDoc) return;
    
    try {
      const res = await apiFetch('/confirm_review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          document_id: reviewDoc.document_id,
          verified_data: verifiedData,
          corrections: corrections,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setReviewDoc(null);
        setBanner({
          tone: data.document_status === 'Accepted' ? 'green' : 'amber',
          title: `Document ${data.document_status}`,
          message: data.message || 'Document reviewed and saved successfully.',
        });
        await Promise.all([fetchVault(query), fetchIdentity()]);
      } else {
        setError({ title: 'Verification Failed', message: data.error || 'Could not save review.' });
      }
    } catch {
      setError({ title: 'Verification Failed', message: 'Could not reach server to save review.' });
    }
  };

  const handleDelete = async (docId) => {
    if (!window.confirm('Delete this document from your vault?')) return;
    const res = await apiFetch(`/${docId}?user_id=${encodeURIComponent(userId)}`, { method: 'DELETE' });
    if (res.ok) {
      setBanner({ tone: 'green', title: 'Deleted', message: 'The document was removed from your vault.' });
      fetchVault(query);
    } else {
      const data = await res.json().catch(() => ({}));
      setError({ title: 'Delete failed', message: data.error || 'Could not delete the document.' });
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await Promise.all([fetchIdentity(), fetchVault(query)]);
    setRefreshing(false);
  };

  const handleReset = async () => {
    setResetBusy(true);
    try {
      const res = await apiFetch('/identity/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          password: resetPassword,
          reason: 'User Requested',
          device: navigator.userAgent,
          ipAddress: '',
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setResetOpen(false);
        setResetPassword('');
        setBanner({ tone: 'green', title: 'Identity successfully reset', message: data.message });
        await Promise.all([fetchIdentity(), fetchVault('')]);
        navigate('/verify-aadhaar');
      } else {
        setError({ title: 'Reset failed', message: data.error || 'Could not reset identity lock.' });
      }
    } catch {
      setError({ title: 'Reset failed', message: 'Could not reach the server.' });
    } finally {
      setResetBusy(false);
    }
  };

  const acceptedCount = documents.filter((d) => (d.document_status || d.verification_status || '').toUpperCase() === 'ACCEPTED').length;
  const rejectedCount = documents.filter((d) => (d.document_status || d.verification_status || '').toUpperCase() === 'REJECTED').length;
  const pendingCount = documents.length - acceptedCount - rejectedCount;
  const avgConfidence = documents.length
    ? Math.round(documents.reduce((acc, doc) => acc + (doc.confidence || 0), 0) / documents.length)
    : 0;

  if (!userId) {
    return (
      <div style={styles.shell}>
        <div style={styles.heroBackdrop} />
        <div style={styles.contentWrap}>
          <div style={styles.emptyState}>
            <Lock size={36} />
            <h1 style={{ margin: '18px 0 8px', fontSize: 28, fontWeight: 900 }}>Secure Vault Login Required</h1>
            <p style={{ margin: 0, color: '#475569', lineHeight: 1.7 }}>
              Please sign in to access your SATYA Document Vault.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.shell}>
      <div style={styles.heroBackdrop} />
      <div style={styles.contentWrap}>
        <header style={styles.header}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
              <div style={styles.brandMark}>
                <Shield size={22} />
              </div>
              <Badge tone="blue">SATYA Secure Vault</Badge>
              <Badge tone="amber">Government-grade workflow</Badge>
            </div>
            <h1 style={styles.title}>AI-powered Secure Document Vault</h1>
            <p style={styles.subtitle}>
              SATYA is not affiliated with any government agency and does not replace official government verification.
            </p>
          </div>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <button onClick={handleRefresh} disabled={refreshing} style={styles.secondaryBtn}>
              <RefreshCw size={16} /> Refresh
            </button>
            <button onClick={() => document.getElementById('vault-upload-input')?.click()} style={styles.primaryBtn}>
              <Upload size={16} /> Upload Document
            </button>
          </div>
        </header>

        <div style={styles.statsGrid}>
          <StatCard icon={ShieldCheck} label="Accepted" value={acceptedCount} accent="#16a34a" subtext="Stored after full verification" />
          <StatCard icon={Clock3} label="Pending" value={pendingCount} accent="#d97706" subtext="Awaiting final review" />
          <StatCard icon={XCircle} label="Rejected" value={rejectedCount} accent="#dc2626" subtext="Blocked for safety" />
          <StatCard icon={Sparkles} label="Avg confidence" value={`${avgConfidence}%`} accent="#2563eb" subtext="Across all stored documents" />
        </div>

        <AnimatePresence>
          {banner && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={styles.bannerSuccess}>
              <CheckCircle2 size={18} />
              <div>
                <div style={{ fontWeight: 900, color: '#14532d' }}>{banner.title}</div>
                <div style={{ color: '#166534', fontSize: 13 }}>{banner.message}</div>
              </div>
            </motion.div>
          )}
          {error && (
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} style={styles.bannerError}>
              <BadgeAlert size={18} />
              <div>
                <div style={{ fontWeight: 900, color: '#7f1d1d' }}>{error.title}</div>
                <div style={{ color: '#991b1b', fontSize: 13 }}>{error.message}</div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <div style={{ marginTop: 24, marginBottom: 24 }}>
          <IdentityLockCard
            identity={identity}
            resetAvailable={identity.resetAvailable !== false}
            onReset={() => setResetOpen(true)}
          />
        </div>

        <div style={styles.mainGrid}>
          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <div style={styles.panelKicker}>Upload</div>
                <h2 style={styles.panelTitle}>Add a document</h2>
              </div>
              <Badge tone={identity.identityLocked ? 'green' : 'amber'}>
                {identity.identityLocked ? 'Identity locked' : 'Aadhaar required'}
              </Badge>
            </div>

            <div style={styles.uploadBox} onClick={() => document.getElementById('vault-upload-input')?.click()}>
              <input
                id="vault-upload-input"
                type="file"
                accept=".jpg,.jpeg,.png,.pdf,image/jpeg,image/png,application/pdf"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleUpload(file);
                }}
              />
              <div style={styles.uploadIcon}>
                {uploading ? <Loader2 size={24} className="spin" /> : <Upload size={24} />}
              </div>
              <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>
                Drag and drop or browse files
              </div>
              <div style={{ color: '#64748b', textAlign: 'center', lineHeight: 1.7 }}>
                Files are checked for quality, OCR confidence, fraud, QR validity, and identity match before storage.
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center' }}>
                {SUPPORTS.map((item) => <Badge key={item}>{item}</Badge>)}
              </div>
            </div>

            <AnimatePresence>
              {uploading && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  style={styles.progressCard}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div>
                      <div style={{ color: '#64748b', fontSize: 12, fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                        Processing
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 900, color: '#0f172a' }}>
                        {stage === 'uploading' ? 'Uploading' : stage === 'ocr' ? 'OCR Progress' : stage === 'matching' ? 'Identity Matching' : stage === 'fraud' ? 'Fraud Detection' : 'Saving to Vault'}
                      </div>
                    </div>
                    <Loader2 size={20} className="spin" />
                  </div>
                  <div style={styles.stepTrack}>
                    {['uploading', 'ocr', 'matching', 'fraud', 'saving'].map((step, idx) => (
                      <div key={step} style={{ ...styles.stepDot, background: idx <= ['uploading', 'ocr', 'matching', 'fraud', 'saving'].indexOf(stage) ? '#2563eb' : '#cbd5e1' }} />
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </section>

          <section style={styles.panel}>
            <div style={styles.panelHeader}>
              <div>
                <div style={styles.panelKicker}>Vault</div>
                <h2 style={styles.panelTitle}>Your documents</h2>
              </div>
              <div style={{ minWidth: 260 }}>
                <div style={styles.searchBox}>
                  <Search size={16} color="#64748b" />
                  <input
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder='Search e.g. "income certificate"'
                    style={styles.searchInput}
                  />
                </div>
              </div>
            </div>

            {loading ? (
              <div style={styles.skeletonGrid}>
                {[1, 2, 3].map((i) => <div key={i} style={styles.skeletonCard} />)}
              </div>
            ) : documents.length === 0 ? (
              <div style={styles.emptyVault}>
                <FileSearch size={42} />
                <h3 style={{ margin: '14px 0 8px', fontSize: 22, fontWeight: 900 }}>No documents yet</h3>
                <p style={{ margin: 0, color: '#475569', lineHeight: 1.7, textAlign: 'center' }}>
                  Upload your identity-linked documents to build a private vault with AI verification and audit logs.
                </p>
              </div>
            ) : (
              <div style={styles.docGrid}>
                <AnimatePresence>
                  {documents.map((doc) => (
                    <DocumentCard 
                      key={doc._id} 
                      doc={doc} 
                      onDelete={handleDelete} 
                      onDownload={(id) => window.open(`${API_BASE}/download/${id}?user_id=${userId}`, '_blank')}
                      onPreview={(id) => window.open(`${API_BASE}/preview/${id}?user_id=${userId}`, '_blank')}
                    />
                  ))}
                </AnimatePresence>
              </div>
            )}
          </section>
        </div>

        <div style={styles.bottomGrid}>
          <div style={styles.infoPanel}>
            <div style={styles.panelKicker}>Capabilities</div>
            <h3 style={styles.panelTitle}>What the vault checks</h3>
            <ul style={styles.list}>
              <li>Document quality, blur, crop, and screenshot heuristics.</li>
              <li>OCR confidence with second-pass fallback when confidence is low.</li>
              <li>Identity Lock matching against name, DOB, gender, and reference IDs.</li>
              <li>QR and barcode validation with mismatch rejection.</li>
              <li>Fraud heuristics for tampering, edits, and manipulated documents.</li>
            </ul>
          </div>
          <div style={styles.infoPanel}>
            <div style={styles.panelKicker}>Policy</div>
            <h3 style={styles.panelTitle}>Family documents</h3>
            <p style={styles.paragraph}>
              Ration cards are accepted only when the logged-in user appears in the family member list. The cardholder is never used as the primary match target.
            </p>
            <p style={styles.paragraph}>
              To keep the vault safe, documents are only stored after quality, fraud, identity match, and QR/signature checks pass.
            </p>
          </div>
        </div>
      </div>

      <AnimatePresence>
        {confirmation && pendingUpload && (
          <Modal
            title="Confirm Document Ownership"
            subtitle={`Identity match score: ${Math.round(confirmation.score || 0)}%`}
            onClose={() => {
              setConfirmation(null);
              setPendingUpload(null);
            }}
          >
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={styles.callout}>
                <Badge tone="amber"><BadgeInfo size={14} /> Low confidence</Badge>
                <div style={{ marginTop: 10, color: '#7c2d12', lineHeight: 1.7 }}>
                  {confirmation.message}
                </div>
              </div>
              <div style={styles.confirmGrid}>
                {Object.entries(confirmation.details || {}).slice(0, 6).map(([key, value]) => (
                  <div key={key} style={styles.confirmField}>
                    <div style={styles.confirmLabel}>{key.replace(/_/g, ' ')}</div>
                    <div style={styles.confirmValue}>{displayValue(value)}</div>
                  </div>
                ))}
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={() => {
                    setConfirmation(null);
                    setPendingUpload(null);
                  }}
                  style={styles.secondaryBtn}
                >
                  Cancel
                </button>
                <button type="button" onClick={confirmPendingUpload} style={styles.primaryBtn}>
                  Confirm and Add
                </button>
              </div>
            </div>
          </Modal>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {resetOpen && (
          <Modal
            title="Reset Identity Verification"
            subtitle="This permanently removes your Identity Lock and all identity-linked documents."
            onClose={() => setResetOpen(false)}
            width={720}
          >
            <div style={{ display: 'grid', gap: 14 }}>
              <div style={styles.calloutDanger}>
                Resetting your Identity Lock will permanently remove your verified identity and all identity-linked document verification. All documents in your SATYA Vault will also be permanently deleted because they are linked to your verified identity. This action cannot be undone.
              </div>
              <div style={styles.inputGrid}>
                <label style={styles.label}>
                  Account Password
                  <input
                    type="password"
                    value={resetPassword}
                    onChange={(e) => setResetPassword(e.target.value)}
                    style={styles.input}
                    placeholder="Re-enter your password"
                  />
                </label>
              </div>
              <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setResetOpen(false)} style={styles.secondaryBtn} disabled={resetBusy}>
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleReset}
                  disabled={resetBusy || !resetPassword}
                  style={{
                    ...styles.dangerBtn,
                    opacity: resetBusy || !resetPassword ? 0.6 : 1,
                    cursor: resetBusy || !resetPassword ? 'not-allowed' : 'pointer',
                  }}
                >
                  {resetBusy ? 'Resetting...' : 'Continue'}
                </button>
              </div>
            </div>
          </Modal>
        )}
      </AnimatePresence>

      <DocumentReviewModal
        key={reviewDoc?.document_id || 'review-modal'}
        isOpen={!!reviewDoc}
        document={reviewDoc?.document || {}}
        onClose={() => {
          setReviewDoc(null);
          fetchVault(query); // refresh to show Awaiting Review doc
        }}
        onConfirm={handleReviewConfirm}
      />

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}

const styles = {
  shell: {
    minHeight: '100vh',
    position: 'relative',
    overflow: 'hidden',
    background: 'linear-gradient(180deg, #FF9933 0%, #FFFFFF 50%, #138808 100%)',
  },
  heroBackdrop: {
    position: 'absolute',
    inset: 0,
    background: 'radial-gradient(circle at 15% 20%, rgba(255,153,51,0.15), transparent 28%), radial-gradient(circle at 85% 8%, rgba(19,136,8,0.16), transparent 24%), radial-gradient(circle at 50% 85%, rgba(79,70,229,0.08), transparent 28%)',
    pointerEvents: 'none',
  },
  contentWrap: {
    position: 'relative',
    zIndex: 1,
    maxWidth: 1440,
    margin: '0 auto',
    padding: '32px 24px 80px',
  },
  header: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 20,
    flexWrap: 'wrap',
    marginBottom: 22,
  },
  brandMark: {
    width: 46,
    height: 46,
    borderRadius: 16,
    background: 'linear-gradient(135deg, #0f172a, #2563eb)',
    color: '#fff',
    display: 'grid',
    placeItems: 'center',
    boxShadow: '0 18px 36px rgba(15,23,42,0.18)',
  },
  title: {
    margin: 0,
    fontSize: 'clamp(2rem, 4vw, 3.4rem)',
    lineHeight: 1.02,
    fontWeight: 950,
    letterSpacing: '-0.04em',
    color: '#0f172a',
  },
  subtitle: {
    margin: '14px 0 0',
    maxWidth: 860,
    color: '#475569',
    fontSize: 15,
    lineHeight: 1.8,
  },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    border: 'none',
    borderRadius: 16,
    background: 'linear-gradient(135deg, #0f172a, #2563eb)',
    color: '#fff',
    fontWeight: 900,
    padding: '13px 18px',
    boxShadow: '0 18px 32px rgba(37,99,235,0.22)',
    cursor: 'pointer',
  },
  secondaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: 10,
    borderRadius: 16,
    padding: '13px 18px',
    border: '1px solid rgba(148,163,184,0.28)',
    background: 'rgba(255,255,255,0.9)',
    color: '#0f172a',
    fontWeight: 900,
    cursor: 'pointer',
  },
  dangerBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    padding: '13px 18px',
    border: 'none',
    background: 'linear-gradient(135deg, #dc2626, #ef4444)',
    color: '#fff',
    fontWeight: 900,
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: 16,
    marginBottom: 22,
  },
  bannerSuccess: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
    padding: 16,
    borderRadius: 20,
    background: 'linear-gradient(135deg, rgba(220,252,231,0.95), rgba(240,253,244,0.95))',
    border: '1px solid rgba(34,197,94,0.18)',
    marginBottom: 14,
  },
  bannerError: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 12,
    padding: 16,
    borderRadius: 20,
    background: 'linear-gradient(135deg, rgba(254,226,226,0.95), rgba(255,247,247,0.95))',
    border: '1px solid rgba(239,68,68,0.16)',
    marginBottom: 14,
  },
  mainGrid: {
    display: 'grid',
    gridTemplateColumns: 'minmax(320px, 430px) 1fr',
    gap: 20,
    alignItems: 'start',
  },
  panel: {
    background: 'rgba(255,255,255,0.8)',
    border: '1px solid rgba(148,163,184,0.16)',
    borderRadius: 28,
    padding: 22,
    backdropFilter: 'blur(18px)',
    boxShadow: '0 22px 60px rgba(15,23,42,0.08)',
  },
  panelHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    flexWrap: 'wrap',
    alignItems: 'flex-start',
    marginBottom: 16,
  },
  panelKicker: {
    color: '#2563eb',
    fontSize: 11,
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: '0.12em',
  },
  panelTitle: {
    margin: '6px 0 0',
    color: '#0f172a',
    fontSize: 24,
    fontWeight: 950,
    letterSpacing: '-0.03em',
  },
  uploadBox: {
    minHeight: 430,
    borderRadius: 28,
    border: '1.5px dashed rgba(37,99,235,0.22)',
    background: 'linear-gradient(180deg, rgba(248,250,252,0.95), rgba(255,255,255,0.9))',
    display: 'grid',
    placeItems: 'center',
    padding: 26,
    gap: 18,
    cursor: 'pointer',
  },
  uploadIcon: {
    width: 72,
    height: 72,
    borderRadius: 24,
    background: 'linear-gradient(135deg, rgba(37,99,235,0.12), rgba(16,185,129,0.12))',
    display: 'grid',
    placeItems: 'center',
    color: '#2563eb',
  },
  progressCard: {
    marginTop: 16,
    background: '#fff',
    borderRadius: 22,
    padding: 18,
    border: '1px solid rgba(148,163,184,0.14)',
  },
  stepTrack: {
    display: 'grid',
    gridTemplateColumns: 'repeat(5, 1fr)',
    gap: 8,
    marginTop: 14,
  },
  stepDot: {
    height: 8,
    borderRadius: 999,
    transition: 'background 200ms ease',
  },
  searchBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    background: '#fff',
    borderRadius: 16,
    border: '1px solid rgba(148,163,184,0.2)',
    padding: '0 14px',
    height: 50,
  },
  searchInput: {
    border: 'none',
    outline: 'none',
    width: '100%',
    fontSize: 14,
    background: 'transparent',
    color: '#0f172a',
  },
  skeletonGrid: {
    display: 'grid',
    gap: 14,
  },
  skeletonCard: {
    height: 170,
    borderRadius: 22,
    background: 'linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 37%, #f1f5f9 63%)',
    backgroundSize: '400% 100%',
    animation: 'shimmer 1.4s ease infinite',
  },
  emptyVault: {
    minHeight: 360,
    borderRadius: 26,
    border: '1px dashed rgba(148,163,184,0.24)',
    background: 'linear-gradient(180deg, rgba(248,250,252,0.8), rgba(255,255,255,0.9))',
    display: 'grid',
    placeItems: 'center',
    padding: 28,
    color: '#334155',
    textAlign: 'center',
  },
  docGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: 16,
  },
  bottomGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: 16,
    marginTop: 20,
  },
  infoPanel: {
    background: 'rgba(255,255,255,0.82)',
    border: '1px solid rgba(148,163,184,0.14)',
    borderRadius: 24,
    padding: 22,
    boxShadow: '0 18px 50px rgba(15,23,42,0.06)',
  },
  list: {
    margin: '14px 0 0',
    paddingLeft: 20,
    color: '#334155',
    lineHeight: 1.85,
  },
  paragraph: {
    margin: '12px 0 0',
    color: '#334155',
    lineHeight: 1.8,
  },
  modalOverlay: {
    position: 'fixed',
    inset: 0,
    background: 'rgba(15,23,42,0.62)',
    backdropFilter: 'blur(8px)',
    zIndex: 80,
    display: 'grid',
    placeItems: 'center',
    padding: 16,
  },
  modalCard: {
    background: '#fff',
    borderRadius: 26,
    padding: 24,
    boxShadow: '0 30px 90px rgba(15,23,42,0.28)',
    border: '1px solid rgba(148,163,184,0.12)',
  },
  callout: {
    background: 'linear-gradient(180deg, #fff7ed, #fffbeb)',
    border: '1px solid rgba(245,158,11,0.18)',
    borderRadius: 18,
    padding: 16,
  },
  calloutDanger: {
    background: 'linear-gradient(180deg, #fef2f2, #fff7f7)',
    border: '1px solid rgba(239,68,68,0.16)',
    borderRadius: 18,
    padding: 16,
    color: '#7f1d1d',
    lineHeight: 1.8,
  },
  confirmGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
    gap: 12,
  },
  confirmField: {
    background: '#f8fafc',
    borderRadius: 16,
    padding: 14,
    border: '1px solid rgba(148,163,184,0.12)',
  },
  confirmLabel: {
    color: '#64748b',
    fontSize: 11,
    fontWeight: 900,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
  },
  confirmValue: {
    color: '#0f172a',
    fontWeight: 800,
    marginTop: 6,
    wordBreak: 'break-word',
  },
  inputGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))',
    gap: 14,
  },
  label: {
    display: 'grid',
    gap: 8,
    color: '#0f172a',
    fontSize: 13,
    fontWeight: 800,
  },
  input: {
    height: 48,
    borderRadius: 14,
    border: '1px solid rgba(148,163,184,0.22)',
    padding: '0 14px',
    fontSize: 14,
    outline: 'none',
    background: '#fff',
  },
  emptyState: {
    background: 'rgba(255,255,255,0.88)',
    borderRadius: 28,
    padding: 28,
    textAlign: 'center',
    maxWidth: 700,
    margin: '80px auto 0',
    boxShadow: '0 24px 72px rgba(15,23,42,0.12)',
    border: '1px solid rgba(148,163,184,0.16)',
  },
};
