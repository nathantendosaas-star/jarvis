import React, { useState } from "react";
import {
  Play,
  RotateCw,
  Plus,
  PlusCircle,
  Zap,
  Bot,
  Mail,
  FileCode,
  CheckCircle2,
  Clock,
  ArrowRight,
  TrendingUp,
  AlertTriangle,
  PlayCircle
} from "lucide-react";
import { WorkflowNode, WorkflowConnection } from "../types";

interface AutomationViewProps {
  nodes: WorkflowNode[];
  setNodes: React.Dispatch<React.SetStateAction<WorkflowNode[]>>;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function AutomationView({
  nodes,
  triggerNotification,
}: AutomationViewProps) {
  const [history] = useState<Array<{ id: string; name: string; time: string; status: string; logs: string }>>([]);

  const handleRunPipeline = () => {
    triggerNotification("Automation Unavailable", "No real automation runner is connected yet.", "warning");
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 text-slate-200">
      
      {/* Intro Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-800/40">
        <div>
          <h1 className="text-xl font-display font-bold text-white tracking-wide mt-0.5">Workflow Automations</h1>
          <p className="text-xs text-slate-400 mt-1">Design triggers, conditions, modeling actions, and notifications connected as automated sequences.</p>
        </div>

        <button
          onClick={handleRunPipeline}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl text-xs transition-all flex items-center gap-2 shadow-lg shadow-blue-600/20 cursor-pointer"
        >
          <Play className="w-3.5 h-3.5" />
          <span>Run Pipeline</span>
        </button>
      </div>

      {/* SVG Connections & Flex Node board layout */}
      <div className="glass-panel p-6 rounded-xl border border-slate-800/60 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-purple-600/5 rounded-full blur-3xl -z-10" />

        <div className="flex items-center justify-between mb-6">
          <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold">Active Visual Layout Canvas</span>
          <span className="text-xs text-slate-400 font-semibold">{nodes.length} connected modules</span>
        </div>

        {/* Visual Pipeline layout */}
        <div className="relative flex flex-col md:flex-row items-center justify-between gap-8 md:gap-4 py-8">
          
          {/* Animated SVG connecting lines */}
          <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 border-t-2 border-dashed border-slate-800 -translate-y-1/2 -z-10 animate-dash" />

          {nodes.length === 0 && (
            <div className="w-full py-16 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No workflow nodes are stored in the backend yet.
            </div>
          )}
          {nodes.map((node) => {
            const isCompleted = node.status === "completed";
            const isRunning = node.status === "running";

            const getIcon = () => {
              switch (node.type) {
                case "trigger": return <Zap className="w-5 h-5 text-amber-400" />;
                case "ai": return <Bot className="w-5 h-5 text-purple-400" />;
                case "action": return <FileCode className="w-5 h-5 text-blue-400" />;
                default: return <Mail className="w-5 h-5 text-emerald-400" />;
              }
            };

            const getBorderStyles = () => {
              if (isRunning) return "border-blue-500 shadow-md shadow-blue-500/10 animate-pulse";
              if (isCompleted) return "border-emerald-500 bg-slate-900/40";
              return "border-slate-800 bg-transparent";
            };

            return (
              <div
                key={node.id}
                className={`w-52 glass-panel p-4 rounded-xl border flex flex-col space-y-3 relative transition-all ${getBorderStyles()}`}
              >
                {/* Node Status Dot indicator */}
                <div className="absolute -top-1.5 -right-1.5 flex h-3 w-3">
                  {isRunning && (
                    <>
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
                    </>
                  )}
                  {isCompleted && (
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500" />
                  )}
                  {!isRunning && !isCompleted && (
                    <span className="relative inline-flex rounded-full h-3 w-3 bg-slate-700" />
                  )}
                </div>

                <div className="flex items-center gap-2.5">
                  <div className="p-2 bg-slate-950 border border-slate-900 rounded-lg shrink-0">
                    {getIcon()}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold text-white line-clamp-1">{node.name}</h4>
                    <span className="text-[9px] font-mono text-slate-500 uppercase tracking-wider">{node.type}</span>
                  </div>
                </div>

                <div className="pt-2 border-t border-slate-850 text-[10px] text-slate-400 font-mono space-y-1">
                  {Object.entries(node.config).map(([k, v]) => (
                    <div key={k} className="flex justify-between">
                      <span className="text-slate-500">{k}:</span>
                      <span className="text-slate-300 font-bold truncate max-w-[100px]">{String(v)}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Execution history list logs */}
      <div className="glass-panel p-5 rounded-xl border border-slate-800/60 space-y-4">
        <span className="text-[10px] font-mono text-slate-500 uppercase tracking-wider font-semibold block">Automation execution registry</span>
        
        <div className="space-y-2">
          {history.length === 0 && (
            <div className="p-6 text-center text-xs text-slate-500 border border-dashed border-slate-800 rounded-xl">
              No automation execution records available.
            </div>
          )}
          {history.map((hist) => (
            <div
              key={hist.id}
              className="p-3 bg-slate-900/30 border border-slate-850 hover:border-slate-800 rounded-xl flex items-center justify-between gap-4 transition-all text-xs"
            >
              <div className="flex items-center gap-3">
                <CheckCircle2 className={`w-4 h-4 shrink-0 ${hist.status === 'completed' ? "text-emerald-500" : "text-red-500"}`} />
                <div>
                  <h4 className="font-bold text-white">{hist.name}</h4>
                  <span className="text-[10px] text-slate-500 font-mono">Logs: {hist.logs}</span>
                </div>
              </div>

              <span className="text-[10px] font-mono text-slate-500">{hist.time}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
