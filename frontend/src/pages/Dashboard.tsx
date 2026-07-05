import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Search,
  History,
  ArrowRight,
  TrendingUp,
  Clock
} from 'lucide-react';
import ResearchExecution from './ResearchExecution';

const Dashboard: React.FC = () => {
  const [query, setQuery] = useState('');
  const [isResearching, setIsResearching] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const response = await axios.get('http://localhost:8000/reports');
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history:', error);
    }
  };

  const handleResearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      setIsResearching(true);
    }
  };

  if (isResearching) {
    return <ResearchExecution query={query} onCancel={() => setIsResearching(false)} />;
  }

  return (
    <div className="space-y-12">
      <div className="flex flex-col items-center justify-center pt-20 pb-12 text-center max-w-2xl mx-auto">
        <h1 className="text-4xl font-extrabold mb-4 tracking-tight text-zinc-900 dark:text-zinc-100">
          Professional Intelligence
        </h1>
        <p className="text-zinc-500 dark:text-zinc-400 mb-8 text-lg">
          Deconstruct complex topics with reasoning-driven research and analytical synthesis.
        </p>

        <form onSubmit={handleResearch} className="w-full relative group">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Research any topic..."
            className="w-full h-16 pl-14 pr-32 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 shadow-2xl shadow-zinc-200/50 dark:shadow-none focus:outline-none focus:ring-4 focus:ring-blue-500/10 transition-all text-lg"
          />
          <div className="absolute left-5 top-5 text-zinc-400">
            <Search className="h-6 w-6" />
          </div>
          <div className="absolute right-3 top-3">
            <button
              type="submit"
              disabled={!query.trim()}
              className="h-10 px-6 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl text-sm font-bold transition-all shadow-lg shadow-blue-600/20 active:scale-95"
            >
              Research
            </button>
          </div>
        </form>
      </div>

      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold flex items-center">
            <History className="h-5 w-5 mr-2 text-zinc-400" />
            Recent Investigations
          </h2>
          <button className="text-sm font-medium text-blue-600 hover:text-blue-700">View all</button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {history.length > 0 ? history.slice(0, 6).map((item) => (
            <div key={item.id} className="p-6 rounded-2xl border border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:shadow-xl hover:border-blue-500/30 transition-all cursor-pointer group">
              <div className="flex items-start justify-between mb-4">
                 <div className="px-2 py-1 rounded-lg bg-blue-50 dark:bg-blue-900/20 text-[10px] font-bold text-blue-700 dark:text-blue-400 uppercase tracking-wider">
                   {item.grade || 'Grade A'}
                 </div>
                 <ArrowRight className="h-4 w-4 text-zinc-300 group-hover:text-blue-500 transition-colors" />
              </div>
              <h3 className="font-bold text-zinc-900 dark:text-zinc-100 mb-6 line-clamp-2 leading-tight">
                {item.query}
              </h3>
              <div className="flex items-center space-x-4 text-[10px] font-bold text-zinc-400 uppercase">
                <div className="flex items-center">
                   <Clock className="h-3 w-3 mr-1" />
                   {item.runtime || '5m'}
                </div>
                <div className="flex items-center">
                   <TrendingUp className="h-3 w-3 mr-1" />
                   {item.confidence?.toFixed(0) || '92'}% Conf.
                </div>
              </div>
            </div>
          )) : (
            <div className="col-span-full py-12 text-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-3xl text-zinc-400">
               No recent research found. Start your first investigation above.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
