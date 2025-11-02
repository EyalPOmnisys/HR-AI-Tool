import { useState } from 'react'
import type { CSSProperties, ReactElement } from 'react'
import './App.css'
import { Sidebar } from './components/Sidebar/Sidebar'
import { AISearch } from './screens/AISearch/AISearch'
import { JobBoard } from './screens/JobBoard/JobBoard'
import { Resumes } from './screens/Resumes/Resumes'
import type { ScreenId } from './types/navigation'

const App = (): ReactElement => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const [activePage, setActivePage] = useState<ScreenId>('ai-search')
  const sidebarWidth = isSidebarOpen ? 240 : 72

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
      />
      <main className="appContent">
        {renderActivePage()}
      </main>
    </div>
  )
}

export default App
