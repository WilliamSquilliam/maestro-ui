import { AppShell } from './components/layout/AppShell'
import { Toaster } from 'sonner' // Using sonner toaster
import { MaestroSocketHost } from './lib/ws'

function App() {
  return (
    <div className="dark"> {/* Enforce dark mode base styling since it's dark-mode first for now */}
      <MaestroSocketHost />
      <AppShell />
      <Toaster theme="dark" />
    </div>
  )
}

export default App
