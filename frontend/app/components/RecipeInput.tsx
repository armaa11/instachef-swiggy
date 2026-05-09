import { useState, useEffect } from 'react'
import { useStore } from '../../lib/store'
import { api } from '../../lib/api'
import { Youtube, Globe, Type, Sparkles, ArrowRight, Link2, Instagram, Brain, ShoppingCart, Search, Shield, Zap } from 'lucide-react'

export default function RecipeInput() {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const { session_id, setScreen, reset } = useStore()
  const [auth, setAuth] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [isConnected, setIsConnected] = useState(false)

  const handleConnect = async () => {
    setIsConnecting(true)
    try {
      const res = await api.getLoginUrl(session_id)
      if (res.url.includes('mock_auth=success')) {
        setIsConnecting(false)
        setIsConnected(true)
        setTimeout(() => {
          setAuth(true)
        }, 1500)
      } else {
        window.location.href = res.url
      }
    } catch (e) {
      console.error(e)
      setIsConnecting(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setLoading(true)
    reset()
    try {
      await api.processRecipe(session_id, url)
      setScreen('progress')
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const detectInputType = (input: string) => {
    const lower = input.toLowerCase()
    if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube'
    if (lower.includes('instagram.com')) return 'instagram'
    if (lower.startsWith('http')) return 'blog'
    if (input.length > 10) return 'text'
    return null
  }

  const inputType = detectInputType(url)

  // ── Auth screen ───────────────────────────────────────
  if (!auth) {
    return (
      <div className="flex flex-col items-center justify-center mt-16 animate-fade-in">
        <div className="swiggy-card p-10 text-center max-w-md relative overflow-hidden">
          {/* Subtle gradient accent */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-swiggy via-orange-400 to-swiggy-600" />

          <div className="w-16 h-16 bg-gradient-to-br from-swiggy-50 to-swiggy-100 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-sm">
            <Link2 className="w-8 h-8 text-swiggy" />
          </div>
          <h2 className="text-2xl font-bold text-brand-dark mb-2">Connect Instamart</h2>
          <p className="text-brand-subtle text-sm mb-8 leading-relaxed">
            Link your Swiggy account so we can search products, build your cart, and place orders on Instamart.
          </p>
          <button
            onClick={handleConnect}
            disabled={isConnecting || isConnected}
            className={`w-full py-3.5 text-base rounded-xl font-semibold transition-all duration-300 flex items-center justify-center gap-2 ${
              isConnected
                ? 'bg-green-500 text-white shadow-lg shadow-green-500/20'
                : 'swiggy-btn-primary'
            }`}
          >
            {isConnecting ? (
              <>
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Connecting...
              </>
            ) : isConnected ? (
              <>
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                </svg>
                Connected Successfully
              </>
            ) : (
              'Connect Swiggy Account'
            )}
          </button>
        </div>
      </div>
    )
  }

  // ── Main input screen ─────────────────────────────────
  return (
    <div className="max-w-2xl mx-auto mt-6 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 bg-gradient-to-r from-swiggy-50 to-orange-50 text-swiggy-700 px-4 py-2 rounded-full text-sm font-medium mb-5 border border-swiggy-100/60 shadow-sm animate-fade-in-up">
          <Sparkles className="w-4 h-4" />
          10-Node Agentic Pipeline
        </div>
        <h2 className="text-4xl font-bold text-brand-dark mb-3 leading-tight animate-fade-in-up" style={{ animationDelay: '100ms' }}>
          What are we cooking<br />today?
        </h2>
        <p className="text-brand-subtle text-base animate-fade-in-up" style={{ animationDelay: '200ms' }}>
          Paste any recipe source — our AI pipeline extracts, understands,<br className="hidden sm:block" />
          normalizes, and builds your Instamart cart automatically.
        </p>
      </div>

      {/* Input Card */}
      <div className="swiggy-card p-6 relative overflow-hidden animate-fade-in-up" style={{ animationDelay: '300ms' }}>
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-swiggy/40 to-transparent" />
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <input
              type="text"
              id="recipe-input"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="Paste a YouTube URL, Instagram Reel, blog link, or type a recipe..."
              className="swiggy-input pr-12 text-lg"
            />
            {inputType && (
              <div className="absolute right-4 top-1/2 -translate-y-1/2 animate-scale-in">
                {inputType === 'youtube' && <Youtube className="w-5 h-5 text-red-500" />}
                {inputType === 'instagram' && <Instagram className="w-5 h-5 text-pink-500" />}
                {inputType === 'blog' && <Globe className="w-5 h-5 text-blue-500" />}
                {inputType === 'text' && <Type className="w-5 h-5 text-brand-subtle" />}
              </div>
            )}
          </div>

          {/* Quick examples */}
          <div className="flex flex-wrap gap-2">
            <span className="text-xs text-brand-muted">Try:</span>
            <button
              type="button"
              onClick={() => setUrl('https://www.youtube.com/watch?v=9WXinXCkJoI')}
              className="text-xs text-swiggy hover:text-swiggy-700 underline underline-offset-2 transition"
            >
              Butter Chicken (YouTube)
            </button>
            <span className="text-xs text-brand-muted">•</span>
            <button
              type="button"
              onClick={() => setUrl('Make dal tadka for 4 people. Need 200g toor dal, 2 tomatoes, 1 onion, 1 tsp cumin, 1 tsp turmeric, 1 tbsp ghee, salt to taste.')}
              className="text-xs text-swiggy hover:text-swiggy-700 underline underline-offset-2 transition"
            >
              Dal Tadka (text)
            </button>
          </div>

          <button
            type="submit"
            id="cook-this-btn"
            disabled={loading || !url.trim()}
            className="swiggy-btn-primary w-full py-4 text-lg flex items-center justify-center gap-2 group"
          >
            {loading ? (
              <>
                <span className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Processing...
              </>
            ) : (
              <>
                Cook This
                <ArrowRight className="w-5 h-5 group-hover:translate-x-0.5 transition-transform" />
              </>
            )}
          </button>
        </form>
      </div>

      {/* ── Pipeline Architecture Showcase ─────────────── */}
      <div className="mt-10 animate-fade-in-up" style={{ animationDelay: '500ms' }}>
        <p className="text-center text-[11px] text-brand-muted uppercase tracking-widest font-medium mb-4">What happens when you press Cook This</p>
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
          {[
            { icon: <Brain className="w-4 h-4" />, label: 'Classify', desc: '4 input types' },
            { icon: <Zap className="w-4 h-4" />, label: 'Extract', desc: '3-tier fallback' },
            { icon: <Sparkles className="w-4 h-4" />, label: 'Understand', desc: 'LLM parsing' },
            { icon: <Search className="w-4 h-4" />, label: 'Search', desc: '8× parallel' },
            { icon: <Shield className="w-4 h-4" />, label: 'Validate', desc: '2 gate checks' },
          ].map((step, i) => (
            <div key={step.label} className="bg-white rounded-xl border border-brand-border/60 p-3 text-center hover:shadow-card transition-shadow group cursor-default">
              <div className="w-8 h-8 bg-swiggy-50 rounded-lg flex items-center justify-center mx-auto mb-2 text-swiggy group-hover:bg-swiggy group-hover:text-white transition-colors">
                {step.icon}
              </div>
              <p className="text-xs font-semibold text-brand-dark">{step.label}</p>
              <p className="text-[10px] text-brand-muted mt-0.5">{step.desc}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Feature pills */}
      <div className="flex flex-wrap justify-center gap-2.5 mt-8 animate-fade-in-up" style={{ animationDelay: '600ms' }}>
        {[
          { icon: '🎥', label: 'YouTube' },
          { icon: '📸', label: 'Instagram' },
          { icon: '📝', label: 'Blogs' },
          { icon: '✍️', label: 'Text' },
          { icon: '🧠', label: 'Pantry AI' },
          { icon: '📊', label: 'Waste Opt.' },
          { icon: '⭐', label: 'Personalized' },
        ].map(f => (
          <div key={f.label} className="flex items-center gap-1.5 bg-white/80 text-brand-subtle text-[11px] px-2.5 py-1.5 rounded-full border border-brand-border/60">
            <span>{f.icon}</span>
            {f.label}
          </div>
        ))}
      </div>
    </div>
  )
}
