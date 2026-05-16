import { Routes, Route, NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Models from './pages/Models'
import Settings from './pages/Settings'
import Logs from './pages/Logs'
import About from './pages/About'
import StatusBar from './components/StatusBar'

const navItems = [
  { path: '/', label: '仪表板', icon: '◉' },
  { path: '/models', label: '模型配置', icon: '⚙' },
  { path: '/settings', label: '全局设置', icon: '⊡' },
  { path: '/logs', label: '监控日志', icon: '☰' },
  { path: '/about', label: '关于', icon: 'ⓘ' },
]

export default function App() {
  const [status, setStatus] = useState<any>(null)

  useEffect(() => {
    let timer: any
    const poll = async () => {
      try {
        const resp = await fetch('/admin/api/status')
        const data = await resp.json()
        setStatus(data)
      } catch { setStatus(null) }
    }
    poll()
    timer = setInterval(poll, 3000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1 className="app-title">Codex 国内模型适配工具</h1>
        <StatusBar data={status} />
      </header>
      <div className="app-body">
        <nav className="sidebar">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `sidebar-link${isActive ? ' active' : ''}`
              }
            >
              <span className="sidebar-icon">{item.icon}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Dashboard status={status} />} />
            <Route path="/models" element={<Models />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/logs" element={<Logs />} />
            <Route path="/about" element={<About />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
