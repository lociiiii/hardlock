import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { appsApi, adminApi } from '../api/client';
import StatsBanner from '../components/StatsBanner';

export default function Apps() {
  const [apps, setApps] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState('');
  const [newDescription, setNewDescription] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [appsRes, statsRes] = await Promise.all([
        appsApi.list(),
        adminApi.stats().catch(() => ({ data: null })),
      ]);
      setApps(appsRes.data);
      setStats(statsRes.data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load applications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newName.trim()) return;

    setCreating(true);
    try {
      await appsApi.create(newName.trim(), newDescription.trim() || null);
      setNewName('');
      setNewDescription('');
      setShowCreate(false);
      await fetchData();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create application.');
    } finally {
      setCreating(false);
    }
  };

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Applications</h1>
          <p className="mt-1 text-sm text-gray-400">
            Manage your protected applications and API keys.
          </p>
        </div>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          <PlusIcon />
          <span className="ml-2">New Application</span>
        </button>
      </div>

      <StatsBanner stats={stats} loading={loading} />

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {showCreate && (
        <div className="card mb-6">
          <h2 className="mb-4 text-lg font-semibold text-white">Create Application</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-300">Name</label>
              <input
                className="input-field"
                placeholder="My Protected App"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                autoFocus
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-gray-300">
                Description <span className="text-gray-500">(optional)</span>
              </label>
              <textarea
                className="input-field resize-none"
                rows={2}
                placeholder="Brief description of your application"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
              />
            </div>
            <div className="flex gap-3">
              <button type="submit" disabled={creating || !newName.trim()} className="btn-primary">
                {creating ? 'Creating…' : 'Create'}
              </button>
              <button
                type="button"
                onClick={() => setShowCreate(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card h-36 animate-pulse !p-4">
              <div className="mb-3 h-5 w-2/3 rounded bg-hardlock-700" />
              <div className="h-4 w-full rounded bg-hardlock-700" />
            </div>
          ))}
        </div>
      ) : apps.length === 0 ? (
        <div className="card text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-hardlock-800">
            <BoxIcon />
          </div>
          <h3 className="text-lg font-medium text-white">No applications yet</h3>
          <p className="mt-1 text-sm text-gray-400">
            Create your first application to start generating license keys.
          </p>
          <button onClick={() => setShowCreate(true)} className="btn-primary mt-4">
            Create Application
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {apps.map((app) => (
            <Link
              key={app.id}
              to={`/apps/${app.id}`}
              className="card group transition hover:border-hardlock-500/50 hover:shadow-hardlock-500/5 !p-5"
            >
              <div className="mb-3 flex items-start justify-between">
                <h3 className="text-lg font-semibold text-white group-hover:text-hardlock-accent">
                  {app.name}
                </h3>
                <ArrowIcon />
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500">API Key</span>
                  <code className="truncate font-mono text-xs text-gray-400">
                    {app.api_key}
                  </code>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500">
                  <span>{app.license_count ?? 0} licenses</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
    </svg>
  );
}

function BoxIcon() {
  return (
    <svg className="h-6 w-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
    </svg>
  );
}

function ArrowIcon() {
  return (
    <svg className="h-5 w-5 text-gray-600 transition group-hover:text-hardlock-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
    </svg>
  );
}
