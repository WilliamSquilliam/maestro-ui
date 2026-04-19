import { AppShell } from './components/layout/AppShell'
import { Toaster } from 'sonner' // Using sonner toaster

function App() {
  return (
    <div className="dark"> {/* Enforce dark mode base styling since it's dark-mode first for now */}
      <AppShell />
      <Toaster theme="dark" />
    </div>
  )
}

export default App
