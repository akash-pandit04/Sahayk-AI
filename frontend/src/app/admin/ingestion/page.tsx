"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

interface IngestionRecordItem {
  id: string;
  source_url?: string;
  source_type?: string;
  source_domain?: string;
  source_title?: string;
  status: string;
  content_hash?: string;
  fetched_at?: string;
  normalized_data?: any;
  ambiguity_flags?: Record<string, string>;
  raw_text?: string;
  scheme_id?: string;
  rejection_reason?: string;
}

const SOURCE_TYPES = [
  { value: "OFFICIAL_GOVERNMENT", label: "Official Government (.gov.in / .nic.in)" },
  { value: "STATE_GOVERNMENT", label: "State Government Portal" },
  { value: "GOVERNMENT_PORTAL", label: "Authorized Government Portal" },
  { value: "MINISTRY", label: "Union / State Ministry" },
  { value: "OTHER", label: "Other (Requires Manual Verification, Cannot Publish)" },
];

export default function IngestionDashboardPage() {
  const [records, setRecords] = useState<IngestionRecordItem[]>([]);
  const [selectedRecord, setSelectedRecord] = useState<IngestionRecordItem | null>(null);
  const [editedJson, setEditedJson] = useState("");
  const [url, setUrl] = useState("");
  const [urlSourceType, setUrlSourceType] = useState("OFFICIAL_GOVERNMENT");
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [pdfSourceType, setPdfSourceType] = useState("OFFICIAL_GOVERNMENT");
  const [pdfSourceUrl, setPdfSourceUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

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

  const loadRecords = async () => {
    try {
      const data = await proxyCall("/admin/ingestion", "GET");
      setRecords(data.items || []);
    } catch (e: any) {
      setError(e.message);
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const handleIngestUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const res = await proxyCall("/admin/ingestion/url", "POST", {
        url,
        source_type: urlSourceType,
      });
      setMessage(`Extracted URL content (Record ${res.id.slice(0, 8)}). Run AI normalization next.`);
      setUrl("");
      await loadRecords();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleIngestPdf = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pdfFile) return;
    setLoading(true);
    setError("");
    setMessage("");
    try {
      const formData = new FormData();
      formData.append("endpoint", "/admin/ingestion/pdf");
      formData.append("source_type", pdfSourceType);
      if (pdfSourceUrl) formData.append("source_url", pdfSourceUrl);
      formData.append("file", pdfFile);

      const res = await fetch("/api/admin_proxy", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "PDF ingestion failed");
      setMessage(`Extracted PDF text (Record ${data.id.slice(0, 8)}). Run AI normalization next.`);
      setPdfFile(null);
      setPdfSourceUrl("");
      await loadRecords();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleNormalize = async (recordId: string) => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      await proxyCall(`/admin/ingestion/${recordId}/normalize`, "POST");
      setMessage("LLM normalization complete. Review the extracted proposal before approving.");
      await loadRecords();
      await handleInspect(recordId);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleInspect = async (recordId: string) => {
    setError("");
    try {
      const full = await proxyCall(`/admin/ingestion/${recordId}`, "GET");
      setSelectedRecord(full);
      setEditedJson(JSON.stringify(full.normalized_data || {}, null, 2));
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleApprove = async (recordId: string) => {
    setLoading(true);
    setError("");
    setMessage("");
    try {
      let parsedBody: any = undefined;
      if (selectedRecord?.id === recordId && editedJson.trim()) {
        parsedBody = { normalized_data: JSON.parse(editedJson) };
      }
      const res = await proxyCall(`/admin/ingestion/${recordId}/approve`, "POST", parsedBody);
      setMessage(`Approved! Created Draft Scheme (${res.scheme_id}). Verify rules & sources before publishing.`);
      setSelectedRecord(null);
      await loadRecords();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async (recordId: string) => {
    const reason = window.prompt("Reason for rejecting this ingestion record:", "Source invalid or ambiguous");
    if (!reason) return;
    setLoading(true);
    setError("");
    try {
      await proxyCall(`/admin/ingestion/${recordId}/reject`, "POST", { reason });
      setMessage("Ingestion record rejected.");
      if (selectedRecord?.id === recordId) setSelectedRecord(null);
      await loadRecords();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Verified Scheme Ingestion</h1>
        <p className="text-sm text-gray-600 mt-1">
          Human-in-the-loop pipeline: Fetch official government URL/PDF &rarr; Extract text &rarr; AI Normalize &rarr; Admin Review &rarr; Draft Scheme.
        </p>
      </div>

      {error && <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg text-sm">{error}</div>}
      {message && <div className="p-4 bg-green-50 border border-green-200 text-green-800 rounded-lg text-sm">{message}</div>}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Ingest from Official URL</h2>
          <form onSubmit={handleIngestUrl} className="space-y-3">
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://pmkisan.gov.in/..."
              className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
            />
            <select
              value={urlSourceType}
              onChange={(e) => setUrlSourceType(e.target.value)}
              className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium text-sm"
            >
              Fetch &amp; Extract URL
            </button>
          </form>
        </div>

        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-900 mb-3">Upload Official Guideline PDF</h2>
          <form onSubmit={handleIngestPdf} className="space-y-3">
            <input
              type="file"
              accept="application/pdf,.pdf"
              required
              onChange={(e) => setPdfFile(e.target.files?.[0] || null)}
              className="w-full p-2 border border-gray-300 rounded-lg text-sm"
            />
            <input
              type="url"
              value={pdfSourceUrl}
              onChange={(e) => setPdfSourceUrl(e.target.value)}
              placeholder="Original official PDF URL (optional)"
              className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
            />
            <select
              value={pdfSourceType}
              onChange={(e) => setPdfSourceType(e.target.value)}
              className="w-full p-2.5 border border-gray-300 rounded-lg text-sm"
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <button
              type="submit"
              disabled={loading || !pdfFile}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white py-2.5 rounded-lg font-medium text-sm"
            >
              Upload &amp; Extract PDF
            </button>
          </form>
        </div>
      </div>

      {/* Ingestion Queue Table */}
      <div className="bg-white rounded-xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-lg font-semibold text-gray-900">Ingestion Records</h2>
          <button onClick={loadRecords} className="text-sm text-blue-600 hover:underline">Refresh</button>
        </div>
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200 text-xs uppercase text-gray-500">
              <th className="p-4">Source</th>
              <th className="p-4">Trust Tier</th>
              <th className="p-4">Status</th>
              <th className="p-4">Hash</th>
              <th className="p-4">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 text-sm">
            {records.length === 0 && (
              <tr>
                <td colSpan={5} className="p-6 text-center text-gray-500">No ingestion records yet.</td>
              </tr>
            )}
            {records.map((rec) => (
              <tr key={rec.id} className="hover:bg-gray-50">
                <td className="p-4">
                  <div className="font-medium text-gray-900">{rec.source_title || rec.source_domain || "Uploaded Document"}</div>
                  {rec.source_url && (
                    <a href={rec.source_url} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline break-all">
                      {rec.source_url}
                    </a>
                  )}
                </td>
                <td className="p-4 text-xs text-gray-600">{rec.source_type || "-"}</td>
                <td className="p-4">
                  <span className={`px-2 py-1 text-xs font-medium rounded-full ${
                    rec.status === "REVIEWED" ? "bg-green-100 text-green-800" :
                    rec.status === "NORMALIZED" ? "bg-blue-100 text-blue-800" :
                    rec.status === "REJECTED" ? "bg-red-100 text-red-800" :
                    "bg-amber-100 text-amber-800"
                  }`}>
                    {rec.status}
                  </span>
                </td>
                <td className="p-4 font-mono text-xs text-gray-500">{rec.content_hash ? rec.content_hash.slice(0, 10) : "-"}</td>
                <td className="p-4 space-x-2 whitespace-nowrap">
                  <button onClick={() => handleInspect(rec.id)} className="text-gray-700 hover:underline">Inspect</button>
                  {rec.status === "EXTRACTED" && (
                    <button
                      onClick={() => handleNormalize(rec.id)}
                      disabled={loading}
                      className="text-blue-600 font-medium hover:underline"
                    >
                      Normalize
                    </button>
                  )}
                  {rec.status === "NORMALIZED" && (
                    <>
                      <button
                        onClick={() => handleApprove(rec.id)}
                        disabled={loading}
                        className="text-green-600 font-medium hover:underline"
                      >
                        Approve Draft
                      </button>
                      <button
                        onClick={() => handleReject(rec.id)}
                        disabled={loading}
                        className="text-red-600 hover:underline"
                      >
                        Reject
                      </button>
                    </>
                  )}
                  {rec.status === "REVIEWED" && rec.scheme_id && (
                    <Link href={`/admin/schemes/${rec.scheme_id}`} className="text-indigo-600 font-medium hover:underline">
                      Open Scheme &rarr;
                    </Link>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Review Drawer / Inspector */}
      {selectedRecord && (
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold text-gray-900">
              Review Proposal ({selectedRecord.status})
            </h3>
            <button onClick={() => setSelectedRecord(null)} className="text-sm text-gray-500 hover:text-gray-800">
              Close
            </button>
          </div>

          {selectedRecord.ambiguity_flags && Object.keys(selectedRecord.ambiguity_flags).length > 0 && (
            <div className="p-4 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-sm font-semibold text-amber-800 mb-1">Ambiguity Flags (Requires Manual Review)</p>
              <ul className="list-disc pl-5 text-xs text-amber-900 space-y-1">
                {Object.entries(selectedRecord.ambiguity_flags).map(([k, v]) => (
                  <li key={k}><span className="font-semibold">{k}:</span> {String(v)}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
                Extracted Untrusted Raw Text
              </label>
              <textarea
                readOnly
                value={selectedRecord.raw_text || ""}
                rows={14}
                className="w-full p-3 border border-gray-200 bg-gray-50 rounded-lg font-mono text-xs"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-600 uppercase mb-1">
                Normalized Scheme Proposal (Editable JSON)
              </label>
              <textarea
                value={editedJson}
                onChange={(e) => setEditedJson(e.target.value)}
                rows={14}
                className="w-full p-3 border border-gray-300 rounded-lg font-mono text-xs"
              />
            </div>
          </div>

          {selectedRecord.status === "NORMALIZED" && (
            <div className="flex justify-end gap-3">
              <button
                onClick={() => handleReject(selectedRecord.id)}
                disabled={loading}
                className="px-4 py-2 border border-red-300 text-red-700 rounded-lg text-sm hover:bg-red-50"
              >
                Reject Proposal
              </button>
              <button
                onClick={() => handleApprove(selectedRecord.id)}
                disabled={loading}
                className="px-5 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium"
              >
                Approve &amp; Create Draft Scheme
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
