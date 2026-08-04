import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, Server, Zap, HardDrive, Cpu, Play, Brain, TrendingUp,
  AlertTriangle, CheckCircle, XCircle, Clock, BarChart3, Users,
  Shield, Wifi, WifiOff, Loader, LogIn, UserPlus, ChevronDown,
  FileText, Search, RefreshCw, Bell, BellOff, X, Settings,
  ChevronRight, Terminal, Network, Database, Layers, Eye,
  ArrowUpRight, ArrowDownRight, Gauge, Sliders, Info, AlertCircle
} from 'lucide-react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Cell, PieChart, Pie, Legend
} from 'recharts';

const API = import.meta.env.VITE_API_URL || '/api/v1';
const WS_BASE = (import.meta.env.VITE_WS_URL || window.location.origin.replace(/^http/, 'ws'));

// ─── Utility: severity color maps ───────────────────────────────────────────
const SEVERITY = {
  error:   { bg: 'bg-red-500/10',    border: 'border-red-500/30',    text: 'text-red-400',    icon: XCircle },
  warning: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30', text: 'text-yellow-400', icon: AlertTriangle },
  info:    { bg: 'bg-blue-500/10',   border: 'border-blue-500/30',   text: 'text-blue-400',   icon: Info },
};

const STATUS_CONFIG = {
  online:  { color: 'text-emerald-400', bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', icon: Wifi,   label: 'Online' },
  offline: { color: 'text-red-400',     bg: 'bg-red-500/10',     border: 'border-red-500/20',     icon: WifiOff,label: 'Offline' },
  busy:    { color: 'text-yellow-400',  bg: 'bg-yellow-500/10',  border: 'border-yellow-500/20',  icon: Loader, label: 'Busy' },
};

function fmt(n, dec = 1) { return n != null ? Number(n).toFixed(dec) : '—'; }
function fmtTime(iso) { return iso ? new Date(iso).toLocaleString() : '—'; }

// ─── Auth Screen ─────────────────────────────────────────────────────────────
function AuthScreen({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const body = isLogin ? { username, password } : { username, email, password };
      const res = await fetch(`${API}${endpoint}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Auth failed');
      localStorage.setItem('token', data.access_token);
      onAuth(data.user, data.access_token);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4 relative overflow-hidden">
      {/* Background orbs */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent/5 rounded-full blur-3xl pointer-events-none" />

      <div className="glass-panel p-10 w-full max-w-md space-y-8 scale-in relative z-10">
        <div className="text-center space-y-3">
          <div className="flex items-center justify-center gap-3 mb-2">
            <div className="p-2.5 rounded-xl bg-primary/10 border border-primary/20">
              <Zap className="text-primary w-7 h-7" />
            </div>
          </div>
          <h1 className="text-3xl font-extrabold gradient-text">CoCompute</h1>
          <p className="text-gray-400 text-sm">Collaborative Distributed Computing</p>
        </div>

        <div className="flex bg-white/5 rounded-xl p-1">
          {['Sign In', 'Register'].map((tab, i) => (
            <button key={tab} onClick={() => { setIsLogin(i === 0); setError(''); }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${(isLogin ? i === 0 : i === 1) ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'}`}>
              {tab}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input id="auth-username" value={username} onChange={e => setUsername(e.target.value)} placeholder="Username"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          {!isLogin && (
            <input id="auth-email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
              className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          )}
          <input id="auth-password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" type="password"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
          {error && <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">{error}</p>}
          <button id="auth-submit" type="submit" disabled={loading}
            className="w-full bg-primary hover:bg-blue-500 transition-all text-white py-3 rounded-xl font-semibold shadow-lg shadow-primary/20 flex items-center justify-center gap-2 disabled:opacity-50 glow-primary">
            {loading ? <Loader className="w-5 h-5 animate-spin" /> : isLogin ? <LogIn className="w-5 h-5" /> : <UserPlus className="w-5 h-5" />}
            {isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
      </div>
    </div>
  );
}

// ─── Stat Card ──────────────────────────────────────────────────────────────
function StatCard({ label, value, icon: Icon, color = 'text-gray-400', sub, trend }) {
  return (
    <div className="glass-panel p-5 hover:border-white/20 transition-all duration-300 group">
      <div className="flex items-center justify-between text-gray-400">
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
        <div className={`p-1.5 rounded-lg bg-white/5 group-hover:bg-white/10 transition-colors ${color}`}>
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <p className="text-2xl font-bold mt-3 text-white">{value}</p>
      {sub && <p className="text-xs text-gray-500 mt-1">{sub}</p>}
      {trend != null && (
        <div className={`flex items-center gap-1 mt-1 text-xs ${trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
          {trend >= 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
          {Math.abs(trend).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

// ─── Metric Bar ─────────────────────────────────────────────────────────────
function MetricBar({ label, value, color = 'bg-primary', textColor = 'text-gray-400' }) {
  const pct = Math.min(Math.max(value || 0, 0), 100);
  const barColor = pct > 90 ? 'bg-red-500' : pct > 75 ? 'bg-yellow-500' : color;
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className={textColor}>{label}</span>
        <span className="text-white font-medium">{fmt(pct, 0)}%</span>
      </div>
      <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div className={`${barColor} h-1.5 rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ─── Worker Card ────────────────────────────────────────────────────────────
function WorkerCard({ worker, onClick }) {
  const s = STATUS_CONFIG[worker.status] || STATUS_CONFIG.offline;
  const Icon = s.icon;
  const cpu = worker.cpu_utilization || 0;
  const isOverloaded = cpu > 85 || (worker.ram_usage || 0) > 90;

  return (
    <div onClick={() => onClick(worker)}
      className={`glass-panel-2 p-4 hover:border-white/20 transition-all duration-300 cursor-pointer group ${isOverloaded ? 'border-yellow-500/30' : ''}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <div className={`p-1.5 rounded-lg ${s.bg} ${s.border} border`}>
            <Server className={`w-3.5 h-3.5 ${s.color}`} />
          </div>
          <div>
            <h3 className="font-semibold text-gray-200 text-sm truncate max-w-[120px]">
              {worker.hostname || worker.worker_uid?.slice(0, 8)}
            </h3>
            <p className="text-xs text-gray-500">{worker.platform?.split(' ')[0] || 'Unknown OS'}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {isOverloaded && <AlertTriangle className="w-3.5 h-3.5 text-yellow-400 alert-pulse" />}
          <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${s.bg} ${s.border} border`}>
            <Icon className={`w-2.5 h-2.5 ${s.color} ${worker.status === 'online' ? 'blink' : ''}`} />
            <span className={`text-xs font-medium ${s.color}`}>{s.label}</span>
          </div>
        </div>
      </div>

      <div className="space-y-2.5">
        <MetricBar label={`CPU — ${worker.cpu_cores} cores`} value={cpu} color="bg-primary" textColor="text-gray-400" />
        <MetricBar label={`RAM — ${fmt(worker.ram_total, 1)} GB`} value={worker.ram_usage} color="bg-secondary" textColor="text-gray-400" />
        <MetricBar label="Disk" value={worker.disk_usage} color="bg-accent" textColor="text-gray-400" />
      </div>

      <div className="flex justify-between text-xs text-gray-500 pt-2.5 border-t border-white/5 mt-2.5">
        <span>{worker.running_tasks || 0} running task{worker.running_tasks !== 1 ? 's' : ''}</span>
        <span className="text-emerald-400">⭐ {fmt((worker.reliability_score || 0) * 100, 0)}% reliable</span>
      </div>

      <div className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
        style={{ background: 'linear-gradient(135deg, rgba(59,130,246,0.03) 0%, transparent 100%)' }} />
    </div>
  );
}

// ─── Per-Worker Detail Modal ─────────────────────────────────────────────────
function WorkerDetailModal({ worker, token, onClose }) {
  const [history, setHistory] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!worker) return;
    setLoading(true);
    Promise.all([
      fetch(`${API}/workers/${worker.worker_uid}/history?hours=1`).then(r => r.json()),
      fetch(`${API}/workers/${worker.worker_uid}/tasks?limit=20`).then(r => r.json()),
    ]).then(([h, t]) => {
      setHistory(h.history || []);
      setTasks(t.tasks || []);
    }).catch(console.error).finally(() => setLoading(false));
  }, [worker]);

  if (!worker) return null;

  const s = STATUS_CONFIG[worker.status] || STATUS_CONFIG.offline;
  const SIcon = s.icon;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4 backdrop-in" onClick={onClose}>
      <div className="glass-panel w-full max-w-4xl max-h-[90vh] overflow-y-auto scale-in" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-xl ${s.bg} ${s.border} border`}>
              <Server className={`w-5 h-5 ${s.color}`} />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{worker.hostname || 'Worker Node'}</h2>
              <p className="text-xs text-gray-400 font-mono">{worker.worker_uid}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full ${s.bg} ${s.border} border`}>
              <SIcon className={`w-3.5 h-3.5 ${s.color}`} />
              <span className={`text-xs font-semibold ${s.color} uppercase`}>{s.label}</span>
            </div>
            <button id="worker-modal-close" onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* Hardware Info */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'CPU Cores', value: worker.cpu_cores, icon: Cpu },
              { label: 'RAM Total', value: `${fmt(worker.ram_total, 1)} GB`, icon: HardDrive },
              { label: 'Reliability', value: `${fmt((worker.reliability_score || 0) * 100, 0)}%`, icon: Shield },
              { label: 'Tasks Done', value: worker.total_tasks_completed || 0, icon: CheckCircle },
            ].map(({ label, value, icon: Icon }) => (
              <div key={label} className="bg-white/5 rounded-xl p-3 text-center">
                <Icon className="w-4 h-4 text-primary mx-auto mb-1" />
                <p className="text-white font-bold text-lg">{value}</p>
                <p className="text-gray-500 text-xs">{label}</p>
              </div>
            ))}
          </div>

          {/* Live Charts */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-primary" /> Resource History (last hour)
            </h3>
            {loading ? (
              <div className="h-48 bg-white/5 rounded-xl shimmer" />
            ) : history.length > 0 ? (
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={history}>
                    <defs>
                      <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                    <XAxis dataKey="timestamp" stroke="#4B5563" tick={false} />
                    <YAxis stroke="#4B5563" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6B7280' }} />
                    <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                    <Legend wrapperStyle={{ fontSize: '12px' }} />
                    <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#3B82F6" fill="url(#cpuGrad)" strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="ram" name="RAM %" stroke="#10B981" fill="url(#ramGrad)" strokeWidth={2} dot={false} />
                    <Area type="monotone" dataKey="disk" name="Disk %" stroke="#8B5CF6" fill="none" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="h-48 flex items-center justify-center text-gray-500 bg-white/5 rounded-xl text-sm">
                No metrics history yet
              </div>
            )}
          </div>

          {/* Task History */}
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3 flex items-center gap-2">
              <Terminal className="w-4 h-4 text-secondary" /> Recent Task History
            </h3>
            {loading ? (
              <div className="space-y-2">{[...Array(4)].map((_, i) => <div key={i} className="h-10 bg-white/5 rounded-lg shimmer" />)}</div>
            ) : tasks.length > 0 ? (
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {tasks.map(t => {
                  const statusColor = { completed: 'text-emerald-400', failed: 'text-red-400', assigned: 'text-blue-400', running: 'text-yellow-400', pending: 'text-gray-400' };
                  return (
                    <div key={t.chunk_id} className="flex items-center justify-between bg-white/3 hover:bg-white/6 rounded-lg px-3 py-2 text-xs transition-colors">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-gray-400">#{t.chunk_id}</span>
                        <span className={`font-semibold ${statusColor[t.status] || 'text-gray-400'}`}>{t.status}</span>
                        {t.job_name && <span className="text-gray-500 truncate max-w-[120px]">{t.job_name}</span>}
                      </div>
                      <div className="flex items-center gap-2 text-gray-500">
                        {t.execution_time_seconds != null && <span>{fmt(t.execution_time_seconds, 2)}s</span>}
                        {t.attempt_count > 1 && <span className="text-yellow-400">retry×{t.attempt_count}</span>}
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-center text-gray-500 text-sm py-6 bg-white/5 rounded-xl">No tasks executed yet</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Job Detail Modal ────────────────────────────────────────────────────────
function JobDetailModal({ job, onClose }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!job) return;
    fetch(`${API}/jobs/${job.id}/result`).then(r => r.json()).then(setResult).catch(console.error).finally(() => setLoading(false));
  }, [job]);

  if (!job) return null;
  const pct = job.total_tasks > 0 ? Math.round(((job.completed_tasks + job.failed_tasks) / job.total_tasks) * 100) : 0;
  const statusColors = { pending: 'text-gray-400', running: 'text-blue-400', completed: 'text-emerald-400', failed: 'text-red-400' };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4 backdrop-in" onClick={onClose}>
      <div className="glass-panel w-full max-w-2xl max-h-[85vh] overflow-y-auto scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-6 border-b border-white/10">
          <div>
            <h2 className="text-xl font-bold text-white">{job.name}</h2>
            <p className="text-xs text-gray-400">Job #{job.id} · {job.job_type}</p>
          </div>
          <div className="flex items-center gap-3">
            <span className={`text-sm font-semibold capitalize ${statusColors[job.status]}`}>{job.status}</span>
            <button id="job-modal-close" onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-5">
          {/* Progress */}
          <div>
            <div className="flex justify-between text-xs text-gray-400 mb-2">
              <span>Progress</span><span>{pct}%</span>
            </div>
            <div className="w-full bg-white/5 rounded-full h-2">
              <div className={`h-2 rounded-full transition-all duration-700 ${job.status === 'completed' ? 'bg-emerald-500' : job.status === 'failed' ? 'bg-red-500' : 'bg-primary'}`}
                style={{ width: `${pct}%` }} />
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-emerald-400 font-bold text-xl">{job.completed_tasks}</p>
              <p className="text-gray-500 text-xs">Completed</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-red-400 font-bold text-xl">{job.failed_tasks}</p>
              <p className="text-gray-500 text-xs">Failed</p>
            </div>
            <div className="bg-white/5 rounded-xl p-3 text-center">
              <p className="text-white font-bold text-xl">{job.total_tasks}</p>
              <p className="text-gray-500 text-xs">Total Chunks</p>
            </div>
          </div>

          {/* Timing */}
          <div className="bg-white/5 rounded-xl p-4 space-y-2 text-xs">
            <div className="flex justify-between"><span className="text-gray-400">Submitted</span><span className="text-white">{fmtTime(job.submission_time)}</span></div>
            {job.start_time && <div className="flex justify-between"><span className="text-gray-400">Started</span><span className="text-white">{fmtTime(job.start_time)}</span></div>}
            {job.end_time && <div className="flex justify-between"><span className="text-gray-400">Completed</span><span className="text-white">{fmtTime(job.end_time)}</span></div>}
            {result && result.total_execution_time_seconds != null && (
              <div className="flex justify-between border-t border-white/5 pt-2">
                <span className="text-gray-400">Wall-clock time</span>
                <span className="text-primary font-semibold">{fmt(result.total_execution_time_seconds, 3)}s</span>
              </div>
            )}
          </div>

          {/* Aggregated Result */}
          {loading ? (
            <div className="h-24 bg-white/5 rounded-xl shimmer" />
          ) : result?.aggregated_result ? (
            <div>
              <p className="text-xs text-gray-400 mb-2 font-medium uppercase tracking-wider">Aggregated Result</p>
              <pre className="bg-black/40 rounded-xl p-4 text-xs text-gray-300 overflow-auto max-h-48 font-mono">
                {JSON.stringify(result.aggregated_result, null, 2)}
              </pre>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

// ─── Submit Job Modal ────────────────────────────────────────────────────────
function SubmitJobModal({ show, onClose, token }) {
  const [jobType, setJobType] = useState('prime_generation');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [loading, setLoading] = useState(false);

  const TYPES = {
    prime_generation: {
      label: 'Prime Generation',
      icon: '🔢',
      desc: 'Find prime numbers in a numeric range using parallel sieves',
      defaults: { start: 1, end: 1000000, chunks: 20 }
    },
    matrix_multiply: {
      label: 'Matrix Multiply',
      icon: '🧮',
      desc: 'Distributed matrix multiplication (row-based parallel split)',
      defaults: { rows_a: 50, cols_a: 50, cols_b: 50, chunks: 10 }
    },
    word_count: {
      label: 'Word Count',
      icon: '📝',
      desc: 'MapReduce-style distributed word frequency analysis',
      defaults: { text: 'CoCompute is a distributed computing platform that aggregates idle computational resources from multiple devices into a unified computational network for intelligent resource sharing and parallel task execution across heterogeneous hardware environments', chunks: 5 }
    },
    generic_python: {
      label: 'Generic Python',
      icon: '🐍',
      desc: 'Custom Python script with arbitrary data chunks',
      defaults: { script: "import sys, json\ndata = json.loads(sys.argv[1])\nresult = sum(data['numbers'])\nprint(json.dumps({'sum': result}))", data_chunks: [{ numbers: [1, 2, 3] }, { numbers: [4, 5, 6] }] }
    }
  };

  const submit = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/jobs/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ name: name || `${TYPES[jobType].label} Job`, description: desc || TYPES[jobType].desc, job_type: jobType, params: TYPES[jobType].defaults })
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      onClose(); setName(''); setDesc('');
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  if (!show) return null;
  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4 backdrop-in" onClick={onClose}>
      <div className="glass-panel p-6 w-full max-w-lg space-y-5 scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2"><Play className="w-5 h-5 text-primary" /> Submit New Job</h2>
          <button id="submit-job-close" onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition text-gray-400"><X className="w-4 h-4" /></button>
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider">Job Name</label>
          <input id="job-name" value={name} onChange={e => setName(e.target.value)} placeholder={`${TYPES[jobType].label} Job`}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-primary transition text-sm" />
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider">Job Type</label>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(TYPES).map(([type, info]) => (
              <button key={type} id={`job-type-${type}`} onClick={() => setJobType(type)}
                className={`px-3 py-2.5 rounded-xl text-sm font-medium border transition-all duration-200 text-left flex items-center gap-2 ${jobType === type ? 'bg-primary/15 border-primary/50 text-primary' : 'bg-white/3 border-white/10 text-gray-300 hover:border-white/20'}`}>
                <span>{info.icon}</span> {info.label}
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-500 mt-2">{TYPES[jobType].desc}</p>
        </div>

        <div>
          <label className="text-xs text-gray-400 mb-2 block uppercase tracking-wider">Parameters (read-only preview)</label>
          <pre className="bg-black/30 rounded-xl p-3 text-xs text-gray-400 overflow-auto max-h-28 font-mono border border-white/5">
            {JSON.stringify(TYPES[jobType].defaults, null, 2)}
          </pre>
        </div>

        <div className="flex gap-3 pt-1">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition font-medium text-sm">Cancel</button>
          <button id="job-submit-btn" onClick={submit} disabled={loading}
            className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-blue-500 text-white font-semibold shadow-lg shadow-primary/20 transition flex items-center justify-center gap-2 disabled:opacity-50 text-sm glow-primary">
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />} Submit
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Scheduler Config Panel ──────────────────────────────────────────────────
function SchedulerPanel({ currentAlgo, onClose }) {
  const [algo, setAlgo] = useState(currentAlgo || 'resource_aware');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const ALGOS = [
    { id: 'round_robin', label: 'Round Robin', icon: '🔄', desc: 'Simple rotation — each worker gets one chunk in order. Best for uniform workloads.' },
    { id: 'resource_aware', label: 'Resource Aware', icon: '⚖️', desc: 'Scores workers by CPU cores, RAM, reliability, and current load. Best for heterogeneous clusters.' },
    { id: 'ai_predictive', label: 'AI Predictive', icon: '🧠', desc: 'Random Forest model predicts fastest worker based on historical performance. Best after training data accumulates.' },
  ];

  const apply = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API.replace('/api/v1', '')}/api/v1/scheduler/config`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ algorithm: algo })
      });
      if (!res.ok) throw new Error('Failed');
      setSuccess(true); setTimeout(() => { setSuccess(false); onClose(); }, 1200);
    } catch { alert('Failed to update scheduler'); }
    finally { setLoading(false); }
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4 backdrop-in" onClick={onClose}>
      <div className="glass-panel p-6 w-full max-w-md space-y-5 scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center gap-2"><Sliders className="w-5 h-5 text-accent" /> Scheduler Config</h2>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-white/10 transition text-gray-400"><X className="w-4 h-4" /></button>
        </div>
        <p className="text-xs text-gray-400">Select the active scheduling algorithm. Changes take effect on the next scheduler cycle.</p>

        <div className="space-y-2">
          {ALGOS.map(a => (
            <button key={a.id} id={`algo-${a.id}`} onClick={() => setAlgo(a.id)}
              className={`w-full text-left px-4 py-3 rounded-xl border transition-all duration-200 ${algo === a.id ? 'bg-accent/15 border-accent/50' : 'bg-white/3 border-white/10 hover:border-white/20'}`}>
              <div className="flex items-center gap-2 mb-1">
                <span>{a.icon}</span>
                <span className={`font-semibold text-sm ${algo === a.id ? 'text-accent' : 'text-white'}`}>{a.label}</span>
                {algo === a.id && <span className="ml-auto text-xs bg-accent/20 text-accent px-2 py-0.5 rounded-full">Active</span>}
              </div>
              <p className="text-xs text-gray-500">{a.desc}</p>
            </button>
          ))}
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-white/10 text-gray-300 hover:bg-white/5 transition text-sm">Cancel</button>
          <button id="scheduler-apply" onClick={apply} disabled={loading || algo === currentAlgo}
            className={`flex-1 py-2.5 rounded-xl font-semibold text-sm transition flex items-center justify-center gap-2 disabled:opacity-50 ${success ? 'bg-emerald-500 text-white' : 'bg-accent hover:bg-violet-500 text-white shadow-lg shadow-accent/20'}`}>
            {success ? <><CheckCircle className="w-4 h-4" /> Applied!</> : loading ? <Loader className="w-4 h-4 animate-spin" /> : 'Apply'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Alert Item ──────────────────────────────────────────────────────────────
function AlertItem({ alert, onDismiss }) {
  const sev = SEVERITY[alert.severity] || SEVERITY.info;
  const Icon = sev.icon;
  return (
    <div className={`flex items-start gap-3 p-3 rounded-xl border ${sev.bg} ${sev.border} slide-in-right`}>
      <Icon className={`w-4 h-4 ${sev.text} flex-shrink-0 mt-0.5`} />
      <div className="flex-1 min-w-0">
        <p className="text-xs text-white font-medium leading-snug">{alert.message}</p>
        <p className="text-xs text-gray-500 mt-0.5">{fmtTime(alert.timestamp)}</p>
      </div>
      {onDismiss && (
        <button onClick={() => onDismiss(alert.id)} className="text-gray-500 hover:text-white transition flex-shrink-0">
          <X className="w-3.5 h-3.5" />
        </button>
      )}
    </div>
  );
}

// ─── Alerts Tray ─────────────────────────────────────────────────────────────
function AlertsTray({ alerts, show, onClose, onDismiss }) {
  const errors = alerts.filter(a => a.severity === 'error');
  const warnings = alerts.filter(a => a.severity === 'warning');

  if (!show) return null;
  return (
    <div className="fixed top-16 right-4 z-40 w-80 slide-in-right">
      <div className="glass-panel p-4 space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-4 h-4 text-primary" />
            <span className="text-sm font-semibold text-white">Active Alerts</span>
          </div>
          <div className="flex items-center gap-2">
            {errors.length > 0 && <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded-full border border-red-500/30">{errors.length} error{errors.length !== 1 ? 's' : ''}</span>}
            {warnings.length > 0 && <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded-full border border-yellow-500/30">{warnings.length} warn</span>}
            <button onClick={onClose} className="text-gray-400 hover:text-white transition"><X className="w-4 h-4" /></button>
          </div>
        </div>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {alerts.length === 0 ? (
            <div className="text-center text-gray-500 text-xs py-6 flex flex-col items-center gap-2">
              <CheckCircle className="w-8 h-8 text-emerald-400/50" />
              All systems healthy
            </div>
          ) : (
            alerts.map(a => <AlertItem key={a.id || a.type + a.timestamp} alert={a} onDismiss={onDismiss} />)
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Tooltip Charts (custom) ─────────────────────────────────────────────────
const ChartTooltipStyle = { backgroundColor: '#111827', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', color: '#fff', fontSize: '12px' };

// ─── MAIN APP ────────────────────────────────────────────────────────────────
function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  // Data state
  const [workers, setWorkers] = useState([]);
  const [cluster, setCluster] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [schedulerAlgo, setSchedulerAlgo] = useState('resource_aware');
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set());

  // UI state
  const [showSubmit, setShowSubmit] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [logLevel, setLogLevel] = useState('');
  const [logSearch, setLogSearch] = useState('');
  const [showAlerts, setShowAlerts] = useState(false);
  const [showScheduler, setShowScheduler] = useState(false);
  const [selectedWorker, setSelectedWorker] = useState(null);
  const [selectedJob, setSelectedJob] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');

  const wsRef = useRef(null);
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  // ── REST fallback fetch ──
  const fetchAll = useCallback(async () => {
    if (!token) return;
    try {
      const [wRes, cRes, jRes] = await Promise.all([
        fetch(`${API}/workers/`), fetch(`${API}/metrics/cluster`), fetch(`${API}/jobs/`)
      ]);
      if (wRes.ok) setWorkers(await wRes.json());
      if (cRes.ok) setCluster(await cRes.json());
      if (jRes.ok) setJobs(await jRes.json());

      const [spRes, rkRes, logRes, alRes, scRes] = await Promise.all([
        fetch(`${API}/analytics/speedup`),
        fetch(`${API}/analytics/workers/ranking`),
        fetch(`${API}/logs/?limit=200`),
        fetch(`${API}/alerts/`),
        fetch(`${API.replace('/api/v1', '')}/api/v1/scheduler/config`),
      ]);
      if (spRes.ok) { const d = await spRes.json(); setAnalytics(d); }
      if (rkRes.ok) { const d = await rkRes.json(); setRankings(d.rankings || []); }
      if (logRes.ok) { const d = await logRes.json(); setLogs(d.logs || []); }
      if (alRes.ok) { const d = await alRes.json(); setAlerts(d.alerts || []); }
      if (scRes.ok) { const d = await scRes.json(); setSchedulerAlgo(d.algorithm); }
    } catch (e) { console.error('Fetch error:', e); }
  }, [token]);

  // ── WebSocket live push ──
  useEffect(() => {
    if (!token) return;
    let reconnectTimeout;

    const connectWs = () => {
      const wsUrl = `${WS_BASE}/ws/live`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => { setWsStatus('connected'); console.log('[WS] Connected to /ws/live'); };
      ws.onclose = () => {
        setWsStatus('reconnecting');
        reconnectTimeout = setTimeout(connectWs, 5000);
      };
      ws.onerror = () => setWsStatus('error');

      ws.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data);
          if (data.type === 'CLUSTER_UPDATE') {
            setCluster(data.cluster);
            setWorkers(data.workers || []);
            setAlerts(data.alerts || []);
            if (data.scheduler_algorithm) setSchedulerAlgo(data.scheduler_algorithm);
          }
        } catch (err) { console.error('WS parse error', err); }
      };
    };

    connectWs();

    // Keep REST polling for jobs/analytics/logs (not pushed via WS)
    fetchAll();
    const iv = setInterval(fetchAll, 8000);

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
      clearInterval(iv);
    };
  }, [token, fetchAll]);

  // ── Auth check on mount ──
  useEffect(() => {
    if (!token) return;
    fetch(`${API}/auth/me`, { headers }).then(r => {
      if (r.ok) r.json().then(setUser);
      else { setToken(null); localStorage.removeItem('token'); }
    }).catch(() => {});
  }, [token]);

  if (!token) return <AuthScreen onAuth={(u, t) => { setUser(u); setToken(t); }} />;

  const c = cluster || {};
  const taskStats = c.tasks || {};
  const jobStats = c.jobs || {};
  const onlineW = workers.filter(w => w.status === 'online');
  const activeAlerts = alerts.filter(a => !dismissedAlerts.has(a.id || a.type + a.timestamp));
  const errorCount = activeAlerts.filter(a => a.severity === 'error').length;

  const TABS = [
    { id: 'overview',  label: 'Overview',  icon: Activity },
    { id: 'tasks',     label: 'Tasks',     icon: Clock },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'workers',   label: 'Workers',   icon: Server },
    { id: 'alerts',    label: 'Alerts',    icon: Bell, badge: errorCount || null },
    { id: 'logs',      label: 'Logs',      icon: FileText },
  ];

  const pieData = [
    { name: 'Completed', value: taskStats.completed || 0, fill: '#10B981' },
    { name: 'Running',   value: taskStats.running   || 0, fill: '#3B82F6' },
    { name: 'Failed',    value: taskStats.failed    || 0, fill: '#EF4444' },
    { name: 'Pending',   value: taskStats.pending   || 0, fill: '#6B7280' },
  ].filter(d => d.value > 0);

  return (
    <div className="min-h-screen bg-background">
      {/* ── Header ── */}
      <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-[1700px] mx-auto px-5 py-3 flex justify-between items-center">
          {/* Logo */}
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
              <Zap className="text-primary w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold gradient-text">CoCompute</h1>
            {/* WS status indicator */}
            <div className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${wsStatus === 'connected' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-400 blink' : 'bg-yellow-400'}`} />
              {wsStatus === 'connected' ? 'Live' : 'Polling'}
            </div>
          </div>

          {/* Nav */}
          <nav className="flex gap-0.5 bg-white/5 rounded-xl p-1">
            {TABS.map(t => (
              <button key={t.id} id={`tab-${t.id}`} onClick={() => setActiveTab(t.id)}
                className={`relative flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition-all duration-200 ${activeTab === t.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                <t.icon className="w-3.5 h-3.5" /> {t.label}
                {t.badge && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center alert-pulse">
                    {t.badge}
                  </span>
                )}
              </button>
            ))}
          </nav>

          {/* Actions */}
          <div className="flex items-center gap-2">
            {/* Scheduler toggle */}
            <button id="scheduler-btn" onClick={() => setShowScheduler(true)}
              className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 text-gray-400 hover:text-white transition text-xs font-medium">
              <Sliders className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">{schedulerAlgo.replace('_', ' ')}</span>
            </button>

            {/* Alert bell */}
            <button id="alerts-btn" onClick={() => setShowAlerts(v => !v)}
              className={`relative p-2 rounded-xl border transition ${errorCount > 0 ? 'bg-red-500/10 border-red-500/20 text-red-400 hover:bg-red-500/20' : 'bg-white/5 border-white/10 text-gray-400 hover:text-white hover:border-white/20'}`}>
              <Bell className={`w-4 h-4 ${errorCount > 0 ? 'alert-pulse' : ''}`} />
              {activeAlerts.length > 0 && (
                <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
                  {activeAlerts.length}
                </span>
              )}
            </button>

            {/* Submit job */}
            <button id="submit-job-btn" onClick={() => setShowSubmit(true)}
              className="bg-primary hover:bg-blue-500 transition text-white px-4 py-2 rounded-xl flex items-center gap-2 font-semibold shadow-lg shadow-primary/20 text-xs glow-primary">
              <Play className="w-3.5 h-3.5 fill-current" /> Submit Job
            </button>

            {/* User badge */}
            <div className="flex items-center gap-1.5 px-3 py-2 bg-white/5 rounded-xl border border-white/10 text-xs text-gray-400">
              <Shield className="w-3.5 h-3.5" />
              <span>{user?.username}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Alerts tray */}
      <AlertsTray
        alerts={activeAlerts}
        show={showAlerts}
        onClose={() => setShowAlerts(false)}
        onDismiss={(id) => setDismissedAlerts(prev => new Set([...prev, id]))}
      />

      <main className="max-w-[1700px] mx-auto px-5 py-5 space-y-5">

        {/* ══ OVERVIEW TAB ══════════════════════════════════════════════════ */}
        {activeTab === 'overview' && (
          <>
            {/* Stat grid */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <StatCard label="Total Nodes"   value={c.total_nodes   || 0}                           icon={Server}    />
              <StatCard label="Online"         value={c.online_nodes  || 0}                           icon={Wifi}      color="text-emerald-400" />
              <StatCard label="Offline"        value={c.offline_nodes || 0}                           icon={WifiOff}   color="text-red-400" />
              <StatCard label="Active Cores"   value={c.active_cores  || 0}                           icon={Cpu}       color="text-accent" />
              <StatCard label="RAM Pool"       value={`${c.aggregated_ram || 0} GB`}                  icon={HardDrive} color="text-primary" />
              <StatCard label="Efficiency"     value={`${c.efficiency || 0}%`}                        icon={Gauge}     color="text-emerald-400" />
            </div>

            {/* Charts row */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Resource history */}
              <div className="glass-panel p-5 lg:col-span-2">
                <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" /> Cluster Resource Utilization
                </h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={c.history || []}>
                      <defs>
                        <linearGradient id="cpuArea" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.25}/><stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="ramArea" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10B981" stopOpacity={0.25}/><stop offset="95%" stopColor="#10B981" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="timestamp" stroke="#4B5563" tick={false} />
                      <YAxis stroke="#4B5563" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6B7280' }} />
                      <Tooltip contentStyle={ChartTooltipStyle} />
                      <Area type="monotone" dataKey="cpu"  name="CPU %"  stroke="#3B82F6" fill="url(#cpuArea)" strokeWidth={2} dot={false} />
                      <Area type="monotone" dataKey="ram"  name="RAM %"  stroke="#10B981" fill="url(#ramArea)" strokeWidth={2} dot={false} />
                      <Area type="monotone" dataKey="disk" name="Disk %" stroke="#F59E0B" fill="none" strokeWidth={1.5} dot={false} strokeDasharray="4 2" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Task pie */}
              <div className="glass-panel p-5">
                <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                  <Layers className="w-4 h-4 text-secondary" /> Task Distribution
                </h2>
                {pieData.length > 0 ? (
                  <div className="h-48">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={3}>
                          {pieData.map((entry, i) => <Cell key={i} fill={entry.fill} />)}
                        </Pie>
                        <Tooltip contentStyle={ChartTooltipStyle} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <div className="h-48 flex items-center justify-center text-gray-500 text-sm">No tasks yet</div>
                )}
                <div className="grid grid-cols-2 gap-2 mt-3">
                  {[
                    { label: 'Completed', val: taskStats.completed || 0, color: 'text-emerald-400' },
                    { label: 'Running',   val: taskStats.running   || 0, color: 'text-blue-400' },
                    { label: 'Failed',    val: taskStats.failed    || 0, color: 'text-red-400' },
                    { label: 'Queued',    val: taskStats.pending   || 0, color: 'text-gray-400' },
                  ].map(({ label, val, color }) => (
                    <div key={label} className="text-center">
                      <p className={`text-xl font-bold ${color}`}>{val}</p>
                      <p className="text-xs text-gray-500">{label}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Worker grid */}
            <div className="glass-panel p-5">
              <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                <Server className="w-4 h-4" /> Worker Nodes ({workers.length})
                {onlineW.length > 0 && <span className="ml-auto text-xs text-emerald-400">{onlineW.length} online</span>}
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3 relative">
                {workers.map(w => <WorkerCard key={w.id} worker={w} onClick={setSelectedWorker} />)}
                {workers.length === 0 && (
                  <div className="col-span-full flex flex-col items-center justify-center py-16 text-gray-500">
                    <Server className="w-12 h-12 mb-3 opacity-20" />
                    <p className="text-sm">No workers registered yet</p>
                    <p className="text-xs mt-1">Start a worker node to join the cluster</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* ══ TASKS TAB ══════════════════════════════════════════════════════ */}
        {activeTab === 'tasks' && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Total Jobs"   value={jobStats.total     || 0} icon={BarChart3}   />
              <StatCard label="Running"      value={jobStats.running   || 0} icon={Loader}       color="text-blue-400" />
              <StatCard label="Completed"    value={jobStats.completed || 0} icon={CheckCircle}  color="text-emerald-400" />
              <StatCard label="Queue Length" value={taskStats.queue_length || 0} icon={Clock}   color="text-yellow-400" />
            </div>

            <div className="glass-panel overflow-hidden">
              <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Job Queue</h2>
                <button onClick={fetchAll} className="p-1.5 rounded-lg hover:bg-white/10 transition text-gray-400 hover:text-white">
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>
              <table className="w-full">
                <thead>
                  <tr className="border-b border-white/8 text-left text-xs text-gray-500 uppercase tracking-wider">
                    {['ID', 'Name', 'Type', 'Status', 'Progress', 'Chunks', 'Submitted'].map(h => (
                      <th key={h} className="px-5 py-3">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {jobs.map(j => {
                    const pct = j.total_tasks > 0 ? Math.round(((j.completed_tasks + j.failed_tasks) / j.total_tasks) * 100) : 0;
                    const sc = { pending: 'text-gray-400', running: 'text-blue-400', completed: 'text-emerald-400', failed: 'text-red-400' };
                    return (
                      <tr key={j.id} id={`job-row-${j.id}`} onClick={() => setSelectedJob(j)}
                        className="border-b border-white/5 hover:bg-white/5 transition text-xs cursor-pointer">
                        <td className="px-5 py-3 text-gray-400 font-mono">#{j.id}</td>
                        <td className="px-5 py-3 text-white font-medium">{j.name}</td>
                        <td className="px-5 py-3">
                          <span className="bg-white/5 text-gray-400 px-2 py-0.5 rounded-full border border-white/10">{j.job_type}</span>
                        </td>
                        <td className="px-5 py-3">
                          <span className={`font-semibold capitalize ${sc[j.status] || 'text-gray-400'}`}>{j.status}</span>
                        </td>
                        <td className="px-5 py-3">
                          <div className="w-24 bg-white/5 rounded-full h-1.5">
                            <div className={`h-1.5 rounded-full ${j.status === 'completed' ? 'bg-emerald-500' : j.status === 'failed' ? 'bg-red-500' : 'bg-primary'}`}
                              style={{ width: `${pct}%` }} />
                          </div>
                        </td>
                        <td className="px-5 py-3 text-gray-400">{j.completed_tasks}/{j.total_tasks}</td>
                        <td className="px-5 py-3 text-gray-500">{fmtTime(j.submission_time)}</td>
                      </tr>
                    );
                  })}
                  {jobs.length === 0 && (
                    <tr><td colSpan={7} className="px-5 py-16 text-center text-gray-500">
                      <Clock className="w-10 h-10 mx-auto mb-3 opacity-20" />
                      <p>No jobs submitted yet</p>
                    </td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </>
        )}

        {/* ══ ANALYTICS TAB ══════════════════════════════════════════════════ */}
        {activeTab === 'analytics' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard label="Avg Speedup"      value={`${analytics?.avg_speedup?.toFixed(2)    || '0'}x`} icon={Zap}       color="text-accent" />
              <StatCard label="Avg Efficiency"   value={`${((analytics?.avg_efficiency||0)*100).toFixed(1)}%`} icon={TrendingUp} color="text-emerald-400" />
              <StatCard label="Cluster Efficiency" value={`${c.efficiency||0}%`}               icon={Gauge}     color="text-primary" />
            </div>

            {/* Algorithm tag */}
            <div className="glass-panel p-4 flex items-center gap-4">
              <div className="p-2 rounded-xl bg-accent/10 border border-accent/20">
                <Brain className="w-5 h-5 text-accent" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">Active Scheduler: <span className="text-accent capitalize">{schedulerAlgo.replace(/_/g, ' ')}</span></p>
                <p className="text-xs text-gray-500">FR-6 — Resource-aware scheduling with FR-14 high-utilization guard (85% CPU / 90% RAM threshold)</p>
              </div>
              <button onClick={() => setShowScheduler(true)}
                className="ml-auto text-xs px-3 py-1.5 rounded-lg bg-accent/10 border border-accent/20 text-accent hover:bg-accent/20 transition">
                Change
              </button>
            </div>

            {/* Speedup chart */}
            {analytics?.per_job?.length > 0 && (
              <div className="glass-panel p-5">
                <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                  <Zap className="w-4 h-4 text-accent" /> Speedup per Job
                </h2>
                <div className="h-60">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={analytics.per_job}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="job_name" stroke="#4B5563" tick={{ fontSize: 10, fill: '#6B7280' }} />
                      <YAxis stroke="#4B5563" tick={{ fontSize: 10, fill: '#6B7280' }} />
                      <Tooltip contentStyle={ChartTooltipStyle} />
                      <Bar dataKey="speedup" name="Speedup (×)" fill="#8B5CF6" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Worker rankings table */}
            {rankings.length > 0 && (
              <div className="glass-panel overflow-hidden">
                <div className="px-5 py-4 border-b border-white/10">
                  <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                    <TrendingUp className="w-4 h-4" /> Worker Performance Rankings
                  </h2>
                </div>
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/8 text-left text-xs text-gray-500 uppercase tracking-wider">
                      {['Rank', 'Worker', 'Status', 'Done', 'Failed', 'Reliability', 'Avg Time', 'Score'].map(h => (
                        <th key={h} className="px-5 py-3">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {rankings.map((r, i) => (
                      <tr key={r.worker_uid} className="border-b border-white/5 hover:bg-white/5 transition text-xs">
                        <td className="px-5 py-3 text-gray-400">#{i + 1}</td>
                        <td className="px-5 py-3 text-white font-medium">{r.hostname}</td>
                        <td className="px-5 py-3"><span className={`text-xs font-semibold uppercase ${r.status === 'online' ? 'text-emerald-400' : 'text-red-400'}`}>{r.status}</span></td>
                        <td className="px-5 py-3 text-emerald-400">{r.tasks_completed}</td>
                        <td className="px-5 py-3 text-red-400">{r.tasks_failed}</td>
                        <td className="px-5 py-3 text-gray-300">{(r.reliability_score * 100).toFixed(0)}%</td>
                        <td className="px-5 py-3 text-gray-300">{r.avg_execution_seconds.toFixed(2)}s</td>
                        <td className="px-5 py-3 text-primary font-bold">{r.composite_score}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* ══ WORKERS TAB ═══════════════════════════════════════════════════ */}
        {activeTab === 'workers' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard label="Online Workers"  value={onlineW.length}                       icon={Wifi}  color="text-emerald-400" />
              <StatCard label="Offline Workers" value={workers.filter(w=>w.status!=='online').length} icon={WifiOff} color="text-red-400" />
              <StatCard label="Total Cores"     value={c.active_cores || 0}                  icon={Cpu}   color="text-primary" />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
              {workers.map(w => <WorkerCard key={w.id} worker={w} onClick={setSelectedWorker} />)}
              {workers.length === 0 && (
                <div className="col-span-full glass-panel p-16 text-center text-gray-500">
                  <Server className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p className="text-sm">No workers registered. Start a worker node to begin.</p>
                </div>
              )}
            </div>
          </>
        )}

        {/* ══ ALERTS TAB ════════════════════════════════════════════════════ */}
        {activeTab === 'alerts' && (
          <>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard label="Total Alerts"   value={activeAlerts.length}                                    icon={Bell}          />
              <StatCard label="Errors"         value={activeAlerts.filter(a=>a.severity==='error').length}     icon={XCircle}       color="text-red-400" />
              <StatCard label="Warnings"       value={activeAlerts.filter(a=>a.severity==='warning').length}   icon={AlertTriangle} color="text-yellow-400" />
            </div>

            <div className="glass-panel p-5 space-y-3">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Bell className="w-4 h-4 text-primary" /> Active Cluster Alerts (FR-15)
                </h2>
                <button onClick={fetchAll} className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition">
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
              </div>

              {activeAlerts.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-gray-500">
                  <CheckCircle className="w-12 h-12 mb-3 text-emerald-400/40" />
                  <p className="text-sm">All systems healthy — no active alerts</p>
                  <p className="text-xs mt-1 text-gray-600">Alerts appear here when workers disconnect, jobs fail, or SLA is breached</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {activeAlerts.map((a, i) => (
                    <AlertItem key={a.id || i} alert={a}
                      onDismiss={(id) => setDismissedAlerts(prev => new Set([...prev, id]))} />
                  ))}
                </div>
              )}

              {/* Alert legend */}
              <div className="border-t border-white/5 pt-3 mt-3">
                <p className="text-xs text-gray-600 mb-2">Alert Types</p>
                <div className="grid grid-cols-2 gap-2 text-xs text-gray-500">
                  <div className="flex items-center gap-1.5"><XCircle className="w-3.5 h-3.5 text-red-400" /> Worker Disconnection</div>
                  <div className="flex items-center gap-1.5"><XCircle className="w-3.5 h-3.5 text-red-400" /> Job Failure</div>
                  <div className="flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-yellow-400" /> SLA Breach (&gt;5 min)</div>
                  <div className="flex items-center gap-1.5"><AlertTriangle className="w-3.5 h-3.5 text-yellow-400" /> High Utilization (FR-14)</div>
                </div>
              </div>
            </div>
          </>
        )}

        {/* ══ LOGS TAB ═══════════════════════════════════════════════════════ */}
        {activeTab === 'logs' && (() => {
          const filteredLogs = logs.filter(log => {
            if (logLevel && log.level !== logLevel) return false;
            if (logSearch && !log.source?.toLowerCase().includes(logSearch.toLowerCase()) && !log.message?.toLowerCase().includes(logSearch.toLowerCase())) return false;
            return true;
          });
          const levelCls = {
            INFO:     'bg-blue-500/10 text-blue-400 border-blue-500/20',
            WARNING:  'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
            ERROR:    'bg-red-500/10 text-red-400 border-red-500/20',
            CRITICAL: 'bg-red-600/15 text-red-300 border-red-600/30',
          };
          return (
            <>
              <div className="flex flex-wrap gap-2 items-center">
                <div className="flex gap-1 bg-white/5 rounded-xl p-1">
                  {['', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'].map(level => (
                    <button key={level} id={`log-level-${level || 'all'}`} onClick={() => setLogLevel(level)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 ${logLevel === level ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white'}`}>
                      {level || 'ALL'}
                    </button>
                  ))}
                </div>
                <div className="flex-1 min-w-[200px] relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" />
                  <input id="log-search" value={logSearch} onChange={e => setLogSearch(e.target.value)} placeholder="Search logs..."
                    className="w-full bg-white/5 border border-white/10 rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder-gray-500 outline-none focus:ring-2 focus:ring-primary transition" />
                </div>
                <button onClick={fetchAll} className="px-3 py-2 rounded-xl bg-white/5 border border-white/10 text-gray-400 hover:text-white hover:border-white/20 transition flex items-center gap-1.5 text-xs">
                  <RefreshCw className="w-3.5 h-3.5" /> Refresh
                </button>
                <span className="text-xs text-gray-500">{filteredLogs.length} entries</span>
              </div>

              <div className="glass-panel overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-white/8 text-left text-xs text-gray-500 uppercase tracking-wider">
                      {['Timestamp', 'Level', 'Source', 'Message'].map(h => (
                        <th key={h} className="px-5 py-3">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredLogs.map(log => (
                      <tr key={log.id} className="border-b border-white/5 hover:bg-white/5 transition text-xs">
                        <td className="px-5 py-2.5 text-gray-500 whitespace-nowrap">{fmtTime(log.timestamp)}</td>
                        <td className="px-5 py-2.5">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border ${levelCls[log.level] || 'bg-gray-500/10 text-gray-400 border-gray-500/20'}`}>{log.level}</span>
                        </td>
                        <td className="px-5 py-2.5 text-gray-300 font-mono">{log.source}</td>
                        <td className="px-5 py-2.5 text-gray-300">{log.message}</td>
                      </tr>
                    ))}
                    {filteredLogs.length === 0 && (
                      <tr><td colSpan={4} className="px-5 py-16 text-center text-gray-500">
                        <FileText className="w-10 h-10 mx-auto mb-3 opacity-20" />
                        <p>No log entries found</p>
                      </td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </>
          );
        })()}
      </main>

      {/* ── Modals ── */}
      <SubmitJobModal show={showSubmit} onClose={() => setShowSubmit(false)} token={token} />
      {showScheduler && <SchedulerPanel currentAlgo={schedulerAlgo} onClose={() => { setShowScheduler(false); fetchAll(); }} />}
      {selectedWorker && <WorkerDetailModal worker={selectedWorker} token={token} onClose={() => setSelectedWorker(null)} />}
      {selectedJob   && <JobDetailModal   job={selectedJob}         onClose={() => setSelectedJob(null)} />}
    </div>
  );
}

export default App;
