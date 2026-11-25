import { fetchAPI } from "@/lib/api";
import { getToken } from "@/app/actions/auth";
import Link from "next/link";

export default async function DashboardPage() {
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

  const total = schemes.length;
  const published = schemes.filter((s: any) => s.status === "PUBLISHED").length;
  const drafts = schemes.filter((s: any) => s.status === "DRAFT").length;
  const verified = schemes.filter((s: any) => s.status === "SOURCE_VERIFIED").length;

  return (
    <div className="p-8">
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <Link href="/admin/schemes/new" className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700">
          + New Scheme
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-gray-500 text-sm font-medium mb-1">Total Schemes</h3>
          <p className="text-3xl font-bold text-gray-900">{total}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-gray-500 text-sm font-medium mb-1">Published</h3>
          <p className="text-3xl font-bold text-green-600">{published}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-gray-500 text-sm font-medium mb-1">Verified (Pending Publish)</h3>
          <p className="text-3xl font-bold text-blue-600">{verified}</p>
        </div>
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="text-gray-500 text-sm font-medium mb-1">Drafts</h3>
          <p className="text-3xl font-bold text-amber-500">{drafts}</p>
        </div>
      </div>
    </div>
  );
}
