import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  Search,
  History,
  Bookmark,
  BarChart2,
  Settings,
  FileText,
  Activity,
  Moon,
  Sun,
  Monitor
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const Sidebar: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const navItems = [
    { icon: Search, label: 'New Research', path: '/' },
    { icon: History, label: 'Previous Reports', path: '/reports' },
    { icon: Bookmark, label: 'Saved Reports', path: '/saved' },
    { icon: BarChart2, label: 'Benchmarks', path: '/benchmarks' },
    { icon: Settings, label: 'Settings', path: '/settings' },
    { icon: FileText, label: 'Logs', path: '/logs' },
    { icon: Activity, label: 'System Health', path: '/health' },
  ];

  return (
    <div className="w-64 h-full bg-white dark:bg-zinc-900 border-r border-zinc-200 dark:border-zinc-800 flex flex-col transition-colors duration-200">
      <div className="p-6">
        <h1 className="text-xl font-bold bg-gradient-to-r from-blue-600 to-indigo-600 bg-clip-text text-transparent">
          Analyst Research
        </h1>
      </div>

      <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.label}
            to={item.path}
            className={({ isActive }) => cn(
              "flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors",
              isActive
                ? "bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400"
                : "text-zinc-600 hover:bg-zinc-100 dark:text-zinc-400 dark:hover:bg-zinc-800"
            )}
          >
            <item.icon className="mr-3 h-5 w-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-800 flex items-center justify-between">
        <div className="flex bg-zinc-100 dark:bg-zinc-800 p-1 rounded-lg w-full">
          <button
            onClick={() => setTheme('light')}
            className={cn("flex-1 flex justify-center py-1.5 rounded-md transition-all", theme === 'light' ? "bg-white dark:bg-zinc-700 shadow-sm" : "")}
          >
            <Sun className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
          </button>
          <button
            onClick={() => setTheme('system')}
            className={cn("flex-1 flex justify-center py-1.5 rounded-md transition-all", theme === 'system' ? "bg-white dark:bg-zinc-700 shadow-sm" : "")}
          >
            <Monitor className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={cn("flex-1 flex justify-center py-1.5 rounded-md transition-all", theme === 'dark' ? "bg-white dark:bg-zinc-700 shadow-sm" : "")}
          >
            <Moon className="h-4 w-4 text-zinc-600 dark:text-zinc-400" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default Sidebar;
