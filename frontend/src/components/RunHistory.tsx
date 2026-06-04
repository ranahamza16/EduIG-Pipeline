import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Clock, CheckCircle2, XCircle } from 'lucide-react';

export default function RunHistory() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: async () => {
      const res = await fetch('/api/data/runs');
      if (!res.ok) throw new Error('Failed to fetch runs');
      return res.json();
    }
  });

  return (
    <div className="glass rounded-xl p-6 w-full">
      <h2 className="text-xl font-bold text-white mb-6 flex items-center">
        <Clock className="w-6 h-6 mr-2 text-primary" />
        Pipeline Run History
      </h2>

      <div className="overflow-hidden rounded-lg border border-dark-700">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-dark-800 text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">Run ID</th>
              <th className="px-4 py-3 font-medium">Started At</th>
              <th className="px-4 py-3 font-medium">Completed At</th>
              <th className="px-4 py-3 font-medium text-center">Targets Processed</th>
              <th className="px-4 py-3 font-medium text-center">Successful</th>
              <th className="px-4 py-3 font-medium text-right">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700 bg-dark-900/30">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">Loading history...</td>
              </tr>
            ) : runs?.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">No pipeline runs found.</td>
              </tr>
            ) : (
              runs?.map((run: any) => (
                <tr key={run.run_id} className="hover:bg-dark-800/30 transition-colors text-slate-300">
                  <td className="px-4 py-3 font-mono text-xs text-primary">{run.run_id.split('-')[0]}...</td>
                  <td className="px-4 py-3">{run.started_at}</td>
                  <td className="px-4 py-3">{run.completed_at || 'In Progress'}</td>
                  <td className="px-4 py-3 text-center">{run.targets_count || 0}</td>
                  <td className="px-4 py-3 text-center">{run.success_count || 0}</td>
                  <td className="px-4 py-3 text-right">
                    {run.completed_at ? (
                      <span className="inline-flex items-center text-emerald-400 bg-emerald-900/30 px-2 py-1 rounded text-xs border border-emerald-900/50">
                        <CheckCircle2 className="w-3 h-3 mr-1" /> Completed
                      </span>
                    ) : (
                      <span className="inline-flex items-center text-yellow-400 bg-yellow-900/30 px-2 py-1 rounded text-xs border border-yellow-900/50">
                        <Clock className="w-3 h-3 mr-1" /> Running
                      </span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
