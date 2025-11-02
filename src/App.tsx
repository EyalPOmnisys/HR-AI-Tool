import { useState } from 'react'
import './App.css'
import { Sidebar } from './components/Sidebar/Sidebar'
import { JobBoard } from './screens/JobBoard/JobBoard'

const App = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)

  return (
    <div className="appShell">
      <Sidebar
        open={isSidebarOpen}
        onToggle={() => setIsSidebarOpen((previous) => !previous)}
        activeItem="Job Board"
      />
      <main className="appContent">
        <JobBoard />
      </main>
    </div>
  )
}

export default App
