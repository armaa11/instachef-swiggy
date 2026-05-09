import { useState } from 'react'
import { useStore } from '../../lib/store'
import { api } from '../../lib/api'
import { ChevronDown, ChevronUp, Leaf, AlertTriangle, PackageCheck, ShoppingCart, ArrowRight, Info, Trash2, Copy, Check, TrendingDown, Recycle } from 'lucide-react'

const CONFIDENCE_BADGE: Record<string, { label: string; color: string; bg: string; border: string }> = {
  high:        { label: 'High Match',    color: 'text-green-700',  bg: 'bg-green-50',  border: 'border-green-200' },
  medium:      { label: 'Partial Match', color: 'text-amber-700',  bg: 'bg-amber-50',  border: 'border-amber-200' },
  low:         { label: 'Low Match',     color: 'text-red-700',    bg: 'bg-red-50',    border: 'border-red-200' },
  substitute:  { label: 'Substitute',    color: 'text-blue-700',   bg: 'bg-blue-50',   border: 'border-blue-200' },
  unavailable: { label: 'Unavailable',   color: 'text-gray-600',   bg: 'bg-gray-50',   border: 'border-gray-200' },
  pantry:      { label: 'Pantry Item',   color: 'text-indigo-700', bg: 'bg-indigo-50',  border: 'border-indigo-200' },
}

const CONFIDENCE_DOT: Record<string, string> = {
  high: 'bg-green-500', medium: 'bg-amber-500', low: 'bg-red-500',
  substitute: 'bg-blue-500', unavailable: 'bg-gray-400', pantry: 'bg-indigo-500',
}

export default function CartReview() {
  const { session_id, cart_proposal, setScreen } = useStore()
  const [items, setItems] = useState(cart_proposal?.cart_items || [])
  const [loading, setLoading] = useState(false)
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null)
  const [copied, setCopied] = useState(false)

  if (!cart_proposal) return null;

  const handleCopyList = async () => {
    const text = items
      .filter((i: any) => i.spin_id)
      .map((i: any) => `${i.ingredient_name} — ${i.product_name} (${i.product_quantity_display}) ₹${i.product_price}`)
      .join('\n')
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for older browsers
      const textarea = document.createElement('textarea')
      textarea.value = text
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleRemove = (index: number) => {
    const newItems = [...items];
    newItems.splice(index, 1);
    setItems(newItems);
  }

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const buyableItems = items.filter((i: any) => i.spin_id);
      await api.confirmCart(session_id, buyableItems);
      setScreen('tracking');
    } catch (err: any) {
      alert(err.message || 'Error placing order');
    } finally {
      setLoading(false);
    }
  }

  const buyableItems = items.filter((i: any) => i.spin_id);
  const pantryItems = items.filter((i: any) => i.confidence === 'pantry');
  const unavailableItems = items.filter((i: any) => i.confidence === 'unavailable');

  const total = buyableItems.reduce((sum: number, i: any) => sum + (i.product_price * (i.quantity || 1)), 0);
  const avgWaste = buyableItems.length > 0
    ? buyableItems.reduce((sum: number, i: any) => sum + (i.waste_pct || 0), 0) / buyableItems.length
    : 0;

  // Waste intelligence: find items where we saved the most
  const wasteOptimized = buyableItems
    .filter((i: any) => i.waste_pct !== undefined && i.waste_pct < 30)
    .length;
  const highWasteItems = buyableItems.filter((i: any) => (i.waste_pct || 0) > 50);

  return (
    <div className="pb-10 animate-fade-in max-w-6xl mx-auto">
      {/* Header */}
      <div className="mb-6 mt-4 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-brand-dark mb-1">Review Your Cart</h2>
          <p className="text-sm text-brand-subtle">AI-optimized basket for your recipe</p>
        </div>
        <button
          onClick={handleCopyList}
          className="flex items-center gap-1.5 text-xs font-medium text-brand-subtle hover:text-brand-dark bg-brand-bg px-3 py-2 rounded-lg border border-brand-border transition-all"
        >
          {copied ? <Check className="w-3.5 h-3.5 text-green-600" /> : <Copy className="w-3.5 h-3.5" />}
          {copied ? 'Copied!' : 'Copy List'}
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Intelligence Cards & Cart Items */}
        <div className="lg:col-span-2 space-y-4">
          
          {/* Metrics strip */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Items', value: String(buyableItems.length), accent: 'text-brand-dark' },
              { label: 'Total', value: `₹${total}`, accent: 'text-swiggy' },
              { label: 'Waste', value: `${avgWaste.toFixed(0)}%`, accent: avgWaste > 30 ? 'text-amber-600' : 'text-green-600' },
              { label: 'Pantry Saved', value: String(pantryItems.length), accent: 'text-indigo-600' },
            ].map(m => (
              <div key={m.label} className="swiggy-card p-3.5 text-center">
                <p className="text-[10px] text-brand-muted uppercase tracking-wider font-medium">{m.label}</p>
                <p className={`text-xl font-bold mt-0.5 ${m.accent}`}>{m.value}</p>
              </div>
            ))}
          </div>

          {/* Waste Intelligence Card */}
          {buyableItems.length > 0 && (
            <div className="bg-green-50 border border-green-100 rounded-2xl p-4 animate-slide-up">
              <div className="flex items-center gap-2 mb-2">
                <Recycle className="w-4 h-4 text-green-600" />
                <h3 className="text-sm font-semibold text-green-800">Waste Minimization Summary</h3>
              </div>
              <p className="text-xs text-green-700 leading-relaxed">
                We picked the smallest viable pack for each ingredient to reduce food waste.
                {wasteOptimized > 0 && <> <span className="font-semibold">{wasteOptimized}/{buyableItems.length}</span> items optimized below 30% waste.</>}
                {avgWaste > 0 && <> Average waste is <span className={`font-semibold ${avgWaste > 30 ? 'text-amber-700' : 'text-green-800'}`}>{avgWaste.toFixed(0)}%</span>.</>}
                {highWasteItems.length > 0 && <> {highWasteItems.length} item{highWasteItems.length > 1 ? 's' : ''} have high waste — consider sharing leftovers.</>}
              </p>
            </div>
          )}

          {/* Pantry Intelligence */}
          {pantryItems.length > 0 && (
            <div className="bg-indigo-50 border border-indigo-100 rounded-2xl p-4 animate-slide-up">
              <div className="flex items-center gap-2 mb-2">
                <Leaf className="w-4 h-4 text-indigo-600" />
                <h3 className="text-sm font-semibold text-indigo-800">Pantry Intelligence — {pantryItems.length} items skipped</h3>
              </div>
              <p className="text-xs text-indigo-600 mb-2.5 leading-relaxed">
                These are common kitchen staples that most Indian households already have. We removed them from your cart to save money.
              </p>
              <div className="flex flex-wrap gap-2">
                {pantryItems.map((item: any, i: number) => (
                  <span key={i} className="text-xs bg-white px-2.5 py-1 rounded-full text-indigo-700 border border-indigo-200 font-medium shadow-sm">
                    {item.ingredient_name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Unavailable items */}
          {unavailableItems.length > 0 && (
            <div className="bg-amber-50 border border-amber-100 rounded-2xl p-4 animate-slide-up">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-600" />
                <h3 className="text-sm font-semibold text-amber-800">Not Found on Instamart</h3>
              </div>
              <div className="flex flex-wrap gap-2">
                {unavailableItems.map((item: any, i: number) => (
                  <span key={i} className="text-xs bg-white px-2.5 py-1 rounded-full text-amber-700 border border-amber-200 font-medium">
                    {item.ingredient_name}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Cart items */}
          <div className="space-y-3 mt-4">
            {buyableItems.map((item: any, i: number) => {
              const badge = CONFIDENCE_BADGE[item.confidence] || CONFIDENCE_BADGE.medium;
              const dot = CONFIDENCE_DOT[item.confidence] || 'bg-gray-400';
              const isExpanded = expandedIdx === i;

              return (
                <div key={i} className="swiggy-card overflow-hidden animate-slide-up" style={{ animationDelay: `${i * 50}ms` }}>
                  <div className="p-4 flex items-start gap-3">
                    {/* Product image */}
                    <div className="w-16 h-16 bg-brand-bg rounded-xl overflow-hidden shrink-0 flex items-center justify-center border border-brand-border">
                      {item.image_url ? (
                        <img src={item.image_url} alt={item.product_name} className="w-full h-full object-cover" />
                      ) : (
                        <ShoppingCart className="w-6 h-6 text-brand-muted" />
                      )}
                    </div>

                    {/* Details */}
                    <div className="flex-grow min-w-0">
                      <div className="flex justify-between items-start">
                        <div className="min-w-0 pr-2">
                          <p className="text-[11px] text-brand-muted truncate">
                            {item.ingredient_name} • {item.ingredient_quantity_display}
                          </p>
                          <h3 className="font-bold text-brand-dark text-sm mt-0.5 leading-snug">{item.product_name}</h3>
                          <p className="text-xs text-brand-subtle mt-0.5">
                            {item.product_quantity_display}
                            {item.quantity > 1 && <span className="text-swiggy font-medium"> × {item.quantity}</span>}
                          </p>
                        </div>
                        <div className="text-right shrink-0">
                          <p className="font-bold text-brand-dark text-base">₹{item.product_price * (item.quantity || 1)}</p>
                        </div>
                      </div>

                      {/* Badges row */}
                      <div className="flex items-center gap-2 mt-2 flex-wrap">
                        <span className={`swiggy-badge ${badge.bg} ${badge.color} ${badge.border}`}>
                          <span className={`w-1.5 h-1.5 rounded-full ${dot}`}></span>
                          {badge.label}
                        </span>
                        {item.waste_pct > 0 && (
                          <span className="text-[11px] text-brand-muted font-medium bg-brand-bg px-2 py-0.5 rounded-full">
                            {item.waste_pct}% waste
                          </span>
                        )}
                        {/* Intelligence Badges */}
                        {item.selection_reasons?.some((r: string) => r.includes("Your go-to item")) && (
                          <span className="swiggy-badge bg-violet-50 text-violet-700 border-violet-200">
                            ⭐ Go-to Item
                          </span>
                        )}
                        {item.selection_reasons?.some((r: string) => r.includes("Your usual brand") || r.includes("Preferred brand")) && (
                          <span className="swiggy-badge bg-pink-50 text-pink-700 border-pink-200">
                            ❤️ Preferred Brand
                          </span>
                        )}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center justify-between mt-2.5">
                        <button
                          onClick={() => setExpandedIdx(isExpanded ? null : i)}
                          className="text-[11px] text-swiggy font-bold hover:text-swiggy-700 flex items-center gap-1 transition uppercase tracking-wide"
                        >
                          <Info className="w-3.5 h-3.5" />
                          AI Reasoning
                          {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                        </button>
                        <button
                          onClick={() => handleRemove(items.indexOf(item))}
                          className="text-xs text-red-400 hover:text-red-600 flex items-center gap-1 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Remove
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Smart Substitutions & Expanded Reasoning */}
                  {isExpanded && (
                    <div className="border-t border-brand-border bg-gradient-to-b from-brand-bg/50 to-white px-5 py-4 space-y-4 animate-slide-up">
                      {item.selection_reasons?.length > 0 && (
                        <div>
                          <p className="text-[10px] font-bold text-swiggy uppercase tracking-widest mb-2 flex items-center gap-1.5">
                            <Brain className="w-3.5 h-3.5" /> Why we chose this
                          </p>
                          <ul className="space-y-1.5">
                            {item.selection_reasons.map((reason: string, ri: number) => (
                              <li key={ri} className="text-xs text-brand-text flex items-start gap-2 leading-relaxed">
                                <PackageCheck className="w-4 h-4 text-green-500 shrink-0" />
                                {reason}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {item.alternatives?.length > 0 && (
                        <div>
                          <p className="text-[10px] font-bold text-brand-subtle uppercase tracking-widest mb-2">Smart Substitutions</p>
                          <div className="bg-white rounded-xl border border-brand-border shadow-sm divide-y divide-brand-border/50">
                            {item.alternatives.slice(0, 2).map((alt: any, ai: number) => (
                              <div key={ai} className="text-xs text-brand-text flex items-center justify-between p-2.5">
                                <div className="truncate pr-2">
                                  <span className="font-medium block truncate">{alt.product_name}</span>
                                  <span className="text-brand-muted text-[10px]">{alt.product_quantity_display}</span>
                                </div>
                                <span className="font-bold text-brand-dark shrink-0">₹{alt.product_price}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Right Column: Cooking Profile Sidebar & Checkout */}
        <div className="lg:col-span-1">
          <div className="sticky top-20 space-y-4">
            
            {/* Cooking History & Personalization Sidebar */}
            <div className="swiggy-card p-5 animate-slide-up">
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-swiggy-50 rounded-lg flex items-center justify-center text-swiggy">
                  <TrendingDown className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-brand-dark">Your Cooking Profile</h3>
                  <p className="text-[10px] text-brand-muted uppercase tracking-wider">Active Personalization</p>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-brand-dark">Price Conscious</p>
                    <p className="text-[11px] text-brand-subtle leading-relaxed mt-0.5">We prioritized value-packs and competitive pricing over premium variants for basic ingredients.</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-pink-500 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-brand-dark">Brand Loyalty</p>
                    <p className="text-[11px] text-brand-subtle leading-relaxed mt-0.5">Matched your preferred dairy brand (Amul) based on past 5 orders.</p>
                  </div>
                </div>
                <div className="flex items-start gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-indigo-500 mt-1.5 shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-brand-dark">Dietary Patterns</p>
                    <p className="text-[11px] text-brand-subtle leading-relaxed mt-0.5">No distinct allergens detected. Standard Indian vegetarian staples loaded.</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Checkout Card */}
            <div className="swiggy-card p-5 animate-slide-up">
              <h3 className="text-sm font-bold text-brand-dark mb-4">Order Summary</h3>
              <div className="space-y-2 mb-4 text-sm">
                <div className="flex justify-between text-brand-subtle">
                  <span>Item Total</span>
                  <span>₹{total}</span>
                </div>
                <div className="flex justify-between text-brand-subtle">
                  <span>Delivery Fee</span>
                  <span className="text-green-600 font-medium">FREE</span>
                </div>
                <div className="pt-2 border-t border-brand-border flex justify-between font-bold text-brand-dark text-lg mt-2">
                  <span>To Pay</span>
                  <span>₹{total}</span>
                </div>
              </div>

              <button 
                onClick={handleConfirm}
                disabled={loading || buyableItems.length === 0}
                className="swiggy-btn-primary w-full py-3.5 text-base flex items-center justify-center gap-2 shadow-lg shadow-swiggy/20"
              >
                {loading ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Placing Order...
                  </>
                ) : (
                  <>
                    Place Order ({buyableItems.length})
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
            
          </div>
        </div>
      </div>
    </div>
  )
}
