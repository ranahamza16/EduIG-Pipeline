import React, { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Shield, Target, Terminal, Database, Clock } from 'lucide-react';
import TargetManager from './components/TargetManager';
import ExecutionDashboard from './components/ExecutionDashboard';
import CollectedData from './components/CollectedData';
import RunHistory from './components/RunHistory';
import DatabaseViewer from './components/DatabaseViewer';

const queryClient = new QueryClient();

export default function App() {
  const [activeTab, setActiveTab] = useState('targets');

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen flex text-slate-200">
        {/* Sidebar */}
        <aside className="w-64 bg-dark-800/80 backdrop-blur-xl border-r border-dark-700 p-4 flex flex-col z-10">
          <div className="flex items-center gap-3 mb-10 px-2 mt-4">
            <Shield className="w-8 h-8 text-primary" />
            <div>
              <h1 className="font-bold text-lg text-white">EduIG-Pipeline</h1>
              <p className="text-xs text-slate-400">IRB Compliant v2.0</p>
            </div>
          </div>
          
          <nav className="flex-1 space-y-2">
            {[
              { id: 'targets', label: 'Target Manager', icon: Target },
              { id: 'execution', label: 'Execution', icon: Terminal },
              { id: 'data', label: 'Collected Data', icon: Database },
              { id: 'history', label: 'Run History', icon: Clock },
              { id: 'admin', label: 'DB Admin', icon: Shield },
            ].map((item) => (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors font-medium ${
                  activeTab === item.id 
                    ? 'bg-primary/20 text-primary border border-primary/30 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
                    : 'text-slate-400 hover:bg-dark-700/50 hover:text-white'
                }`}
              >
                <item.icon className="w-5 h-5" />
                {item.label}
              </button>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-8 z-10 overflow-y-auto">
          <div className="max-w-6xl mx-auto">
            {activeTab === 'targets' && <TargetManager />}
            {activeTab === 'execution' && <ExecutionDashboard />}
            {activeTab === 'data' && <CollectedData />}
            {activeTab === 'history' && <RunHistory />}
            {activeTab === 'admin' && <DatabaseViewer />}
          </div>
        </main>
      </div>
    </QueryClientProvider>
  );
}
