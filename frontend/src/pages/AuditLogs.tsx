import { useState, useEffect } from 'react';
import { api } from '../api/client';
import type { AuditLog } from '../types';
import { format } from 'date-fns';

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [entityType, setEntityType] = useState('');
  const [action, setAction] = useState('');
  const limit = 50;

  const fetchLogs = async () => {
    try {
      setLoading(true);
      const params: Record<string, string | number> = { limit, offset };
      if (entityType) params.entity_type = entityType;
      if (action) params.action = action;
      
      const data = await api.getAuditLogs(params);
      setLogs(data.logs);
      setTotal(data.total);
    } catch {
      setError('Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs();
  }, [offset, entityType, action]);

  return (
    <div>
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '2rem' }}>Audit Logs</h1>

      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem' }}>
        <select
          className="input"
          style={{ width: 'auto' }}
          value={entityType}
          onChange={(e) => { setEntityType(e.target.value); setOffset(0); }}
        >
          <option value="">All Entity Types</option>
          <option value="patient">Patient</option>
          <option value="session">Session</option>
          <option value="note_version">Note Version</option>
        </select>

        <select
          className="input"
          style={{ width: 'auto' }}
          value={action}
          onChange={(e) => { setAction(e.target.value); setOffset(0); }}
        >
          <option value="">All Actions</option>
          <option value="create">Create</option>
          <option value="update">Update</option>
          <option value="delete">Delete</option>
          <option value="finalize_version">Finalize</option>
          <option value="rollback_version">Rollback</option>
        </select>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem' }}>
          <span className="spinner" />
        </div>
      ) : logs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', color: 'var(--color-text-secondary)' }}>
          <p>No audit logs found.</p>
        </div>
      ) : (
        <>
          <div className="card">
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Timestamp</th>
                  <th>Actor</th>
                  <th>Action</th>
                  <th>Entity</th>
                  <th>Before Hash</th>
                  <th>After Hash</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id}>
                    <td>{log.id}</td>
                    <td style={{ whiteSpace: 'nowrap' }}>
                      {format(new Date(log.created_at), 'MMM d, yyyy h:mm:ss a')}
                    </td>
                    <td>User #{log.actor_user_id}</td>
                    <td>
                      <span className={`badge ${getActionBadgeClass(log.action)}`}>
                        {log.action}
                      </span>
                    </td>
                    <td>
                      {log.entity_type} #{log.entity_id}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {log.before_hash ? `${log.before_hash.slice(0, 8)}...` : '-'}
                    </td>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.75rem' }}>
                      {log.after_hash ? `${log.after_hash.slice(0, 8)}...` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '1rem' }}>
            <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.875rem' }}>
              Showing {offset + 1} - {Math.min(offset + limit, total)} of {total}
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button
                className="btn btn-outline"
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
              >
                Previous
              </button>
              <button
                className="btn btn-outline"
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function getActionBadgeClass(action: string): string {
  switch (action) {
    case 'create':
      return 'badge-success';
    case 'update':
      return 'badge-info';
    case 'delete':
      return 'badge-error';
    case 'finalize_version':
      return 'badge-success';
    case 'rollback_version':
      return 'badge-warning';
    default:
      return 'badge-info';
  }
}
