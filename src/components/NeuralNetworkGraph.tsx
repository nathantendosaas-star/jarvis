import React, { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { Brain, Search, Info, HelpCircle, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";
import { MemoryItem, Agent, Project } from "../types";

interface GraphNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  type: "root" | "agent" | "project" | "memory" | "file";
  details?: string;
  color: string;
  size: number;
}

interface GraphLink extends d3.SimulationLinkDatum<GraphNode> {
  source: string | GraphNode;
  target: string | GraphNode;
  value?: number;
}

interface NeuralNetworkGraphProps {
  memories: MemoryItem[];
  agents: Agent[];
  projects: Project[];
}

export default function NeuralNetworkGraph({ memories, agents, projects }: NeuralNetworkGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 500 });
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [hoveredNode, setHoveredNode] = useState<GraphNode | null>(null);

  // Auto-resize handler
  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({
          width: Math.max(width, 400),
          height: Math.max(height, 400)
        });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  // Compute graph data based on dynamic items
  const graphData = React.useMemo(() => {
    const nodes: GraphNode[] = [];
    const links: GraphLink[] = [];

    // 1. Root Core JARVIS Node
    nodes.push({
      id: "jarvis-core",
      label: "JARVIS OS Core",
      type: "root",
      details: "Central AI Orchestrator running live inside Cloud Sandbox. Synchronized with Gemini 3.1 Pro.",
      color: "#3b82f6", // Bright Blue
      size: 18
    });

    // 2. Active Agents
    agents.forEach((agent) => {
      nodes.push({
        id: agent.id,
        label: agent.name,
        type: "agent",
        details: `${agent.role} (Status: ${agent.status.toUpperCase()}). CPU: ${agent.usage.cpu}%, RAM: ${agent.usage.memory}MB.`,
        color: "#10b981", // Emerald
        size: 12
      });
      // Link Agent to JARVIS core
      links.push({ source: "jarvis-core", target: agent.id, value: 3 });
    });

    // 3. Workspaces / Projects
    projects.forEach((proj) => {
      nodes.push({
        id: proj.id,
        label: proj.name,
        type: "project",
        details: proj.description,
        color: proj.color || "#8b5cf6", // Purple / custom
        size: 14
      });
      // Link Project to JARVIS Core
      links.push({ source: "jarvis-core", target: proj.id, value: 4 });
    });

    // 4. Memories / Rules
    memories.forEach((mem) => {
      const typeLabel = mem.type.replace("_", " ").toUpperCase();
      nodes.push({
        id: mem.id,
        label: mem.text.length > 30 ? mem.text.substring(0, 30) + "..." : mem.text,
        type: "memory",
        details: `[${typeLabel} - Importance Weight: ${mem.importance}/5] ${mem.text}`,
        color: mem.type === "user_preference" ? "#ec4899" : mem.type === "writing_style" ? "#a855f7" : "#06b6d4", // Pink, Purple, Cyan
        size: 8
      });

      // Semantic link mapping helper
      let targetNodeId = "jarvis-core";
      if (mem.text.toLowerCase().includes("kampala") || mem.text.toLowerCase().includes("outreach")) {
        // Link to Kampala project if matches
        const kampalaProj = projects.find(p => p.name.toLowerCase().includes("kampala"));
        if (kampalaProj) targetNodeId = kampalaProj.id;
      } else if (mem.text.toLowerCase().includes("preference") || mem.text.toLowerCase().includes("style")) {
        const devAgent = agents.find(a => a.id === "a-dev");
        if (devAgent) targetNodeId = devAgent.id;
      }
      links.push({ source: targetNodeId, target: mem.id, value: 1.5 });
    });

    return { nodes, links };
  }, [memories, agents, projects]);

  const zoomRef = useRef<any>(null);

  // Force simulation logic
  useEffect(() => {
    if (!svgRef.current || dimensions.width === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const { nodes, links } = JSON.parse(JSON.stringify(graphData)) as { nodes: GraphNode[]; links: GraphLink[] };

    const width = dimensions.width;
    const height = dimensions.height;

    // Create a container group for zooming
    const gContainer = svg.append("g").attr("class", "graph-content");

    // Add zoom behavior
    const zoom = d3.zoom()
      .scaleExtent([0.3, 4])
      .on("zoom", (event) => {
        gContainer.attr("transform", event.transform);
      });

    zoomRef.current = zoom;
    svg.call(zoom as any);

    // Force simulation
    const simulation = d3.forceSimulation<GraphNode, GraphLink>(nodes)
      .force("link", d3.forceLink<GraphNode, GraphLink>(links)
        .id((d) => d.id)
        .distance((d) => {
          if (d.source === "jarvis-core" || (d.source as any).id === "jarvis-core") return 110;
          return 65;
        })
      )
      .force("charge", d3.forceManyBody().strength(-150))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<GraphNode>().radius((d) => d.size + 15));

    // Draw links
    const link = gContainer.append("g")
      .attr("stroke", "rgba(255, 255, 255, 0.1)")
      .attr("stroke-opacity", 0.6)
      .selectAll("line")
      .data(links)
      .enter()
      .append("line")
      .attr("stroke-width", (d) => d.value || 1.5)
      .attr("class", "transition-all duration-300");

    // Draw nodes
    const node = gContainer.append("g")
      .selectAll("g")
      .data(nodes)
      .enter()
      .append("g")
      .attr("class", "cursor-grab active:cursor-grabbing")
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", dragstarted)
          .on("drag", dragged)
          .on("end", dragended) as any
      );

    // Glowing defs
    const defs = svg.append("defs");
    nodes.forEach(n => {
      const filter = defs.append("filter").attr("id", `glow-${n.id}`);
      filter.append("feGaussianBlur").attr("stdDeviation", 3).attr("result", "coloredBlur");
      const merge = filter.append("feMerge");
      merge.append("feMergeNode").attr("in", "coloredBlur");
      merge.append("feMergeNode").attr("in", "SourceGraphic");
    });

    // Node circles
    node.append("circle")
      .attr("r", (d) => d.size)
      .attr("fill", (d) => d.color)
      .attr("stroke", "#020617")
      .attr("stroke-width", 2)
      .style("filter", d => `drop-shadow(0 0 6px ${d.color}40)`)
      .attr("class", "transition-transform duration-200 hover:scale-125")
      .on("click", (event, d) => {
        setSelectedNode(d);
      })
      .on("mouseenter", (event, d) => {
        setHoveredNode(d);
        // Highlight active connections
        link.attr("stroke", (l) => {
          const sourceId = typeof l.source === "object" ? l.source.id : l.source;
          const targetId = typeof l.target === "object" ? l.target.id : l.target;
          return (sourceId === d.id || targetId === d.id) ? d.color : "rgba(255, 255, 255, 0.06)";
        })
        .attr("stroke-opacity", (l) => {
          const sourceId = typeof l.source === "object" ? l.source.id : l.source;
          const targetId = typeof l.target === "object" ? l.target.id : l.target;
          return (sourceId === d.id || targetId === d.id) ? 1.0 : 0.2;
        });
      })
      .on("mouseleave", () => {
        setHoveredNode(null);
        link.attr("stroke", "rgba(255, 255, 255, 0.1)").attr("stroke-opacity", 0.6);
      });

    // Node labels
    node.append("text")
      .attr("dx", (d) => d.size + 6)
      .attr("dy", ".31em")
      .attr("fill", "rgba(255, 255, 255, 0.85)")
      .attr("font-size", (d) => d.type === "root" ? "11px" : "9px")
      .attr("font-family", "monospace")
      .attr("font-weight", (d) => d.type === "root" || d.type === "agent" ? "bold" : "normal")
      .text((d) => d.label)
      .style("pointer-events", "none")
      .style("text-shadow", "0 1px 3px rgba(0,0,0,0.9)");

    // Update coordinates on simulation tick
    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as any).x)
        .attr("y1", (d) => (d.source as any).y)
        .attr("x2", (d) => (d.target as any).x)
        .attr("y2", (d) => (d.target as any).y);

      node.attr("transform", (d) => `translate(${d.x}, ${d.y})`);
    });

    // Drag helpers
    function dragstarted(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      d.fx = d.x;
      d.fy = d.y;
    }

    function dragged(event: any, d: any) {
      d.fx = event.x;
      d.fy = event.y;
    }

    function dragended(event: any, d: any) {
      if (!event.active) simulation.alphaTarget(0);
      d.fx = null;
      d.fy = null;
    }

    // Zoom controls helper functions
    const handleZoomIn = () => {
      svg.transition().duration(250).call(zoom.scaleBy as any, 1.3);
    };

    const handleZoomOut = () => {
      svg.transition().duration(250).call(zoom.scaleBy as any, 1 / 1.3);
    };

    const handleReset = () => {
      svg.transition().duration(250).call(
        zoom.transform as any,
        d3.zoomIdentity.translate(0, 0).scale(1)
      );
    };

    (svg as any)._zoomIn = handleZoomIn;
    (svg as any)._zoomOut = handleZoomOut;
    (svg as any)._zoomReset = handleReset;

    return () => {
      simulation.stop();
    };
  }, [graphData, dimensions]);

  // Handle manual trigger calls
  const triggerZoom = (action: "in" | "out" | "reset") => {
    if (!svgRef.current) return;
    const svgEl = svgRef.current as any;
    if (action === "in" && svgEl._zoomIn) svgEl._zoomIn();
    if (action === "out" && svgEl._zoomOut) svgEl._zoomOut();
    if (action === "reset" && svgEl._zoomReset) svgEl._zoomReset();
  };

  // Filtered nodes for fast search highlighted rings
  const searchedNodes = React.useMemo(() => {
    if (!searchQuery.trim()) return [];
    return graphData.nodes.filter(
      n => n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
           (n.details && n.details.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  }, [searchQuery, graphData]);

  return (
    <div className="flex flex-col flex-1 min-h-[400px] h-full bg-slate-950/40 border border-slate-900 rounded-2xl overflow-hidden relative">
      {/* Top action header bar */}
      <div className="px-4 py-3 bg-slate-950/80 border-b border-slate-900/60 flex flex-wrap items-center justify-between gap-3 z-10">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-pink-500/10 border border-pink-500/20 rounded-lg text-pink-400">
            <Brain className="w-4 h-4 animate-pulse" />
          </div>
          <div>
            <span className="text-[10px] font-mono text-pink-400 uppercase tracking-widest font-bold">Obsidian Engine</span>
            <h2 className="text-xs font-bold text-white tracking-wide">Synaptic Neural Graph</h2>
          </div>
        </div>

        {/* Searching knowledge graph */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-2.5 top-2 w-3.5 h-3.5 text-slate-500" />
            <input
              type="text"
              placeholder="Search neural junctions..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-44 pl-8 pr-2.5 py-1 text-[10px] bg-slate-900/90 border border-slate-800 rounded-lg text-slate-300 focus:outline-none focus:border-pink-500/60 font-mono transition-all"
            />
          </div>

          {/* Controls */}
          <div className="flex items-center bg-slate-900/80 border border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => triggerZoom("in")}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-all cursor-pointer"
              title="Zoom In"
            >
              <ZoomIn className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => triggerZoom("out")}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-all cursor-pointer"
              title="Zoom Out"
            >
              <ZoomOut className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => triggerZoom("reset")}
              className="p-1 hover:bg-slate-800 rounded text-slate-400 hover:text-white transition-all cursor-pointer"
              title="Reset Viewport"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Visual Workspace Area */}
      <div ref={containerRef} className="flex-1 w-full h-full relative overflow-hidden bg-slate-950/10">
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
          className="w-full h-full block"
        />

        {/* Static legend details */}
        <div className="absolute left-4 bottom-4 p-3 bg-slate-950/80 backdrop-blur-md border border-slate-900 rounded-xl space-y-1.5 pointer-events-none text-[9px] font-mono select-none">
          <div className="text-slate-500 font-bold uppercase border-b border-slate-900 pb-1 mb-1">Synaptic Legend</div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-blue-500" />
            <span className="text-slate-300">OS CORE</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-emerald-500" />
            <span className="text-slate-300">AGENTS</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-purple-500" />
            <span className="text-slate-300 font-bold">WORKSPACES</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full bg-pink-500" />
            <span className="text-slate-300">MEMORY INDEX</span>
          </div>
        </div>

        {/* Dynamic Detail Card / Obsidian Note Inspector */}
        {selectedNode && (
          <div className="absolute right-4 bottom-4 w-72 bg-slate-950/95 backdrop-blur-lg border border-slate-850 p-4 rounded-xl shadow-2xl z-20 space-y-2 text-xs">
            <div className="flex justify-between items-start">
              <span className="text-[8px] font-mono font-bold tracking-widest text-pink-400 uppercase bg-pink-500/10 border border-pink-500/20 px-2 py-0.5 rounded">
                {selectedNode.type}
              </span>
              <button
                onClick={() => setSelectedNode(null)}
                className="text-slate-500 hover:text-white transition-all text-xs font-bold font-mono px-1 rounded hover:bg-slate-900"
              >
                ✕
              </button>
            </div>

            <div className="text-sm font-bold text-white leading-snug">{selectedNode.label}</div>
            <p className="text-[11px] text-slate-300 leading-relaxed bg-slate-900/60 p-2.5 rounded-lg border border-slate-900/60 font-mono">
              {selectedNode.details || "No secondary synaptic details declared."}
            </p>

            <div className="text-[9px] text-slate-500 uppercase font-mono flex items-center gap-1">
              <Info className="w-3 h-3 text-pink-500 shrink-0" />
              <span>Drag node to anchor link positions</span>
            </div>
          </div>
        )}

        {/* Hover quick HUD overlay */}
        {hoveredNode && !selectedNode && (
          <div className="absolute left-1/2 bottom-4 -translate-x-1/2 px-4 py-2 bg-slate-950/90 backdrop-blur border border-slate-900 rounded-full text-[10px] font-mono text-slate-300 flex items-center gap-2 pointer-events-none shadow-xl">
            <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: hoveredNode.color }} />
            <span className="text-white font-bold">{hoveredNode.label}</span>
            <span className="text-slate-500">|</span>
            <span className="text-slate-400 capitalize">{hoveredNode.type} Node</span>
          </div>
        )}
      </div>
    </div>
  );
}
