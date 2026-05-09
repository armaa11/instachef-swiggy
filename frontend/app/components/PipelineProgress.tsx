import { useEffect } from 'react'
import { useStore } from '../../lib/store'
import { CheckCircle2, CircleDashed, XCircle, Clock, Zap, ChefHat, ArrowLeft, TrendingUp } from 'lucide-react'

export default function PipelineProgress() {
  const { session_id, pipeline_events, addEvent, setCartProposal, setScreen } = useStore()

  useEffect(() => {
    if (!session_id) return;

    const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const evtSource = new EventSource(`${API_URL}/api/stream?session_id=${session_id}`);

    evtSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.stage === 'heartbeat') return;
      addEvent(data);

      if (data.stage === 'proposal_ready') {
        setCartProposal(data);
        setTimeout(() => setScreen('review'), 1200);
      }
    };

    return () => evtSource.close();
  }, [session_id, addEvent, setCartProposal, setScreen]);

  const stages = [
    { id: 'classify',        label: 'Classifying input',       icon: '🔍', accent: 'from-blue-500 to-blue-600' },
    { id: 'user_context',    label: 'Loading your preferences', icon: '👤', accent: 'from-violet-500 to-violet-600' },
    { id: 'extract',         label: 'Extracting content',      icon: '📄', accent: 'from-emerald-500 to-emerald-600' },
    { id: 'understand',      label: 'Understanding recipe',    icon: '🧠', accent: 'from-purple-500 to-purple-600' },
    { id: 'validate_recipe', label: 'Validating recipe',       icon: '✅', accent: 'from-green-500 to-green-600' },
    { id: 'normalize',       label: 'Mapping ingredients',     icon: '📐', accent: 'from-amber-500 to-amber-600' },
    { id: 'search',          label: 'Searching Instamart',     icon: '🔎', accent: 'from-swiggy to-swiggy-600' },
    { id: 'optimize',        label: 'Optimizing basket',       icon: '🛒', accent: 'from-indigo-500 to-indigo-600' },
    { id: 'validate_cart',   label: 'Final validation',        icon: '🛡️', accent: 'from-teal-500 to-teal-600' },
  ];

  const getStageEvent = (stageId: string) => {
    return pipeline_events.find(e => e.stage === stageId && e.status === 'done');
  };

  const getActiveStage = () => {
    for (let i = stages.length - 1; i >= 0; i--) {
      if (getStageEvent(stages[i].id)) {
        return i < stages.length - 1 ? stages[i+1].id : null;
      }
    }
    return stages[0].id;
  };

  const hasError = pipeline_events.some(e => e.stage === 'error');
  const errorMsg = pipeline_events.find(e => e.stage === 'error')?.message;
  const activeStage = getActiveStage();
  const completedCount = stages.filter(s => getStageEvent(s.id)).length;
  const progress = (completedCount / stages.length) * 100;

  const totalDuration = pipeline_events
    .filter(e => e.duration_ms)
    .reduce((sum: number, e: any) => sum + (e.duration_ms || 0), 0);

  // Calculate stage-by-stage speed rating
  const getSpeedRating = (ms: number) => {
    if (ms < 200) return { label: 'Instant', color: 'text-green-600' }
    if (ms < 1000) return { label: 'Fast', color: 'text-green-500' }
    if (ms < 3000) return { label: 'Normal', color: 'text-amber-500' }
    return { label: 'Slow', color: 'text-red-400' }
  }

  return (
    <div className="max-w-2xl mx-auto mt-8 animate-fade-in">
      {/* Progress header card */}
      <div className="swiggy-card p-6 mb-4 relative overflow-hidden">
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-transparent via-swiggy/30 to-transparent" />
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-swiggy-50 to-swiggy-100 rounded-xl flex items-center justify-center">
              <ChefHat className="w-5 h-5 text-swiggy" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-brand-dark">Processing Recipe</h2>
              <p className="text-xs text-brand-muted">
                {completedCount}/{stages.length} nodes complete
                {completedCount === stages.length && ' — Ready!'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {totalDuration > 0 && (
              <div className="flex items-center gap-1.5 text-xs text-brand-subtle bg-brand-bg px-3 py-1.5 rounded-lg border border-brand-border/60">
                <Clock className="w-3.5 h-3.5" />
                {(totalDuration / 1000).toFixed(1)}s
              </div>
            )}
          </div>
        </div>

        {/* Progress bar with percentage */}
        <div className="relative">
          <div className="w-full h-2 bg-brand-bg rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-swiggy-400 to-swiggy rounded-full transition-all duration-700 ease-out"
              style={{ width: `${progress}%` }}
            />
          </div>
          <span className="absolute right-0 -top-5 text-[10px] font-mono text-brand-muted tabular-nums">
            {Math.round(progress)}%
          </span>
        </div>
      </div>

      {/* Pipeline stages */}
      <div className="swiggy-card overflow-hidden">
        {stages.map((stage, idx) => {
          const event = getStageEvent(stage.id);
          const isActive = activeStage === stage.id;
          const isDone = !!event;
          const isLast = idx === stages.length - 1;
          const speed = event?.duration_ms !== undefined ? getSpeedRating(event.duration_ms) : null;

          return (
            <div
              key={stage.id}
              className={`px-5 py-4 flex items-start gap-4 transition-all duration-300
                ${!isLast ? 'border-b border-brand-border/60' : ''}
                ${isActive ? 'bg-swiggy-50/40' : isDone ? 'bg-white' : 'bg-white opacity-40'}
                ${isDone ? 'animate-slide-up' : ''}
              `}
            >
              {/* Status indicator */}
              <div className="mt-0.5 shrink-0">
                {isDone ? (
                  <div className="w-7 h-7 bg-green-100 rounded-full flex items-center justify-center animate-scale-in">
                    <CheckCircle2 className="w-4 h-4 text-green-600" />
                  </div>
                ) : isActive ? (
                  <div className="w-7 h-7 bg-swiggy-100 rounded-full flex items-center justify-center">
                    <CircleDashed className="w-4 h-4 text-swiggy animate-spin" />
                  </div>
                ) : (
                  <div className="w-7 h-7 bg-brand-bg rounded-full flex items-center justify-center">
                    <span className="text-sm">{stage.icon}</span>
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="flex-grow min-w-0">
                <div className="flex items-center justify-between">
                  <h3 className={`text-sm font-semibold ${
                    isActive ? 'text-swiggy-700' : isDone ? 'text-brand-dark' : 'text-brand-muted'
                  }`}>
                    {stage.label}
                  </h3>
                  {event?.duration_ms !== undefined && (
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] font-medium ${speed?.color}`}>
                        {speed?.label}
                      </span>
                      <span className="text-[11px] text-brand-muted flex items-center gap-1 tabular-nums">
                        <Zap className="w-3 h-3" />
                        {event.duration_ms < 1000 ? `${event.duration_ms}ms` : `${(event.duration_ms / 1000).toFixed(1)}s`}
                      </span>
                    </div>
                  )}
                </div>

                {/* Active stage shimmer */}
                {isActive && !isDone && (
                  <div className="mt-2 h-3 w-3/4 bg-brand-bg rounded shimmer" />
                )}

                {/* Rich metadata for each completed stage */}
                {isDone && stage.id === 'classify' && event?.input_type && (
                  <p className="text-xs text-brand-subtle mt-1">
                    Detected <span className="font-medium text-brand-text capitalize">{event.input_type}</span> source
                  </p>
                )}
                {isDone && stage.id === 'extract' && (
                  <p className="text-xs text-brand-subtle mt-1">
                    {event.word_count} words via <span className="font-medium text-brand-text">{event.source}</span>
                  </p>
                )}
                {isDone && stage.id === 'understand' && (
                  <div className="mt-1.5 flex items-center gap-2 flex-wrap">
                    <span className="swiggy-badge bg-swiggy-50 text-swiggy-700 border-swiggy-200">
                      {event.recipe_name}
                    </span>
                    <span className="text-xs text-brand-subtle">
                      {event.ingredient_count} ingredients • {Math.round((event.confidence || 0) * 100)}% confidence
                    </span>
                  </div>
                )}
                {isDone && stage.id === 'validate_recipe' && (
                  <div className="mt-1 flex items-center gap-2">
                    {event.passed ? (
                      <span className="swiggy-badge bg-green-50 text-green-700 border-green-200">Clean</span>
                    ) : (
                      <span className="swiggy-badge bg-amber-50 text-amber-700 border-amber-200">Issues Found</span>
                    )}
                    {event.repairs?.length > 0 && (
                      <span className="text-xs text-brand-subtle">{event.repairs.length} auto-repaired</span>
                    )}
                  </div>
                )}
                {isDone && stage.id === 'normalize' && (
                  <p className="text-xs text-brand-subtle mt-1">
                    {event.db_matched}/{event.total} matched via fuzzy string search
                  </p>
                )}
                {isDone && stage.id === 'search' && (
                  <div className="mt-1 flex items-center gap-2">
                    <span className="swiggy-badge bg-green-50 text-green-700 border-green-200">{event.found_count} found</span>
                    {event.missing_count > 0 && (
                      <span className="swiggy-badge bg-amber-50 text-amber-700 border-amber-200">{event.missing_count} missing</span>
                    )}
                  </div>
                )}
                {isDone && stage.id === 'user_context' && (
                  <div className="mt-1 flex items-center gap-2 flex-wrap">
                    <span className="swiggy-badge bg-violet-50 text-violet-700 border-violet-200">
                      {event.go_to_items || 0} go-to items
                    </span>
                    <span className="swiggy-badge bg-violet-50 text-violet-700 border-violet-200">
                      {event.preferred_brands || 0} brand prefs
                    </span>
                    {event.dietary_signals?.length > 0 && (
                      <span className="text-xs text-brand-subtle">{event.dietary_signals.join(', ')}</span>
                    )}
                  </div>
                )}
                {isDone && stage.id === 'optimize' && (
                  <div className="mt-1.5 flex items-center gap-3 flex-wrap">
                    <span className="text-sm font-bold text-brand-dark">₹{event.cart_total}</span>
                    <span className="text-xs text-brand-subtle">{event.item_count} items</span>
                    {event.pantry_skipped > 0 && (
                      <span className="text-xs text-indigo-600">{event.pantry_skipped} pantry skipped</span>
                    )}
                    {event.avg_waste_pct !== undefined && (
                      <span className={`text-xs ${event.avg_waste_pct > 30 ? 'text-amber-600' : 'text-green-600'}`}>
                        {event.avg_waste_pct}% waste
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>

      {/* Performance summary when done */}
      {completedCount === stages.length && totalDuration > 0 && (
        <div className="swiggy-card p-4 mt-4 flex items-center gap-3 animate-fade-in-up">
          <div className="w-9 h-9 bg-green-50 rounded-xl flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-green-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-brand-dark">Pipeline complete</p>
            <p className="text-xs text-brand-subtle">
              {stages.length} nodes processed in {(totalDuration / 1000).toFixed(1)}s
              {' '}({(totalDuration / stages.length).toFixed(0)}ms avg per node)
            </p>
          </div>
        </div>
      )}

      {/* Error state */}
      {hasError && (
        <div className="swiggy-card p-5 mt-4 border-red-200 bg-red-50 flex items-start gap-3 animate-slide-up">
          <XCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <div>
            <h4 className="font-semibold text-red-800 text-sm">Pipeline Error</h4>
            <p className="text-xs text-red-600 mt-1">{errorMsg}</p>
            <button
              onClick={() => useStore.getState().setScreen('input')}
              className="mt-3 text-xs font-medium text-red-700 flex items-center gap-1 hover:underline"
            >
              <ArrowLeft className="w-3 h-3" /> Try again
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
