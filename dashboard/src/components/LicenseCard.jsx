import { useState } from 'react';
import { licensesApi } from '../api/client';

const STATE_STYLES = {
  ISSUED: 'bg-blue-500/20 text-blue-400 ring-blue-500/30',
  ACTIVE: 'bg-green-500/20 text-green-400 ring-green-500/30',
  SUSPENDED: 'bg-yellow-500/20 text-yellow-400 ring-yellow-500/30',
  REVOKED: 'bg-red-500/20 text-red-400 ring-red-500/30',
};

export default function LicenseCard({ license, onRevoked }) {
  const [revoking, setRevoking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(license.license_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleRevoke = async () => {
    if (!confirm(`Revoke license ${license.license_key}? This cannot be undone.`)) return;

    setRevoking(true);
    setError('');
    try {
      await licensesApi.revoke(license.license_key);
      onRevoked?.(license.license_key);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to revoke license.');
    } finally {
      setRevoking(false);
    }
  };

  const stateClass = STATE_STYLES[license.state] || STATE_STYLES.ISSUED;

  return (
    <div className="card !p-4">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <code className="truncate font-mono text-sm text-hardlock-accent">
              {license.license_key}
            </code>
            <button
              onClick={handleCopy}
              className="shrink-0 rounded p-1 text-gray-500 transition hover:bg-hardlock-800 hover:text-gray-300"
              title="Copy license key"
            >
              {copied ? <CheckIcon /> : <CopyIcon />}
            </button>
          </div>

          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${stateClass}`}>
              {license.state}
            </span>
            <span className="text-xs text-gray-500">
              {license.registered_devices ?? 0} / {license.max_devices ?? 1} devices
            </span>
            {license.expires_at && (
              <span className="text-xs text-gray-500">
                Expires {new Date(license.expires_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {error && <p className="mt-2 text-xs text-red-400">{error}</p>}
        </div>

        {license.state !== 'REVOKED' && (
          <button
            onClick={handleRevoke}
            disabled={revoking}
            className="btn-danger shrink-0"
          >
            {revoking ? 'Revoking…' : 'Revoke'}
          </button>
        )}
      </div>
    </div>
  );
}

function CopyIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M15.666 3.888A2.25 2.25 0 0013.5 2.25h-3c-1.03 0-1.9.693-2.166 1.638m7.332 0c.055.194.084.4.084.612v0a.75.75 0 01-.75.75H9.75a.75.75 0 01-.75-.75v0c0-.212.03-.418.084-.612m7.332 0c.646.049 1.288.11 1.927.184 1.1.128 1.907 1.077 1.907 2.185V19.5a2.25 2.25 0 01-2.25 2.25H6.75A2.25 2.25 0 014.5 19.5V6.257c0-1.108.806-2.057 1.907-2.185a48.208 48.208 0 011.927-.184" />
    </svg>
  );
}

function CheckIcon() {
  return (
    <svg className="h-4 w-4 text-hardlock-success" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
    </svg>
  );
}
