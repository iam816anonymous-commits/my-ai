import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  Search,
  Filter,
  Trash2,
  Download,
  Clock,
  TrendingUp,
  FileText
} from 'lucide-react';
import { Link } from 'react-router-dom';

const ReportLibrary: React.FC = () => {
  const [reports, setReports] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const response = await axios.get('http://localhost:8000/reports');
      setReports(response.data);
    } catch (error) {
      console.error('Failed to fetch reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredReports = reports.filter(r =>
    r.query.toLowerCase().includes(search.toLowerCase()) ||
    r.id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
           <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Research Library</h1>
           <p className="text-zinc-500 text-sm">Access and manage all historical research reports.</p>
        </div>

        <div className="flex items-center space-x-3">
           <div className="relative group">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-400 group-focus-within:text-blue-500 transition-colors" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search reports..."
                className="pl-10 pr-4 py-2 w-64 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
           </div>
           <button className="p-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors">
              <Filter className="h-4 w-4 text-zinc-500" />
           </button>
        </div>
      </div>

      {loading ? (
        <div className="py-20 flex justify-center">
           <div className="animate-spin h-8 w-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
        </div>
      ) : filteredReports.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
           {filteredReports.map((report) => (
             <Link
               to={`/reports/${report.id}`}
               key={report.id}
               className="group flex flex-col p-6 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl hover:border-blue-500/30 hover:shadow-xl transition-all"
             >
                <div className="flex items-start justify-between mb-6">
                   <div className="px-2 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-[10px] font-bold text-indigo-700 dark:text-indigo-400 uppercase tracking-wider">
                     {report.grade || 'Grade A'}
                   </div>
                   <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button className="p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400">
                         <Download className="h-3.5 w-3.5" />
                      </button>
                      <button className="p-1.5 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md text-zinc-400">
                         <Trash2 className="h-3.5 w-3.5" />
                      </button>
                   </div>
                </div>

                <h3 className="font-bold text-zinc-900 dark:text-zinc-100 mb-2 line-clamp-2 min-h-[3rem] group-hover:text-blue-600 transition-colors leading-tight">
                  {report.query}
                </h3>

                <div className="mt-auto pt-6 border-t border-zinc-100 dark:border-zinc-800 flex items-center justify-between">
                   <div className="flex items-center space-x-3">
                      <div className="flex items-center text-[10px] font-bold text-zinc-400 uppercase">
                         <Clock className="h-3 w-3 mr-1" />
                         {report.runtime || '4m'}
                      </div>
                      <div className="flex items-center text-[10px] font-bold text-zinc-400 uppercase">
                         <TrendingUp className="h-3 w-3 mr-1" />
                         {report.confidence?.toFixed(0) || '90'}%
                      </div>
                   </div>
                   <div className="text-[10px] font-medium text-zinc-500">
                      {report.id}
                   </div>
                </div>
             </Link>
           ))}
        </div>
      ) : (
        <div className="py-20 text-center border-2 border-dashed border-zinc-200 dark:border-zinc-800 rounded-3xl">
           <FileText className="h-12 w-12 text-zinc-200 dark:text-zinc-800 mx-auto mb-4" />
           <p className="text-zinc-500">No reports matching your criteria were found.</p>
        </div>
      )}
    </div>
  );
};

export default ReportLibrary;
