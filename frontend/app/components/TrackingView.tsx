import { useEffect, useState } from 'react'
import { useStore } from '../../lib/store'
import { api } from '../../lib/api'
import { Package, Truck, CheckCircle, Clock, ArrowLeft, ChefHat } from 'lucide-react'

const STATUS_CONFIG: Record<string, { icon: any; color: string; bg: string; label: string }> = {
  'Order Placed':      { icon: Package,     color: 'text-swiggy',    bg: 'bg-swiggy-50',  label: 'Order Placed' },
  'Being Packed':      { icon: Package,     color: 'text-blue-600',  bg: 'bg-blue-50',    label: 'Being Packed' },
  'Out for Delivery':  { icon: Truck,       color: 'text-green-600', bg: 'bg-green-50',   label: 'Out for Delivery' },
  'Delivered':         { icon: CheckCircle, color: 'text-green-600', bg: 'bg-green-50',   label: 'Delivered' },
}

export default function TrackingView() {
  const { session_id, setScreen } = useStore()
  const [status, setStatus] = useState<any>(null)

  useEffect(() => {
    const poll = async () => {
      try {
        const data = await api.trackOrder(session_id)
        setStatus(data)
      } catch (e) {
        console.error(e)
      }
    }
    poll()
    const interval = setInterval(poll, 10000)
    return () => clearInterval(interval)
  }, [session_id])

  if (!status) {
    return (
      <div className="flex items-center justify-center mt-20">
        <div className="w-8 h-8 border-3 border-brand-border border-t-swiggy rounded-full animate-spin" />
      </div>
    )
  }

  const config = STATUS_CONFIG[status.status] || STATUS_CONFIG['Order Placed']
  const StatusIcon = config.icon

  const steps = [
    { id: 'placed',    label: 'Order Placed',      done: true },
    { id: 'packed',    label: 'Being Packed',       done: ['Being Packed', 'Out for Delivery', 'Delivered'].includes(status.status) },
    { id: 'delivery',  label: 'Out for Delivery',  done: ['Out for Delivery', 'Delivered'].includes(status.status) },
    { id: 'delivered', label: 'Delivered',           done: status.status === 'Delivered' },
  ]

  return (
    <div className="max-w-lg mx-auto mt-10 animate-fade-in">
      {/* Success card */}
      <div className="swiggy-card p-8 text-center mb-4">
        {/* Animated check */}
        <div className={`w-20 h-20 ${config.bg} rounded-full flex items-center justify-center mx-auto mb-5`}>
          <StatusIcon className={`w-10 h-10 ${config.color}`} />
        </div>

        <h2 className="text-2xl font-bold text-brand-dark mb-1">Order Confirmed!</h2>
        <p className="text-sm text-brand-subtle mb-6">
          Order ID: <span className="font-mono font-medium text-brand-text">{status.orderId || 'mock_order_123'}</span>
        </p>

        {/* Status timeline */}
        <div className="flex items-center justify-between px-4 mb-6">
          {steps.map((step, idx) => (
            <div key={step.id} className="flex items-center">
              <div className="flex flex-col items-center">
                <div className={`w-3.5 h-3.5 rounded-full border-2 transition-all duration-500 ${
                  step.done
                    ? 'bg-swiggy border-swiggy'
                    : 'bg-white border-brand-border'
                }`} />
                <p className={`text-[10px] mt-1.5 w-16 text-center leading-tight ${
                  step.done ? 'text-brand-dark font-medium' : 'text-brand-muted'
                }`}>
                  {step.label}
                </p>
              </div>
              {idx < steps.length - 1 && (
                <div className={`h-0.5 w-8 -mt-4 mx-1 transition-all duration-500 ${
                  step.done ? 'bg-swiggy' : 'bg-brand-border'
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* ETA */}
        {status.eta_minutes && (
          <div className="bg-swiggy-50 border border-swiggy-100 rounded-xl p-4 flex items-center justify-center gap-3">
            <Clock className="w-5 h-5 text-swiggy" />
            <div>
              <p className="text-sm font-bold text-swiggy-700">
                Arriving in ~{status.eta_minutes} minutes
              </p>
              <p className="text-xs text-swiggy-600/70">Delivery partner on the way</p>
            </div>
          </div>
        )}
      </div>

      {/* Cook along CTA */}
      <div className="swiggy-card p-5 flex items-center gap-4">
        <div className="w-12 h-12 bg-brand-bg rounded-xl flex items-center justify-center shrink-0">
          <ChefHat className="w-6 h-6 text-brand-subtle" />
        </div>
        <div className="flex-grow">
          <h3 className="text-sm font-bold text-brand-dark">Start Cooking!</h3>
          <p className="text-xs text-brand-subtle mt-0.5">Your groceries are on the way. Time to prep!</p>
        </div>
      </div>

      {/* New recipe button */}
      <button
        onClick={() => useStore.getState().reset()}
        className="w-full mt-4 py-3 text-sm font-medium text-brand-subtle hover:text-brand-dark flex items-center justify-center gap-2 transition"
      >
        <ArrowLeft className="w-4 h-4" />
        Cook another recipe
      </button>
    </div>
  )
}
