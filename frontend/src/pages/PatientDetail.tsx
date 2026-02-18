import { useState, useEffect, FormEvent } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { useAuthStore } from '../store/authStore';
import type { Patient, Session } from '../types';
import { format } from 'date-fns';

export default function PatientDetail() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showNewSession, setShowNewSession] = useState(false);
  
  const user = useAuthStore((state) => state.user);
  const canCreate = user?.role === 'admin' || user?.role === 'clinician';
  const navigate = useNavigate();

  useEffect(() => {
    const fetchData = async () => {
      if (!patientId) return;
      
      try {
        setLoading(true);
        const [patientData, sessionsData] = await Promise.all([
          api.getPatient(parseInt(patientId)),
          api.getPatientSessions(parseInt(patientId)),
        ]);
        setPatient(patientData);
        setSessions(sessionsData.sessions);
      } catch {
        setError('Failed to load patient data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [patientId]);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '2rem' }}>
        <span className="spinner" />
      </div>
    );
  }

  if (error || !patient) {
    return (
      <div className="alert alert-error">
        {error || 'Patient not found'}
      </div>
    );
  }

  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <Link to="/patients" style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
          &larr; Back to Patients
        </Link>
      </div>

      <div className="card" style={{ marginBottom: '2rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              {patient.name}
            </h1>
            <div style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
              {patient.external_id && <p>External ID: {patient.external_id}</p>}
              {patient.dob && <p>DOB: {patient.dob}</p>}
              <p>Created: {format(new Date(patient.created_at), 'MMMM d, yyyy')}</p>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600 }}>Sessions</h2>
        {canCreate && (
          <button className="btn btn-primary" onClick={() => setShowNewSession(true)}>
            + New Session
          </button>
        )}
      </div>

      {sessions.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>
          <p>No sessions yet.</p>
          {canCreate && (
            <button
              className="btn btn-primary"
              style={{ marginTop: '1rem' }}
              onClick={() => setShowNewSession(true)}
            >
              Create First Session
            </button>
          )}
        </div>
      ) : (
        <div className="card">
          <table className="table">
            <thead>
              <tr>
                <th>Session</th>
                <th>Created</th>
                <th>Transcript Length</th>
                <th>AI Suggestions</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((session) => (
                <tr key={session.id}>
                  <td>
                    <Link to={`/sessions/${session.id}`} style={{ fontWeight: 500 }}>
                      Session #{session.id}
                    </Link>
                  </td>
                  <td>{format(new Date(session.created_at), 'MMM d, yyyy h:mm a')}</td>
                  <td>{session.transcript_length.toLocaleString()} chars</td>
                  <td>
                    {session.has_ai_suggestions ? (
                      <span className="badge badge-success">Yes</span>
                    ) : (
                      <span className="badge badge-warning">No</span>
                    )}
                  </td>
                  <td>
                    {session.latest_version_status && (
                      <span className={`badge ${session.latest_version_status === 'final' ? 'badge-success' : 'badge-info'}`}>
                        {session.latest_version_status}
                      </span>
                    )}
                  </td>
                  <td>
                    <Link
                      to={`/sessions/${session.id}`}
                      className="btn btn-outline"
                      style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showNewSession && (
        <NewSessionModal
          patientId={patient.id}
          onClose={() => setShowNewSession(false)}
          onCreated={(sessionId) => {
            setShowNewSession(false);
            navigate(`/sessions/${sessionId}`);
          }}
        />
      )}
    </div>
  );
}

function NewSessionModal({ 
  patientId, 
  onClose, 
  onCreated 
}: { 
  patientId: number; 
  onClose: () => void; 
  onCreated: (sessionId: number) => void;
}) {
  const [transcript, setTranscript] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    
    if (!transcript.trim()) {
      setError('Transcript is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const session = await api.createSession(patientId, transcript);
      onCreated(session.id);
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } };
      setError(error.response?.data?.detail || 'Failed to create session');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
    }}>
      <div className="card" style={{ width: '100%', maxWidth: '700px', maxHeight: '90vh', overflow: 'auto' }}>
        <h2 style={{ fontSize: '1.25rem', fontWeight: 600, marginBottom: '1.5rem' }}>
          New Session
        </h2>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="label" htmlFor="transcript">
              Session Transcript *
            </label>
            <p style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)', marginBottom: '0.5rem' }}>
              Paste your session notes or transcript here. This will be used to generate AI suggestions.
            </p>
            <textarea
              id="transcript"
              className="input textarea"
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              placeholder="Patient is a 35-year-old male presenting with..."
              style={{ minHeight: '300px' }}
              required
            />
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: '1.5rem' }}>
            <button type="button" className="btn btn-outline" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : 'Create Session'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
