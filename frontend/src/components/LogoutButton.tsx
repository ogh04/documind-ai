"use client";

import { useAuth } from "@/components/AuthProvider";

export function LogoutButton() {
  const { logout } = useAuth();

  return (
    <button
      type="button"
      onClick={logout}
      className="mt-4 w-full rounded-xl border border-slate-700 px-4 py-3 text-sm font-semibold text-slate-300 transition hover:border-red-400 hover:text-red-300"
    >
      Logout
    </button>
  );
}
