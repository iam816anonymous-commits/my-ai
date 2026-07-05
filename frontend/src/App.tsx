import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import ReportLibrary from './pages/ReportLibrary';
import ReportViewer from './pages/ReportViewer';
import SystemHealth from './pages/SystemHealth';
import Settings from './pages/Settings';

// Placeholder Pages
const Saved = () => <div>Saved Reports</div>;
const Benchmarks = () => <div>Benchmark Dashboard</div>;
const Logs = () => <div>System Logs</div>;

const App: React.FC = () => {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="reports" element={<ReportLibrary />} />
            <Route path="reports/:id" element={<ReportViewer />} />
            <Route path="saved" element={<Saved />} />
            <Route path="benchmarks" element={<Benchmarks />} />
            <Route path="settings" element={<Settings />} />
            <Route path="logs" element={<Logs />} />
            <Route path="health" element={<SystemHealth />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
};

export default App;
