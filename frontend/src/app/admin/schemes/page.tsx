import { fetchAPI } from "@/lib/api";
import { getToken } from "@/app/actions/auth";
import Link from "next/link";

export default async function SchemesListPage() {
  const token = await getToken();
  
  let schemes = [];
  try {
    const res = await fetchAPI("/admin/schemes", {
      headers: { Authorization: `Bearer ${token}` }
    });
    schemes = res?.data?.items || [];
  } catch (e) {
    console.error(e);
  }

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Schemes</h1>
        <Link href="/admin/schemes/new" className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          + New Scheme
        </Link>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="p-4 text-sm font-semibold text-gray-600">Name</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Status</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Target Group</th>
              <th className="p-4 text-sm font-semibold text-gray-600">Actions</th>
            </tr>
          </thead>
          <tbody>
            {schemes.length === 0 && (
              <tr>
                <td colSpan={4} className="p-4 text-center text-gray-500">No schemes found.</td>
              </tr>
            )}
            {schemes.map((scheme: any) => (
              <tr key={scheme.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-4">
                  <div className="font-medium text-gray-900">{scheme.name}</div>
                  <div className="text-xs text-gray-500 mt-1 truncate max-w-xs">{scheme.short_description}</div>
                </td>
                <td className="p-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    scheme.status === 'PUBLISHED' ? 'bg-green-100 text-green-800' :
                    scheme.status === 'DRAFT' ? 'bg-amber-100 text-amber-800' :
                    'bg-blue-100 text-blue-800'
                  }`}>
                    {scheme.status}
                  </span>
                </td>
                <td className="p-4 text-sm text-gray-600">{scheme.target_group || "-"}</td>
                <td className="p-4">
                  {/* We will route to a detail/edit page, but for now just link to edit */}
                  <Link href={`/admin/schemes/${scheme.id}`} className="text-blue-600 hover:underline text-sm font-medium">
                    Edit
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
