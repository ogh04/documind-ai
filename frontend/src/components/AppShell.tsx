import Link from "next/link";
import { ReactNode } from "react";

import { appNavigation } from "@/lib/navigation";

type AppShellProps = {
  children: ReactNode;
  title: string;
  description: string;
};

export function AppShell({ children, title, description }: AppShellProps) {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <aside className="fixed inset-y-0 left-0 hidden w-72 border-r border-slate-800 bg-slate-900/80 p-6 lg:block">
        <Link href="/" className="block">
          <p className="text-sm font-semibold uppercase tracking-[0.3em] text-cyan-400">
            DocuMind AI
          </p>
          <h1 className="mt-3 text-2xl font-bold">RAG Workspace</h1>
        </Link>

        <nav className="mt-10 space-y-2">
          {appNavigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="block rounded-xl px-4 py-3 text-sm font-medium text-slate-300 transition hover:bg-slate-800 hover:text-cyan-300"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="absolute bottom-6 left-6 right-6 rounded-2xl border border-slate-800 bg-slate-950 p-4 text-sm text-slate-400">
          Backend target:
          <span className="mt-1 block font-mono text-cyan-300">
            localhost:8000
          </span>
        </div>
      </aside>

      <section className="lg:pl-72">
        <header className="border-b border-slate-800 bg-slate-950/80 px-6 py-6 backdrop-blur">
          <div className="mx-auto max-w-6xl">
            <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-400">
              Frontend Foundation
            </p>
            <h2 className="mt-3 text-3xl font-bold">{title}</h2>
            <p className="mt-2 max-w-2xl text-slate-400">{description}</p>
          </div>
        </header>

        <div className="mx-auto max-w-6xl px-6 py-8">{children}</div>
      </section>
    </main>
  );
}
