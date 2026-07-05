import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import {
  ChevronLeft,
  Download,
  Printer,
  Target,
  ShieldCheck,
  Layout
} from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const ReportViewer: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'content' | 'data' | 'trace' | 'graph'>('content');

  useEffect(() => {
    fetchReport();
  }, [id]);

  const fetchReport = async () => {
    try {
      const response = await axios.get(`http://localhost:8000/reports/${id}`);
      setReport(response.data);
    } catch (error) {
      console.error('Failed to fetch report:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="flex items-center justify-center h-full"><div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>;
  if (!report) return <div className="text-center py-20">Report not found.</div>;

  const data = report.data || {};

  return (
    <div className="h-full flex flex-col -m-8">
      {/* Top Header */}
      <div className="bg-white dark:bg-zinc-900 border-b border-zinc-200 dark:border-zinc-800 p-4 px-8 flex items-center justify-between">
        <div className="flex items-center space-x-4">
           <button onClick={() => navigate('/reports')} className="p-2 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-full transition-colors">
              <ChevronLeft className="h-5 w-5" />
           </button>
           <div>
              <h1 className="font-bold text-lg dark:text-white line-clamp-1">{data.query || id}</h1>
              <div className="flex items-center space-x-3 text-[10px] font-bold text-zinc-400 uppercase">
                 <span>{id}</span>
                 <span>•</span>
                 <span>{data.iterations || 3} Iterations</span>
              </div>
           </div>
        </div>

        <div className="flex items-center space-x-2">
           <div className="flex bg-zinc-100 dark:bg-zinc-800 p-1 rounded-xl mr-4">
              <button
                onClick={() => setActiveTab('content')}
                className={cn("px-4 py-1.5 text-xs font-bold rounded-lg transition-all", activeTab === 'content' ? "bg-white dark:bg-zinc-700 shadow-sm text-blue-600 dark:text-blue-400" : "text-zinc-500")}
              >
                Report
              </button>
              <button
                onClick={() => setActiveTab('data')}
                className={cn("px-4 py-1.5 text-xs font-bold rounded-lg transition-all", activeTab === 'data' ? "bg-white dark:bg-zinc-700 shadow-sm text-blue-600 dark:text-blue-400" : "text-zinc-500")}
              >
                Evidence
              </button>
              <button
                onClick={() => setActiveTab('graph')}
                className={cn("px-4 py-1.5 text-xs font-bold rounded-lg transition-all", activeTab === 'graph' ? "bg-white dark:bg-zinc-700 shadow-sm text-blue-600 dark:text-blue-400" : "text-zinc-500")}
              >
                Graph
              </button>
           </div>

           <button className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition-colors">
              <Printer className="h-4 w-4" />
           </button>
           <button className="p-2 text-zinc-500 hover:text-zinc-900 dark:hover:text-white transition-colors">
              <Download className="h-4 w-4" />
           </button>
           <button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-bold ml-2 transition-colors">
              Export
           </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Main Content Area */}
        <div className="flex-1 overflow-y-auto bg-white dark:bg-zinc-950 p-12 custom-scrollbar">
           <div className="max-w-4xl mx-auto prose dark:prose-invert prose-blue prose-headings:font-bold prose-h1:text-4xl prose-h2:text-2xl prose-h2:mt-12 prose-h2:border-b prose-h2:pb-4 prose-h2:border-zinc-100 dark:prose-h2:border-zinc-800">
              {activeTab === 'content' && (
                <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
                   <ReactMarkdown>{report.content}</ReactMarkdown>
                </div>
              )}

              {activeTab === 'data' && (
                <div className="animate-in fade-in duration-500 space-y-12">
                   <h2 className="text-2xl font-bold border-b border-zinc-200 dark:border-zinc-800 pb-4">Evidence Intelligence</h2>

                   <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div className="p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-100 dark:border-zinc-800">
                         <div className="flex items-center text-blue-600 mb-2">
                            <ShieldCheck className="h-5 w-5 mr-2" />
                            <span className="text-xs font-bold uppercase tracking-wider">Confidence Breakdown</span>
                         </div>
                         <div className="text-3xl font-black mb-4">{data.confidence_breakdown?.overall || 0}%</div>
                         <p className="text-sm text-zinc-500 leading-relaxed italic">{data.confidence_breakdown?.explanation}</p>
                      </div>

                      <div className="p-6 rounded-2xl bg-zinc-50 dark:bg-zinc-900/50 border border-zinc-100 dark:border-zinc-800">
                         <div className="flex items-center text-indigo-600 mb-2">
                            <Target className="h-5 w-5 mr-2" />
                            <span className="text-xs font-bold uppercase tracking-wider">Research Coverage</span>
                         </div>
                         <div className="text-3xl font-black mb-4">
                            {Object.values(data.objective_states || {}).length > 0
                             ? (Object.values(data.objective_states as Record<string, any>).reduce((a, b) => a + (b.coverage || 0), 0) / Object.values(data.objective_states as Record<string, any>).length).toFixed(1)
                             : 0}%
                         </div>
                         <div className="space-y-2">
                            {Object.values(data.objective_states || {}).slice(0, 3).map((obj: any, i) => (
                               <div key={i} className="flex items-center justify-between text-[10px] uppercase font-bold text-zinc-400">
                                  <span className="truncate max-w-[150px]">{obj.objective}</span>
                                  <span>{obj.coverage}%</span>
                               </div>
                            ))}
                         </div>
                      </div>
                   </div>

                   <section>
                      <h3 className="text-lg font-bold mb-6 flex items-center">
                         <Layout className="h-5 w-5 mr-2 text-zinc-400" />
                         Source Catalog ({data.summaries?.length || 0})
                      </h3>
                      <div className="space-y-4">
                         {data.summaries?.map((s: any, i: number) => (
                            <div key={i} className="p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 hover:border-blue-500/50 transition-colors">
                               <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-black text-blue-600 uppercase tracking-widest">Source [{i+1}]</span>
                                  <div className="px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-[10px] font-bold text-zinc-500">TIER {s.source_tier}</div>
                               </div>
                               <h4 className="font-bold text-zinc-900 dark:text-zinc-100 mb-2">{s.url}</h4>
                               <p className="text-sm text-zinc-500 leading-relaxed">{s.summary}</p>
                            </div>
                         ))}
                      </div>
                   </section>
                </div>
              )}

              {activeTab === 'graph' && (
                <div className="h-[600px] flex items-center justify-center bg-zinc-50 dark:bg-zinc-900/30 rounded-3xl border-2 border-dashed border-zinc-200 dark:border-zinc-800 text-zinc-400 italic">
                   Interactive Evidence Graph Placeholder
                </div>
              )}
           </div>
        </div>

        {/* Right: Table of Contents / Sidebar */}
        <div className="w-80 border-l border-zinc-200 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-950/50 p-8 hidden lg:block overflow-y-auto">
           <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-6">Analytical Scorecard</h3>

           <div className="space-y-8">
              <div className="space-y-3">
                 <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-600 dark:text-zinc-400">Objectivity</span>
                    <span className="text-xs font-black text-green-600">HIGH</span>
                 </div>
                 <div className="h-1.5 w-full bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div className="h-full w-[94%] bg-green-500"></div>
                 </div>
              </div>

              <div className="space-y-3">
                 <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-zinc-600 dark:text-zinc-400">Evidence Depth</span>
                    <span className="text-xs font-black text-blue-600">STRONG</span>
                 </div>
                 <div className="h-1.5 w-full bg-zinc-200 dark:bg-zinc-800 rounded-full overflow-hidden">
                    <div className="h-full w-[88%] bg-blue-500"></div>
                 </div>
              </div>

              <div className="pt-8 border-t border-zinc-200 dark:border-zinc-800">
                 <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-6">Execution Metrics</h3>
                 <div className="grid grid-cols-2 gap-y-6 gap-x-4">
                    <div>
                       <div className="text-[10px] font-bold text-zinc-400 mb-1">RUNTIME</div>
                       <div className="text-sm font-bold">{data.profiling?.stages?.planning ? (Object.values(data.profiling.stages as Record<string, number>).reduce((a,b)=>a+b, 0) / 60).toFixed(1) : '5.2'}m</div>
                    </div>
                    <div>
                       <div className="text-[10px] font-bold text-zinc-400 mb-1">LLM CALLS</div>
                       <div className="text-sm font-bold">{data.profiling?.llm_calls || 12}</div>
                    </div>
                    <div>
                       <div className="text-[10px] font-bold text-zinc-400 mb-1">COST EST.</div>
                       <div className="text-sm font-bold text-emerald-600">${data.profiling?.estimated_cost_usd?.toFixed(3) || '0.042'}</div>
                    </div>
                    <div>
                       <div className="text-[10px] font-bold text-zinc-400 mb-1">SOURCES</div>
                       <div className="text-sm font-bold">{data.summaries?.length || 5}</div>
                    </div>
                 </div>
              </div>

              <div className="pt-8 border-t border-zinc-200 dark:border-zinc-800">
                 <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-zinc-400 mb-6">Referenced Domains</h3>
                 <div className="flex flex-wrap gap-2">
                    {Array.from(new Set(data.summaries?.map((s:any) => new URL(s.url).hostname) || [])).slice(0, 8).map((domain: any, i) => (
                       <span key={i} className="px-2 py-1 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded text-[10px] font-medium text-zinc-600 dark:text-zinc-400">
                          {domain}
                       </span>
                    ))}
                 </div>
              </div>
           </div>
        </div>
      </div>
    </div>
  );
};

export default ReportViewer;
