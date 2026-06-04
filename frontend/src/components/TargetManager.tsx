import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Trash2, UserPlus, AlertCircle, CheckCircle } from 'lucide-react';

export default function TargetManager() {
  const queryClient = useQueryClient();
  const [newTarget, setNewTarget] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['targets'],
    queryFn: async () => {
      const res = await fetch('/api/targets');
      if (!res.ok) throw new Error('Failed to fetch targets');
      return res.json();
    }
  });

  const addMutation = useMutation({
    mutationFn: async (target: string) => {
      const res = await fetch('/api/targets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target, consent: 'false' })
      });
      if (!res.ok) {
        const d = await res.json();
        throw new Error(d.detail || 'Failed to add target');
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
      setNewTarget('');
      setSuccess('Target added successfully');
      setError('');
      setTimeout(() => setSuccess(''), 3000);
    },
    onError: (err: Error) => {
      setError(err.message);
      setSuccess('');
    }
  });

  const deleteMutation = useMutation({
    mutationFn: async (target: string) => {
      const res = await fetch(`/api/targets/${target}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete target');
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['targets'] });
    }
  });

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTarget.trim()) {
      setError('Username cannot be empty');
      return;
    }
    addMutation.mutate(newTarget.trim());
  };

  return (
    <div className="glass rounded-xl p-6 w-full max-w-2xl mx-auto">
      <h2 className="text-xl font-bold mb-4 text-white">Target Manager</h2>
      
      {error && (
        <div className="mb-4 p-3 bg-red-900/50 border border-red-500/50 rounded-lg flex items-center text-red-200">
          <AlertCircle className="w-5 h-5 mr-2" />
          {error}
        </div>
      )}
      
      {success && (
        <div className="mb-4 p-3 bg-green-900/50 border border-green-500/50 rounded-lg flex items-center text-green-200">
          <CheckCircle className="w-5 h-5 mr-2" />
          {success}
        </div>
      )}

      <form onSubmit={handleAdd} className="flex gap-3 mb-6">
        <input
          type="text"
          value={newTarget}
          onChange={e => setNewTarget(e.target.value)}
          placeholder="Instagram username..."
          className="flex-1 bg-dark-900/50 border border-dark-700 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-primary"
        />
        <button
          type="submit"
          disabled={addMutation.isPending}
          className="bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center transition-colors disabled:opacity-50"
        >
          <UserPlus className="w-5 h-5 mr-2" />
          {addMutation.isPending ? 'Adding...' : 'Add Target'}
        </button>
      </form>

      <div className="overflow-hidden rounded-lg border border-dark-700">
        <table className="w-full text-left text-sm">
          <thead className="bg-dark-800 text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">Username</th>
              <th className="px-4 py-3 font-medium">Consent</th>
              <th className="px-4 py-3 font-medium text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700 bg-dark-900/30">
            {isLoading ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-slate-400">Loading targets...</td>
              </tr>
            ) : data?.targets?.length === 0 ? (
              <tr>
                <td colSpan={3} className="px-4 py-8 text-center text-slate-400">No targets found. Add one above.</td>
              </tr>
            ) : (
              data?.targets?.map((t: any) => (
                <tr key={t.target} className="hover:bg-dark-800/30 transition-colors">
                  <td className="px-4 py-3 font-medium text-white">{t.target}</td>
                  <td className="px-4 py-3">
                    <span className="px-2 py-1 bg-yellow-900/30 text-yellow-500 rounded text-xs border border-yellow-900/50">
                      Public Browser
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => deleteMutation.mutate(t.target)}
                      className="text-red-400 hover:text-red-300 transition-colors"
                      title="Delete target"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
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
