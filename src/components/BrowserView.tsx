import React, { useState } from "react";
import {
  Globe,
  ArrowLeft,
  ArrowRight,
  RotateCw,
  Search,
  ExternalLink,
  Terminal,
  Activity,
  Play,
  PlayCircle,
  Download,
  CheckCircle2,
  AlertCircle
} from "lucide-react";
import { BrowserTab } from "../types";

interface BrowserViewProps {
  tabs: BrowserTab[];
  setTabs: React.Dispatch<React.SetStateAction<BrowserTab[]>>;
  triggerNotification: (title: string, msg: string, type: any) => void;
}

export default function BrowserView({
  tabs,
  setTabs,
  triggerNotification,
}: BrowserViewProps) {
  const [activeTabId, setActiveTabId] = useState(tabs[0]?.id || "");
  const [urlInput, setUrlInput] = useState(tabs[0]?.url || "");
  const [logs] = useState<string[]>([]);

  const activeTab = tabs.find(t => t.id === activeTabId) || null;

  const handleNavigate = (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    const tab: BrowserTab = {
      id: "tab-" + Date.now(),
      url: urlInput,
      title: urlInput.replace("https://", "").replace("http://", "").split("/")[0],
      status: "loaded",
      content: "No browser automation backend is connected for this URL yet.",
    };

    setTabs(prev => [tab, ...prev]);
    setActiveTabId(tab.id);
    triggerNotification("Browser Tab Recorded", `Added "${tab.title}" to the local UI session.`, "info");
  };

  const handleTriggerAutomation = () => {
    triggerNotification("Browser Automation Unavailable", "No real browser automation service is connected yet.", "warning");
  };

  return (
    <div className="flex-1 flex overflow-hidden text-slate-200">
      
      {/* Left side: Browser viewport frame */}
      <div className="flex-1 flex flex-col h-full border-r border-slate-800/40">
        {/* Navigation Bar */}
        <div className="px-6 py-3 border-b border-slate-800/40 bg-slate-950/40 flex items-center gap-3 shrink-0">
          <div className="flex items-center gap-1.5 shrink-0">
            <button className="p-1 hover:bg-slate-900 rounded text-slate-500 hover:text-slate-200 cursor-pointer"><ArrowLeft className="w-4 h-4" /></button>
            <button className="p-1 hover:bg-slate-900 rounded text-slate-500 hover:text-slate-200 cursor-pointer"><ArrowRight className="w-4 h-4" /></button>
            <button className="p-1 hover:bg-slate-900 rounded text-slate-500 hover:text-slate-200 cursor-pointer"><RotateCw className="w-3.5 h-3.5" /></button>
          </div>

          <form onSubmit={handleNavigate} className="flex-1 relative flex items-center">
            <Globe className="absolute left-3 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Enter web link to autonomous navigation index..."
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="w-full glass-input pl-9 pr-3 py-1.5 h-9 text-xs"
            />
          </form>

          <button
            onClick={handleTriggerAutomation}
            className="px-3.5 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-bold text-white flex items-center gap-1.5 shrink-0 transition-colors cursor-pointer"
          >
            <PlayCircle className="w-4 h-4 animate-pulse" />
            <span>Run Automation</span>
          </button>
        </div>

        {/* Browser Display */}
        <div className="flex-1 overflow-y-auto p-6 bg-slate-950/40">
          {activeTab ? (
            <div className="max-w-3xl mx-auto glass-panel border border-slate-800/80 rounded-2xl overflow-hidden shadow-2xl">
              
              <div className="px-4 py-2 bg-slate-950 border-b border-slate-900 flex items-center justify-between text-[10px] font-mono text-slate-500">
                <span className="flex items-center gap-1.5 font-bold"><Globe className="w-3.5 h-3.5 text-blue-500" /> RECORDED URL</span>
                <span>STATUS: {activeTab.status}</span>
              </div>

              {/* Render body preview */}
              <div className="p-6 space-y-4">
                {activeTab.status === "loading" ? (
                  <div className="py-20 text-center space-y-3">
                    <span className="relative flex h-6 w-6 mx-auto">
                      <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                      <span className="relative inline-flex rounded-full h-6 w-6 bg-blue-500"></span>
                    </span>
                    <span className="text-xs font-mono text-slate-400 block animate-pulse">AUTONOMOUS_RENDERING_DOM_TREE...</span>
                  </div>
                ) : (
                  <div className="prose prose-invert prose-xs text-xs text-slate-300">
                    <p className="font-semibold text-sm text-white mb-2">Web Content for: {activeTab.url}</p>
                    <div className="whitespace-pre-wrap leading-relaxed font-mono bg-slate-950/60 p-4 border border-slate-900 rounded-xl text-emerald-400">
                      {activeTab.content}
                    </div>
                  </div>
                )}
              </div>

            </div>
          ) : (
            <div className="text-center text-slate-500 p-12 text-xs">No browser records yet.</div>
          )}
        </div>
      </div>

      {/* Right side: Autonomous automation logs */}
      <div className="w-80 border-l border-slate-800/40 p-5 flex flex-col h-full bg-slate-950/10 shrink-0">
        <div className="flex items-center gap-2 mb-3 shrink-0">
          <Terminal className="w-4 h-4 text-purple-400" />
          <h2 className="text-sm font-mono font-bold text-white uppercase tracking-wider">Browser Console Log</h2>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 bg-slate-950/40 p-3.5 border border-slate-900 rounded-xl font-mono text-[10px] text-slate-400 space-y-2">
          {logs.length === 0 && (
            <div className="text-slate-600">No browser automation logs recorded.</div>
          )}
          {logs.map((log, idx) => (
            <div key={idx} className="leading-relaxed border-b border-slate-900 pb-1 last:border-0">
              {log}
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
