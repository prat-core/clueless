import { useState, useEffect } from 'react'
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom'
import reactLogo from './assets/react.svg'
import viteLogo from '/vite.svg'
import './App.css'
import TopBar from './components/TopBar'
import NavBar from './components/NavBar'
import SubNavBar from './components/SubNavBar'
import MainContent from './components/MainContent'
import SecretsSection from './components/SecretsSection'
import CreateSecretModal from './components/CreateSecretModal'
import CreateSecretForm from './components/CreateSecretForm'
import NotebooksSection from './components/NotebooksSection'
import StorageSection from './components/StorageSection'
import LogsSection from './components/LogsSection'
import SettingsPage from './components/SettingsPage'

function App() {
  const [count, setCount] = useState(0)
  const navigate = useNavigate()
  const location = useLocation()

  const handleTabChange = (tab) => {
    const routes = {
      'Apps': '/apps',
      'Logs': '/logs',
      'Secrets': '/secrets',
      'Storage': '/storage',
      'Notebooks': '/notebooks'
    }
    navigate(routes[tab])
  }

  const handleCreateSecret = () => {
    navigate('/secrets/create')
  }

  const handleBackToSecrets = () => {
    navigate('/secrets')
  }

  // Redirect root to /apps
  useEffect(() => {
    if (location.pathname === '/') {
      navigate('/apps')
    }
  }, [location.pathname, navigate])

  return (
    <>
      <TopBar />
      <NavBar />
      <SubNavBar onTabChange={handleTabChange} />
      <Routes>
        <Route path="/apps" element={<MainContent />} />
        <Route path="/logs" element={<LogsSection />} />
        <Route path="/secrets" element={<SecretsSection onCreateSecret={handleCreateSecret} />} />
        <Route path="/secrets/create" element={<CreateSecretModal onBack={handleBackToSecrets} />} />
        <Route path="/secrets/create/:type" element={<CreateSecretForm />} />
        <Route path="/storage" element={<StorageSection />} />
        <Route path="/notebooks" element={<NotebooksSection />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/settings/profile" element={<SettingsPage />} />
        <Route path="/settings/workspaces" element={<SettingsPage />} />
        <Route path="/settings/notifications" element={<SettingsPage />} />
        <Route path="/settings/usage-and-billing" element={<SettingsPage />} />
        <Route path="/settings/plans" element={<SettingsPage />} />
        <Route path="/settings/api-tokens" element={<SettingsPage />} />
        <Route path="/settings/proxy-auth-tokens" element={<SettingsPage />} />
        <Route path="/settings/domains" element={<SettingsPage />} />
        <Route path="/settings/image-config" element={<SettingsPage />} />
        <Route path="/settings/proxies" element={<SettingsPage />} />
      </Routes>
    </>
  )
}

export default App
