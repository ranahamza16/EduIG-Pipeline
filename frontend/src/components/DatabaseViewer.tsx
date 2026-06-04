import React, { useState } from 'react';
import { Database } from 'lucide-react';
import CollectedData from './CollectedData';
import RunHistory from './RunHistory';

export default function DatabaseViewer() {
  const [activeTable, setActiveTable] = useState('profiles');

  return (
    <div className="w-full">
      <div className="flex items-center gap-4 mb-6">
        <Database className="w-8 h-8 text-purple-400" />
        <h2 className="text-2xl font-bold text-white">Database Viewer (Admin)</h2>
      </div>

      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setActiveTable('profiles')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTable === 'profiles' ? 'bg-purple-600 text-white' : 'bg-dark-800 text-slate-400 hover:bg-dark-700'
          }`}
        >
          Profiles Table
        </button>
        <button
          onClick={() => setActiveTable('runs')}
          className={`px-4 py-2 rounded-lg font-medium transition-colors ${
            activeTable === 'runs' ? 'bg-purple-600 text-white' : 'bg-dark-800 text-slate-400 hover:bg-dark-700'
          }`}
        >
          Runs Table
        </button>
      </div>

      <div className="w-full">
        {activeTable === 'profiles' ? <CollectedData /> : <RunHistory />}
      </div>
    </div>
  );
}
