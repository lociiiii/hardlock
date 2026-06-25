export default function DeviceTable({ devices }) {
  if (!devices?.length) {
    return (
      <div className="rounded-lg border border-dashed border-hardlock-600 px-6 py-10 text-center">
        <p className="text-sm text-gray-500">No devices registered yet.</p>
        <p className="mt-1 text-xs text-gray-600">
          Devices appear here after end-users register via the SDK.
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg border border-hardlock-700">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-hardlock-700 bg-hardlock-800/50">
            <th className="px-4 py-3 font-medium text-gray-400">Label</th>
            <th className="px-4 py-3 font-medium text-gray-400">Fingerprint</th>
            <th className="px-4 py-3 font-medium text-gray-400">Registered</th>
            <th className="px-4 py-3 font-medium text-gray-400">Last Seen</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-hardlock-700">
          {devices.map((device) => (
            <tr key={device.id} className="transition hover:bg-hardlock-800/30">
              <td className="px-4 py-3 text-gray-200">
                {device.label || <span className="text-gray-500 italic">Unnamed</span>}
              </td>
              <td className="px-4 py-3">
                <code className="font-mono text-xs text-gray-400">
                  {device.fingerprint?.slice(0, 16)}…
                </code>
              </td>
              <td className="px-4 py-3 text-gray-400">
                {device.registered_at
                  ? new Date(device.registered_at).toLocaleString()
                  : '—'}
              </td>
              <td className="px-4 py-3 text-gray-400">
                {device.last_seen
                  ? new Date(device.last_seen).toLocaleString()
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
