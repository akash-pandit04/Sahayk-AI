import { ReactNode } from "react";
import Link from "next/link";
import { logout } from "@/app/actions/auth";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-200">
          <span className="text-xl font-bold text-gray-800">Sahayak Admin</span>
        </div>
        <nav className="flex-1 px-4 py-6 space-y-2">
          <Link href="/admin" className="block px-4 py-2 text-gray-700 rounded hover:bg-gray-100 font-medium">
            Dashboard
          </Link>
          <Link href="/admin/schemes" className="block px-4 py-2 text-gray-700 rounded hover:bg-gray-100 font-medium">
            Schemes
          </Link>
          <Link href="/admin/ingestion" className="block px-4 py-2 text-gray-700 rounded hover:bg-gray-100 font-medium">
            Ingestion Queue
          </Link>
          <Link href="/admin/audit-logs" className="block px-4 py-2 text-gray-700 rounded hover:bg-gray-100 font-medium">
            Audit Logs
          </Link>
        </nav>
        <div className="p-4 border-t border-gray-200">
          <form action={logout}>
            <button type="submit" className="w-full px-4 py-2 text-left text-red-600 rounded hover:bg-red-50 font-medium">
              Logout
            </button>
          </form>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-auto">
        {children}
      </div>
    </div>
  );
}
