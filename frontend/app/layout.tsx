import "./globals.css"
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'], variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'InstaChef AI — Cooking Commerce Agent',
  description: 'Turn any recipe video, blog, or text into a Swiggy Instamart grocery order in seconds. Powered by a 10-node AI pipeline with semantic matching, pantry intelligence, and real-time order tracking.',
  keywords: ['recipe', 'grocery', 'AI', 'Swiggy', 'Instamart', 'cooking', 'commerce', 'agent'],
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.variable} font-sans`}>
        <div className="min-h-screen flex flex-col bg-gray-50">
          {/* ── Header ──────────────────────────────────────── */}
          <header className="sticky top-0 z-50 border-b border-brand-border bg-white shadow-sm">
            <div className="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
              {/* Logo */}
              <div className="flex items-center gap-3">
                <div className="relative w-10 h-10 bg-gradient-to-br from-swiggy to-swiggy-600 rounded-2xl flex items-center justify-center shadow-glow-orange">
                  <svg viewBox="0 0 24 24" className="w-5 h-5 text-white" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z" />
                    <path d="M8 14s1.5 2 4 2 4-2 4-2" />
                    <line x1="9" y1="9" x2="9.01" y2="9" />
                    <line x1="15" y1="9" x2="15.01" y2="9" />
                  </svg>
                  <div className="absolute -top-0.5 -right-0.5 w-3 h-3 bg-green-400 rounded-full border-2 border-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold text-brand-dark leading-none tracking-tight">
                    InstaChef AI
                  </h1>
                  <p className="text-[10px] text-brand-muted font-medium tracking-widest uppercase mt-0.5">
                    Cooking Commerce Agent
                  </p>
                </div>
              </div>

              {/* Right side — Status + pipeline badge */}
              <div className="flex items-center gap-3">
                <div className="hidden sm:flex items-center gap-1.5 text-[11px] text-brand-subtle bg-brand-bg/80 px-3 py-1.5 rounded-full border border-brand-border/60">
                  <span className="font-mono font-medium text-swiggy">10</span>
                  <span>nodes</span>
                  <span className="text-brand-muted">·</span>
                  <span className="font-mono font-medium text-swiggy">2</span>
                  <span>gates</span>
                </div>
                <div className="flex items-center gap-1.5 bg-green-50 text-green-700 px-3 py-1.5 rounded-full text-xs font-medium border border-green-100">
                  <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse-slow" />
                  Live
                </div>
              </div>
            </div>
          </header>

          {/* ── Main Content ─────────────────────────────────── */}
          <main className="flex-1 max-w-5xl w-full mx-auto px-4 py-6">
            {children}
          </main>

          {/* ── Footer ───────────────────────────────────────── */}
          <footer className="border-t border-brand-border bg-white py-4">
            <div className="max-w-5xl mx-auto px-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xs text-brand-muted">Powered by</span>
                <div className="flex items-center gap-1.5">
                  <span className="text-[10px] font-bold text-brand-subtle bg-brand-bg px-2 py-0.5 rounded">LangGraph</span>
                  <span className="text-[10px] font-bold text-brand-subtle bg-brand-bg px-2 py-0.5 rounded">NVIDIA NIM</span>
                  <span className="text-[10px] font-bold text-brand-subtle bg-brand-bg px-2 py-0.5 rounded">Swiggy MCP</span>
                </div>
              </div>
              <p className="text-xs text-brand-muted">
                Swiggy Builders Club 2026
              </p>
            </div>
          </footer>
        </div>
      </body>
    </html>
  )
}
