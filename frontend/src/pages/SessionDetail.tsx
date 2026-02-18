import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';
import type { Session, GenerateResponse, NoteVersion, SOAPNote, DiagnosisSuggestion, MedicationEducation, SafetyPlan, Citation } from '../types';
import { format } from 'date-fns';
import clsx from 'clsx';

export default function SessionDetail() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [session, setSession] = useState<Session | null>(null);
  const [transcript, setTranscript] = useState('');
  const [versions, setVersions] = useState<NoteVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<NoteVersion | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const [warning, setWarning] = useState('');
  const [activeTab, setActiveTab] = useState<'soap' | 'diagnosis' | 'medications' | 'safety'>('soap');
  const [showTranscript, setShowTranscript] = useState(false);
  const [showVersions, setShowVersions] = useState(false);
  
  const user = useAuthStore((state) => state.user);
  const canEdit = user?.role === 'admin' || user?.role === 'clinician';

  const fetchData = async () => {
    if (!sessionId) return;
    
    try {
      setLoading(true);
      const [sessionData, versionsData] = await Promise.all([
        api.getSession(parseInt(sessionId)),
        api.getSessionVersions(parseInt(sessionId)),
      ]);
      setSession(sessionData);
      setVersions(versionsData.versions);
      
      // Set current version to latest
      if (versionsData.versions.length > 0) {
        setCurrentVersion(versionsData.versions[0]);
      }

      // Try to get transcript (clinician/admin only)
      if (canEdit) {
        try {
          const transcriptData = await api.getSessionTranscript(parseInt(sessionId));
          setTranscript(transcriptData.transcript);
        } catch {
          // May not have access
        }
      }
    } catch {
      setError('Failed to load session');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [sessionId]);

  const handleGenerate = async () => {
    if (!sessionId) return;
    
    setGenerating(true);
    setError('');
    setWarning('');

    try {
      const response: GenerateResponse = await api.generateAiSuggestions(parseInt(sessionId));
      
      if (response.warning_message) {
        setWarning(response.warning_message);
      }
      
      // Refresh versions
      const versionsData = await api.getSessionVersions(parseInt(sessionId));
      setVersions(versionsData.versions);
      setCurrentVersion(versionsData.versions[0]);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'AI generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleFinalize = async () => {
    if (!currentVersion) return;
    
    try {
      await api.finalizeVersion(currentVersion.id);
      await fetchData();
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to finalize');
    }
  };

  const handleRollback = async (versionId: number) => {
    if (!sessionId) return;
    
    try {
      await api.rollbackVersion(parseInt(sessionId), versionId);
      await fetchData();
      setShowVersions(false);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to rollback');
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <span className="spinner" />
      </div>
    );
  }

  if (!session) {
    return <div className="alert alert-error">Session not found</div>;
  }

  // Parse JSON from current version
  let soap: SOAPNote | null = null;
  let diagnosis: DiagnosisSuggestion | null = null;
  let medications: MedicationEducation | null = null;
  let safetyPlan: SafetyPlan | null = null;

  if (currentVersion) {
    try {
      if (currentVersion.soap_json) soap = JSON.parse(currentVersion.soap_json);
      if (currentVersion.dx_json) diagnosis = JSON.parse(currentVersion.dx_json);
      if (currentVersion.meds_json) medications = JSON.parse(currentVersion.meds_json);
      if (currentVersion.safety_json) safetyPlan = JSON.parse(currentVersion.safety_json);
    } catch {
      // Invalid JSON
    }
  }

  return (
    <div>
      <div style={{ marginBottom: '1rem' }}>
        <Link to={`/patients/${session.patient_id}`} style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
          &larr; Back to Patient
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {warning && <div className="alert alert-warning">{warning}</div>}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 600 }}>Session #{session.id}</h1>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
            Created {format(new Date(session.created_at), 'MMMM d, yyyy h:mm a')}
          </p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button className="btn btn-outline" onClick={() => setShowTranscript(!showTranscript)}>
            {showTranscript ? 'Hide' : 'Show'} Transcript
          </button>
          <button className="btn btn-outline" onClick={() => setShowVersions(!showVersions)}>
            Version History
          </button>
          {canEdit && (
            <button className="btn btn-primary" onClick={handleGenerate} disabled={generating}>
              {generating ? <span className="spinner" /> : 'Generate AI'}
            </button>
          )}
        </div>
      </div>

      {showTranscript && transcript && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '0.5rem' }}>Transcript</h3>
          <div style={{ 
            background: 'var(--color-bg)', 
            padding: '1rem', 
            borderRadius: 'var(--radius)',
            whiteSpace: 'pre-wrap',
            fontSize: '0.875rem',
            maxHeight: '300px',
            overflow: 'auto',
          }}>
            {transcript}
          </div>
        </div>
      )}

      {showVersions && (
        <div className="card" style={{ marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: '1rem' }}>Version History</h3>
          <table className="table">
            <thead>
              <tr>
                <th>Version</th>
                <th>Status</th>
                <th>Created</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {versions.map((version) => (
                <tr key={version.id}>
                  <td>v{version.version_number}</td>
                  <td>
                    <span className={`badge ${version.status === 'final' ? 'badge-success' : 'badge-info'}`}>
                      {version.status}
                    </span>
                  </td>
                  <td>{format(new Date(version.created_at), 'MMM d, yyyy h:mm a')}</td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button
                        className="btn btn-outline"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                        onClick={() => setCurrentVersion(version)}
                      >
                        View
                      </button>
                      {canEdit && version.status !== 'final' && (
                        <button
                          className="btn btn-outline"
                          style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                          onClick={() => handleRollback(version.id)}
                        >
                          Rollback
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {currentVersion && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <div>
              <span style={{ fontWeight: 500 }}>Version {currentVersion.version_number}</span>
              <span className={`badge ${currentVersion.status === 'final' ? 'badge-success' : 'badge-info'}`} style={{ marginLeft: '0.5rem' }}>
                {currentVersion.status}
              </span>
            </div>
            {canEdit && currentVersion.status === 'draft' && (
              <button className="btn btn-success" onClick={handleFinalize}>
                Finalize Note
              </button>
            )}
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '1px solid var(--color-border)', paddingBottom: '0.5rem' }}>
            {(['soap', 'diagnosis', 'medications', 'safety'] as const).map((tab) => (
              <button
                key={tab}
                className={clsx('btn', activeTab === tab ? 'btn-primary' : 'btn-outline')}
                onClick={() => setActiveTab(tab)}
              >
                {tab === 'soap' ? 'SOAP Note' : tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
          </div>

          {activeTab === 'soap' && soap && <SOAPView soap={soap} />}
          {activeTab === 'diagnosis' && diagnosis && <DiagnosisView diagnosis={diagnosis} />}
          {activeTab === 'medications' && medications && <MedicationsView medications={medications} />}
          {activeTab === 'safety' && safetyPlan && <SafetyPlanView safetyPlan={safetyPlan} />}

          {!soap && !diagnosis && !medications && !safetyPlan && (
            <div style={{ textAlign: 'center', color: 'var(--color-text-secondary)', padding: '2rem' }}>
              <p>No content yet. Generate AI suggestions to get started.</p>
            </div>
          )}
        </div>
      )}

      {!currentVersion && versions.length === 0 && (
        <div className="card" style={{ textAlign: 'center', color: 'var(--color-text-secondary)', padding: '2rem' }}>
          <p>No notes yet. Generate AI suggestions to get started.</p>
          {canEdit && (
            <button className="btn btn-primary" style={{ marginTop: '1rem' }} onClick={handleGenerate} disabled={generating}>
              {generating ? <span className="spinner" /> : 'Generate AI Suggestions'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function CitationSpan({ citation }: { citation: Citation }) {
  return (
    <span className="citation" title={`${citation.start_offset ?? '?'}-${citation.end_offset ?? '?'}`}>
      "{citation.text}"
    </span>
  );
}

function SOAPView({ soap }: { soap: SOAPNote }) {
  const sections = [
    { key: 'subjective', label: 'Subjective', data: soap.subjective },
    { key: 'objective', label: 'Objective', data: soap.objective },
    { key: 'assessment', label: 'Assessment', data: soap.assessment },
    { key: 'plan', label: 'Plan', data: soap.plan },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {sections.map(({ key, label, data }) => (
        <div key={key}>
          <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>{label}</h4>
          <p style={{ whiteSpace: 'pre-wrap' }}>{data.content}</p>
          {data.citations.length > 0 && (
            <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
              {data.citations.map((citation, i) => (
                <CitationSpan key={i} citation={citation} />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function DiagnosisView({ diagnosis }: { diagnosis: DiagnosisSuggestion }) {
  return (
    <div>
      {diagnosis.primary && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>Primary Diagnosis</h4>
          <div className="card" style={{ background: 'var(--color-bg)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <span style={{ fontWeight: 500 }}>{diagnosis.primary.diagnosis}</span>
              <span className="badge badge-info">
                {(diagnosis.primary.confidence * 100).toFixed(0)}% confidence
              </span>
            </div>
            <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
              {diagnosis.primary.rationale}
            </p>
            {diagnosis.primary.citations.length > 0 && (
              <div style={{ marginTop: '0.5rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {diagnosis.primary.citations.map((citation, i) => (
                  <CitationSpan key={i} citation={citation} />
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {diagnosis.differential.length > 0 && (
        <div>
          <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>Differential Diagnoses</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {diagnosis.differential.map((dx, i) => (
              <div key={i} className="card" style={{ background: 'var(--color-bg)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <span style={{ fontWeight: 500 }}>{dx.diagnosis}</span>
                  <span className="badge badge-info">
                    {(dx.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <p style={{ fontSize: '0.875rem', color: 'var(--color-text-secondary)' }}>
                  {dx.rationale}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MedicationsView({ medications }: { medications: MedicationEducation }) {
  return (
    <div>
      {medications.general_guidance && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>General Guidance</h4>
          <p>{medications.general_guidance}</p>
        </div>
      )}

      {medications.medications.length > 0 && (
        <div>
          <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', color: 'var(--color-primary)' }}>Medications</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {medications.medications.map((med, i) => (
              <div key={i} className="card" style={{ background: 'var(--color-bg)' }}>
                <h5 style={{ fontWeight: 600, marginBottom: '0.5rem' }}>{med.medication}</h5>
                <p style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>{med.education}</p>
                {med.warnings.length > 0 && (
                  <div style={{ marginTop: '0.5rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--color-warning)' }}>Warnings:</span>
                    <ul style={{ fontSize: '0.875rem', marginLeft: '1rem', marginTop: '0.25rem' }}>
                      {med.warnings.map((warning, j) => (
                        <li key={j}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SafetyPlanView({ safetyPlan }: { safetyPlan: SafetyPlan }) {
  const sections = [
    { key: 'warning_signs', label: 'Warning Signs', items: safetyPlan.warning_signs },
    { key: 'coping_strategies', label: 'Coping Strategies', items: safetyPlan.coping_strategies },
    { key: 'support_contacts', label: 'Support Contacts', items: safetyPlan.support_contacts },
    { key: 'professional_contacts', label: 'Professional Contacts', items: safetyPlan.professional_contacts },
    { key: 'environment_safety', label: 'Environment Safety', items: safetyPlan.environment_safety },
    { key: 'reasons_for_living', label: 'Reasons for Living', items: safetyPlan.reasons_for_living },
  ];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem' }}>
      {sections.map(({ key, label, items }) => items.length > 0 && (
        <div key={key} className="card" style={{ background: 'var(--color-bg)' }}>
          <h4 style={{ fontWeight: 600, marginBottom: '0.75rem', color: 'var(--color-primary)' }}>{label}</h4>
          <ul style={{ paddingLeft: '1.25rem' }}>
            {items.map((item, i) => (
              <li key={i} style={{ marginBottom: '0.5rem' }}>
                <span>{item.item}</span>
                {item.notes && (
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', display: 'block' }}>
                    {item.notes}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
