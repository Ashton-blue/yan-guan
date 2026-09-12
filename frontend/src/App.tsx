import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import Login from './pages/Login'
import Register from './pages/Register'
import ChangePassword from './pages/ChangePassword'
import Dashboard from './pages/Dashboard'
import Members from './pages/Members'
import PolicyAssistant from './pages/PolicyAssistant'
import Account from './pages/Account'
import Meetings from './pages/Meetings'
import Files from './pages/Files'
import Messages from './pages/Messages'

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/change-password" element={<ChangePassword />} />
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<Dashboard />} />
            <Route path="meetings" element={<Meetings />} />
            <Route path="files" element={<Files />} />
            <Route path="messages" element={<Messages />} />
            <Route path="members" element={<Members />} />
            <Route path="account" element={<Account />} />
            <Route path="policy" element={<PolicyAssistant />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
