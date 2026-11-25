import { fetchAPI } from "@/lib/api";
import { getToken } from "@/app/actions/auth";

export default async function AuditLogsPage() {
  const token = await getToken();
  let logs = [];
  
  try {
    const res = await fetchAPI("/admin/audit-logs", {
      headers: { Authorization: `Bearer ${token}` }
    });
    logs = res?.data?.items || [];
  } catch (e) {
    console.error(e);
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Audit Logs</h1>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="p-4 text-sm font-semibold text-gray-600">Timestamp</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Action</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Entity</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Admin ID</th>
            </tr>
          </thead>
          <tbody>
            {logs.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center text-gray-500">No audit logs found.</td>
              </tr>
            )}
            {logs.map((log: any) => (
              <tr key={log.id} className="border-b border-gray-100 hover:bg-gray-50 text-sm">
                <td className="p-4 whitespace-nowrap text-gray-500">
                  {new Date(log.timestamp).toLocaleString()}
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    log.action === 'CREATE' ? 'bg-green-100 text-green-800' :
                    log.action === 'UPDATE' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {log.action}
                  </span>
                </td>
                <td className="p-4 font-medium text-gray-700">{log.entity_type} <span className="text-gray-400 font-normal">({log.entity_id.split('-')[0]})</span></td>
                <td className="p-4 text-gray-500 font-mono text-xs">{log.admin_id || "System"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
