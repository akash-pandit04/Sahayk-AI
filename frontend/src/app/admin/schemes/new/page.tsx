"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { API_BASE } from "@/lib/api";

export default function NewSchemePage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    
    const formData = new FormData(e.currentTarget);
    
    try {
      const res = await fetch("/api/admin_proxy", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          endpoint: "/admin/schemes",
          method: "POST",
          body: {
            name: formData.get("name"),
            short_description: formData.get("short_description"),
            detailed_description: formData.get("detailed_description"),
            target_group: formData.get("target_group"),
          }
        })
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || "Failed to create scheme");
      }
      
      const data = await res.json();
      router.push(`/admin/schemes/${data.data.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Create New Scheme</h1>
      
      {error && <div className="bg-red-50 text-red-600 p-4 rounded-md mb-6">{error}</div>}
      
      <form onSubmit={handleSubmit} className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Scheme Name *</label>
          <input name="name" required className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Short Description *</label>
          <input name="short_description" required className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
        </div>
        
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Detailed Description *</label>
          <textarea name="detailed_description" required rows={4} className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Target Group</label>
          <input name="target_group" className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500" />
        </div>
        
        <button type="submit" disabled={loading} className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Creating..." : "Create Scheme"}
        </button>
      </form>
    </div>
  );
}
