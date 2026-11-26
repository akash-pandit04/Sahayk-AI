"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

export default function ClientSchemeEditor({ initialScheme }: { initialScheme: any }) {
  const router = useRouter();
  const [scheme, setScheme] = useState(initialScheme);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busySourceId, setBusySourceId] = useState<string | null>(null);

  const proxyCall = async (endpoint: string, method: string, body?: any) => {
    const res = await fetch("/api/admin_proxy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ endpoint, method, body }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Request failed");
    return data;
  };

  const handlePublish = async () => {
    try {
      setError("");
      setMessage("");
      await proxyCall(`/admin/schemes/${scheme.id}`, "PATCH", { status: "PUBLISHED" });
      setMessage("Scheme published successfully!");
      router.refresh();
      setScheme({ ...scheme, status: "PUBLISHED" });
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleCreateNewVersion = async () => {
    try {
      setError("");
      setMessage("");
      const res = await proxyCall(`/admin/schemes/${scheme.id}/new-version`, "POST");
      const newScheme = res.data;
      setMessage(`Created Draft v${newScheme.version}. Redirecting...`);
      router.push(`/admin/schemes/${newScheme.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleRecheckSource = async (sourceId: string) => {
    try {
      setBusySourceId(sourceId);
      setError("");
      setMessage("");
      const res = await proxyCall(`/admin/schemes/${scheme.id}/sources/${sourceId}/recheck`, "POST");
      const result = res.data;
      setScheme({
        ...scheme,
        sources: scheme.sources.map((s: any) =>
          s.id === sourceId
            ? {
                ...s,
                verification_status: result.verification_status,
                content_hash: result.content_hash,
                last_fetched_at: result.last_fetched_at,
                last_verified_at: result.last_verified_at,
              }
            : s
        ),
      });
      setMessage(
        result.changed
          ? "Source content changed! Status set to NEEDS_REVIEW."
          : "Source checked: content hash unchanged."
      );
      router.refresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusySourceId(null);
    }
  };

  const handleVerifySource = async (sourceId: string) => {
    try {
      setBusySourceId(sourceId);
      setError("");
      setMessage("");
      await proxyCall(`/admin/schemes/${scheme.id}/sources/${sourceId}`, "PATCH", {
        verification_status: "VERIFIED",
      });
      setScheme({
        ...scheme,
        sources: scheme.sources.map((s: any) =>
          s.id === sourceId ? { ...s, verification_status: "VERIFIED", last_verified_at: new Date().toISOString() } : s
        ),
      });
      setMessage("Source marked VERIFIED.");
      router.refresh();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusySourceId(null);
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
        verification_status: "VERIFIED",
      });
      setMessage("Source added and verified!");
      router.refresh();
      window.location.reload();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const addRule = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    try {
      await proxyCall(`/admin/schemes/${scheme.id}/rules`, "POST", {
        field: fd.get("field"),
        operator: fd.get("operator"),
        value: fd.get("value"),
        data_type: fd.get("data_type"),
      });
      setMessage("Rule added!");
      router.refresh();
      window.location.reload();
    } catch (e: any) {
      setError(e.message);
    }
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
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <div className="space-y-6">
      {error && <div className="p-4 bg-red-50 text-red-600 rounded-lg">{error}</div>}
      {message && <div className="p-4 bg-green-50 text-green-700 rounded-lg">{message}</div>}

      <div className="bg-white p-6 rounded-xl border border-gray-200 flex flex-wrap justify-between items-center gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold">
              Status: <span className="text-blue-600">{scheme.status}</span>
            </h2>
            <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
              Version v{scheme.version || 1}
            </span>
          </div>
          {scheme.parent_scheme_id && (
            <p className="text-xs text-gray-500 mt-1">
              Derived from{" "}
              <Link href={`/admin/schemes/${scheme.parent_scheme_id}`} className="text-blue-600 hover:underline">
                parent scheme
              </Link>
            </p>
          )}
          <p className="text-gray-500 text-sm mt-1">
            Schemes must have benefits, rules, and verified official government sources to be published.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleCreateNewVersion}
            className="bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 px-4 py-2 rounded font-medium text-sm"
          >
            Create Draft v{(scheme.version || 1) + 1}
          </button>
          {scheme.status !== "PUBLISHED" && (
            <button onClick={handlePublish} className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded font-medium text-sm">
              Publish Scheme
            </button>
          )}
        </div>
      </div>

      {/* Structured Add Forms */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Source */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 md:col-span-2">
          <h3 className="font-semibold mb-4 text-lg">Sources &amp; Freshness Verification</h3>
          <form onSubmit={addSource} className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <input name="title" placeholder="Source Title" required className="p-2 border rounded text-sm" />
            <input name="url" type="url" placeholder="https://..." required className="p-2 border rounded text-sm" />
            <select name="source_type" required className="p-2 border rounded text-sm">
              <option value="OFFICIAL_GOVERNMENT">Official Government</option>
              <option value="STATE_GOVERNMENT">State Government</option>
              <option value="GOVERNMENT_PORTAL">Government Portal</option>
              <option value="MINISTRY">Ministry</option>
            </select>
            <button className="bg-blue-100 text-blue-700 py-2 px-4 rounded hover:bg-blue-200 text-sm font-medium">
              Add &amp; Verify Source
            </button>
          </form>

          <div className="mt-5 pt-4 border-t">
            <p className="font-medium text-sm text-gray-500 mb-3">Current Sources:</p>
            <div className="space-y-3">
              {scheme.sources?.length === 0 && <p className="text-sm text-gray-400">No sources attached.</p>}
              {scheme.sources?.map((s: any) => (
                <div key={s.id} className="p-3 bg-gray-50 border border-gray-200 rounded-lg flex flex-wrap justify-between items-center gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm text-gray-900">{s.title}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-gray-200 text-gray-700">{s.source_type}</span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded font-medium ${
                          s.verification_status === "VERIFIED"
                            ? "bg-green-100 text-green-800"
                            : s.verification_status === "NEEDS_REVIEW"
                            ? "bg-red-100 text-red-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {s.verification_status}
                      </span>
                    </div>
                    <a href={s.url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline block break-all">
                      {s.url}
                    </a>
                    <div className="text-xs text-gray-500 flex flex-wrap gap-4">
                      <span>Last Verified: {s.last_verified_at ? new Date(s.last_verified_at).toLocaleString() : "Never"}</span>
                      <span>Last Fetched: {s.last_fetched_at ? new Date(s.last_fetched_at).toLocaleString() : "Never"}</span>
                      {s.content_hash && <span className="font-mono">Hash: {s.content_hash.slice(0, 10)}</span>}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={busySourceId === s.id}
                      onClick={() => handleRecheckSource(s.id)}
                      className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-300 rounded hover:bg-gray-100 disabled:opacity-50"
                    >
                      {busySourceId === s.id ? "Checking..." : "Re-check Source"}
                    </button>
                    {s.verification_status !== "VERIFIED" && (
                      <button
                        type="button"
                        disabled={busySourceId === s.id || s.source_type === "OTHER"}
                        onClick={() => handleVerifySource(s.id)}
                        className="px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
                      >
                        Mark Verified
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
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
              <option value="BOOLEAN">Boolean</option>
            </select>
            <button className="w-full bg-blue-100 text-blue-700 py-2 rounded hover:bg-blue-200">Add Rule</button>
          </form>

          <div className="mt-4 pt-4 border-t">
            <p className="font-medium text-sm text-gray-500">Current Rules:</p>
            <ul className="text-sm mt-2 space-y-1">
              {scheme.eligibility_rules?.map((r: any) => (
                <li key={r.id}>
                  {r.field} {r.operator} {r.value}
                </li>
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
              {scheme.benefits?.map((b: any) => (
                <li key={b.id}>{b.description}</li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
