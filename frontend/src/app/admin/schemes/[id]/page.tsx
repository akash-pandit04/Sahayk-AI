import { fetchAPI } from "@/lib/api";
import { getToken } from "@/app/actions/auth";
import Link from "next/link";
import ClientSchemeEditor from "./ClientSchemeEditor";

export default async function EditSchemePage({ params }: { params: { id: string } }) {
  const token = await getToken();
  let scheme = null;
  
  try {
    const res = await fetchAPI(`/admin/schemes/${params.id}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    scheme = res?.data;
  } catch (e) {
    console.error(e);
  }

  if (!scheme) {
    return <div className="p-8 text-red-600">Scheme not found.</div>;
  }

  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Manage Scheme: {scheme.name}</h1>
        <Link href="/admin/schemes" className="text-gray-500 hover:text-gray-700 underline">
          &larr; Back to Schemes
        </Link>
      </div>

      <ClientSchemeEditor initialScheme={scheme} />
    </div>
  );
}
