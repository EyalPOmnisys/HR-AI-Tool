import { useState, useEffect } from 'react'
import type { CSSProperties, ReactElement } from 'react'
import './App.css'
import { Sidebar } from './components/Sidebar/Sidebar'
import { LoginModal } from './components/common/LoginModal/LoginModal'
import AISearch from './screens/AISearch/AISearch'
import { JobBoard } from './screens/JobBoard/JobBoard'
import { Resumes } from './screens/Resumes/Resumes'
import type { ScreenId } from './types/navigation'

const App = (): ReactElement => {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [activePage, setActivePage] = useState<ScreenId>('ai-search')
  const sidebarWidth = isSidebarOpen ? 240 : 72

  useEffect(() => {
    const auth = localStorage.getItem('is_authenticated')
    if (auth === 'true') {
      setIsAuthenticated(true)
    }
  }, [])

  const handleLogin = (password: string): boolean => {
    const correctPassword = import.meta.env.VITE_APP_PASSWORD || 'admin123'
    if (password === correctPassword) {
      setIsAuthenticated(true)
      localStorage.setItem('is_authenticated', 'true')
      return true
    }
    return false
  }

  const handleLogout = () => {
    setIsAuthenticated(false)
    localStorage.removeItem('is_authenticated')
  }

  const handleNavigationSelect = (itemId: ScreenId) => {
    setActivePage(itemId)
  }

  const renderActivePage = (): ReactElement => {
    if (activePage === 'ai-search') {
      return <AISearch />
    }
    if (activePage === 'resumes') {
      return <Resumes />
    }
    return <JobBoard />
  }

  if (!isAuthenticated) {
    return <LoginModal onLogin={handleLogin} />
  }

  return (
    <div
      className="appShell"
      style={{ '--sidebar-width': `${sidebarWidth}px` } as CSSProperties}
    >
      <Sidebar
        open={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((previous) => !previous)}
        activeItem={activePage}
        onSelect={handleNavigationSelect}
        onLogout={handleLogout}
      />
      <main className="appContent">
        {renderActivePage()}
      </main>
    </div>
  )
}

export default App
