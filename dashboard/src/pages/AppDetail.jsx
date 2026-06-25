import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { appsApi, licensesApi } from '../api/client';
import LicenseCard from '../components/LicenseCard';
import DeviceTable from '../components/DeviceTable';

export default function AppDetail() {
  const { id } = useParams();
  const [app, setApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genCount, setGenCount] = useState(1);
  const [genMaxDevices, setGenMaxDevices] = useState(1);
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState('licenses');

  const fetchApp = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await appsApi.get(id);
      setApp(data);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load application.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApp();
  }, [id]);

  const handleGenerate = async () => {
    setGenerating(true);
    setError('');
    try {
      await licensesApi.generate(id, genCount, genMaxDevices);
      await fetchApp();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate licenses.');
    } finally {
      setGenerating(false);
    }
  };

  const handleRevoked = () => {
    fetchApp();
  };

  const handleCopyApiKey = async () => {
    await navigator.clipboard.writeText(app.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const allDevices = app?.licenses?.flatMap((lic) =>
    (lic.devices || []).map((d) => ({ ...d, license_key: lic.license_key })),
  ) ?? [];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 animate-pulse rounded bg-hardlock-700" />
        <div className="card h-64 animate-pulse" />
      </div>
    );
  }

  if (error && !app) {
    return (
      <div>
        <Link to="/apps" className="mb-4 inline-flex items-center text-sm text-gray-400 hover:text-gray-200">
          ← Back to Applications
        </Link>
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      </div>
    );
  }

  return (
    <div>
      <Link to="/apps" className="mb-4 inline-flex items-center text-sm text-gray-400 transition hover:text-gray-200">
        ← Back to Applications
      </Link>

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">{app.name}</h1>
        {app.description && (
          <p className="mt-1 text-sm text-gray-400">{app.description}</p>
        )}
      </div>

      <div className="card mb-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-gray-500">API Key</p>
            <code className="mt-1 block font-mono text-sm text-hardlock-accent">{app.api_key}</code>
          </div>
          <button onClick={handleCopyApiKey} className="btn-secondary">
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
        <p className="mt-3 text-xs text-gray-500">
          Use this key in the HardLock SDK: <code className="text-gray-400">HardLock(api_key=&quot;…&quot;)</code>
        </p>
      </div>

      {app.stats && (
        <div className="mb-6 grid grid-cols-3 gap-4">
          {[
            { label: 'Licenses', value: app.stats.total_licenses ?? app.licenses?.length ?? 0 },
            { label: 'Active Devices', value: app.stats.active_devices ?? allDevices.length },
            { label: 'Launches', value: app.stats.total_launches ?? '—' },
          ].map(({ label, value }) => (
            <div key={label} className="card !p-4 text-center">
              <p className="text-xs text-gray-500">{label}</p>
              <p className="text-xl font-bold text-white">{value}</p>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="mb-6 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      <div className="mb-4 flex gap-1 rounded-lg border border-hardlock-700 bg-hardlock-900 p-1">
        {['licenses', 'devices'].map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 rounded-md px-4 py-2 text-sm font-medium capitalize transition ${
              activeTab === tab
                ? 'bg-hardlock-800 text-white'
                : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === 'licenses' && (
        <div>
          <div className="card mb-4 !p-4">
            <h3 className="mb-3 text-sm font-medium text-gray-300">Generate Licenses</h3>
            <div className="flex flex-wrap items-end gap-4">
              <div>
                <label className="mb-1 block text-xs text-gray-500">Count</label>
                <input
                  type="number"
                  min={1}
                  max={100}
                  className="input-field w-24"
                  value={genCount}
                  onChange={(e) => setGenCount(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-gray-500">Max Devices</label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  className="input-field w-24"
                  value={genMaxDevices}
                  onChange={(e) => setGenMaxDevices(Number(e.target.value))}
                />
              </div>
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="btn-primary"
              >
                {generating ? 'Generating…' : 'Generate'}
              </button>
            </div>
          </div>

          <div className="space-y-3">
            {app.licenses?.length ? (
              app.licenses.map((license) => (
                <LicenseCard
                  key={license.id || license.license_key}
                  license={license}
                  onRevoked={handleRevoked}
                />
              ))
            ) : (
              <div className="rounded-lg border border-dashed border-hardlock-600 px-6 py-10 text-center">
                <p className="text-sm text-gray-500">No licenses generated yet.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'devices' && <DeviceTable devices={allDevices} />}
    </div>
  );
}
