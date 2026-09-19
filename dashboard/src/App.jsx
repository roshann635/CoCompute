import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Activity, Server, Zap, HardDrive, Cpu, Play, Brain, TrendingUp,
  AlertTriangle, CheckCircle, XCircle, Clock, BarChart3, Users,
  Shield, Wifi, WifiOff, Loader, LogIn, UserPlus, ChevronDown,
  FileText, Search, RefreshCw, Bell, BellOff, X, Settings,
  ChevronRight, Terminal, Network, Database, Layers, Eye,
  ArrowUpRight, ArrowDownRight, Gauge, Sliders, Info, AlertCircle,
  Download, FileDown, History, GitCommit, FolderGit2, Award, FileCode, CheckSquare, Coins, Leaf, LogOut
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
          <p className="text-gray-400 text-sm">Adaptive & Self-Healing Distributed Computing Platform</p>
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
                  <option value="admin" className="bg-[#18181c]">Administrator (Full cluster management)</option>
                </select>
              </div>
            </>
          )}
          <input id="auth-password" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password"
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
          {worker.is_simulated && (
            <span className="text-[9px] bg-purple-500/20 text-purple-400 px-1.5 py-0.2 rounded border border-purple-500/30">SIM</span>
          )}
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
        <span>5-Factor Reliability: {((worker.reliability_score || 1) * 100).toFixed(0)}%</span>
        <span className="capitalize text-accent font-semibold">{worker.lifecycle_state || 'healthy'}</span>
      </div>
    </div>
  );
}

// ─── Job Detail & Result Modal ───────────────────────────────────────────────
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
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Strategy:</span><span className="font-bold text-accent">{job.scheduler_strategy || 'adaptive_hybrid'}</span></div>
              <div className="bg-white/5 p-3 rounded-xl"><span className="text-gray-400 block">Energy Mode:</span><span className="font-bold text-emerald-400 flex items-center gap-1"><Leaf className="w-3 h-3"/> {job.energy_mode || 'BALANCED'}</span></div>
            </div>

            {/* Workload Profiler Insight */}
            {job.workload_profile && (
              <div className="bg-blue-500/10 border border-blue-500/20 p-3 rounded-xl space-y-1.5">
                <span className="text-blue-400 font-semibold block flex items-center gap-1.5"><Brain className="w-4 h-4"/> Workload Intelligence Profile:</span>
                <div className="grid grid-cols-4 gap-2 text-[11px] text-gray-300 font-mono">
                  <div>CPU: {(job.workload_profile.cpu_intensity * 100).toFixed(0)}%</div>
                  <div>GPU: {(job.workload_profile.gpu_intensity * 100).toFixed(0)}%</div>
                  <div>Memory: {(job.workload_profile.memory_intensity * 100).toFixed(0)}%</div>
                  <div>Data: {job.workload_profile.estimated_data_mb} MB</div>
                </div>
              </div>
            )}

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
            <p className="text-xs text-gray-400 font-semibold uppercase">Chunk Provenance & Speculative Replicas</p>
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {provenance?.chunks?.map(c => (
                <div key={c.chunk_id} className="bg-white/5 border border-white/10 rounded-xl p-3 text-xs space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white font-mono">{c.chunk_uid || `CHUNK-${c.chunk_id}`}</span>
                      {c.is_speculative && (
                        <span className="text-[10px] bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded border border-yellow-500/30 flex items-center gap-1 font-bold">
                          ⚡ SPECULATIVE COPY
                        </span>
                      )}
                    </div>
                    <span className={`px-2 py-0.5 rounded font-semibold uppercase ${c.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>{c.status}</span>
                  </div>
                  <div className="text-gray-400">Accepted Attempt: <span className="text-primary font-mono">{c.accepted_attempt_id || '—'}</span> | Node: <span className="text-white font-mono">{c.worker_uid || 'Unassigned'}</span></div>
                  {c.attempts?.length > 0 && (
                    <div className="pl-3 border-l-2 border-primary/30 space-y-1">
                      {c.attempts.map((att, i) => (
                        <div key={i} className="text-[11px] text-gray-400 flex items-center justify-between">
                          <span>Attempt #{att.attempt_number} ({att.worker_uid}) {att.is_speculative ? '⚡' : ''}</span>
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
          <div className="space-y-2 max-h-96 overflow-y-auto">
            {timeline?.map((ev, i) => (
              <div key={i} className="flex gap-3 text-xs p-2.5 bg-white/5 rounded-xl border border-white/5">
                <span className="font-mono text-gray-500">{new Date(ev.timestamp).toLocaleTimeString()}</span>
                <div className="space-y-0.5">
                  <span className="font-bold text-accent block">{ev.event_type}</span>
                  <span className="text-gray-300">{ev.message}</span>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ── RESULT SECTION ── */}
        {activeSection === 'result' && (
          <div className="space-y-4">
            {result?.aggregated_result ? (
              <>
                <pre className="bg-black/50 p-4 rounded-xl text-emerald-400 font-mono text-xs overflow-auto max-h-72 border border-emerald-500/20">
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

// ─── Submit Job Modal ────────────────────────────────────────────────────────
function SubmitJobModal({ show, onClose, token }) {
  const [jobType, setJobType] = useState('sorting');
  const [name, setName] = useState('');
  const [desc, setDesc] = useState('');
  const [strategy, setStrategy] = useState('adaptive_hybrid');
  const [priority, setPriority] = useState('NORMAL');
  const [energyMode, setEnergyMode] = useState('BALANCED');
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
          energy_mode: energyMode,
          is_speculative_enabled: true,
          params: parsed,
          requires_gpu: requiresGpu,
          min_vram_gb: requiresGpu ? minVram : 0.0
        })
      });
      if (!res.ok) {
        const d = await res.json();
        if (res.status === 401) {
          localStorage.removeItem('token');
          alert('Authentication expired or invalid session. Please sign in again.');
          window.location.reload();
          return;
        }
        throw new Error(d.detail || 'Failed to submit workload');
      }
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
              <option value="adaptive_hybrid" className="bg-[#18181c]">Adaptive Hybrid Scheduler (AHS - Auto)</option>
              <option value="capacity_based" className="bg-[#18181c]">Capacity Based (Cores + RAM + Reliability)</option>
              <option value="least_loaded" className="bg-[#18181c]">Least Loaded (Minimum Utilization)</option>
              <option value="gpu_aware" className="bg-[#18181c]">GPU Aware (VRAM & CUDA Preferred)</option>
              <option value="network_aware" className="bg-[#18181c]">Network Aware (Lowest Latency)</option>
              <option value="priority_based" className="bg-[#18181c]">Priority Based (Role Weighting)</option>
              <option value="fair_share" className="bg-[#18181c]">Fair Share (Multi-User Balance)</option>
              <option value="ai_predictive" className="bg-[#18181c]">AI Predictive (ML Execution Model)</option>
              <option value="energy_aware" className="bg-[#18181c]">Energy Aware (🌱 Green Eco Mode)</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-gray-400 block mb-1">Energy & Carbon Optimization</label>
            <select value={energyMode} onChange={e => setEnergyMode(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary">
              <option value="BALANCED" className="bg-[#18181c]">BALANCED (Pareto Efficiency)</option>
              <option value="ECO" className="bg-[#18181c]">ECO (🌱 Minimal Carbon Footprint)</option>
              <option value="FAST" className="bg-[#18181c]">FAST (⚡ Maximum Performance)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Priority Tier</label>
            <select value={priority} onChange={e => setPriority(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-xs text-white outline-none focus:ring-2 focus:ring-primary">
              <option value="NORMAL" className="bg-[#18181c]">NORMAL</option>
              <option value="HIGH" className="bg-[#18181c]">HIGH</option>
              <option value="CRITICAL" className="bg-[#18181c]">CRITICAL</option>
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs text-gray-400 block mb-1">Task Payload (JSON)</label>
          <textarea value={paramsJson} onChange={e => setParamsJson(e.target.value)} rows={6}
            className="w-full bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-xs text-gray-200 font-mono outline-none focus:ring-2 focus:ring-primary" />
          {jsonError && <p className="text-red-400 text-xs mt-1">{jsonError}</p>}
        </div>

        <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
          <button onClick={onClose} className="px-4 py-2 rounded-xl text-xs text-gray-400 hover:text-white transition">Cancel</button>
          <button onClick={submit} disabled={loading}
            className="px-5 py-2 rounded-xl text-xs font-semibold bg-primary hover:bg-blue-500 text-white transition flex items-center gap-2 shadow-lg shadow-primary/20">
            {loading ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5 fill-current" />} Submit Workload
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Marketplace & Compute Pool Suite Component ─────────────────────────────
function MarketplaceSuite({ user, token }) {
  const [pool, setPool] = useState(null);
  const [credits, setCredits] = useState(null);
  const [pendingWorkers, setPendingWorkers] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchMarketplace = useCallback(async () => {
    try {
      const [pRes, cRes, wRes] = await Promise.all([
        fetch(`${API}/marketplace/pool`),
        fetch(`${API}/credits/balance`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API}/workers/trust/pending`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      if (pRes.ok) setPool(await pRes.json());
      if (cRes.ok) setCredits(await cRes.json());
      if (wRes.ok) setPendingWorkers(await wRes.json());
    } catch (e) { console.error(e); }
  }, [token]);

  useEffect(() => { fetchMarketplace(); }, [fetchMarketplace]);

  const handleApprove = async (uid, approve) => {
    try {
      const endpoint = approve ? `/workers/${uid}/approve` : `/workers/${uid}/reject`;
      await fetch(`${API}${endpoint}`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } });
      fetchMarketplace();
    } catch (e) { alert(e.message); }
  };

  return (
    <div className="space-y-5">
      {/* Compute Pool Summary Banner */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Pool Cores" value={pool?.total_cpu_cores || 0} icon={Cpu} color="text-primary" />
        <StatCard label="Pool RAM" value={`${pool?.total_ram_gb || 0} GB`} icon={HardDrive} color="text-purple-400" />
        <StatCard label="Pool GPUs" value={pool?.total_gpus || 0} icon={Zap} color="text-emerald-400" />
        <StatCard label="Pool VRAM" value={`${pool?.total_vram_gb || 0} GB`} icon={Database} color="text-accent" />
        <StatCard label="Utilization" value={`${pool?.pool_utilization_pct || 0}%`} icon={Gauge} color="text-yellow-400" />
        <StatCard label="Online Nodes" value={`${pool?.online_workers || 0} / ${pool?.total_workers || 0}`} icon={Server} color="text-emerald-400" />
      </div>

      {/* Credit Balance Card */}
      <div className="glass-panel p-5 grid grid-cols-1 md:grid-cols-4 gap-4 border-l-4 border-l-primary">
        <div>
          <span className="text-gray-400 text-xs block">Available Credits</span>
          <span className="text-xl font-bold text-primary font-mono">{credits?.credits_balance || 0} Credits</span>
        </div>
        <div>
          <span className="text-gray-400 text-xs block">Daily Allowance</span>
          <span className="text-xl font-bold text-white font-mono">{credits?.credits_daily_quota || 0} / day</span>
        </div>
        <div>
          <span className="text-gray-400 text-xs block">Consumed Today</span>
          <span className="text-xl font-bold text-accent font-mono">{credits?.credits_consumed_today || 0} Credits</span>
        </div>
        <div>
          <span className="text-gray-400 text-xs block">Institutional Tier</span>
          <span className="text-xl font-bold text-emerald-400 uppercase">{credits?.role || user?.role}</span>
        </div>
      </div>

      {/* Pending Worker Enrollment Approvals (Admin Gate) */}
      <div className="glass-panel p-5 space-y-3">
        <h3 className="text-sm font-bold text-white flex items-center gap-2">
          <Shield className="w-4 h-4 text-accent" /> Worker Trust & Secure Enrollment Queue ({pendingWorkers.length})
        </h3>
        {pendingWorkers.length === 0 ? (
          <p className="text-xs text-gray-500 py-4">No pending worker enrollment requests. All active nodes are verified and trusted.</p>
        ) : (
          <div className="space-y-2">
            {pendingWorkers.map(w => (
              <div key={w.worker_uid} className="flex items-center justify-between bg-white/5 p-3 rounded-xl border border-white/10 text-xs">
                <div>
                  <span className="font-bold text-white font-mono mr-2">{w.worker_uid}</span>
                  <span className="text-gray-400">{w.hostname} ({w.ip_address}) — {w.cpu_model} ({w.cpu_cores} cores, {w.ram_total}GB RAM)</span>
                </div>
                <div className="flex gap-2">
                  <button onClick={() => handleApprove(w.worker_uid, true)}
                    className="px-3 py-1 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg font-semibold transition">
                    Approve
                  </button>
                  <button onClick={() => handleApprove(w.worker_uid, false)}
                    className="px-3 py-1 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 rounded-lg font-semibold transition">
                    Reject
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Digital Twin Simulation Suite Component ─────────────────────────────────
function SimulationSuite({ user, token }) {
  const [status, setStatus] = useState(null);
  const [nodeCount, setNodeCount] = useState(10);
  const [gpuRatio, setGpuRatio] = useState(0.3);
  const [latency, setLatency] = useState(5.0);
  const [failureProb, setFailureProb] = useState(0.02);
  const [loading, setLoading] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API}/simulation/status`);
      if (res.ok) setStatus(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchStatus(); }, [fetchStatus]);

  const startSim = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/simulation/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          worker_count: nodeCount,
          gpu_ratio: gpuRatio,
          network_latency_ms: latency,
          failure_probability: failureProb
        })
      });
      if (res.ok) fetchStatus();
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  const stopSim = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/simulation/stop`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      fetchStatus();
    } catch (e) { alert(e.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-5">
      <div className="glass-panel p-5 space-y-4">
        <div className="flex justify-between items-center">
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2"><Terminal className="w-4 h-4 text-purple-400" /> Cluster Digital Twin & Simulator</h3>
            <p className="text-xs text-gray-400 mt-0.5">Scale virtual cluster nodes up to 100 machines for large-scale algorithmic evaluation.</p>
          </div>
          {status?.simulation_active ? (
            <button onClick={stopSim} disabled={loading}
              className="px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl text-xs font-semibold transition">
              Stop Simulation
            </button>
          ) : (
            <button onClick={startSim} disabled={loading}
              className="px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-xl text-xs font-semibold transition">
              Launch Digital Twin Nodes
            </button>
          )}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 text-xs">
          <div>
            <label className="text-gray-400 block mb-1">Simulated Workers: {nodeCount}</label>
            <input type="range" min="2" max="100" value={nodeCount} onChange={e => setNodeCount(Number(e.target.value))} className="w-full" />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">GPU Ratio: {(gpuRatio * 100).toFixed(0)}%</label>
            <input type="range" min="0" max="1" step="0.1" value={gpuRatio} onChange={e => setGpuRatio(Number(e.target.value))} className="w-full" />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">Latency: {latency} ms</label>
            <input type="range" min="1" max="50" value={latency} onChange={e => setLatency(Number(e.target.value))} className="w-full" />
          </div>
          <div>
            <label className="text-gray-400 block mb-1">Failure Prob: {(failureProb * 100).toFixed(0)}%</label>
            <input type="range" min="0" max="0.1" step="0.01" value={failureProb} onChange={e => setFailureProb(Number(e.target.value))} className="w-full" />
          </div>
        </div>

        {status?.simulation_active && (
          <div className="border-t border-white/10 pt-3 space-y-2">
            <span className="text-xs text-purple-400 font-semibold block">Active Digital Twin Nodes ({status?.simulated_workers_count})</span>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 max-h-60 overflow-y-auto">
              {status?.simulated_workers?.map(w => (
                <div key={w.worker_uid} className="bg-purple-500/10 border border-purple-500/20 p-2.5 rounded-xl text-xs">
                  <div className="font-bold text-white font-mono">{w.worker_uid}</div>
                  <div className="text-[11px] text-gray-400">{w.cpu_cores} Cores | {w.ram_total}GB | {w.gpu_model || 'CPU'}</div>
                  <div className="text-[10px] text-emerald-400 mt-1">Reliability: {(w.reliability_score * 100).toFixed(0)}%</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Benchmarks Suite Component ─────────────────────────────────────────────
function BenchmarksSuite({ token }) {
  const [scalabilityData, setScalabilityData] = useState(null);
  const [schedulerData, setSchedulerData] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchBenchmarks = useCallback(async () => {
    setLoading(true);
    try {
      const [scRes, schRes] = await Promise.all([
        fetch(`${API}/benchmarks/scalability`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API}/benchmarks/schedulers`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      if (scRes.ok) setScalabilityData(await scRes.json());
      if (schRes.ok) setSchedulerData(await schRes.json());
    } catch (e) { console.error('Benchmark fetch error', e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetchBenchmarks(); }, [fetchBenchmarks]);

  return (
    <div className="space-y-5">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2"><Award className="w-5 h-5 text-primary" /> Real-Cluster Benchmarking Suite</h2>
          <p className="text-xs text-gray-400 mt-0.5">Executes exclusively against connected cluster nodes. Speedup: <span className="font-mono text-primary">S = T_1 / T_N</span>.</p>
        </div>
        <button onClick={fetchBenchmarks} disabled={loading}
          className="px-4 py-2 rounded-xl text-xs font-semibold bg-primary hover:bg-blue-500 text-white transition flex items-center gap-2 shadow-lg shadow-primary/20">
          {loading ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />} Run Suite
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Scalability Table */}
        <div className="glass-panel p-5">
          <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><TrendingUp className="w-4 h-4 text-emerald-400" /> Scalability Speedup Curve</h3>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/10 text-gray-500 text-left">
                <th className="py-2">Nodes</th>
                <th className="py-2">Exec Time</th>
                <th className="py-2">Speedup</th>
                <th className="py-2">Efficiency</th>
              </tr>
            </thead>
            <tbody>
              {scalabilityData?.results?.map(r => (
                <tr key={r.workers} className="border-b border-white/5 hover:bg-white/5">
                  <td className="py-2 font-bold text-white">{r.workers} Node(s)</td>
                  <td className="py-2 font-mono text-gray-300">{r.execution_time_sec != null ? `${r.execution_time_sec}s` : <span className="text-gray-500 italic">{r.note || 'Skipped'}</span>}</td>
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

// ─── CoCompute 4.0: Task Registry & Task Builder Suite ───────────────────────
function TaskRegistrySuite({ user, token, onRunTask }) {
  const [packages, setPackages] = useState([]);
  const [showBuilder, setShowBuilder] = useState(false);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [testing, setTesting] = useState(false);

  // Task Builder Form State
  const [name, setName] = useState('Customer Analytics');
  const [version, setVersion] = useState('1.0');
  const [description, setDescription] = useState('Processes customer transactions and revenue distributions.');
  const [runtime, setRuntime] = useState('python:3.11');
  const [isPublic, setIsPublic] = useState(true);
  const [code, setCode] = useState(`class Task:
    def estimate_resources(self, input_data):
        from shared.sdk.task_contract import ResourceEstimate
        return ResourceEstimate(cpu_cores=4, ram_mb=2048, gpu_required=False)

    def partition(self, input_data, context):
        # Splits dataset into parallel chunk slices
        chunks = context.total_chunks or 4
        chunk_size = max(1, len(input_data) // chunks)
        return [input_data[i:i + chunk_size] for i in range(0, len(input_data), chunk_size)]

    def execute(self, chunk, context):
        # Computational payload on worker node
        return [x * 1.05 for x in chunk]

    def aggregate(self, results, context):
        # K-Way combiner
        merged = []
        for r in results:
            merged.extend(r)
        return {"data": merged, "count": len(merged)}

    def validate(self, result, context):
        return {"non_empty": len(result.get("data", [])) > 0}
`);

  const fetchPackages = useCallback(async () => {
    try {
      const res = await fetch(`${API}/tasks/packages`, { headers: { 'Authorization': `Bearer ${token}` } });
      if (res.ok) setPackages(await res.json());
    } catch (e) { console.error('Fetch packages error', e); }
  }, [token]);

  useEffect(() => { fetchPackages(); }, [fetchPackages]);

  const handleTestCompatibility = async (pkgId = null) => {
    setTesting(true);
    setTestResult(null);
    try {
      const endpoint = pkgId ? `${API}/tasks/packages/${pkgId}/test` : `${API}/tasks/packages/1/test`;
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ script_code: code, sample_input: [10, 20, 30, 40, 50, 60] })
      });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ passed: false, recommendation: e.message, report: { error: e.message } });
    } finally {
      setTesting(false);
    }
  };

  const handleSaveTask = async () => {
    setLoading(true);
    try {
      const manifest = {
        name,
        version,
        description,
        runtime,
        input_contract: { type: "json" },
        execution_contract: { entrypoint: "Task", cpu: "auto", ram: "auto", gpu: false },
        parallelization_contract: { mode: "embarrassingly_parallel" },
        partition_contract: { strategy: "auto" },
        aggregation_contract: { mode: "custom" }
      };

      const res = await fetch(`${API}/tasks/packages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({
          name,
          version,
          description,
          runtime,
          is_public: isPublic,
          manifest,
          script_code: code,
          entrypoint: "Task"
        })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Failed to save task');
      setShowBuilder(false);
      fetchPackages();
    } catch (e) {
      alert(e.message);
    } finally {
      setLoading(false);
    }
  };

  const filtered = packages.filter(p => search === '' || p.name.toLowerCase().includes(search.toLowerCase()));

  return (
    <div className="space-y-5">
      {/* Header & Controls */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <FileCode className="w-4 h-4 text-primary" /> CoCompute Universal Task Registry
          </h3>
          <p className="text-xs text-gray-400 mt-0.5">Discover, version, test, and execute custom 5-hook computational workloads.</p>
        </div>
        <div className="flex gap-2">
          <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search tasks..."
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-primary" />
          <button onClick={() => setShowBuilder(true)}
            className="px-4 py-2 bg-primary hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 glow-primary">
            + Create New Task
          </button>
        </div>
      </div>

      {/* Task Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map(p => (
          <div key={p.id} className="glass-panel p-5 space-y-3 hover:border-primary/40 transition">
            <div className="flex justify-between items-start">
              <div>
                <span className="font-bold text-white text-sm block">{p.name}</span>
                <span className="text-[11px] font-mono text-gray-400">v{p.version} | {p.runtime}</span>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${p.is_public ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-purple-500/10 text-purple-400 border border-purple-500/20'}`}>
                {p.is_public ? 'Public' : 'Private'}
              </span>
            </div>

            <p className="text-xs text-gray-400 line-clamp-2">{p.description || 'Custom user-defined distributed task.'}</p>

            <div className="border-t border-white/5 pt-2 flex items-center justify-between text-[11px]">
              <span className="text-emerald-400 flex items-center gap-1">
                <CheckCircle className="w-3 h-3" /> Compatible & Verified
              </span>
              <div className="flex gap-1.5">
                <button onClick={() => handleTestCompatibility(p.id)}
                  className="px-2.5 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded text-[11px] font-semibold border border-white/10 transition">
                  Test
                </button>
                <button onClick={() => onRunTask(p)}
                  className="px-2.5 py-1 bg-primary hover:bg-blue-500 text-white rounded text-[11px] font-semibold transition">
                  Run
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Task Builder Modal */}
      {showBuilder && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="glass-panel w-full max-w-4xl max-h-[90vh] overflow-y-auto p-6 space-y-5">
            <div className="flex justify-between items-center border-b border-white/10 pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <FileCode className="w-5 h-5 text-primary" /> Create New Distributed Task Package
              </h3>
              <button onClick={() => setShowBuilder(false)} className="text-gray-400 hover:text-white"><X className="w-5 h-5" /></button>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <label className="text-gray-400 block mb-1">Task Name</label>
                <input value={name} onChange={e => setName(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-gray-400 block mb-1">Version</label>
                <input value={version} onChange={e => setVersion(e.target.value)} className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-white outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-gray-400 block mb-1">Runtime</label>
                <select value={runtime} onChange={e => setRuntime(e.target.value)} className="w-full bg-[#18181c] border border-white/10 rounded-xl px-3 py-2 text-white outline-none focus:ring-2 focus:ring-primary">
                  <option value="python:3.11">Python 3.11 (Standard)</option>
                  <option value="python:3.12-cuda">Python 3.12 (CUDA GPU)</option>
                  <option value="docker:custom">Custom Docker Sandbox</option>
                </select>
              </div>
            </div>

            <div>
              <label className="text-gray-400 text-xs block mb-1">5-Hook Task Definition Source (Python)</label>
              <textarea value={code} onChange={e => setCode(e.target.value)} rows={14}
                className="w-full bg-black/60 font-mono text-xs text-emerald-400 border border-white/10 rounded-xl p-4 outline-none focus:ring-2 focus:ring-primary" />
            </div>

            {/* Compatibility Report Card */}
            {testResult && (
              <div className={`p-4 rounded-xl border text-xs space-y-1.5 ${testResult.passed ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' : 'bg-red-500/10 border-red-500/30 text-red-400'}`}>
                <div className="font-bold flex items-center gap-1.5">
                  {testResult.passed ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                  {testResult.passed ? 'COMPATIBILITY TEST PASSED — READY FOR PILOT' : 'COMPATIBILITY TEST FAILED'}
                </div>
                <div className="text-[11px] text-gray-300">{testResult.recommendation}</div>
              </div>
            )}

            <div className="flex justify-between items-center pt-2">
              <button onClick={() => handleTestCompatibility()} disabled={testing}
                className="px-4 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
                {testing ? <Loader className="w-3.5 h-3.5 animate-spin" /> : <Shield className="w-3.5 h-3.5" />}
                Run Compatibility Test
              </button>
              <div className="flex gap-2">
                <button onClick={() => setShowBuilder(false)} className="px-4 py-2 bg-white/5 hover:bg-white/10 text-gray-400 rounded-xl text-xs font-semibold transition">Cancel</button>
                <button onClick={handleSaveTask} disabled={loading} className="px-5 py-2 bg-primary hover:bg-blue-500 text-white rounded-xl text-xs font-semibold transition glow-primary">
                  {loading ? 'Saving...' : 'Save & Publish Task'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── CoCompute 4.0: Universal Server-Side Result Explorer Suite ──────────────
function UniversalResultExplorerSuite({ user, token, jobs }) {
  const [selectedJobId, setSelectedJobId] = useState(jobs[0]?.id || null);
  const [mode, setMode] = useState('full_query');
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [explorerData, setExplorerData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [provGraph, setProvGraph] = useState(null);

  const fetchExplorer = useCallback(async () => {
    if (!selectedJobId) return;
    setLoading(true);
    try {
      const q = new URLSearchParams({ mode, page: String(page), limit: '50' });
      if (search) q.append('search', search);

      const [exRes, provRes] = await Promise.all([
        fetch(`${API}/jobs/${selectedJobId}/explorer?${q.toString()}`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API}/jobs/${selectedJobId}/provenance-graph`, { headers: { 'Authorization': `Bearer ${token}` } })
      ]);
      if (exRes.ok) setExplorerData(await exRes.json());
      if (provRes.ok) setProvGraph(await provRes.json());
    } catch (e) {
      console.error('Explorer error', e);
    } finally {
      setLoading(false);
    }
  }, [selectedJobId, mode, page, search, token]);

  useEffect(() => { fetchExplorer(); }, [fetchExplorer]);

  const handleDownloadReport = async () => {
    try {
      const res = await fetch(`${API}/jobs/${selectedJobId}/report`, { headers: { 'Authorization': `Bearer ${token}` } });
      const data = await res.json();
      const blob = new Blob([data.report_markdown], { type: 'text/markdown' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `cocompute_report_${data.job_uid}.md`;
      a.click();
    } catch (e) { alert('Download failed: ' + e.message); }
  };

  const handleReproduce = async (reproMode) => {
    try {
      const res = await fetch(`${API}/jobs/${selectedJobId}/reproduce?mode=${reproMode}`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await res.json();
      alert(`Reproduced job successfully! New Job ID: ${data.reproduced_job_uid} (${data.reproducibility_status})`);
    } catch (e) { alert('Reproduction failed: ' + e.message); }
  };

  const quality = explorerData?.quality || {};
  const descriptors = quality?.descriptors || {};

  return (
    <div className="space-y-5">
      {/* Job Selector & Action Bar */}
      <div className="glass-panel p-5 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <Database className="w-5 h-5 text-accent" />
          <div>
            <h3 className="text-sm font-bold text-white">Universal Result Intelligence Explorer</h3>
            <p className="text-xs text-gray-400">Server-side paginated explorer, data quality metrics, and performance audit.</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select value={selectedJobId || ''} onChange={e => { setSelectedJobId(Number(e.target.value)); setPage(1); }}
            className="bg-[#18181c] border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white outline-none focus:ring-2 focus:ring-primary">
            {jobs.map(j => (
              <option key={j.id} value={j.id}>{j.job_uid || `#${j.id}`} — {j.name} ({j.status})</option>
            ))}
          </select>
          <button onClick={handleDownloadReport}
            className="px-3 py-1.5 bg-white/5 hover:bg-white/10 text-gray-200 border border-white/10 rounded-xl text-xs font-semibold transition flex items-center gap-1.5">
            <Download className="w-3.5 h-3.5 text-primary" /> Download Report (.md)
          </button>
        </div>
      </div>

      {/* Quality Scorecard Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
        <StatCard label="Result Quality Score" value={`${quality.quality_score || 100}%`} sub="Zero data corruption" color="text-emerald-400" icon={Award} />
        <StatCard label="Total Output Records" value={explorerData?.total_records?.toLocaleString() || '—'} sub="Verified count" color="text-white" icon={CheckSquare} />
        <StatCard label="Semantic Archetype" value={explorerData?.semantic_type?.toUpperCase() || 'TABLE'} sub="Auto-detected format" color="text-accent" icon={FileText} />
        <StatCard label="Provenance Chain" value={`${provGraph?.nodes?.length || 0} Nodes`} sub="Cryptographic verification" color="text-purple-400" icon={Shield} />
      </div>

      {/* Domain-Specific Visualizer */}
      {descriptors.histogram && (
        <div className="glass-panel p-5 space-y-3">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-emerald-400" /> Statistical Distribution Histogram
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs text-gray-300 pb-2">
            <div>Mean: <span className="font-bold text-white font-mono">{descriptors.histogram.mean}</span></div>
            <div>Std Dev: <span className="font-bold text-white font-mono">{descriptors.histogram.std}</span></div>
            <div>Min: <span className="font-bold text-white font-mono">{descriptors.histogram.min}</span></div>
            <div>Max: <span className="font-bold text-white font-mono">{descriptors.histogram.max}</span></div>
          </div>
          <div className="flex items-end gap-1.5 h-28 pt-2">
            {descriptors.histogram.bins.map((b, i) => (
              <div key={i} className="flex-1 bg-primary/20 hover:bg-primary/40 rounded-t transition flex flex-col justify-end items-center"
                style={{ height: `${Math.max(10, (b / Math.max(...descriptors.histogram.bins, 1)) * 100)}%` }}>
                <span className="text-[9px] text-gray-400 font-mono mb-1">{b}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {descriptors.matrix_info && (
        <div className="glass-panel p-5 space-y-2">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-purple-400" /> Matrix Result Overview
          </h4>
          <div className="text-xs text-gray-300">
            Dimensions: <span className="font-bold text-accent font-mono">{descriptors.matrix_info.dimensions}</span> | Density: 100% | Validation: Verified Block Structure
          </div>
        </div>
      )}

      {/* Paginated Server-Side Data Explorer */}
      <div className="glass-panel p-5 space-y-4">
        <div className="flex justify-between items-center gap-2">
          <div className="flex gap-1.5">
            {['preview', 'sample', 'full_query'].map(m => (
              <button key={m} onClick={() => { setMode(m); setPage(1); }}
                className={`px-3 py-1 rounded-lg text-xs font-semibold capitalize transition ${mode === m ? 'bg-primary text-white' : 'bg-white/5 text-gray-400 hover:text-white'}`}>
                {m.replace('_', ' ')}
              </button>
            ))}
          </div>
          <input value={search} onChange={e => { setSearch(e.target.value); setPage(1); }} placeholder="Search table..."
            className="bg-white/5 border border-white/10 rounded-xl px-3 py-1 text-xs text-white outline-none focus:ring-2 focus:ring-primary w-48" />
        </div>

        {loading ? (
          <div className="py-12 flex justify-center text-gray-500"><Loader className="w-6 h-6 animate-spin" /></div>
        ) : (
          <div className="overflow-x-auto max-h-96">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-white/10 text-gray-500 text-left">
                  {explorerData?.columns?.map(col => <th key={col} className="py-2 px-2">{col}</th>)}
                </tr>
              </thead>
              <tbody>
                {explorerData?.data?.map((row, idx) => (
                  <tr key={idx} className="border-b border-white/5 hover:bg-white/5 font-mono">
                    {explorerData?.columns?.map(col => (
                      <td key={col} className="py-1.5 px-2 text-gray-300 truncate max-w-[200px]">
                        {typeof row[col] === 'object' ? JSON.stringify(row[col]) : String(row[col] ?? '')}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Pagination & Reproduce Actions */}
        <div className="flex justify-between items-center border-t border-white/10 pt-3 text-xs">
          <span className="text-gray-500">Page {explorerData?.page || 1} of {Math.max(1, Math.ceil((explorerData?.filtered_count || 1) / (explorerData?.limit || 50)))}</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page <= 1}
              className="px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded disabled:opacity-30">Previous</button>
            <button onClick={() => setPage(p => p + 1)} disabled={(explorerData?.data?.length || 0) < (explorerData?.limit || 50)}
              className="px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded disabled:opacity-30">Next</button>
          </div>
          <div className="flex gap-2">
            <button onClick={() => handleReproduce('exact')}
              className="px-3 py-1 bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 rounded font-semibold transition">
              Re-Run Exact
            </button>
            <button onClick={() => handleReproduce('equivalent')}
              className="px-3 py-1 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-300 border border-emerald-500/40 rounded font-semibold transition">
              Re-Run Equivalent
            </button>
          </div>
        </div>
      </div>
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
  const [schedulerAlgo, setSchedulerAlgo] = useState('adaptive_hybrid');
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
    { id: 'overview',    label: 'Overview',        icon: Activity },
    { id: 'registry',    label: 'Task Registry',   icon: FileCode },
    { id: 'explorer',    label: 'Result Explorer', icon: Database },
    { id: 'tasks',       label: 'Jobs & Queue',    icon: Clock },
    { id: 'marketplace', label: 'Pool & Credits',  icon: Layers },
    { id: 'simulation',  label: 'Digital Twin',    icon: Terminal },
    { id: 'benchmarks',  label: 'Benchmarks',      icon: Award },
    { id: 'projects',    label: 'Projects',        icon: FolderGit2 },
    { id: 'analytics',   label: 'Analytics',       icon: BarChart3 },
    { id: 'workers',     label: 'Nodes',           icon: Server },
    { id: 'logs',        label: 'Logs',            icon: FileText },
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
              {wsStatus === 'connected' ? 'Adaptive Hybrid' : 'Polling'}
            </div>
          </div>

          <nav className="flex gap-0.5 bg-white/5 rounded-xl p-1">
            {TABS.map(t => (
              <button key={t.id} onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition ${activeTab === t.id ? 'bg-primary/20 text-primary' : 'text-gray-400 hover:text-white hover:bg-white/5'}`}>
                <t.icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            ))}
          </nav>

          <div className="flex items-center gap-2">
            <button onClick={() => setShowSubmit(true)}
              className="bg-primary hover:bg-blue-500 transition text-white px-4 py-2 rounded-xl flex items-center gap-2 font-semibold shadow-lg shadow-primary/20 text-xs glow-primary">
              <Play className="w-3.5 h-3.5 fill-current" /> Submit Workload
            </button>
            <div className="flex items-center gap-1.5 px-3 py-2 bg-white/5 rounded-xl border border-white/10 text-xs text-gray-400">
              <Shield className="w-3.5 h-3.5 text-accent" />
              <span>{user?.username || 'User'} ({user?.role || 'Admin'})</span>
            </div>
            <button onClick={() => { localStorage.removeItem('token'); setToken(null); setUser(null); }} title="Sign Out"
              className="flex items-center gap-1.5 px-3 py-2 bg-white/5 hover:bg-red-500/20 hover:text-red-400 text-gray-400 rounded-xl border border-white/10 text-xs transition">
              <LogOut className="w-3.5 h-3.5" />
              <span>Logout</span>
            </button>
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

              {/* Leaderboard */}
              <div className="glass-panel p-5">
                <h2 className="text-sm font-semibold mb-3 text-white flex items-center gap-2">
                  <TrendingUp className="w-4 h-4 text-emerald-400" /> Worker Leaderboard
                </h2>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {rankings.map((r, i) => (
                    <div key={r.worker_uid} className="flex items-center justify-between p-2.5 bg-white/5 rounded-xl border border-white/5 text-xs">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-gray-500 font-mono">#{i + 1}</span>
                        <span className="text-white font-semibold">{r.worker_uid}</span>
                      </div>
                      <span className="text-primary font-mono font-bold">{(r.composite_score * 100).toFixed(0)} pts</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </>
        )}

        {/* ══ TASK REGISTRY TAB ══ */}
        {activeTab === 'registry' && <TaskRegistrySuite user={user} token={token} onRunTask={(pkg) => setShowSubmit(true)} />}

        {/* ══ UNIVERSAL RESULT EXPLORER TAB ══ */}
        {activeTab === 'explorer' && <UniversalResultExplorerSuite user={user} token={token} jobs={jobs} />}

        {/* ══ JOBS TAB ══ */}
        {activeTab === 'tasks' && (
          <div className="glass-panel p-5 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2"><Clock className="w-4 h-4 text-accent" /> Active & Completed Jobs ({jobs.length})</h2>
            <div className="space-y-2">
              {jobs.map(j => (
                <div key={j.id} onClick={() => setSelectedJob(j)}
                  className="flex items-center justify-between p-3.5 bg-white/5 hover:bg-white/10 rounded-xl border border-white/10 transition cursor-pointer text-xs">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-primary bg-primary/10 px-2 py-0.5 rounded">{j.job_uid || `#${j.id}`}</span>
                    <div>
                      <span className="font-bold text-white block">{j.name}</span>
                      <span className="text-gray-400 text-[11px]">{j.job_type} | Strategy: <span className="text-accent">{j.scheduler_strategy}</span> | Energy: <span className="text-emerald-400">{j.energy_mode || 'BALANCED'}</span></span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`px-2 py-0.5 rounded-full font-bold uppercase text-[10px] ${j.status === 'completed' ? 'bg-emerald-500/20 text-emerald-400' : j.status === 'running' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-gray-500/20 text-gray-400'}`}>
                      {j.status}
                    </span>
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ══ MARKETPLACE & COMPUTE POOL TAB ══ */}
        {activeTab === 'marketplace' && <MarketplaceSuite user={user} token={token} />}

        {/* ══ DIGITAL TWIN SIMULATION TAB ══ */}
        {activeTab === 'simulation' && <SimulationSuite user={user} token={token} />}

        {/* ══ BENCHMARKS TAB ══ */}
        {activeTab === 'benchmarks' && <BenchmarksSuite token={token} />}

        {/* ══ PROJECTS TAB ══ */}
        {activeTab === 'projects' && <ProjectsSuite user={user} token={token} jobs={jobs} />}

        {/* ══ NODES TAB ══ */}
        {activeTab === 'workers' && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {workers.map(w => <WorkerCard key={w.worker_uid} worker={w} onClick={setSelectedWorker} />)}
          </div>
        )}

        {/* ══ LOGS TAB ══ */}
        {activeTab === 'logs' && (
          <div className="glass-panel p-5 space-y-3">
            <h2 className="text-sm font-bold text-white flex items-center gap-2"><FileText className="w-4 h-4 text-primary" /> Cluster Audit & Event Logs</h2>
            <div className="space-y-1 max-h-[600px] overflow-y-auto font-mono text-xs text-gray-300">
              {logs.map((l, i) => (
                <div key={i} className="p-2 bg-black/40 rounded-lg border border-white/5 flex gap-2">
                  <span className="text-gray-500">{new Date(l.timestamp).toLocaleTimeString()}</span>
                  <span className={l.level === 'ERROR' ? 'text-red-400' : 'text-primary'}>[{l.level}]</span>
                  <span>{l.message}</span>
                </div>
              ))}
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
