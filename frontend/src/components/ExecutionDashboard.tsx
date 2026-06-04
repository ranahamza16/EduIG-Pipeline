import React, { useState, useRef, useEffect } from 'react';
import { Play, Square, Terminal, Download, Trash2 } from 'lucide-react';

export default function ExecutionDashboard() {
  const [logs, setLogs] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);

  const startPipeline = async () => {
    setIsRunning(true);
    setLogs(['> Initiating EduIG-Pipeline execution...', '> Connecting to secure API...']);
    
    try {
      const response = await fetch('/api/run', { method: 'POST' });
      if (!response.body) throw new Error('No response body');
      
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        
        const chunk = decoder.decode(value);
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '));
        
        setLogs(prev => [...prev, ...lines.map(l => l.replace('data: ', ''))]);
      }
    } catch (err) {
      setLogs(prev => [...prev, '> Error executing pipeline.']);
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [logs]);

  const clearLogs = () => setLogs([]);

  return (
    <div className="glass rounded-xl p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-white flex items-center">
          <Terminal className="w-6 h-6 mr-2 text-primary" />
          Pipeline Execution
        </h2>
        <div className="flex gap-3">
          <button
            onClick={startPipeline}
            disabled={isRunning}
            className={`px-4 py-2 rounded-lg flex items-center transition-colors font-medium ${
              isRunning ? 'bg-dark-700 text-slate-400 cursor-not-allowed' : 'bg-accent hover:bg-emerald-400 text-dark-900'
            }`}
          >
            {isRunning ? <Square className="w-5 h-5 mr-2" /> : <Play className="w-5 h-5 mr-2" />}
            {isRunning ? 'Running...' : 'Run Scraper'}
          </button>
        </div>
      </div>

      <div className="bg-[#0D1117] rounded-lg border border-dark-700 overflow-hidden shadow-inner flex flex-col h-[500px]">
        <div className="bg-dark-800 px-4 py-2 flex items-center justify-between border-b border-dark-700">
          <div className="flex gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500"></div>
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
          </div>
          <div className="text-xs font-mono text-slate-400">python run.py</div>
          <div className="flex gap-2">
            <button onClick={clearLogs} className="text-slate-400 hover:text-white transition-colors" title="Clear logs">
              <Trash2 className="w-4 h-4" />
            </button>
            <button className="text-slate-400 hover:text-white transition-colors" title="Download logs">
              <Download className="w-4 h-4" />
            </button>
          </div>
        </div>
        <div 
          ref={terminalRef}
          className="p-4 font-mono text-sm overflow-y-auto flex-1 space-y-1"
        >
          {logs.length === 0 ? (
            <div className="text-slate-500 italic">Ready to execute. Press "Run Scraper" to start.</div>
          ) : (
            logs.map((log, i) => {
              // Basic syntax highlighting for structlogs
              let colorClass = "text-slate-300";
              if (log.includes('"level": "error"')) colorClass = "text-red-400";
              else if (log.includes('"level": "warning"')) colorClass = "text-yellow-400";
              else if (log.includes('"level": "info"')) colorClass = "text-emerald-400";
              else if (log.startsWith('>')) colorClass = "text-blue-400 font-bold";
              
              return <div key={i} className={`${colorClass} break-all`}>{log}</div>
            })
          )}
        </div>
      </div>
    </div>
  );
}
