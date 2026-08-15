import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, Server, Zap, HardDrive, Cpu, Play, Brain, TrendingUp,
  AlertTriangle, CheckCircle, XCircle, Clock, BarChart3, Users,
  Shield, Wifi, WifiOff, Loader, LogIn, UserPlus, ChevronDown,
  FileText, Search, RefreshCw, Bell, BellOff, X, Settings,
  ChevronRight, Terminal, Network, Database, Layers, Eye,
  ArrowUpRight, ArrowDownRight, Gauge, Sliders, Info, AlertCircle,
  Download, FileDown, History, GitCommit, FolderGit2, Award, FileCode, CheckSquare
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
  suspected:{ color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/20', icon: AlertTriangle, label: 'Suspected' },
};

function fmt(n, dec = 1) { return n != null ? Number(n).toFixed(dec) : '—'; }
function fmtTime(iso) { return iso ? new Date(iso).toLocaleString() : '—'; }

// ─── Auth Screen ─────────────────────────────────────────────────────────────
function AuthScreen({ onAuth }) {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('researcher');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const body = isLogin ? { username, password } : { username, email, password, role };
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
          <p className="text-gray-400 text-sm">Enterprise Distributed Computing Platform</p>
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
            <>
              <input id="auth-email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" type="email"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:ring-2 focus:ring-primary outline-none transition" required />
              <div>
                <label className="text-xs text-gray-400 mb-1 block uppercase">Institutional Role</label>
                <select value={role} onChange={e => setRole(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:ring-2 focus:ring-primary transition">
                  <option value="student" className="bg-[#18181c]">Student (2 jobs, 5 workers, CPU only)</option>
                  <option value="researcher" className="bg-[#18181c]">Researcher (5 jobs, 20 workers, 4 GPUs)</option>
                  <option value="faculty" className="bg-[#18181c]">Faculty (10 jobs, 50 workers, 8 GPUs)</option>
                  <option value="admin" className="bg-[#18181c]">Administrator (Unlimited)</option>
                </select>
              </div>
            </>
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

// ─── Stat Card ───────────────────────────────────────────────────────────────
function StatCard({ label, value, sub, icon: Icon, color = "text-white" }) {
  return (
    <div className="glass-panel p-4 flex flex-col justify-between relative overflow-hidden">
      <div className="flex justify-between items-start">
        <span className="text-xs text-gray-400 font-medium uppercase tracking-wider">{label}</span>
        {Icon && <Icon className={`w-4 h-4 ${color} opacity-80`} />}
      </div>
      <div className="mt-2">
        <span className={`text-2xl font-bold ${color}`}>{value}</span>
        {sub && <p className="text-[11px] text-gray-500 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

// ─── Worker Card ─────────────────────────────────────────────────────────────
function WorkerCard({ worker, onClick }) {
  const st = STATUS_CONFIG[worker.status] || STATUS_CONFIG.offline;
  const StIcon = st.icon;
  const cpu = worker.cpu_utilization || 0;
  const ram = worker.ram_usage || 0;
  const gpu = worker.gpu_utilization || 0;

  return (
    <div onClick={() => onClick(worker)}
      className="glass-panel p-4 cursor-pointer hover:border-primary/40 transition duration-200 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <StIcon className={`w-3.5 h-3.5 ${st.color}`} />
          <span className="font-semibold text-white text-sm truncate max-w-[140px]">{worker.hostname || worker.worker_uid}</span>
        </div>
        <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${st.bg} ${st.color} border ${st.border}`}>
          {st.label}
        </span>
      </div>

      <div className="space-y-1.5 text-xs text-gray-400">
        <div className="flex justify-between">
          <span>CPU ({worker.cpu_cores || 4} cores):</span>
          <span className="text-white font-mono">{cpu.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1">
          <div className="bg-primary h-1 rounded-full transition-all" style={{ width: `${Math.min(100, cpu)}%` }} />
        </div>

        <div className="flex justify-between">
          <span>RAM ({worker.ram_total || 8} GB):</span>
          <span className="text-white font-mono">{ram.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-white/5 rounded-full h-1">
          <div className="bg-purple-500 h-1 rounded-full transition-all" style={{ width: `${Math.min(100, ram)}%` }} />
        </div>

        {worker.gpu_count > 0 && (
          <>
            <div className="flex justify-between text-emerald-400">
              <span>GPU ({worker.gpu_model || 'CUDA'}):</span>
              <span className="font-mono">{gpu.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-white/5 rounded-full h-1">
              <div className="bg-emerald-500 h-1 rounded-full transition-all" style={{ width: `${Math.min(100, gpu)}%` }} />
            </div>
          </>
        )}
      </div>

      <div className="flex items-center justify-between text-[11px] text-gray-500 border-t border-white/5 pt-2">
        <span>Score: {((worker.reliability_score || 1) * 100).toFixed(0)}%</span>
        <span>Tasks: {worker.total_tasks_completed || 0}</span>
      </div>
    </div>
  );
}

// ─── Job Detail Modal (with Provenance, Timeline, Results & Download Formats) ─
function JobDetailModal({ job, onClose }) {
  const [activeSection, setActiveSection] = useState('overview');
  const [provenance, setProvenance] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!job) return;
    setLoading(true);
    Promise.all([
      fetch(`${API}/jobs/${job.id}/provenance`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/jobs/${job.id}/timeline`).then(r => r.ok ? r.json() : null),
      fetch(`${API}/jobs/${job.id}/result`).then(r => r.ok ? r.json() : null)
    ]).then(([provData, timeData, resData]) => {
      setProvenance(provData);
      setTimeline(timeData?.events || []);
      setResult(resData);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, [job]);

  if (!job) return null;

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-panel p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto space-y-5 scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-white/10 pb-4">
          <div>
            <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20 mr-2">{job.job_uid || `#${job.id}`}</span>
            <span className="text-lg font-bold text-white">{job.name}</span>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-white/10 text-gray-400"><X className="w-5 h-5" /></button>
        </div>

        {/* Section Tabs */}
        <div className="flex gap-1 bg-white/5 p-1 rounded-xl">
          {['overview', 'provenance', 'timeline', 'result'].map(sec => (
            <button key={sec} onClick={() => setActiveSection(sec)}
              className={`flex-1 py-1.5 rounded-lg text-xs font-semibold capitalize transition ${activeSection === sec ? 'bg-primary text-white shadow-md' : 'text-gray-400 hover:text-white'}`}>
              {sec}
            </button>
          ))}
        </div>

        {/* ── OVERVIEW SECTION ── */}
        {activeSection === 'overview' && (
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Status:</span><span className="font-bold text-emerald-400 uppercase">{job.status}</span></div>
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Type:</span><span className="font-bold text-white">{job.job_type}</span></div>
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Strategy:</span><span className="font-bold text-accent">{job.scheduler_strategy || 'capacity_based'}</span></div>
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Priority:</span><span className="font-bold text-yellow-400">{job.priority || 'NORMAL'}</span></div>
            </div>

            {job.result_preview && (
              <div className="bg-emerald-500/10 border border-emerald-500/20 p-3 rounded-xl">
                <span className="text-emerald-400 font-semibold block mb-1">Result Summary:</span>
                <p className="text-white font-mono">{job.result_preview}</p>
              </div>
            )}

            {job.checkpoint_location && (
              <div className="bg-purple-500/10 border border-purple-500/20 p-3 rounded-xl text-purple-300">
                <span className="font-semibold block mb-0.5">Model / Checkpoint Reference:</span>
                <p className="font-mono">{job.checkpoint_location}</p>
              </div>
            )}

            <div>
              <span className="text-gray-400 block mb-1 uppercase tracking-wider">Job Parameters:</span>
              <pre className="bg-black/40 p-3 rounded-xl text-gray-300 font-mono overflow-auto max-h-48">{JSON.stringify(job.params, null, 2)}</pre>
            </div>
          </div>
        )}

        {/* ── PROVENANCE SECTION ── */}
        {activeSection === 'provenance' && (
          <div className="space-y-3">
            <p className="text-xs text-gray-400 font-semibold uppercase">Chunk Provenance & Execution Attempts</p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {provenance?.chunks?.map(c => (
                <div key={c.chunk_id} className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-white font-mono">{c.chunk_uid || `CHUNK-${c.chunk_id}`}</span>
                    <span className={`px-2 py-0.5 rounded font-semibold uppercase ${c.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{c.status}</span>
                  </div>
                  <div className="text-gray-400">Accepted Attempt: <span className="text-primary font-mono">{c.accepted_attempt_id || '—'}</span> | Node: <span className="text-white font-mono">{c.worker_uid || 'Unassigned'}</span></div>
                  {c.attempts?.length > 0 && (
                    <div className="pl-3 border-l-2 border-primary/30 space-y-1">
                      {c.attempts.map((att, i) => (
                        <div key={i} className="text-[11px] text-gray-400 flex items-center justify-between">
                          <span>Attempt #{att.attempt_number} ({att.worker_uid})</span>
                          <span className={att.status === 'completed' ? 'text-emerald-400' : 'text-red-400'}>{att.status} {att.duration_seconds ? `(${att.duration_seconds.toFixed(2)}s)` : ''}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── TIMELINE SECTION ── */}
        {activeSection === 'timeline' && (
          <div className="space-y-3">
            <p className="text-xs text-gray-400 font-semibold uppercase">Chronological Event Milestone Logs</p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {timeline.map((evt, i) => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs flex items-start justify-between">
                  <div>
                    <span className="text-primary font-bold block">{evt.event_type}</span>
                    <span className="text-white">{evt.message}</span>
                  </div>
                  <span className="text-gray-500 font-mono text-[10px]">{fmtTime(evt.timestamp)}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── RESULT & DOWNLOAD SECTION ── */}
        {activeSection === 'result' && (
          <div className="space-y-4">
            <p className="text-xs text-gray-400 font-semibold uppercase">Aggregated Result & File Exports</p>
            {result?.aggregated_result ? (
              <>
                <pre className="bg-black/40 p-4 rounded-xl text-emerald-400 font-mono text-xs overflow-auto max-h-72 border border-emerald-500/20">
                  {JSON.stringify(result.aggregated_result, null, 2)}
                </pre>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2">
                  <a href={`${API}/files/jobs/${job.id}/download`} download
                    className="py-2 px-3 bg-primary/20 border border-primary/40 text-primary hover:bg-primary/30 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition">
                    <Download className="w-3.5 h-3.5" /> JSON (.json)
                  </a>
                  <a href={`${API}/files/jobs/${job.id}/export/csv`} download
                    className="py-2 px-3 bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 hover:bg-emerald-500/30 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition">
                    <FileDown className="w-3.5 h-3.5" /> CSV (.csv)
                  </a>
                  <a href={`${API}/files/jobs/${job.id}/export/txt`} download
                    className="py-2 px-3 bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition">
                    <FileText className="w-3.5 h-3.5" /> Text (.txt)
                  </a>
                  <a href={`${API}/files/jobs/${job.id}/export/zip`} download
                    className="py-2 px-3 bg-yellow-500/20 border border-yellow-500/40 text-yellow-400 hover:bg-yellow-500/30 rounded-xl font-semibold text-xs flex items-center justify-center gap-1.5 transition">
                    <Database className="w-3.5 h-3.5" /> Bundle (.zip)
                  </a>
                </div>
              </>
            ) : (
              <p className="text-gray-500 text-center py-8 text-xs">No result produced yet.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Submit Job Modal (Supports All 11 Standard Task Presets + Strategy + Quota)
function SubmitJobModal({ show, onClose, token }) {
  const [jobType, setJobType] = useState('sorting');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [strategy, setStrategy] = useState('capacity_based');
  const [priority, setPriority] = useState('NORMAL');
  const [requiresGpu, setRequiresGpu] = useState(false);
  const [minVram, setMinVram] = useState(4.0);
  const [loading, setLoading] = useState(false);
  const [jsonError, setJsonError] = useState('');

  const TASK_PRESETS = {
    sorting: { label: 'Merge Sort', icon: '📶', desc: 'Parallel sort using K-way merge aggregation', defaults: { array_size: 25000, chunks: 5 } },
    matrix_multiply: { label: 'Matrix Mult', icon: '🧮', desc: 'Row-sliced matrix multiplication C = A x B', defaults: { rows_a: 50, cols_a: 50, cols_b: 50, chunks: 5 } },
    statistics: { label: 'Statistics', icon: '📊', desc: 'Mean, median, std dev, min/max analysis', defaults: { array_size: 20000, chunks: 5 } },
    search: { label: 'Value Search', icon: '🔍', desc: 'Parallel pattern search with global index tracking', defaults: { array_size: 100000, target: 42, chunks: 5 } },
    word_count: { label: 'Word Count', icon: '📝', desc: 'MapReduce word frequency reduction', defaults: { text: 'CoCompute distributed framework intelligently schedules tasks across heterogeneous edge hardware', chunks: 4 } },
    image_processing: { label: 'Image Filter', icon: '🖼️', desc: 'Tile-based filters (grayscale, invert, edge)', defaults: { images_count: 6, filter_type: 'grayscale', chunks: 3 } },
    prime_generation: { label: 'Prime Gen', icon: '🔢', desc: 'Numeric range prime sieve', defaults: { start: 1, end: 100000, chunks: 5 } },
    cipher: { label: 'Substitution Cipher', icon: '🔐', desc: 'Parallel text encryption & decryption', defaults: { text: 'CoCompute Distributed Enterprise Cluster Platform', shift: 7, mode: 'encrypt', chunks: 4 } },
    ml_training: { label: 'PyTorch Training', icon: '🤖', desc: 'Data-parallel PyTorch model training', defaults: { model_name: 'ResNet-50', epochs: 10, batch_size: 64, dataset_size: 10000, chunks: 4 }, gpu: true, vram: 8 },
    distributed_inference: { label: 'Batch Inference', icon: '⚡', desc: 'Parallel batch model inference', defaults: { model: 'vit-base-patch16', batch_count: 100, chunks: 4 }, gpu: true, vram: 4 },
    llm_finetune: { label: 'LLM Fine-Tuning', icon: '🧠', desc: 'Data-sharded LLM fine-tuning with step checkpointing', defaults: { model_name: 'custom-llm-7b', steps: 1000, epochs: 5, chunks: 4 }, gpu: true, vram: 16 },
    generic_python: { label: 'Custom Python', icon: '🐍', desc: 'User-provided script executed across chunks', defaults: { script: "import json, sys\nprint(json.dumps({'status': 'ok'}))", data_chunks: [{ a: 1 }, { a: 2 }] } }
  };

  const [paramsJson, setParamsJson] = useState(JSON.stringify(TASK_PRESETS['sorting'].defaults, null, 2));

  const handleSelect = (t) => {
    setJobType(t);
    const p = TASK_PRESETS[t];
    setParamsJson(JSON.stringify(p.defaults, null, 2));
    if (p.gpu) { setRequiresGpu(true); setMinVram(p.vram || 4.0); }
    else { setRequiresGpu(false); }
    setJsonError('');
  };

  const submit = async () => {
    setLoading(true);
    setJsonError('');
    let parsed = {};
    try { parsed = JSON.parse(paramsJson); } catch (e) { setJsonError(`JSON Error: ${e.message}`); setLoading(false); return; }

    try {
      const res = await fetch(`${API}/jobs/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          name: name || `${TASK_PRESETS[jobType].label} Job`,
          description: desc || TASK_PRESETS[jobType].desc,
          job_type: jobType,
          scheduler_strategy: strategy,
          priority: priority,
          params: parsed,
          requires_gpu: requiresGpu,
          min_vram_gb: requiresGpu ? minVram : 0.0
        })
      });
      if (!res.ok) { const d = await res.json(); throw new Error(d.detail); }
      onClose();
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-md z-50 flex items-center justify-center p-4" onClick={onClose}>
      <div className="glass-panel p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto space-y-4 scale-in" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between border-b border-white/10 pb-3">
          <h2 className="text-lg font-bold text-white flex items-center gap-2"><Play className="w-5 h-5 text-primary" /> Submit Distributed Job</h2>
          <button onClick={onClose} className="p-1 rounded text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
        </div>

        {/* Task presets */}
        <div>
          <label className="text-xs text-gray-400 uppercase tracking-wider block mb-2 font-semibold">Standard Task Preset (11 Types)</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {Object.entries(TASK_PRESETS).map(([k, info]) => (
              <button key={k} onClick={() => handleSelect(k)}
                className={`p-2.5 rounded-xl border text-left text-xs transition ${jobType === k ? 'bg-primary/20 border-primary text-primary font-bold' : 'bg-white/5 border-white/10 text-gray-300 hover:border-white/20'}`}>
                <span>{info.icon}</span> <span className="block truncate mt-1">{info.label}</span>
              </button>
            ))}
          </div>
          <p className="text-xs text-gray-400 mt-2 italic">{TASK_PRESETS[jobType].desc}</p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Job Name</label>
            <input value={name} onChange={e => setName(e.target.value)} placeholder={`${TASK_PRESETS[jobType].label} Task`}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary" />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Scheduler Strategy</label>
            <select value={strategy} onChange={e => setStrategy(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary">
              <option value="capacity_based" className="bg-[#18181c]">Capacity Based (Hardware + Reliability)</option>
              <option value="round_robin" className="bg-[#18181c]">Round Robin (Uniform Rotation)</option>
              <option value="least_loaded" className="bg-[#18181c]">Least Loaded (Min CPU/RAM)</option>
              <option value="gpu_aware" className="bg-[#18181c]">GPU Aware (VRAM & Thermal)</option>
              <option value="network_aware" className="bg-[#18181c]">Network Aware (Bandwidth/Latency)</option>
              <option value="priority_based" className="bg-[#18181c]">Priority Based (User Quota Weight)</option>
              <option value="fair_share" className="bg-[#18181c]">Fair Share (Equal Multi-User Dist)</option>
              <option value="ai_predictive" className="bg-[#18181c]">AI Predictive (ML Runtime Model)</option>
            </select>
          </div>
        </div>

        {/* Priority & GPU */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 bg-white/5 p-3 rounded-xl border border-white/10">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Execution Priority</label>
            <select value={priority} onChange={e => setPriority(e.target.value)}
              className="w-full bg-black/40 border border-white/10 rounded-lg px-2.5 py-1.5 text-xs text-white outline-none">
              <option value="NORMAL" className="bg-[#18181c]">NORMAL</option>
              <option value="HIGH" className="bg-[#18181c]">HIGH (Priority Queue)</option>
              <option value="CRITICAL" className="bg-[#18181c]">CRITICAL (Preempts standard queue)</option>
            </select>
          </div>
          <div className="flex items-center justify-between pt-4">
            <label className="flex items-center gap-2 text-xs text-gray-300 cursor-pointer">
              <input type="checkbox" checked={requiresGpu} onChange={e => setRequiresGpu(e.target.checked)} className="rounded accent-emerald-500" />
              <span>Require GPU / CUDA</span>
            </label>
            {requiresGpu && (
              <div className="flex items-center gap-1">
                <input type="number" value={minVram} onChange={e => setMinVram(Number(e.target.value))} className="w-14 bg-black/40 border border-white/10 rounded px-2 py-1 text-xs text-emerald-400 font-mono" />
                <span className="text-[10px] text-gray-400">GB VRAM</span>
              </div>
            )}
          </div>
        </div>

        {/* Parameters editor */}
        <div>
          <label className="text-xs text-gray-400 block mb-1 uppercase font-semibold">Parameters JSON</label>
          <textarea rows={6} value={paramsJson} onChange={e => setParamsJson(e.target.value)}
            className="w-full bg-black/40 border border-white/10 rounded-xl p-3 text-xs text-emerald-400 font-mono outline-none focus:ring-2 focus:ring-primary" />
          {jsonError && <p className="text-red-400 text-xs mt-1">{jsonError}</p>}
        </div>

        <div className="flex gap-3 pt-2">
          <button onClick={onClose} className="flex-1 py-2.5 rounded-xl border border-white/10 text-gray-400 hover:text-white transition text-xs font-semibold">Cancel</button>
          <button onClick={submit} disabled={loading}
            className="flex-1 py-2.5 rounded-xl bg-primary hover:bg-blue-500 text-white font-semibold text-xs transition flex items-center justify-center gap-1.5 shadow-lg shadow-primary/20">
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />} Submit Task
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Benchmarking Suite Component (Real Measured Cluster Values Only) ─────────
function BenchmarksSuite({ token }) {
  const [scalabilityData, setScalabilityData] = useState(null);
  const [schedulerData, setSchedulerData] = useState(null);
  const [runningScalability, setRunningScalability] = useState(false);
  const [runningSchedulers, setRunningSchedulers] = useState(false);

  const fetchBenchmarks = useCallback(async () => {
    try {
      const [scRes, shRes] = await Promise.all([
        fetch(`${API}/benchmarks/scalability`),
        fetch(`${API}/benchmarks/schedulers`)
      ]);
      if (scRes.ok) setScalabilityData(await scRes.json());
      if (shRes.ok) setSchedulerData(await shRes.json());
    } catch (e) { console.error('Error fetching benchmarks:', e); }
  }, []);

  useEffect(() => { fetchBenchmarks(); }, [fetchBenchmarks]);

  const triggerScalability = async () => {
    setRunningScalability(true);
    try {
      const res = await fetch(`${API}/benchmarks/scalability/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ task_type: 'sorting', worker_counts: [1, 5, 10, 25, 50, 100] })
      });
      if (res.ok) setScalabilityData(await res.json());
    } catch (e) { alert('Benchmark failed'); }
    finally { setRunningScalability(false); }
  };

  const triggerSchedulers = async () => {
    setRunningSchedulers(true);
    try {
      const res = await fetch(`${API}/benchmarks/schedulers/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ task_type: 'sorting' })
      });
      if (res.ok) setSchedulerData(await res.json());
    } catch (e) { alert('Scheduler benchmark failed'); }
    finally { setRunningSchedulers(false); }
  };

  return (
    <div className="space-y-5">
      {/* Banner */}
      <div className="glass-panel p-5 border-l-4 border-l-primary flex items-center justify-between">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2"><Award className="w-5 h-5 text-primary" /> Live Cluster Benchmarking Suite</h2>
          <p className="text-xs text-gray-400 mt-1">Real-measured cluster execution metrics. Skipped data points reflect insufficient online physical nodes.</p>
        </div>
        <div className="flex gap-2">
          <button onClick={triggerScalability} disabled={runningScalability}
            className="px-3 py-2 bg-primary/20 border border-primary/40 text-primary hover:bg-primary/30 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
            {runningScalability ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Run Scalability Test
          </button>
          <button onClick={triggerSchedulers} disabled={runningSchedulers}
            className="px-3 py-2 bg-accent/20 border border-accent/40 text-accent hover:bg-accent/30 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
            {runningSchedulers ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Sliders className="w-3.5 h-3.5" />} Compare Schedulers
          </button>
        </div>
      </div>

      {/* Scalability Table & Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><BarChart3 className="w-4 h-4 text-emerald-400" /> Scalability & Speedup Table</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-500 text-left">
                <th className="py-2">Nodes (N)</th>
                <th className="py-2">Status</th>
                <th className="py-2">Time (s)</th>
                <th className="py-2">Speedup (S)</th>
                <th className="py-2">Efficiency</th>
              </tr>
            </thead>
            <tbody>
              {scalabilityData?.results?.map(r => (
                <tr key={r.workers} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 font-mono font-bold text-white">{r.workers} node{r.workers !== 1 ? 's' : ''}</td>
                  <td className="py-2"><span className={`px-2 py-0.5 rounded text-[10px] font-bold ${r.status === 'MEASURED' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'}`}>{r.status}</span></td>
                  <td className="py-2 font-mono text-gray-300">{r.execution_time_sec != null ? `${r.execution_time_sec}s` : '—'}</td>
                  <td className="py-2 font-mono text-primary font-bold">{r.speedup != null ? `${r.speedup}x` : '—'}</td>
                  <td className="py-2 font-mono text-emerald-400">{r.efficiency_pct != null ? `${r.efficiency_pct}%` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Scheduler Comparison Table */}
        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><Sliders className="w-4 h-4 text-accent" /> Scheduling Strategy Evaluation</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-500 text-left">
                <th className="py-2">Strategy</th>
                <th className="py-2">Selected Worker</th>
                <th className="py-2">Score</th>
                <th className="py-2">Decision Latency</th>
              </tr>
            </thead>
            <tbody>
              {schedulerData?.results?.map(s => (
                <tr key={s.strategy} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 font-bold text-accent capitalize">{s.strategy.replace(/_/g, ' ')}</td>
                  <td className="py-2 font-mono text-gray-300">{s.selected_worker || 'None (No match)'}</td>
                  <td className="py-2 font-mono text-white">{s.score}</td>
                  <td className="py-2 font-mono text-emerald-400">{s.scheduling_latency_ms} ms</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Projects & Quotas Suite Component ───────────────────────────────────────
function ProjectsSuite({ user, token, jobs }) {
  const [projects, setProjects] = useState([]);
  const [usersList, setUsersList] = useState([]);
  const [pName, setPName] = useState('');
  const [pDesc, setPDesc] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchProjects = useCallback(async () => {
    try {
      const res = await fetch(`${API}/projects/`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setProjects(await res.json());

      if (user?.role === 'admin') {
        const uRes = await fetch(`${API}/auth/users`, { headers: { 'Authorization': `Bearer ${token}` } });
        if (uRes.ok) setUsersList(await uRes.json());
      }
    } catch (e) { console.error(e); }
  }, [token, user]);

  useEffect(() => { fetchProjects(); }, [fetchProjects]);

  const createProject = async () => {
    if (!pName) return;
    setLoading(true);
    try {
      const res = await fetch(`${API}/projects/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ name: pName, description: pDesc })
      });
      if (res.ok) { setPName(''); setPDesc(''); fetchProjects(); }
    } catch (e) { alert('Failed to create project'); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-5">
      {/* User Quota Banner */}
      <div className="glass-panel p-5 grid grid-cols-2 md:grid-cols-5 gap-3 border-l-4 border-l-accent">
        <div><span className="text-gray-400 text-xs block">Your Role:</span><span className="text-sm font-bold text-accent uppercase">{user?.role}</span></div>
        <div><span className="text-gray-400 text-xs block">Max Concurrent Jobs:</span><span className="text-sm font-bold text-white">{user?.max_concurrent_jobs || 5}</span></div>
        <div><span className="text-gray-400 text-xs block">Max Workers / Job:</span><span className="text-sm font-bold text-white">{user?.max_workers_per_job || 20}</span></div>
        <div><span className="text-gray-400 text-xs block">Max GPUs:</span><span className="text-sm font-bold text-emerald-400">{user?.max_gpu_count || 0} ({user?.max_vram_gb || 0} GB)</span></div>
        <div><span className="text-gray-400 text-xs block">Priority Class:</span><span className="text-sm font-bold text-yellow-400">{user?.priority || 'NORMAL'}</span></div>
      </div>

      {/* Projects List & Create */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Create Project */}
        <div className="glass-panel p-5 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2"><FolderGit2 className="w-4 h-4 text-primary" /> Create Project Container</h3>
          <input value={pName} onChange={e => setPName(e.target.value)} placeholder="Project Name"
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary" />
          <textarea value={pDesc} onChange={e => setPDesc(e.target.value)} placeholder="Project Description & Research Goals" rows={3}
            className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary" />
          <button onClick={createProject} disabled={loading || !pName}
            className="w-full py-2 bg-primary hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition flex items-center justify-center gap-1.5 disabled:opacity-50">
            {loading ? <Loader className="w-3.5 h-3.5 animate-spin" /> : 'Create Project'}
          </button>
        </div>

        {/* Existing Projects */}
        <div className="glass-panel p-5 lg:col-span-2 space-y-3">
          <h3 className="text-sm font-bold text-white">Active Projects ({projects.length})</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
            {projects.map(p => (
              <div key={p.id} className="bg-white/5 border border-white/10 rounded-xl p-3.5 space-y-1.5">
                <div className="flex justify-between items-center">
                  <span className="font-bold text-white text-xs">{p.name}</span>
                  <span className="font-mono text-[10px] text-primary bg-primary/10 px-2 py-0.5 rounded">{p.project_uid}</span>
                </div>
                <p className="text-[11px] text-gray-400 truncate">{p.description || 'No description'}</p>
                <div className="text-[10px] text-gray-500 pt-1 flex justify-between">
                  <span>Jobs: {p.job_count || 0}</span>
                  <span>Created: {fmtTime(p.created_at)}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Admin User Management */}
      {user?.role === 'admin' && usersList.length > 0 && (
        <div className="glass-panel p-5 space-y-3">
          <h3 className="text-sm font-bold text-white flex items-center gap-2"><Users className="w-4 h-4 text-emerald-400" /> Institutional Quotas Management (Admin)</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-500 text-left">
                <th className="py-2">User</th>
                <th className="py-2">Role</th>
                <th className="py-2">Max Jobs</th>
                <th className="py-2">Max Workers</th>
                <th className="py-2">Max GPUs</th>
                <th className="py-2">Priority</th>
              </tr>
            </thead>
            <tbody>
              {usersList.map(u => (
                <tr key={u.id} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 font-bold text-white">{u.username} ({u.email})</td>
                  <td className="py-2 text-accent uppercase font-semibold">{u.role}</td>
                  <td className="py-2 text-gray-300">{u.max_concurrent_jobs}</td>
                  <td className="py-2 text-gray-300">{u.max_workers_per_job}</td>
                  <td className="py-2 text-emerald-400">{u.max_gpu_count}</td>
                  <td className="py-2 text-yellow-400">{u.priority}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── MAIN APP COMPONENT ──────────────────────────────────────────────────────
function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));

  const [workers, setWorkers] = useState([]);
  const [cluster, setCluster] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [rankings, setRankings] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [schedulerAlgo, setSchedulerAlgo] = useState('capacity_based');
  const [dismissedAlerts, setDismissedAlerts] = useState(new Set());

  const [showSubmit, setShowSubmit] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');
  const [logLevel, setLogLevel] = useState('');
  const [logSearch, setLogSearch] = useState('');
  const [showAlerts, setShowAlerts] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedWorker, setSelectedWorker] = useState(null);
  const [wsStatus, setWsStatus] = useState('connecting');

  const wsRef = useRef(null);
  const headers = token ? { 'Authorization': `Bearer ${token}` } : {};

  const fetchAll = useCallback(async () => {
    if (!token) return;
    try {
      const [wRes, cRes, jRes, spRes, rkRes, logRes, alRes] = await Promise.all([
        fetch(`${API}/workers/`), fetch(`${API}/metrics/cluster`), fetch(`${API}/jobs/`),
        fetch(`${API}/analytics/speedup`), fetch(`${API}/analytics/workers/ranking`),
        fetch(`${API}/logs/?limit=200`), fetch(`${API}/alerts/`)
      ]);
      if (wRes.ok) setWorkers(await wRes.json());
      if (cRes.ok) setCluster(await cRes.json());
      if (jRes.ok) setJobs(await jRes.json());
      if (spRes.ok) setAnalytics(await spRes.json());
      if (rkRes.ok) { const d = await rkRes.json(); setRankings(d.rankings || []); }
      if (logRes.ok) { const d = await logRes.json(); setLogs(d.logs || []); }
      if (alRes.ok) { const d = await alRes.json(); setAlerts(d.alerts || []); }
    } catch (e) { console.error('Fetch error:', e); }
  }, [token]);

  useEffect(() => {
    if (!token) return;
    let reconnectTimeout;

    const connectWs = () => {
      const wsUrl = `${WS_BASE}/ws/live`;
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => { setWsStatus('connected'); };
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
        } catch (err) {}
      };
    };

    connectWs();
    fetchAll();
    const iv = setInterval(fetchAll, 6000);

    return () => {
      clearTimeout(reconnectTimeout);
      if (wsRef.current) wsRef.current.close();
      clearInterval(iv);
    };
  }, [token, fetchAll]);

  useEffect(() => {
    if (!token) return;
    fetch(`${API}/auth/me`, { headers }).then(r => {
      if (r.ok) r.json().then(setUser);
      else { setToken(null); localStorage.removeItem('token'); }
    }).catch(() => {});
  }, [token]);

  if (!token) return <AuthScreen onAuth={(u, t) => { setUser(u); setToken(t); }} />;

  const c = cluster || {};
  const onlineW = workers.filter(w => w.status === 'online');
  const activeAlerts = alerts.filter(a => !dismissedAlerts.has(a.id || a.type + a.timestamp));

  const TABS = [
    { id: 'overview',   label: 'Overview',   icon: Activity },
    { id: 'tasks',      label: 'Jobs & Queue', icon: Clock },
    { id: 'benchmarks', label: 'Benchmarks', icon: Award },
    { id: 'projects',   label: 'Projects & Quota', icon: FolderGit2 },
    { id: 'analytics',  label: 'Analytics',  icon: BarChart3 },
    { id: 'workers',    label: 'Nodes',      icon: Server },
    { id: 'logs',       label: 'Logs',       icon: FileText },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-xl border-b border-white/5">
        <div className="max-w-[1700px] mx-auto px-5 py-3 flex justify-between items-center">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-primary/10 border border-primary/20">
              <Zap className="text-primary w-5 h-5" />
            </div>
            <h1 className="text-xl font-extrabold gradient-text">CoCompute</h1>
            <div className={`flex items-center gap-1 text-xs px-2 py-0.5 rounded-full border ${wsStatus === 'connected' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400' : 'bg-yellow-500/10 border-yellow-500/20 text-yellow-400'}`}>
              <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === 'connected' ? 'bg-emerald-400 blink' : 'bg-yellow-400'}`} />
              {wsStatus === 'connected' ? 'Live Streaming' : 'Polling'}
            </div>
          </div>

          <nav className="flex gap-0.5 bg-white/5 rounded-xl p-1">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium transition ${activeTab === t.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                <t.icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <button onClick={() => setShowSubmit(true)}
              className="bg-primary hover:bg-blue-500 transition text-white px-4 py-2 rounded-xl flex items-center gap-2 font-semibold shadow-lg shadow-primary/20 text-xs glow-primary">
              <Play className="w-3.5 h-3.5 fill-current" /> Submit Job
            </button>
            <div className="flex items-center gap-1.5 px-3 py-2 bg-white/5 rounded-xl border border-white/10 text-xs text-gray-400">
              <Shield className="w-3.5 h-3.5 text-accent" />
              <span>{user?.username} ({user?.role})</span>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1700px] mx-auto px-5 py-5 space-y-5">
        {/* ══ OVERVIEW TAB ══ */}
        {activeTab === 'overview' && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
              <StatCard label="Total Nodes" value={c.total_nodes || 0} icon={Server} />
              <StatCard label="Online Nodes" value={c.online_nodes || 0} icon={Wifi} color="text-emerald-400" />
              <StatCard label="Offline Nodes" value={c.offline_nodes || 0} icon={WifiOff} color="text-red-400" />
              <StatCard label="Active Cores" value={c.active_cores || 0} icon={Cpu} color="text-accent" />
              <StatCard label="RAM Pool" value={`${c.aggregated_ram || 0} GB`} icon={HardDrive} color="text-primary" />
              <StatCard label="Cluster Efficiency" value={`${c.efficiency || 0}%`} icon={Gauge} color="text-emerald-400" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="glass-panel p-5 lg:col-span-2">
                <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-primary" /> Real-Time Cluster Resource History
                </h2>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={c.history || []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" />
                      <XAxis dataKey="timestamp" stroke="#4B5563" tick={false} />
                      <YAxis stroke="#4B5563" domain={[0, 100]} tick={{ fontSize: 10, fill: '#6B7280' }} />
                      <Tooltip contentStyle={{ backgroundColor: '#111827', border: '1px solid rgba(255,255,255,0.1)', color: '#fff' }} />
                      <Area type="monotone" dataKey="cpu" name="CPU %" stroke="#3B82F6" fill="#3B82F6" fillOpacity={0.2} strokeWidth={2} dot={false} />
                      <Area type="monotone" dataKey="ram" name="RAM %" stroke="#10B981" fill="#10B981" fillOpacity={0.2} strokeWidth={2} dot={false} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="glass-panel p-5">
                <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                  <Sliders className="w-4 h-4 text-accent" /> Active Scheduling Policy
                </h2>
                <div className="bg-white/5 p-4 rounded-xl space-y-2 border border-white/10">
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400">Current Strategy:</span>
                    <span className="text-xs font-bold text-accent uppercase font-mono">{schedulerAlgo}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400">Redis Queue:</span>
                    <span className="text-xs font-bold text-emerald-400 font-mono">jobs:high / normal</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400">Rescheduling Pub/Sub:</span>
                    <span className="text-xs font-bold text-emerald-400 font-mono">cocompute:reschedule</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-gray-400">Fault Detection:</span>
                    <span className="text-xs font-bold text-primary font-mono">&lt; 1s Immediate</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Workers grid */}
            <div className="glass-panel p-5">
              <h2 className="text-sm font-semibold mb-4 text-white flex items-center gap-2">
                <Server className="w-4 h-4" /> Connected Worker Nodes ({workers.length})
              </h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-3">
                {workers.map(w => <WorkerCard key={w.id} worker={w} onClick={() => {}} />)}
              </div>
            </div>
          </>
        )}

        {/* ══ TASKS & QUEUE TAB ══ */}
        {activeTab === 'tasks' && (
          <div className="glass-panel overflow-hidden">
            <div className="px-5 py-4 border-b border-white/10 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Distributed Job Ledger</h2>
              <button onClick={fetchAll} className="p-1.5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white"><RefreshCw className="w-4 h-4" /></button>
            </div>
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10 text-left text-gray-500 uppercase tracking-wider">
                  {['Job UID', 'Name', 'Type', 'Strategy', 'Priority', 'Status', 'Progress', 'Preview', 'Submitted'].map(h => (
                    <th key={h} className="px-5 py-3">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {jobs.map(j => {
                  const pct = j.total_tasks > 0 ? Math.round(((j.completed_tasks + j.failed_tasks) / j.total_tasks) * 100) : 0;
                  return (
                    <tr key={j.id} onClick={() => setSelectedJob(j)} className="border-b border-white/5 hover:bg-white/5 cursor-pointer">
                      <td className="px-5 py-3 text-primary font-mono font-bold">{j.job_uid || `#${j.id}`}</td>
                      <td className="px-5 py-3 text-white font-medium">{j.name}</td>
                      <td className="px-5 py-3"><span className="bg-white/5 px-2 py-0.5 rounded border border-white/10 font-mono text-[11px]">{j.job_type}</span></td>
                      <td className="px-5 py-3 text-accent capitalize">{j.scheduler_strategy || 'capacity'}</td>
                      <td className="px-5 py-3 text-yellow-400 font-bold">{j.priority || 'NORMAL'}</td>
                      <td className="px-5 py-3"><span className={`font-semibold uppercase ${j.status === 'completed' ? 'text-emerald-400' : j.status === 'failed' ? 'text-red-400' : 'text-blue-400'}`}>{j.status}</span></td>
                      <td className="px-5 py-3">
                        <div className="w-24 bg-white/10 rounded-full h-1.5">
                          <div className={`h-1.5 rounded-full ${j.status === 'completed' ? 'bg-emerald-500' : 'bg-primary'}`} style={{ width: `${pct}%` }} />
                        </div>
                      </td>
                      <td className="px-5 py-3 text-gray-300 font-mono truncate max-w-[180px]">{j.result_preview || '—'}</td>
                      <td className="px-5 py-3 text-gray-500">{fmtTime(j.submission_time)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* ══ BENCHMARKS TAB ══ */}
        {activeTab === 'benchmarks' && <BenchmarksSuite token={token} />}

        {/* ══ PROJECTS & QUOTAS TAB ══ */}
        {activeTab === 'projects' && <ProjectsSuite user={user} token={token} jobs={jobs} />}

        {/* ══ ANALYTICS TAB ══ */}
        {activeTab === 'analytics' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              <StatCard label="Average Speedup" value={`${analytics?.avg_speedup?.toFixed(2) || '1.00'}x`} icon={Zap} color="text-accent" />
              <StatCard label="Parallel Efficiency" value={`${((analytics?.avg_efficiency || 0) * 100).toFixed(1)}%`} icon={TrendingUp} color="text-emerald-400" />
              <StatCard label="Cluster Health Score" value={`${c.efficiency || 95}%`} icon={Gauge} color="text-primary" />
            </div>

            {rankings.length > 0 && (
              <div className="glass-panel overflow-hidden">
                <div className="px-5 py-4 border-b border-white/10"><h2 className="text-sm font-semibold text-white">Node Reliability & Performance Ranking</h2></div>
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/10 text-gray-500 text-left">
                      {['Rank', 'Node', 'Completed', 'Failed', 'Reliability', 'Avg Time', 'Composite Score'].map(h => <th key={h} className="px-5 py-3">{h}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {rankings.map((r, i) => (
                      <tr key={r.worker_uid} className="border-b border-white/5 hover:bg-white/5">
                        <td className="px-5 py-3 text-gray-400 font-bold">#{i + 1}</td>
                        <td className="px-5 py-3 text-white font-medium">{r.hostname || r.worker_uid}</td>
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
          </div>
        )}

        {/* ══ WORKERS TAB ══ */}
        {activeTab === 'workers' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {workers.map(w => <WorkerCard key={w.id} worker={w} onClick={() => {}} />)}
          </div>
        )}

        {/* ══ LOGS TAB ══ */}
        {activeTab === 'logs' && (
          <div className="space-y-3">
            <div className="flex gap-2">
              <input value={logSearch} onChange={e => setLogSearch(e.target.value)} placeholder="Filter audit logs..."
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary" />
              <button onClick={fetchAll} className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-xs text-gray-400 hover:text-white flex items-center gap-1.5"><RefreshCw className="w-3.5 h-3.5" /> Refresh</button>
            </div>
            <div className="glass-panel overflow-hidden max-h-[600px] overflow-y-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-gray-500 text-left">
                    {['Timestamp', 'Level', 'Source', 'Message'].map(h => <th key={h} className="px-4 py-2.5">{h}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {logs.filter(l => !logSearch || l.message?.toLowerCase().includes(logSearch.toLowerCase())).map(l => (
                    <tr key={l.id} className="border-b border-white/5">
                      <td className="px-4 py-2 text-gray-500 font-mono">{fmtTime(l.timestamp)}</td>
                      <td className="px-4 py-2 font-bold text-primary">{l.level}</td>
                      <td className="px-4 py-2 text-gray-400 font-mono">{l.source}</td>
                      <td className="px-4 py-2 text-white">{l.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>

      {/* Modals */}
      <SubmitJobModal show={showSubmit} onClose={() => { setShowSubmit(false); fetchAll(); }} token={token} />
      {selectedJob && <JobDetailModal job={selectedJob} onClose={() => setSelectedJob(null)} />}
    </div>
  );
}

export default App;
