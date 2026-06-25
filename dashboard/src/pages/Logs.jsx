import { useState, useEffect } from 'react';
import { adminApi } from '../api/client';

const REASON_STYLES = {
  OK: 'text-hardlock-success',
  FINGERPRINT_MISMATCH: 'text-red-400',
  REVOKED: 'text-red-400',
  EXPIRED: 'text-yellow-400',
  RATE_LIMITED: 'text-yellow-400',
  NOT_REGISTERED: 'text-gray-400',
};

export default function Logs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const limit = 50;

  const fetchLogs = async (pageNum) => {
    setLoading(true);
    setError('');
    try {
      const { data } = await adminApi.logs(pageNum, limit);
      const items = Array.isArray(data) ? data : data.items ?? data.logs ?? [];
      setLogs(items);
      setHasMore(items.length === limit);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load launch logs.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(page);
  }, [page]);

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Launch Logs</h1>
        <p className="mt-1 text-sm text-gray-400">
          Audit trail of all software launch verification attempts.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-hardlock-700">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b border-hardlock-700 bg-hardlock-800/50">
              <th className="px-4 py-3 font-medium text-gray-400">Status</th>
              <th className="px-4 py-3 font-medium text-gray-400">Reason</th>
              <th className="px-4 py-3 font-medium text-gray-400">Device ID</th>
              <th className="px-4 py-3 font-medium text-gray-400">IP Address</th>
              <th className="px-4 py-3 font-medium text-gray-400">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hardlock-700">
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i}>
                  <td colSpan={5} className="px-4 py-3">
                    <div className="h-4 animate-pulse rounded bg-hardlock-700" />
                  </td>
                </tr>
              ))
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-12 text-center text-gray-500">
                  No launch logs yet. Logs appear when protected software calls verify.
                </td>
              </tr>
            ) : (
              logs.map((log, idx) => (
                <tr key={log.id ?? idx} className="transition hover:bg-hardlock-800/30">
                  <td className="px-4 py-3">
                    <StatusBadge success={log.success} />
                  </td>
                  <td className="px-4 py-3">
                    <span className={`font-mono text-xs ${REASON_STYLES[log.reason] || 'text-gray-400'}`}>
                      {log.reason || '—'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <code className="font-mono text-xs text-gray-400">
                      {log.device_id ? `${String(log.device_id).slice(0, 8)}…` : '—'}
                    </code>
                  </td>
                  <td className="px-4 py-3 text-gray-400">{log.ip_address || '—'}</td>
                  <td className="px-4 py-3 text-gray-400">
                    {log.launched_at
                      ? new Date(log.launched_at).toLocaleString()
                      : '—'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {!loading && logs.length > 0 && (
        <div className="mt-4 flex items-center justify-between">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="btn-secondary"
          >
            Previous
          </button>
          <span className="text-sm text-gray-500">Page {page}</span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={!hasMore}
            className="btn-secondary"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ success }) {
  if (success) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-green-500/20 px-2 py-0.5 text-xs font-medium text-green-400 ring-1 ring-inset ring-green-500/30">
        <span className="h-1.5 w-1.5 rounded-full bg-green-400" />
        Authorized
      </span>
    );
  }

  return (
    <span className="inline-flex items-center gap-1.5 rounded-full bg-red-500/20 px-2 py-0.5 text-xs font-medium text-red-400 ring-1 ring-inset ring-red-500/30">
      <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
      Denied
    </span>
  );
}
