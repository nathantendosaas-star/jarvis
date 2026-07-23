import React, { useMemo, useState, useEffect } from "react";
import {
  Cpu,
  Database,
  Play,
  Pause,
  RotateCw,
  CheckCircle2,
  TrendingUp,
  Sliders,
  Sparkles,
  RefreshCw,
  Activity,
  MoreVertical
} from "lucide-react";
import {
  AreaChart,
  Area,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip
} from "recharts";
import { Agent } from "../types";

interface AgentsViewProps {
  agents: Agent[];
  setAgents: React.Dispatch<React.SetStateAction<Agent[]>>;
  onUpdateAgent: (
    agentId: string,
    patch: {
      status?: string;
      priority?: string;
      cpu_allocation?: number;
      memory_allocation?: number;
      current_task?: string | null;
      activity?: string[];
    }
  ) => Promise<void>;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

// Generate stable mock 24h data based on current usage
const MOCK_DELTAS: Record<string, number[]> = {
  "a-ceo": Array.from({ length: 13 }).map(() => Math.random() * 20 - 10),
  "a-dev": Array.from({ length: 13 }).map(() => Math.random() * 20 - 10),
  "a-res": Array.from({ length: 13 }).map(() => Math.random() * 20 - 10),
  "a-mkt": Array.from({ length: 13 }).map(() => Math.random() * 20 - 10),
};

const getTrendData = (id: string, baseCpu: number, baseMem: number) => {
  const deltas = MOCK_DELTAS[id] || MOCK_DELTAS["a-ceo"];
  return deltas.map((variance, idx) => {
    const time = idx === 12 ? "Now" : `-${(12 - idx) * 2}h`;
    return {
      time,
      cpu: Math.max(0, Math.min(100, Math.round(baseCpu + variance))),
      memory: Math.max(0, Math.min(512, Math.round(baseMem + variance * 2))),
    };
  });
};

export default function AgentsView({
  agents,
  setAgents,
  onUpdateAgent,
  triggerNotification,
}: AgentsViewProps) {
  const [openMenuAgentId, setOpenMenuAgentId] = useState<string | null>(null);

  useEffect(() => {
    const handleOutsideClick = () => setOpenMenuAgentId(null);
    window.addEventListener("click", handleOutsideClick);
    return () => window.removeEventListener("click", handleOutsideClick);
  }, []);

  const handleSetPriority = (id: string, priority: "high" | "medium" | "low") => {
    // Optimistic local update
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          triggerNotification("Priority Shift", `${a.name} task priority queue reallocated to ${priority.toUpperCase()}.`, "info");
          return {
            ...a,
            priority,
            activity: [`Task priority set to ${priority.toUpperCase()}`, ...a.activity]
          };
        }
        return a;
      })
    );
    // Persist to backend
    onUpdateAgent(id, { priority });
  };
  
  const handleToggleStatus = (id: string) => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          const nextStatus = a.status === "working" || a.status === "idle" ? "paused" : "idle";
          triggerNotification("Agent Sync Update", `${a.name} status updated to: ${nextStatus}.`, "info");
          // Persist to backend
          onUpdateAgent(id, {
            status: nextStatus,
            cpu_allocation: nextStatus === "paused" ? 0 : a.usage.cpu,
            memory_allocation: nextStatus === "paused" ? 0 : a.usage.memory,
          });
          return {
            ...a,
            status: nextStatus as any,
            usage: nextStatus === "paused" ? { cpu: 0, memory: 0 } : a.usage
          };
        }
        return a;
      })
    );
  };

  const handleRestartAgent = (id: string) => {
    const restartedCpu = 45;
    const restartedMem = 120;
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          triggerNotification("Orchestrator Action", `Rebooting ${a.name} cognitive node...`, "warning");
          return {
            ...a,
            status: "working" as any,
            usage: { cpu: restartedCpu, memory: restartedMem }
          };
        }
        return a;
      })
    );
    // Persist to backend
    onUpdateAgent(id, { status: "working", cpu_allocation: restartedCpu, memory_allocation: restartedMem });
    setTimeout(() => {
      triggerNotification("Node Calibrated", `Agent successfully synchronized and online.`, "success");
    }, 1500);
  };

  const handleSliderChange = (id: string, field: "cpu" | "memory", value: number) => {
    setAgents(prev =>
      prev.map(a => {
        if (a.id === id) {
          return {
            ...a,
            usage: {
              ...a.usage,
              [field]: value
            }
          };
        }
        return a;
      })
    );
    // Persist to backend (debounced by the slider interaction itself)
    const patch = field === "cpu"
      ? { cpu_allocation: value }
      : { memory_allocation: value };
    onUpdateAgent(id, patch);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
      
      {/* Intro Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
        <div>
          <h1 className="text-xl font-display font-bold text-white tracking-wide mt-0.5">Agent Workforce</h1>
          <p className="text-xs text-slate-400 mt-1">Deploy, monitor, and configure specialized AI agents in your environment.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono text-slate-400">Active Agents: {agents.filter(a => a.status === 'working').length}</span>
        </div>
      </div>

      {/* Grid of Agent Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
        {agents.map((agent) => {
          const isWorking = agent.status === "working";
          const isPaused = agent.status === "paused";
          const isIdle = agent.status === "idle";

          return (
            <div
              key={agent.id}
              className={`glass-panel p-5 rounded-xl border transition-all relative ${
                isWorking
                  ? "border-blue-500/30 shadow-lg shadow-blue-500/5 bg-slate-900/50"
                  : "border-slate-800/60 bg-transparent"
              } flex flex-col justify-between space-y-4`}
            >
              {/* Header: Avatar, Name, Status Badge & Quick Actions Trigger */}
              <div className="flex items-start justify-between relative">
                <div className="flex gap-3">
                  <span className="text-3xl bg-slate-900 border border-slate-800 rounded-xl p-2.5 shadow-sm block leading-none shrink-0">
                    {agent.avatar}
                  </span>
                  <div>
                    <h3 className="font-bold text-white text-sm">{agent.name}</h3>
                    <span className="text-[10px] font-mono text-slate-500">{agent.role}</span>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex flex-col items-end gap-1">
                    <span className={`text-[9px] font-mono px-2 py-0.5 rounded-full font-bold uppercase ${
                      isWorking ? "bg-blue-500/10 text-blue-400 border border-blue-500/20" :
                      isPaused ? "bg-amber-500/10 text-amber-400 border border-amber-500/20" :
                      "bg-slate-800/80 text-slate-400 border border-slate-700/50"
                    }`}>
                      {agent.status}
                    </span>
                    {agent.priority && (
                      <span className={`text-[8px] font-mono px-1.5 py-0.5 rounded border uppercase tracking-wider font-semibold ${
                        agent.priority === "high" ? "bg-rose-500/10 text-rose-400 border-rose-500/20" :
                        agent.priority === "medium" ? "bg-purple-500/10 text-purple-400 border-purple-500/20" :
                        "bg-slate-800/50 text-slate-400 border-slate-700/30"
                      }`}>
                        {agent.priority}
                      </span>
                    )}
                  </div>

                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setOpenMenuAgentId(prev => prev === agent.id ? null : agent.id);
                    }}
                    className="p-1.5 bg-slate-900/60 hover:bg-slate-800 border border-slate-800 hover:border-slate-700 rounded-lg text-slate-400 hover:text-white transition-all cursor-pointer"
                    title="Quick Actions"
                  >
                    <MoreVertical className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Floating Quick Actions Menu */}
              {openMenuAgentId === agent.id && (
                <div 
                  className="absolute right-5 top-16 w-52 bg-slate-950/95 backdrop-blur-lg border border-slate-800 rounded-xl shadow-2xl z-40 p-1.5 space-y-1"
                  onClick={(e) => e.stopPropagation()}
                >
                  <div className="px-2.5 py-1 text-[9px] font-mono text-slate-500 uppercase tracking-widest font-semibold border-b border-slate-900/60 pb-1.5 mb-1">
                    Quick Actions
                  </div>

                  {/* Pause / Resume */}
                  <button
                    onClick={() => {
                      handleToggleStatus(agent.id);
                      setOpenMenuAgentId(null);
                    }}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    {isWorking ? (
                      <>
                        <Pause className="w-3.5 h-3.5 text-amber-500" />
                        <span>Pause Operations</span>
                      </>
                    ) : (
                      <>
                        <Play className="w-3.5 h-3.5 text-emerald-500" />
                        <span>Resume Operations</span>
                      </>
                    )}
                  </button>

                  {/* Restart Node */}
                  <button
                    onClick={() => {
                      handleRestartAgent(agent.id);
                      setOpenMenuAgentId(null);
                    }}
                    className="w-full text-left flex items-center gap-2 px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer"
                  >
                    <RefreshCw className="w-3.5 h-3.5 text-blue-400" />
                    <span>Restart / Reboot Node</span>
                  </button>

                  <div className="border-t border-slate-900/60 my-1 pt-1" />

                  <div className="px-2.5 py-1 text-[9px] font-mono text-slate-500 uppercase tracking-widest font-semibold">
                    Re-prioritize Task
                  </div>

                  {/* High priority */}
                  <button
                    onClick={() => {
                      handleSetPriority(agent.id, "high");
                      setOpenMenuAgentId(null);
                    }}
                    className={`w-full text-left flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer ${
                      agent.priority === "high" ? "bg-rose-500/10 text-rose-400 font-semibold" : ""
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-rose-500 shadow-sm shadow-rose-500/50" />
                      <span>High Priority</span>
                    </span>
                    {agent.priority === "high" && <span className="text-[9px] font-mono bg-rose-500/20 text-rose-400 px-1.5 py-0.5 rounded border border-rose-500/10 scale-90">Active</span>}
                  </button>

                  {/* Medium priority */}
                  <button
                    onClick={() => {
                      handleSetPriority(agent.id, "medium");
                      setOpenMenuAgentId(null);
                    }}
                    className={`w-full text-left flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer ${
                      agent.priority === "medium" ? "bg-purple-500/10 text-purple-400 font-semibold" : ""
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-purple-500 shadow-sm shadow-purple-500/50" />
                      <span>Medium Priority</span>
                    </span>
                    {agent.priority === "medium" && <span className="text-[9px] font-mono bg-purple-500/20 text-purple-400 px-1.5 py-0.5 rounded border border-purple-500/10 scale-90">Active</span>}
                  </button>

                  {/* Low priority */}
                  <button
                    onClick={() => {
                      handleSetPriority(agent.id, "low");
                      setOpenMenuAgentId(null);
                    }}
                    className={`w-full text-left flex items-center justify-between px-2.5 py-1.5 rounded-md text-xs hover:bg-slate-900 text-slate-300 hover:text-white transition-all cursor-pointer ${
                      agent.priority === "low" ? "bg-slate-800/30 text-slate-400 font-semibold" : ""
                    }`}
                  >
                    <span className="flex items-center gap-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
                      <span>Low Priority</span>
                    </span>
                    {agent.priority === "low" && <span className="text-[9px] font-mono bg-slate-800/40 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700/10 scale-90">Active</span>}
                  </button>
                </div>
              )}

              {/* Memory allocations info */}
              <div className="space-y-3 pt-2.5 border-t border-slate-800/40">
                {/* CPU allocation slider */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span className="flex items-center gap-1"><Cpu className="w-3 h-3 text-blue-400" /> Allocated Cycles</span>
                    <span className="font-bold text-slate-300">{agent.usage.cpu}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    disabled={isPaused}
                    value={agent.usage.cpu}
                    onChange={(e) => handleSliderChange(agent.id, "cpu", parseInt(e.target.value))}
                    className="w-full accent-blue-500 h-1 bg-slate-900 rounded-lg cursor-pointer disabled:opacity-50"
                  />
                </div>

                {/* RAM Allocation slider */}
                <div className="space-y-1">
                  <div className="flex justify-between text-[10px] font-mono text-slate-500">
                    <span className="flex items-center gap-1"><Database className="w-3 h-3 text-purple-400" /> Synaptic Storage</span>
                    <span className="font-bold text-slate-300">{agent.usage.memory} MB</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="512"
                    step="8"
                    disabled={isPaused}
                    value={agent.usage.memory}
                    onChange={(e) => handleSliderChange(agent.id, "memory", parseInt(e.target.value))}
                    className="w-full accent-purple-500 h-1 bg-slate-900 rounded-lg cursor-pointer disabled:opacity-50"
                  />
                </div>
              </div>

              {/* Trend Chart */}
              <div className="h-28 w-full mt-2 -mb-2">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={getTrendData(agent.id, agent.usage.cpu, agent.usage.memory)} margin={{ top: 5, right: 0, left: -25, bottom: 0 }}>
                    <defs>
                      <linearGradient id={`colorCpu-${agent.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#60a5fa" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id={`colorMem-${agent.id}`} x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#c084fc" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#c084fc" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" stroke="#475569" fontSize={8} tickLine={false} axisLine={false} />
                    <YAxis stroke="#475569" fontSize={8} tickLine={false} axisLine={false} />
                    <Tooltip
                      contentStyle={{ backgroundColor: "#0f172a", borderColor: "#1e293b", borderRadius: "8px", color: "#f8fafc", fontSize: "10px", padding: "4px 8px" }}
                    />
                    <Area type="monotone" dataKey="cpu" stroke="#60a5fa" strokeWidth={1.5} fillOpacity={1} fill={`url(#colorCpu-${agent.id})`} name="CPU %" />
                    <Area type="monotone" dataKey="memory" stroke="#c084fc" strokeWidth={1.5} fillOpacity={1} fill={`url(#colorMem-${agent.id})`} name="Memory MB" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Capabilities checklist */}
              <div className="space-y-1">
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Cognitive Capabilities</span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.capabilities.map((cap, idx) => (
                    <span key={idx} className="text-[9px] font-mono bg-slate-950 border border-slate-850 px-2 py-0.5 rounded text-slate-400">
                      {cap}
                    </span>
                  ))}
                </div>
              </div>

              {/* Tools list */}
              <div className="space-y-1">
                <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Active Tool Access</span>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {agent.tools.map((tool, idx) => (
                    <span key={idx} className="text-[9px] font-mono bg-slate-900 border border-slate-800/60 px-2 py-0.5 rounded text-slate-400">
                      {tool}
                    </span>
                  ))}
                </div>
              </div>

              {/* Status Task text */}
              {isWorking && agent.currentTask && (
                <div className="p-2.5 bg-slate-950/60 border border-slate-900 rounded-lg space-y-1">
                  <div className="flex items-center gap-1 text-[9px] font-mono text-slate-500 uppercase">
                    <Activity className="w-3 h-3 text-blue-400 animate-pulse" />
                    <span>Real-time Operation:</span>
                  </div>
                  <p className="text-[11px] text-slate-300 leading-normal truncate">{agent.currentTask}</p>
                </div>
              )}

              {/* Action buttons footer */}
              <div className="flex gap-2 pt-2 border-t border-slate-800/40 justify-end">
                <button
                  onClick={() => handleToggleStatus(agent.id)}
                  className={`p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg transition-all cursor-pointer ${
                    isWorking ? "text-amber-400" : "text-emerald-400"
                  }`}
                  title={isWorking ? "Pause Node Operations" : "Initiate Node Operations"}
                >
                  {isWorking ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                </button>
                <button
                  onClick={() => handleRestartAgent(agent.id)}
                  className="p-2 bg-slate-900 hover:bg-slate-800 border border-slate-800 rounded-lg text-slate-400 hover:text-white transition-all cursor-pointer"
                  title="Calibrate / Reboot Node"
                >
                  <RefreshCw className="w-4 h-4" />
                </button>
              </div>

            </div>
          );
        })}
      </div>

    </div>
  );
}
