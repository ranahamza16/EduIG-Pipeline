import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Search } from 'lucide-react';

export default function CollectedData() {
  const [search, setSearch] = useState('');

  const { data: profiles, isLoading } = useQuery({
    queryKey: ['profiles'],
    queryFn: async () => {
      const res = await fetch('/api/data/profiles');
      if (!res.ok) throw new Error('Failed to fetch profiles');
      return res.json();
    }
  });

  const filtered = profiles?.filter((p: any) => 
    p.username?.toLowerCase().includes(search.toLowerCase()) ||
    p.bio?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="glass rounded-xl p-6 w-full">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold text-white">Collected Data</h2>
        <div className="flex gap-3">
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="bg-dark-900/50 border border-dark-700 rounded-lg pl-10 pr-4 py-2 text-white focus:outline-none focus:border-primary"
            />
          </div>
          <button className="bg-dark-700 hover:bg-dark-600 text-white px-4 py-2 rounded-lg flex items-center transition-colors">
            <Download className="w-4 h-4 mr-2" /> CSV
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-lg border border-dark-700">
        <table className="w-full text-left text-sm whitespace-nowrap">
          <thead className="bg-dark-800 text-slate-300">
            <tr>
              <th className="px-4 py-3 font-medium">Username</th>
              <th className="px-4 py-3 font-medium">Full Name</th>
              <th className="px-4 py-3 font-medium">Followers</th>
              <th className="px-4 py-3 font-medium">Following</th>
              <th className="px-4 py-3 font-medium">Posts</th>
              <th className="px-4 py-3 font-medium">Extracted At</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-700 bg-dark-900/30">
            {isLoading ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">Loading data...</td>
              </tr>
            ) : filtered?.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-400">No data found in SQLite database.</td>
              </tr>
            ) : (
              filtered?.map((p: any, i: number) => (
                <tr key={i} className="hover:bg-dark-800/30 transition-colors text-slate-300">
                  <td className="px-4 py-3 font-semibold text-primary">
                    <a href={`https://instagram.com/${p.username}`} target="_blank" rel="noopener noreferrer" className="hover:underline">
                      @{p.username}
                    </a>
                    {p.is_verified && <span className="ml-2 text-blue-400" title="Verified">✓</span>}
                  </td>
                  <td className="px-4 py-3 text-slate-300">{p.full_name || '-'}</td>
                  <td className="px-4 py-3">{p.followers?.toLocaleString() || 'N/A'}</td>
                  <td className="px-4 py-3">{p.following?.toLocaleString() || 'N/A'}</td>
                  <td className="px-4 py-3">{p.posts_count?.toLocaleString() || 'N/A'}</td>
                  <td className="px-4 py-3">{p.extracted_at}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
