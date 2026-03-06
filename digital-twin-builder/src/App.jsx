import React, { useState, useEffect } from 'react'
import LandingPage from './views/LandingPage'
import TopologyCanvas from './views/TopologyCanvas'

function App() {
  const [currentView, setCurrentView] = useState('landing')

  useEffect(() => {
    const handleHashChange = () => {
      if (window.location.hash === '#workspace') {
        setCurrentView('workspace')
      } else {
        setCurrentView('landing')
      }
    }

    // Attach event listener for URL hash changes
    window.addEventListener('hashchange', handleHashChange)
    
    // Initial check on load
    handleHashChange()

    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [])

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {currentView === 'landing' && <LandingPage />}
      {currentView === 'workspace' && <TopologyCanvas />}
    </div>
  )
}

export default App
