import React from 'react';
import {
  Cpu,
  Database,
  Monitor,
  Lock,
  ChevronRight,
  Save
} from 'lucide-react';

const Settings: React.FC = () => {
  const sections = [
    {
      title: 'Research Engine',
      icon: Cpu,
      items: [
        { label: 'Model Name', value: 'nvidia/nemotron-3-ultra-550b', type: 'select' },
        { label: 'Temperature', value: '0.2', type: 'range' },
        { label: 'Max Iterations', value: '3', type: 'number' },
        { label: 'Confidence Threshold', value: '85%', type: 'range' },
      ]
    },
    {
      title: 'Data & Privacy',
      icon: Database,
      items: [
        { label: 'Output Directory', value: './output', type: 'text' },
        { label: 'Retention Period', value: '90 Days', type: 'select' },
        { label: 'Auto-Export Format', value: 'Markdown, JSON, HTML', type: 'multiselect' },
      ]
    },
    {
      title: 'Interface',
      icon: Monitor,
      items: [
        { label: 'Default Theme', value: 'System', type: 'select' },
        { label: 'Refresh Rate', value: '30s', type: 'select' },
        { label: 'Compact Mode', value: 'Disabled', type: 'toggle' },
      ]
    }
  ];

  return (
    <div className="space-y-8 max-w-4xl">
      <div className="flex items-center justify-between">
         <div>
            <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Settings</h1>
            <p className="text-zinc-500 text-sm">Configure your research platform parameters.</p>
         </div>
         <button className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-sm font-bold shadow-lg shadow-blue-600/20 transition-all active:scale-95">
            <Save className="h-4 w-4 mr-2" />
            Save Changes
         </button>
      </div>

      <div className="space-y-6">
         {sections.map((section) => (
            <div key={section.title} className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-3xl overflow-hidden">
               <div className="px-8 py-6 border-b border-zinc-100 dark:border-zinc-800 bg-zinc-50/50 dark:bg-zinc-900/50 flex items-center">
                  <section.icon className="h-5 w-5 mr-3 text-zinc-400" />
                  <h3 className="font-bold text-zinc-900 dark:text-zinc-100">{section.title}</h3>
               </div>
               <div className="p-8 space-y-6">
                  {section.items.map((item) => (
                     <div key={item.label} className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <div>
                           <div className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{item.label}</div>
                           <div className="text-xs text-zinc-500">System default parameter</div>
                        </div>
                        <div className="flex items-center space-x-2">
                           <div className="px-4 py-2 bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-800 rounded-xl text-sm font-medium min-w-[200px] flex justify-between items-center cursor-pointer hover:border-zinc-300 dark:hover:border-zinc-700 transition-colors group">
                              <span>{item.value}</span>
                              <ChevronRight className="h-4 w-4 text-zinc-400 group-hover:translate-x-1 transition-transform" />
                           </div>
                        </div>
                     </div>
                  ))}
               </div>
            </div>
         ))}
      </div>

      <div className="p-6 bg-red-50/50 dark:bg-red-900/10 border border-red-100 dark:border-red-900/30 rounded-3xl">
         <div className="flex items-center space-x-3 text-red-700 dark:text-red-400 mb-2">
            <Lock className="h-5 w-5" />
            <h3 className="font-bold">Administrative Controls</h3>
         </div>
         <p className="text-sm text-red-600/70 dark:text-red-400/60 mb-6">These actions cannot be undone. Please proceed with caution.</p>
         <div className="flex flex-wrap gap-3">
            <button className="px-4 py-2 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 rounded-xl text-xs font-bold hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors">
               Clear Research Cache
            </button>
            <button className="px-4 py-2 border border-red-200 dark:border-red-900/50 text-red-600 dark:text-red-400 rounded-xl text-xs font-bold hover:bg-red-100 dark:hover:bg-red-900/20 transition-colors">
               Reset System Index
            </button>
         </div>
      </div>
    </div>
  );
};

export default Settings;
