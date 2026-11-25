"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function ClientSchemeEditor({ initialScheme }: { initialScheme: any }) {
  const router = useRouter();
  const [scheme, setScheme] = useState(initialScheme);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const proxyCall = async (endpoint: string, method: string, body?: any) => {
    const res = await fetch("/api/admin_proxy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint, method, body })
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  };

  const handlePublish = async () => {
    try {
      setError(""); setMessage("");
      await proxyCall(`/admin/schemes/${scheme.id}`, "PATCH", { status: "PUBLISHED" });
      setMessage("Scheme published successfully!");
      router.refresh();
      setScheme({ ...scheme, status: "PUBLISHED" });
    } catch (e: any) {
      setError(e.message);
    }
  };

  const addSource = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await proxyCall(`/admin/schemes/${scheme.id}/sources`, "POST", {
        title: fd.get("title"),
        url: fd.get("url"),
        source_type: fd.get("source_type"),
        verification_status: "VERIFIED"
      });
      setMessage("Source added and verified!");
      router.refresh();
      window.location.reload(); // Simple refresh for prototype
    } catch(e: any) { setError(e.message); }
  };
  
  const addRule = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await proxyCall(`/admin/schemes/${scheme.id}/rules`, "POST", {
        field: fd.get("field"),
        operator: fd.get("operator"),
        value: fd.get("value"),
        data_type: fd.get("data_type")
      });
      setMessage("Rule added!");
      router.refresh();
      window.location.reload(); 
    } catch(e: any) { setError(e.message); }
  };

  const addBenefit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await proxyCall(`/admin/schemes/${scheme.id}/benefits`, "POST", {
        benefit_type: fd.get("benefit_type"),
        description: fd.get("description"),
      });
      setMessage("Benefit added!");
      router.refresh();
      window.location.reload(); 
    } catch(e: any) { setError(e.message); }
  };

  return (
    <div className="space-y-6">
      {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>}
      {message && <div className="p-4 bg-green-50 text-green-700 rounded-lg">{message}</div>}

      <div className="bg-white p-6 rounded-xl border border-gray-200 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold">Status: <span className="text-blue-600">{scheme.status}</span></h2>
          <p className="text-gray-500 text-sm mt-1">Schemes must have benefits, rules, and verified sources to be published.</p>
        </div>
        {scheme.status !== "PUBLISHED" && (
          <button onClick={handlePublish} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-medium">
            Publish Scheme
          </button>
        )}
      </div>

      {/* Structured Add Forms */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Source */}
        <div className="bg-white p-6 rounded-xl border border-gray-200">
          <h3 className="font-semibold mb-4 text-lg">Add Source</h3>
          <form onSubmit={addSource} className="space-y-3">
            <input name="title" placeholder="Source Title" required className="w-full p-2 border rounded" />
            <input name="url" type="url" placeholder="https://..." required className="w-full p-2 border rounded" />
            <select name="source_type" required className="w-full p-2 border rounded">
              <option value="OFFICIAL_GOVERNMENT">Official Government</option>
              <option value="STATE_GOVERNMENT">State Government</option>
            </select>
            <button className="w-full bg-blue-100 text-blue-700 py-2 rounded hover:bg-blue-200">Add & Verify Source</button>
          </form>
          
          <div className="mt-4 pt-4 border-t">
            <p className="font-medium text-sm text-gray-500">Current Sources:</p>
            <ul className="text-sm mt-2 space-y-1">
              {scheme.sources?.map((s:any) => (
                <li key={s.id} className="flex justify-between">
                  <span>{s.title}</span>
                  {s.verification_status === "VERIFIED" ? <span className="text-green-600">✓ Verified</span> : <span className="text-amber-500">⚠ Unverified</span>}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Rule */}
        <div className="bg-white p-6 rounded-xl border border-gray-200">
          <h3 className="font-semibold mb-4 text-lg">Add Eligibility Rule</h3>
          <form onSubmit={addRule} className="space-y-3">
            <input name="field" placeholder="Field (e.g., age, income)" required className="w-full p-2 border rounded" />
            <select name="operator" required className="w-full p-2 border rounded">
              <option value="EQUALS">Equals</option>
              <option value="GREATER_THAN_EQUALS">Greater Than or Equals</option>
              <option value="LESS_THAN_EQUALS">Less Than or Equals</option>
              <option value="IN">In</option>
            </select>
            <input name="value" placeholder="Value (e.g., 60)" required className="w-full p-2 border rounded" />
            <select name="data_type" required className="w-full p-2 border rounded">
              <option value="NUMBER">Number</option>
              <option value="STRING">String</option>
            </select>
            <button className="w-full bg-blue-100 text-blue-700 py-2 rounded hover:bg-blue-200">Add Rule</button>
          </form>

          <div className="mt-4 pt-4 border-t">
            <p className="font-medium text-sm text-gray-500">Current Rules:</p>
            <ul className="text-sm mt-2 space-y-1">
              {scheme.eligibility_rules?.map((r:any) => (
                <li key={r.id}>{r.field} {r.operator} {r.value}</li>
              ))}
            </ul>
          </div>
        </div>

        {/* Benefit */}
        <div className="bg-white p-6 rounded-xl border border-gray-200">
          <h3 className="font-semibold mb-4 text-lg">Add Benefit</h3>
          <form onSubmit={addBenefit} className="space-y-3">
            <select name="benefit_type" required className="w-full p-2 border rounded">
              <option value="FINANCIAL">Financial</option>
              <option value="SERVICE">Service / Material</option>
            </select>
            <input name="description" placeholder="Description (e.g. Rs 5000/month)" required className="w-full p-2 border rounded" />
            <button className="w-full bg-blue-100 text-blue-700 py-2 rounded hover:bg-blue-200">Add Benefit</button>
          </form>
          
          <div className="mt-4 pt-4 border-t">
            <p className="font-medium text-sm text-gray-500">Current Benefits:</p>
            <ul className="text-sm mt-2 space-y-1">
              {scheme.benefits?.map((b:any) => (
                <li key={b.id}>{b.description}</li>
              ))}
            </ul>
          </div>
        </div>
        
      </div>
    </div>
  );
}
