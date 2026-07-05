import React, { useState, useEffect, useRef } from 'react';
import {
  Loader2,
  CheckCircle2,
  Globe,
  Download,
  FileText,
  Cpu,
  Zap,
  ChevronRight,
  ShieldCheck,
  RotateCcw
} from 'lucide-react';
import { motion } from 'framer-motion';

interface ResearchProgress {
  event: string;
  state: any;
}

const ResearchExecution: React.FC<{ query: string; onCancel: () => void }> = ({ query, onCancel }) => {
  const [progress, setProgress] = useState<ResearchProgress[]>([]);
  const [currentState, setCurrentState] = useState<any>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ws.current = new WebSocket(`ws://${window.location.hostname}:8000/ws/research`);

    ws.current.onopen = () => {
      ws.current?.send(JSON.stringify({ query }));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'complete') {
        setIsComplete(true);
      } else if (data.event === 'error') {
        setError(data.message);
      } else {
        setProgress(prev => [...prev, data]);
        setCurrentState(data.state);
      }
    };

    ws.current.onclose = () => {
      if (!isComplete && !error) {
        setError("Connection lost");
      }
    };

    return () => {
      ws.current?.close();
    };
  }, [query]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [progress]);

  const stages = [
    { key: 'planning', label: 'Planning', icon: Zap },
    { key: 'search', label: 'Searching', icon: Globe },
    { key: 'fetch', label: 'Downloading', icon: Download },
    { key: 'summarize', label: 'Extracting', icon: FileText },
    { key: 'reasoning', label: 'Reasoning', icon: Cpu },
    { key: 'synthesis', label: 'Synthesizing', icon: Zap },
  ];

  const getStageStatus = (stageKey: string) => {
    if (!currentState) return 'pending';
    const events = progress.map(p => p.event);
    if (events.includes(`${stageKey}_complete`)) return 'complete';
    if (events.includes(`${stageKey}_start`)) return 'active';
    return 'pending';
  };

  return (
    <div className="flex flex-col h-full -m-8">
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 p-4 flex items-center justify-between px-8">
        <div className="flex items-center space-x-4">
           <button onClick={onCancel} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors">
              <RotateCcw className="h-5 w-5 text-zinc-500" />
           </button>
           <h2 className="font-semibold text-zinc-900 dark:text-zinc-100 truncate max-w-md">
             Researching: {query}
           </h2>
        </div>
        <div className="flex items-center space-x-4">
           {isComplete ? (
             <button className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium">
               View Full Report
             </button>
           ) : (
             <div className="flex items-center text-sm text-zinc-500">
                <Loader2 className="h-4 w-4 mr-2 animate-spin text-blue-600" />
                Processing...
             </div>
           )}
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* LEFT: Live Report Preview */}
        <div className="flex-1 overflow-y-auto p-8 bg-zinc-50/50 dark:bg-zinc-950/50 border-r border-zinc-200 dark:border-zinc-800">
           <div className="max-w-3xl mx-auto prose dark:prose-invert prose-blue">
              {!currentState && (
                <div className="flex flex-col items-center justify-center h-64 text-zinc-400">
                   <Zap className="h-12 w-12 mb-4 opacity-20" />
                   <p>Initializing analysis engine...</p>
                </div>
              )}
              {currentState && (
                <div className="animate-in fade-in duration-700">
                   <h1 className="text-3xl font-bold mb-8">{query}</h1>
                   <div className="mb-12 p-6 rounded-2xl bg-blue-50/50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30">
                      <div className="flex items-center mb-4 text-blue-700 dark:text-blue-400 font-semibold">
                         <ShieldCheck className="h-5 w-5 mr-2" />
                         Executive Preview
                      </div>
                      <p className="text-zinc-600 dark:text-zinc-400 leading-relaxed italic">
                        Real-time synthesis in progress. The full analytical report will be available once all evidence cycles complete.
                      </p>
                   </div>

                   {/* This would show live content if we streamed it, for now show placeholders for what's found */}
                   <div className="space-y-8">
                      {currentState.summaries?.length > 0 && (
                        <div>
                          <h3 className="text-lg font-bold mb-4 flex items-center">
                            <Globe className="h-5 w-5 mr-2 text-zinc-400" />
                            Evidence Collected ({currentState.summaries.length} sources)
                          </h3>
                          <div className="space-y-4">
                            {currentState.summaries.slice(-3).map((s: any, i: number) => (
                              <div key={i} className="p-4 rounded-xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900/50">
                                 <div className="text-xs text-zinc-500 mb-1 truncate">{s.url}</div>
                                 <div className="text-sm font-medium line-clamp-2">{s.summary}</div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                   </div>
                </div>
              )}
           </div>
        </div>

        {/* RIGHT: Live Progress Monitor */}
        <div className="w-96 bg-white dark:bg-zinc-900 flex flex-col transition-colors">
           <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
              <h3 className="font-bold text-sm uppercase tracking-wider text-zinc-400 mb-6">Execution Pipeline</h3>
              <div className="space-y-6">
                 {stages.map((stage) => {
                   const status = getStageStatus(stage.key);
                   return (
                     <div key={stage.key} className="flex items-start">
                        <div className={`mt-0.5 p-2 rounded-lg ${
                          status === 'active' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600' :
                          status === 'complete' ? 'bg-green-100 dark:bg-green-900/30 text-green-600' :
                          'bg-zinc-100 dark:bg-zinc-800 text-zinc-400'
                        }`}>
                           <stage.icon className="h-4 w-4" />
                        </div>
                        <div className="ml-4 flex-1">
                           <div className="flex items-center justify-between">
                              <span className={`text-sm font-semibold ${status === 'active' ? 'text-blue-600' : 'text-zinc-700 dark:text-zinc-300'}`}>
                                {stage.label}
                              </span>
                              {status === 'active' && <Loader2 className="h-3 w-3 animate-spin text-blue-600" />}
                              {status === 'complete' && <CheckCircle2 className="h-4 w-4 text-green-600" />}
                           </div>
                           <div className="mt-2 h-1.5 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                              <motion.div
                                initial={{ width: 0 }}
                                animate={{ width: status === 'complete' ? '100%' : status === 'active' ? '60%' : '0%' }}
                                className={`h-full ${status === 'complete' ? 'bg-green-500' : 'bg-blue-500'}`}
                              />
                           </div>
                        </div>
                     </div>
                   );
                 })}
              </div>
           </div>

           <div className="flex-1 p-6 overflow-y-auto custom-scrollbar" ref={scrollRef}>
              <h3 className="font-bold text-sm uppercase tracking-wider text-zinc-400 mb-4">Live Metrics</h3>
              {currentState ? (
                <div className="space-y-6">
                   <div className="grid grid-cols-2 gap-4">
                      <div className="p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800">
                         <div className="text-[10px] uppercase font-bold text-zinc-400 mb-1">Confidence</div>
                         <div className="text-xl font-bold text-blue-600">{(currentState.confidence_breakdown?.overall || 0).toFixed(1)}%</div>
                      </div>
                      <div className="p-4 rounded-2xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-800">
                         <div className="text-[10px] uppercase font-bold text-zinc-400 mb-1">Iteration</div>
                         <div className="text-xl font-bold">{currentState.iterations}/3</div>
                      </div>
                   </div>

                   <div className="space-y-4">
                      <div className="flex items-center justify-between text-xs">
                         <span className="text-zinc-500">Objective Coverage</span>
                         <span className="font-bold">
                           {Object.values(currentState.objective_states || {}).length > 0
                             ? (Object.values(currentState.objective_states as Record<string, any>).reduce((a, b) => a + (b.coverage || 0), 0) / Object.values(currentState.objective_states as Record<string, any>).length).toFixed(0)
                             : 0}%
                         </span>
                      </div>
                      <div className="h-2 w-full bg-zinc-100 dark:bg-zinc-800 rounded-full overflow-hidden">
                         <div
                           className="h-full bg-indigo-500 transition-all duration-500"
                           style={{ width: `${Object.values(currentState.objective_states || {}).length > 0 ? (Object.values(currentState.objective_states as Record<string, any>).reduce((a, b) => a + (b.coverage || 0), 0) / Object.values(currentState.objective_states).length) : 0}%` }}
                         />
                      </div>
                   </div>

                   <div className="space-y-3">
                      <div className="text-[10px] uppercase font-bold text-zinc-400">Activity Log</div>
                      <div className="space-y-2">
                         {progress.slice(-5).map((p, i) => (
                           <div key={i} className="text-xs flex items-start text-zinc-500">
                              <ChevronRight className="h-3 w-3 mt-0.5 mr-1 text-zinc-300" />
                              <span>Stage <span className="text-zinc-700 dark:text-zinc-300 font-medium">{p.event}</span> completed.</span>
                           </div>
                         ))}
                      </div>
                   </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-zinc-400 italic text-sm">
                   Waiting for stream...
                </div>
              )}
           </div>
        </div>
      </div>
    </div>
  );
};

export default ResearchExecution;
