import { useState, useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_BASE_URL = 'http://localhost:8000/api/v1'

function App() {
  const [view, setView] = useState('login') // 'login', 'register', 'dashboard'
  
  // Auth state
  const [authForm, setAuthForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [authError, setAuthError] = useState(null)

  // Dashboard state
  const [tasks, setTasks] = useState([])
  const [stats, setStats] = useState({ total_tasks: 0, pending_tasks: 0, in_progress_tasks: 0, completed_tasks: 0, high_priority_tasks: 0, overdue_tasks: 0 })
  
  // Search & Filter state
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState('')
  
  // Form state
  const [editingId, setEditingId] = useState(null)
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    status: 'pending',
    priority: 'medium',
    due_date: ''
  })
  const [error, setError] = useState(null)

  // Initialization check
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      setView('dashboard')
    }
  }, [])

  // Fetch tasks and stats when in dashboard view
  useEffect(() => {
    if (view === 'dashboard') {
      fetchTasks()
      fetchStats()
    }
  }, [view, search, statusFilter, priorityFilter])

  const fetchTasks = async () => {
    try {
      const params = new URLSearchParams()
      if (search) params.append('search', search)
      if (statusFilter) params.append('status', statusFilter)
      if (priorityFilter) params.append('priority', priorityFilter)
      params.append('limit', '100')

      const response = await axios.get(`${API_BASE_URL}/tasks?${params.toString()}`)
      setTasks(response.data.data)
    } catch (err) {
      if (err.response?.status === 401 || err.response?.status === 403) {
        handleLogout()
      }
      console.error("Error fetching tasks:", err)
    }
  }

  const fetchStats = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/dashboard`)
      setStats(response.data.data)
    } catch (err) {
      console.error("Error fetching stats:", err)
    }
  }

  const handleAuthChange = (e) => {
    setAuthForm({ ...authForm, [e.target.name]: e.target.value })
  }

  const handleLogin = async (e) => {
    e.preventDefault()
    setAuthError(null)
    try {
      const res = await axios.post(`${API_BASE_URL}/auth/login`, {
        email: authForm.email,
        password: authForm.password
      })
      const token = res.data.data.access_token
      localStorage.setItem('token', token)
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`
      setView('dashboard')
      setAuthForm({ name: '', email: '', password: '', confirmPassword: '' })
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Invalid credentials")
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setAuthError(null)
    if (authForm.password !== authForm.confirmPassword) {
      setAuthError("Passwords do not match")
      return
    }
    try {
      await axios.post(`${API_BASE_URL}/auth/register`, {
        name: authForm.name,
        email: authForm.email,
        password: authForm.password
      })
      // Auto login after register
      handleLogin(e)
    } catch (err) {
      setAuthError(err.response?.data?.detail || "Registration failed")
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    delete axios.defaults.headers.common['Authorization']
    setView('login')
  }

  const handleInputChange = (e) => {
    const { name, value } = e.target
    setFormData(prev => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    
    const payload = { ...formData }
    if (!payload.due_date) payload.due_date = null
    // Make sure status and priority are correct types
    payload.status = payload.status || 'pending'
    payload.priority = payload.priority || 'medium'

    try {
      if (editingId) {
        await axios.put(`${API_BASE_URL}/tasks/${editingId}`, payload)
      } else {
        await axios.post(`${API_BASE_URL}/tasks`, payload)
      }
      
      setFormData({ title: '', description: '', status: 'pending', priority: 'medium', due_date: '' })
      setEditingId(null)
      fetchTasks()
      fetchStats()
    } catch (err) {
      setError(err.response?.data?.message || err.response?.data?.detail?.[0]?.msg || "An error occurred")
    }
  }

  const handleEdit = (task) => {
    setEditingId(task.id)
    setFormData({
      title: task.title,
      description: task.description || '',
      status: task.status,
      priority: task.priority,
      due_date: task.due_date || ''
    })
  }

  const handleDelete = async (id) => {
    if (window.confirm("Are you sure you want to delete this task?")) {
      try {
        await axios.delete(`${API_BASE_URL}/tasks/${id}`)
        fetchTasks()
        fetchStats()
      } catch (err) {
        console.error(err)
      }
    }
  }

  const cancelEdit = () => {
    setEditingId(null)
    setFormData({ title: '', description: '', status: 'pending', priority: 'medium', due_date: '' })
    setError(null)
  }

  if (view === 'login' || view === 'register') {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h2>{view === 'login' ? 'Login' : 'Create Account'}</h2>
          {authError && <div className="error-message">{authError}</div>}
          <form onSubmit={view === 'login' ? handleLogin : handleRegister}>
            {view === 'register' && (
              <div className="form-group">
                <label>Name</label>
                <input type="text" name="name" value={authForm.name} onChange={handleAuthChange} required minLength={2} />
              </div>
            )}
            <div className="form-group">
              <label>Email</label>
              <input type="email" name="email" value={authForm.email} onChange={handleAuthChange} required />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input type="password" name="password" value={authForm.password} onChange={handleAuthChange} required minLength={8} />
            </div>
            {view === 'register' && (
              <div className="form-group">
                <label>Confirm Password</label>
                <input type="password" name="confirmPassword" value={authForm.confirmPassword} onChange={handleAuthChange} required minLength={8} />
              </div>
            )}
            <button type="submit" className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }}>
              {view === 'login' ? 'Login' : 'Register'}
            </button>
          </form>
          <div className="auth-switch">
            {view === 'login' ? (
              <p>Don't have an account? <span onClick={() => setView('register')}>Create Account</span></p>
            ) : (
              <p>Already have an account? <span onClick={() => setView('login')}>Login</span></p>
            )}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container">
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1>Task Management API Dashboard</h1>
        <button className="btn" style={{ background: '#e5e7eb' }} onClick={handleLogout}>Logout</button>
      </header>

      <div className="dashboard-stats">
        <div className="stat-card">
          <h3>Total Tasks</h3>
          <div className="value">{stats.total_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>Pending</h3>
          <div className="value" style={{color: '#991b1b'}}>{stats.pending_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>In Progress</h3>
          <div className="value" style={{color: '#92400e'}}>{stats.in_progress_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>Completed</h3>
          <div className="value" style={{color: '#065f46'}}>{stats.completed_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>High Priority</h3>
          <div className="value" style={{color: '#9f1239'}}>{stats.high_priority_tasks}</div>
        </div>
        <div className="stat-card">
          <h3>Overdue</h3>
          <div className="value" style={{color: '#dc2626'}}>{stats.overdue_tasks}</div>
        </div>
      </div>

      <div className="main-content">
        <div className="left-column">
          <div className="controls">
            <input 
              type="text" 
              placeholder="Search by title..." 
              value={search} 
              onChange={(e) => setSearch(e.target.value)} 
            />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
            </select>
            <select value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
              <option value="">All Priorities</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>

          <div className="task-list">
            {tasks.length === 0 ? (
              <p>No tasks found.</p>
            ) : (
              tasks.map(task => (
                <div className="task-item" key={task.id}>
                  <div className="task-info">
                    <h4>{task.title}</h4>
                    <p>{task.description}</p>
                    <div className="badges">
                      <span className={`badge status-${task.status}`}>{task.status.replace('_', ' ')}</span>
                      <span className={`badge priority-${task.priority}`}>{task.priority} Priority</span>
                      {task.due_date && <span className="badge" style={{background: '#e5e7eb', color: '#374151'}}>Due: {task.due_date}</span>}
                    </div>
                  </div>
                  <div className="task-actions">
                    <button className="btn btn-edit" onClick={() => handleEdit(task)}>Edit</button>
                    <button className="btn btn-danger" onClick={() => handleDelete(task.id)}>Delete</button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="right-column">
          <div className="task-form">
            <h2>{editingId ? 'Edit Task' : 'Create Task'}</h2>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Title *</label>
                <input 
                  type="text" 
                  name="title" 
                  value={formData.title} 
                  onChange={handleInputChange} 
                  required 
                  minLength={3} 
                  maxLength={100} 
                />
              </div>
              
              <div className="form-group">
                <label>Description</label>
                <textarea 
                  name="description" 
                  value={formData.description} 
                  onChange={handleInputChange} 
                  maxLength={500} 
                />
              </div>

              <div className="form-group">
                <label>Status</label>
                <select name="status" value={formData.status} onChange={handleInputChange}>
                  <option value="pending">Pending</option>
                  <option value="in_progress">In Progress</option>
                  <option value="completed">Completed</option>
                </select>
              </div>

              <div className="form-group">
                <label>Priority</label>
                <select name="priority" value={formData.priority} onChange={handleInputChange}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div className="form-group">
                <label>Due Date</label>
                <input 
                  type="date" 
                  name="due_date" 
                  value={formData.due_date} 
                  onChange={handleInputChange} 
                />
              </div>

              {error && <div className="error-message">{error}</div>}

              <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                <button type="submit" className="btn btn-primary" style={{ flex: 1 }}>
                  {editingId ? 'Update Task' : 'Create Task'}
                </button>
                {editingId && (
                  <button type="button" className="btn" style={{ background: '#e5e7eb' }} onClick={cancelEdit}>
                    Cancel
                  </button>
                )}
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
