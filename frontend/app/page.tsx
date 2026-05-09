"use client"
import { useEffect } from 'react'
import { useStore } from '../lib/store'
import RecipeInput from './components/RecipeInput'
import PipelineProgress from './components/PipelineProgress'
import CartReview from './components/CartReview'
import TrackingView from './components/TrackingView'

export default function Home() {
  const { session_id, screen, setSessionId } = useStore()

  useEffect(() => {
    let sid = localStorage.getItem('session_id')
    if (!sid) {
      sid = crypto.randomUUID()
      localStorage.setItem('session_id', sid)
    }
    setSessionId(sid)
  }, [setSessionId])

  useEffect(() => {
    if (!session_id) return;
    
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('mock_auth') === 'success') {
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, [session_id])

  if (!session_id) return <div>Loading...</div>

  return (
    <div>
      {screen === 'input' && <RecipeInput />}
      {screen === 'progress' && <PipelineProgress />}
      {screen === 'review' && <CartReview />}
      {screen === 'tracking' && <TrackingView />}
    </div>
  )
}
