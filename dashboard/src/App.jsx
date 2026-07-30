import React, { useState, useEffect, useCallback } from 'react';
import {
  Activity, Server, Zap, HardDrive, Cpu, Play, Brain, TrendingUp,
  AlertTriangle, CheckCircle, XCircle, Clock, BarChart3, Users,
  Shield, Wifi, WifiOff, Loader, LogIn, UserPlus, ChevronDown,
  FileText, Search, RefreshCw
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell, PieChart, Pie
} from 'recharts';

const API = import.meta.env.VITE_API_URL || '/api/v1';

/* ───────── Auth Screen ───────── */
function AuthScreen({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const body = isLogin ? { username, password } : { username, email, password };
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Auth failed');
      localStorage.setItem('token', data.access_token);
      onAuth(data.user, data.access_token);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="glass-panel p-10 w-full max-w-md space-y-8">
        <div className="text-center">
          <h1 className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary flex items-center justify-center gap-3">
            <Zap className="text-primary w-8 h-8" /> CoCompute
          </h1>
          <p className="text-gray-400 mt-2 text-sm">Distributed Computing Network</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-5">
          <input value={username} onChange={e => setUsername(e.target.value)} placeholder="Username"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          {!isLogin && (
            <input value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          )}
          <input value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          {error && <p className="text-red-400 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full bg-primary hover:bg-blue-600 transition-colors text-white py-3 rounded-xl font-semibold shadow-lg shadow-primary/30 flex items-center justify-center gap-2 disabled:opacity-50">
            {loading ? <Loader className="w-5 h-5 animate-spin" /> : isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <p className="text-center text-gray-400 text-sm">
          {isLogin ? "Don't have an account?" : 'Already have an account?'}
          <button onClick={() => { setIsLogin(!isLogin); setError(''); }}
            className="text-primary ml-2 hover:underline font-medium">{isLogin ? 'Register' : 'Sign In'}</button>
        </p>
      </div>
    </div>
  );
}

/* ───────── Stat Card ───────── */
function StatCard({ label, value, icon: Icon, color = 'text-gray-400', sub }) {
  return (
    <div className="glass-panel p-5 hover:border-white/20 transition-all duration-300">
      <div className="flex items-center justify-between text-gray-400">
        <span className="text-sm font-medium">{label}</span>
        <Icon className={`w-5 h-5 ${color}`} />
      </div>
      <p className="text-3xl font-bold mt-3 text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
    </div>
  );
}

/* ───────── Submit Job Modal ───────── */
function SubmitJobModal({ show, onClose, token }) {
  const [jobType, setJobType] = useState('prime_generation');
  const [name, setName] = useState('');
  const [loading, setLoading] = useState(false);

  const defaults = {
    prime_generation: { start: 1, end: 1000000, chunks: 20 },
    matrix_multiply: { rows_a: 50, cols_a: 50, cols_b: 50, chunks: 10 },
    word_count: { text: 'CoCompute is a distributed computing platform that aggregates idle computational resources from multiple devices and transforms them into a unified computational network designed for intelligent resource sharing and parallel task execution across heterogeneous hardware', chunks: 5 },
    generic_python: { script: "import sys, json\ndata = json.loads(sys.argv[1])\nresult = sum(data['numbers'])\nprint(json.dumps({'sum': result}))", data_chunks: [{ numbers: [1, 2, 3] }, { numbers: [4, 5, 6] }] }
  };

  const submit = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/jobs/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          name: name || `${jobType} job`,
          description: `Distributed ${jobType} computation`,
          job_type: jobType,
          params: defaults[jobType]
        })
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      onClose();
      setName('');
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  if (!show) return null;
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-panel p-8 w-full max-w-lg space-y-6" onClick={e => e.stopPropagation()}>
        <h2 className="text-2xl font-bold text-white">Submit New Job</h2>
        <input value={name} onChange={e => setName(e.target.value)} placeholder="Job Name (optional)"
          className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-primary" />
        <div>
          <label className="text-sm text-gray-400 mb-2 block">Job Type</label>
          <div className="grid grid-cols-2 gap-3">
            {Object.keys(defaults).map(t => (
              <button key={t} onClick={() => setJobType(t)}
                className={`px-4 py-3 rounded-xl text-sm font-medium border transition-all duration-200 ${jobType === t ? 'bg-primary/20 border-primary text-primary' : 'bg-white/5 border-white/10 text-gray-300 hover:border-white/20'}`}>
                {t.replace('_', ' ')}
              </button>
            ))}
          </div>
        </div>
        <pre className="bg-black/30 rounded-xl p-4 text-xs text-gray-400 overflow-auto max-h-40">
          {JSON.stringify(defaults[jobType], null, 2)}
        </pre>
        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-3 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition font-medium">Cancel</button>
          <button onClick={submit} disabled={loading}
            className="flex-1 py-3 rounded-xl bg-primary hover:bg-blue-600 text-white font-semibold shadow-lg shadow-primary/30 transition flex items-center justify-center gap-2 disabled:opacity-50">
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />} Submit
          </button>
        </div>
      </div>
    </div>
  );
}

/* ───────── Worker Card ───────── */
function WorkerCard({ worker }) {
  const statusConfig = {
    online: { color: 'green', icon: Wifi, label: 'Online' },
    offline: { color: 'red', icon: WifiOff, label: 'Offline' },
    busy: { color: 'yellow', icon: Loader, label: 'Busy' },
  };
  const s = statusConfig[worker.status] || statusConfig.offline;
  const Icon = s.icon;

  return (
    <div className="bg-white/5 hover:bg-white/10 transition-all duration-300 rounded-xl p-4 border border-white/10">
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-gray-200">{worker.hostname || worker.worker_uid?.slice(0, 8)}</h3>
        <div className={`flex items-center gap-1.5 bg-${s.color}-500/10 px-2.5 py-1 rounded-full border border-${s.color}-500/20`}>
          <Icon className={`w-3 h-3 text-${s.color}-400 ${worker.status === 'busy' ? 'animate-spin' : worker.status === 'online' ? 'animate-pulse' : ''}`} />
          <span className={`text-xs text-${s.color}-400 font-medium uppercase tracking-wide`}>{s.label}</span>
        </div>
      </div>
      <div className="space-y-2">
        <div className="flex justify-between text-xs text-gray-400">
          <span>CPU</span><span>{worker.cpu_cores} cores • {Math.round(worker.cpu_utilization || 0)}%</span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1.5">
          <div className="bg-primary h-1.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(worker.cpu_utilization || 0, 100)}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-400">
          <span>RAM</span><span>{worker.ram_total}GB • {Math.round(worker.ram_usage || 0)}%</span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1.5">
          <div className="bg-secondary h-1.5 rounded-full transition-all duration-500" style={{ width: `${Math.min(worker.ram_usage || 0, 100)}%` }} />
        </div>
        <div className="flex justify-between text-xs text-gray-400 pt-1">
          <span>Tasks: {worker.running_tasks || 0} running</span>
          <span>⭐ {(worker.reliability_score * 100).toFixed(0)}%</span>
        </div>
      </div>
    </div>
  );
}

/* ───────── Main App ───────── */
function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [workers, setWorkers] = useState([]);
  const [cluster, setCluster] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [showSubmit, setShowSubmit] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [logs, setLogs] = useState([]);
  const [logLevel, setLogLevel] = useState('');
  const [logSearch, setLogSearch] = useState('');

  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  const fetchAll = useCallback(async () => {
    try {
      const [wRes, cRes, jRes] = await Promise.all([
        fetch(`${API}/workers/`), fetch(`${API}/metrics/cluster`), fetch(`${API}/jobs/`)
      ]);
      if (wRes.ok) setWorkers(await wRes.json());
      if (cRes.ok) setCluster(await cRes.json());
      if (jRes.ok) setJobs(await jRes.json());

      const [spRes, rkRes, logRes] = await Promise.all([
        fetch(`${API}/analytics/speedup`), fetch(`${API}/analytics/workers/ranking`), fetch(`${API}/logs/?limit=200`)
      ]);
      if (spRes.ok) { const d = await spRes.json(); setAnalytics(d); }
      if (rkRes.ok) { const d = await rkRes.json(); setRankings(d.rankings || []); }
      if (logRes.ok) { const d = await logRes.json(); setLogs(d.logs || []); }
    } catch (e) { console.error('Fetch error:', e); }
  }, []);

  useEffect(() => {
    if (!token) return;
    // Validate token
    fetch(`${API}/auth/me`, { headers }).then(r => {
      if (r.ok) { r.json().then(u => setUser(u)); fetchAll(); }
      else { setToken(null); localStorage.removeItem('token'); }
    }).catch(() => {});
    const iv = setInterval(fetchAll, 5000);
    return () => clearInterval(iv);
  }, [token, fetchAll]);

  if (!token) return <AuthScreen onAuth={(u, t) => { setUser(u); setToken(t); }} />;

  const c = cluster || {};
  const tasks = c.tasks || {};
  const jobStats = c.jobs || {};
  const onlineW = workers.filter(w => w.status === 'online');
  const offlineW = workers.filter(w => w.status !== 'online');

  const TABS = [
    { id: 'overview', label: 'Overview', icon: Activity },
    { id: 'tasks', label: 'Tasks', icon: Clock },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'workers', label: 'Workers', icon: Server },
    { id: 'logs', label: 'Logs', icon: FileText },
  ];

  const pieData = [
    { name: 'Completed', value: tasks.completed || 0, fill: '#10B981' },
    { name: 'Running', value: tasks.running || 0, fill: '#3B82F6' },
    { name: 'Failed', value: tasks.failed || 0, fill: '#EF4444' },
    { name: 'Pending', value: tasks.pending || 0, fill: '#6B7280' },
  ].filter(d => d.value > 0);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-[1600px] mx-auto px-6 py-4 flex justify-between items-center">
          <div className="flex items-center gap-3">
            <Zap className="text-primary w-7 h-7" />
            <h1 className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-secondary">CoCompute</h1>
          </div>
          <div className="flex items-center gap-3">
            <nav className="flex gap-1 bg-white/5 rounded-xl p-1 mr-4">
              {TABS.map(t => (
                <button key={t.id} onClick={() => setActiveTab(t.id)}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === t.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'}`}>
                  <t.icon className="w-4 h-4" /> {t.label}
                </button>
              ))}
            </nav>
            <button onClick={() => setShowSubmit(true)}
              className="bg-primary hover:bg-blue-600 transition-colors text-white px-5 py-2.5 rounded-xl flex items-center gap-2 font-semibold shadow-lg shadow-primary/30 text-sm">
              <Play className="w-4 h-4 fill-current" /> Submit Job
            </button>
            <div className="flex items-center gap-2 ml-2 text-sm text-gray-400">
              <Shield className="w-4 h-4" />
              <span>{user?.username}</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1600px] mx-auto px-6 py-6 space-y-6">

        {/* ───── OVERVIEW TAB ───── */}
        {activeTab === 'overview' && (
          <>
            {/* Stat Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
              <StatCard label="Total Nodes" value={c.total_nodes || 0} icon={Server} />
              <StatCard label="Online" value={c.online_nodes || 0} icon={Wifi} color="text-green-400" />
              <StatCard label="Offline" value={c.offline_nodes || 0} icon={WifiOff} color="text-red-400" />
              <StatCard label="Active Cores" value={c.active_cores || 0} icon={Cpu} color="text-secondary" />
              <StatCard label="RAM Pool" value={`${c.aggregated_ram || 0} GB`} icon={HardDrive} color="text-primary" />
              <StatCard label="Efficiency" value={`${c.efficiency || 0}%`} icon={Activity} color="text-green-400" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Resource Chart */}
              <div className="glass-panel p-6 lg:col-span-2">
                <h2 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
                  <Activity className="w-5 h-5" /> Cluster Resource Utilization
                </h2>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={c.history || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="timestamp" stroke="#94a3b8" tick={false} />
                      <YAxis stroke="#94a3b8" domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: 'none', borderRadius: '8px', color: '#fff' }} />
                      <Line type="monotone" dataKey="cpu" name="CPU %" stroke="#3B82F6" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="ram" name="RAM %" stroke="#10B981" strokeWidth={2} dot={false} />
                      <Line type="monotone" dataKey="disk" name="Disk %" stroke="#F59E0B" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Task Pie */}
              <div className="glass-panel p-6">
                <h2 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
                  <Clock className="w-5 h-5" /> Task Distribution
                </h2>
                {pieData.length > 0 ? (
                  <div className="h-56">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3}>
                          {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                        </Pie>
                        <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: 'none', borderRadius: '8px', color: '#fff' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-56 flex items-center justify-center text-gray-500">No tasks yet</div>
                )}
                <div className="grid grid-cols-2 gap-2 mt-4">
                  <div className="text-center"><p className="text-2xl font-bold text-green-400">{tasks.completed || 0}</p><p className="text-xs text-gray-500">Completed</p></div>
                  <div className="text-center"><p className="text-2xl font-bold text-blue-400">{tasks.running || 0}</p><p className="text-xs text-gray-500">Running</p></div>
                  <div className="text-center"><p className="text-2xl font-bold text-red-400">{tasks.failed || 0}</p><p className="text-xs text-gray-500">Failed</p></div>
                  <div className="text-center"><p className="text-2xl font-bold text-gray-400">{tasks.pending || 0}</p><p className="text-xs text-gray-500">Queued</p></div>
                </div>
              </div>
            </div>

            {/* Live Workers */}
            <div className="glass-panel p-6">
              <h2 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
                <Server className="w-5 h-5" /> Worker Nodes ({workers.length})
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {workers.map(w => <WorkerCard key={w.id} worker={w} />)}
                {workers.length === 0 && <p className="text-gray-500 col-span-full text-center py-8">No workers registered yet</p>}
              </div>
            </div>
          </>
        )}

        {/* ───── TASKS TAB ───── */}
        {activeTab === 'tasks' && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Total Jobs" value={jobStats.total || 0} icon={BarChart3} />
              <StatCard label="Running" value={jobStats.running || 0} icon={Loader} color="text-blue-400" />
              <StatCard label="Completed" value={jobStats.completed || 0} icon={CheckCircle} color="text-green-400" />
              <StatCard label="Queue Length" value={tasks.queue_length || 0} icon={Clock} color="text-yellow-400" />
            </div>

            <div className="glass-panel overflow-hidden">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/10 text-left text-sm text-gray-400">
                    <th className="px-6 py-4">ID</th>
                    <th className="px-6 py-4">Name</th>
                    <th className="px-6 py-4">Type</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4">Progress</th>
                    <th className="px-6 py-4">Submitted</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(j => {
                    const pct = j.total_tasks > 0 ? Math.round(((j.completed_tasks + j.failed_tasks) / j.total_tasks) * 100) : 0;
                    const statusColors = { pending: 'text-gray-400', running: 'text-blue-400', completed: 'text-green-400', failed: 'text-red-400' };
                    return (
                      <tr key={j.id} className="border-b border-white/5 hover:bg-white/5 transition text-sm">
                        <td className="px-6 py-4 text-gray-300">#{j.id}</td>
                        <td className="px-6 py-4 text-white font-medium">{j.name}</td>
                        <td className="px-6 py-4 text-gray-400">{j.job_type}</td>
                        <td className="px-6 py-4">
                          <span className={`${statusColors[j.status] || 'text-gray-400'} font-medium capitalize`}>{j.status}</span>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-24 bg-white/5 rounded-full h-2">
                              <div className={`h-2 rounded-full transition-all duration-500 ${j.status === 'completed' ? 'bg-green-500' : j.status === 'failed' ? 'bg-red-500' : 'bg-primary'}`} style={{ width: `${pct}%` }} />
                            </div>
                            <span className="text-xs text-gray-400">{j.completed_tasks}/{j.total_tasks}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-gray-500 text-xs">{new Date(j.submission_time).toLocaleString()}</td>
                      </tr>
                    );
                  })}
                  {jobs.length === 0 && (
                    <tr><td colSpan={6} className="px-6 py-12 text-center text-gray-500">No jobs submitted yet</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* ───── ANALYTICS TAB ───── */}
        {activeTab === 'analytics' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatCard label="Avg Speedup" value={`${analytics?.avg_speedup?.toFixed(2) || '0'}x`} icon={Zap} color="text-purple-400" />
              <StatCard label="Avg Efficiency" value={`${((analytics?.avg_efficiency || 0) * 100).toFixed(1)}%`} icon={TrendingUp} color="text-green-400" />
              <StatCard label="Cluster Efficiency" value={`${c.efficiency || 0}%`} icon={Activity} color="text-secondary" />
            </div>

            {/* Speedup Chart */}
            {analytics?.per_job?.length > 0 && (
              <div className="glass-panel p-6">
                <h2 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
                  <Brain className="w-5 h-5 text-purple-400" /> Speedup per Job
                </h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.per_job}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                      <XAxis dataKey="job_name" stroke="#94a3b8" tick={{ fontSize: 11 }} />
                      <YAxis stroke="#94a3b8" />
                      <Tooltip contentStyle={{ backgroundColor: '#1E293B', border: 'none', borderRadius: '8px', color: '#fff' }} />
                      <Bar dataKey="speedup" fill="#A855F7" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Worker Rankings */}
            {rankings.length > 0 && (
              <div className="glass-panel overflow-hidden">
                <div className="px-6 py-4 border-b border-white/10">
                  <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" /> Worker Performance Rankings
                  </h2>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs text-gray-400 uppercase tracking-wider">
                      <th className="px-6 py-3">Rank</th>
                      <th className="px-6 py-3">Worker</th>
                      <th className="px-6 py-3">Status</th>
                      <th className="px-6 py-3">Completed</th>
                      <th className="px-6 py-3">Failed</th>
                      <th className="px-6 py-3">Reliability</th>
                      <th className="px-6 py-3">Avg Time</th>
                      <th className="px-6 py-3">Score</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankings.map((r, i) => (
                      <tr key={r.worker_uid} className="border-b border-white/5 hover:bg-white/5 transition text-sm">
                        <td className="px-6 py-3 text-gray-400">#{i + 1}</td>
                        <td className="px-6 py-3 text-white font-medium">{r.hostname}</td>
                        <td className="px-6 py-3"><span className={`text-xs font-medium uppercase ${r.status === 'online' ? 'text-green-400' : 'text-red-400'}`}>{r.status}</span></td>
                        <td className="px-6 py-3 text-green-400">{r.tasks_completed}</td>
                        <td className="px-6 py-3 text-red-400">{r.tasks_failed}</td>
                        <td className="px-6 py-3 text-gray-300">{(r.reliability_score * 100).toFixed(0)}%</td>
                        <td className="px-6 py-3 text-gray-300">{r.avg_execution_seconds.toFixed(2)}s</td>
                        <td className="px-6 py-3 text-primary font-bold">{r.composite_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* ───── WORKERS TAB ───── */}
        {activeTab === 'workers' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <StatCard label="Online Workers" value={onlineW.length} icon={Wifi} color="text-green-400" />
              <StatCard label="Offline Workers" value={offlineW.length} icon={WifiOff} color="text-red-400" />
              <StatCard label="Total Cores" value={c.active_cores || 0} icon={Cpu} color="text-primary" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workers.map(w => <WorkerCard key={w.id} worker={w} />)}
              {workers.length === 0 && (
                <div className="col-span-full glass-panel p-12 text-center text-gray-500">
                  <Server className="w-12 h-12 mx-auto mb-4 opacity-30" />
                  <p>No workers registered. Start a worker node to begin.</p>
                </div>
              )}
            </div>
          </>
        )}

        {/* ───── LOGS TAB ───── */}
        {activeTab === 'logs' && (() => {
          const filteredLogs = logs.filter(log => {
            if (logLevel && log.level !== logLevel) return false;
            if (logSearch && !log.source?.toLowerCase().includes(logSearch.toLowerCase()) && !log.message?.toLowerCase().includes(logSearch.toLowerCase())) return false;
            return true;
          });
          const levelColors = {
            INFO: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
            WARNING: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
            ERROR: 'bg-red-500/10 text-red-400 border-red-500/20',
            CRITICAL: 'bg-red-600/20 text-red-300 border-red-600/30',
          };
          return (
            <>
              <div className="flex flex-wrap gap-3 items-center">
                <div className="flex gap-1.5 bg-white/5 rounded-xl p-1">
                  {['', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(level => (
                    <button key={level} onClick={() => setLogLevel(level)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${logLevel === level ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'}`}>
                      {level || 'ALL'}
                    </button>
                  ))}
                </div>
                <div className="flex-1 min-w-[200px]">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input value={logSearch} onChange={e => setLogSearch(e.target.value)} placeholder="Search logs..."
                      className="w-full bg-white/5 border border-white/10 rounded-xl pl-10 pr-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-primary transition" />
                  </div>
                </div>
                <button onClick={fetchAll}
                  className="px-4 py-2.5 rounded-xl bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:border-white/20 transition flex items-center gap-2 text-sm font-medium">
                  <RefreshCw className="w-4 h-4" /> Refresh
                </button>
                <span className="text-xs text-gray-500">{filteredLogs.length} entries</span>
              </div>

              <div className="glass-panel overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/10 text-left text-xs text-gray-400 uppercase tracking-wider">
                      <th className="px-6 py-3 w-48">Timestamp</th>
                      <th className="px-6 py-3 w-28">Level</th>
                      <th className="px-6 py-3 w-40">Source</th>
                      <th className="px-6 py-3">Message</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map(log => (
                      <tr key={log.id} className="border-b border-white/5 hover:bg-white/5 transition text-sm">
                        <td className="px-6 py-3 text-gray-500 text-xs whitespace-nowrap">
                          {log.timestamp ? new Date(log.timestamp).toLocaleString() : '—'}
                        </td>
                        <td className="px-6 py-3">
                          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${levelColors[log.level] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>
                            {log.level}
                          </span>
                        </td>
                        <td className="px-6 py-3 text-gray-300 font-mono text-xs">{log.source}</td>
                        <td className="px-6 py-3 text-gray-300 text-xs">{log.message}</td>
                      </tr>
                    ))}
                    {filteredLogs.length === 0 && (
                      <tr>
                        <td colSpan={4} className="px-6 py-16 text-center text-gray-500">
                          <FileText className="w-10 h-10 mx-auto mb-3 opacity-30" />
                          <p>No log entries found</p>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          );
        })()}
      </main>

      <SubmitJobModal show={showSubmit} onClose={() => setShowSubmit(false)} token={token} />
    </div>
  );
}

export default App;
