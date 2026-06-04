const Toast = {
    show(message, type = 'success') {
        const toast = document.createElement('div');
        toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg text-white transform transition-all duration-300 translate-y-full opacity-0 z-50 flex items-center`;
        
        if (type === 'success') {
            toast.classList.add('bg-green-600');
            toast.innerHTML = `<i class="fa-solid fa-check-circle mr-2"></i> ${message}`;
        } else if (type === 'error') {
            toast.classList.add('bg-red-600');
            toast.innerHTML = `<i class="fa-solid fa-triangle-exclamation mr-2"></i> ${message}`;
        } else {
            toast.classList.add('bg-blue-600');
            toast.innerHTML = `<i class="fa-solid fa-info-circle mr-2"></i> ${message}`;
        }

        document.body.appendChild(toast);
        
        // Trigger animation
        setTimeout(() => {
            toast.classList.remove('translate-y-full', 'opacity-0');
        }, 10);

        // Auto dismiss after 3s
        setTimeout(() => {
            toast.classList.add('translate-y-full', 'opacity-0');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

const Dashboard = {
    currentProfilePage: 1,
    profilesPerPage: 25,

    async apiFetch(endpoint) {
        try {
            const response = await fetch(endpoint);
            if (!response.ok) {
                throw new Error(`API Error: ${response.status}`);
            }
            const data = await response.json();
            return data;
        } catch (error) {
            console.error(`Fetch failed for ${endpoint}:`, error);
            Toast.show(`Failed to fetch data. Are you offline?`, 'error');
            return null;
        }
    },

    updateTimestamp() {
        const syncEl = document.getElementById('last-sync-time');
        if (syncEl) {
            const now = new Date();
            syncEl.textContent = `Last synced: ${now.toLocaleTimeString()}`;
        }
    },

    async loadOverview() {
        const data = await this.apiFetch('/api/stats');
        if (!data) return;

        document.getElementById('stat-profiles').textContent = data.total_profiles.toLocaleString();
        document.getElementById('stat-posts').textContent = data.total_posts.toLocaleString();
        if (data.avg_engagement_rate === null || data.avg_engagement_rate === undefined || data.avg_engagement_rate === 0) {
            document.getElementById('stat-engagement-card').classList.add('hidden');
        } else {
            document.getElementById('stat-engagement-card').classList.remove('hidden');
            document.getElementById('stat-engagement').textContent = `${(data.avg_engagement_rate * 100).toFixed(2)}%`;
        }
        
        const lastRun = data.last_run ? new Date(data.last_run).toLocaleString() : 'Never';
        document.getElementById('stat-last-run').textContent = lastRun;

        if (window.Charts && data.follower_distribution && Object.keys(data.follower_distribution).length > 0) {
            document.getElementById('followerChartCard').classList.remove('hidden');
            Charts.initFollowerHistogram('followerChart', data.follower_distribution);
        } else {
            document.getElementById('followerChartCard').classList.add('hidden');
        }

        if (window.Charts && data.total_profiles > 0) {
            document.getElementById('sourceChartCard').classList.remove('hidden');
            Charts.initSourcePieChart('sourceChart', [
                {label: 'API/Auth', count: data.total_profiles}, // Mocks since we don't track source breakdown fully in stats
                {label: 'Unauth', count: 0}
            ]);
        } else {
            document.getElementById('sourceChartCard').classList.add('hidden');
        }
        this.updateTimestamp();
    },

    async loadProfiles() {
        const searchInput = document.getElementById('searchInput');
        const search = searchInput ? searchInput.value : '';
        const sortSelect = document.getElementById('sortBy');
        const sortBy = sortSelect ? sortSelect.value : 'extracted_at';
        const sortOrderBtn = document.getElementById('sortOrderBtn');
        const order = sortOrderBtn ? sortOrderBtn.dataset.order : 'desc';

        const endpoint = `/api/profiles?page=${this.currentProfilePage}&per_page=${this.profilesPerPage}&search=${encodeURIComponent(search)}&sort_by=${sortBy}&order=${order}`;
        
        const tbody = document.getElementById('profilesTableBody');
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-10 text-center text-gray-500"><i class="fa-solid fa-circle-notch fa-spin text-2xl mb-2"></i><p>Loading...</p></td></tr>`;
        }

        const data = await this.apiFetch(endpoint);
        if (!data) return;

        if (tbody) {
            tbody.innerHTML = '';
            if (data.data.length === 0) {
                tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-10 text-center text-gray-500">No profiles found.</td></tr>`;
            } else {
                data.data.forEach(p => {
                    const tr = document.createElement('tr');
                    tr.className = "hover:bg-gray-50 transition-colors";
                    const engagement = p.avg_engagement_rate ? (p.avg_engagement_rate * 100).toFixed(2) + '%' : 'N/A';
                    tr.innerHTML = `
                        <td class="px-6 py-4 whitespace-nowrap">
                            <div class="flex items-center">
                                <div class="ml-4">
                                    <div class="text-sm font-medium text-slate-100">@${p.username} ${p.is_private ? '<i class="fa-solid fa-lock text-slate-400 text-xs ml-1" title="Private Account"></i>' : ''}</div>
                                    <div class="text-sm text-slate-400">${p.full_name || ''}</div>
                                </div>
                            </div>
                        </td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">${p.followers?.toLocaleString() || '-'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">${p.posts_count?.toLocaleString() || '-'}</td>
                        <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">${engagement}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-400">
                        <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-900/50 text-green-400">${p.source}</span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-slate-400">${new Date(p.extracted_at).toLocaleDateString()}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <a href="/profile/${p.profile_id}" class="text-blue-400 hover:text-blue-300 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded p-1">View</a>
                    </td>
                `;
                    tbody.appendChild(tr);
                });
            }
        }

        const pagInfo = document.getElementById('paginationInfo');
        if (pagInfo) {
            const start = (data.page - 1) * data.per_page + 1;
            const end = Math.min(data.page * data.per_page, data.total);
            pagInfo.innerHTML = `Showing <span class="font-semibold">${data.total > 0 ? start : 0}</span> to <span class="font-semibold">${end}</span> of <span class="font-semibold">${data.total}</span> Entries`;
        }

        const pagControls = document.getElementById('paginationControls');
        if (pagControls) {
            pagControls.innerHTML = `
                <button onclick="Dashboard.changePage(${data.page - 1})" class="px-3 py-1 bg-slate-800 border border-slate-600 text-slate-300 hover:bg-slate-700 rounded-l-md disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500" ${data.page <= 1 ? 'disabled' : ''}>Prev</button>
                <button onclick="Dashboard.changePage(${data.page + 1})" class="px-3 py-1 bg-slate-800 border border-slate-600 text-slate-300 hover:bg-slate-700 rounded-r-md disabled:opacity-50 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500" ${data.page >= data.total_pages ? 'disabled' : ''}>Next</button>
            `;
        }

        this.updateTimestamp();
    },

    changePage(newPage) {
        this.currentProfilePage = newPage;
        this.loadProfiles();
    },

    async loadProfileDetail(profileId) {
        document.getElementById('profileLoading').classList.remove('hidden');
        document.getElementById('profileContent').classList.add('hidden');

        const data = await this.apiFetch(`/api/profile/${profileId}`);
        if (!data) return;

        document.getElementById('profileLoading').classList.add('hidden');
        document.getElementById('profileContent').classList.remove('hidden');

        const p = data.profile;
        document.getElementById('detailUsername').textContent = `@${p.username}`;
        document.getElementById('detailFullName').textContent = p.full_name || '';
        document.getElementById('detailBio').textContent = p.bio || 'No bio provided.';
        document.getElementById('detailPostsCount').textContent = p.posts_count?.toLocaleString() || '-';
        document.getElementById('detailFollowers').textContent = p.followers?.toLocaleString() || '-';
        if (document.getElementById('detailFollowing')) {
            document.getElementById('detailFollowing').textContent = (p.exact_following || p.following)?.toLocaleString() || '-';
        }
        if (p.avg_engagement_rate === null || p.avg_engagement_rate === undefined || p.avg_engagement_rate === 0) {
            document.getElementById('detailEngagementContainer').classList.add('hidden');
        } else {
            document.getElementById('detailEngagementContainer').classList.remove('hidden');
            document.getElementById('detailEngagement').textContent = `${(p.avg_engagement_rate * 100).toFixed(2)}%`;
        }

        if (p.is_verified) {
            document.getElementById('detailVerified').classList.remove('hidden');
        } else {
            document.getElementById('detailVerified').classList.add('hidden');
        }
        
        const privateBadge = document.getElementById('detailPrivateBadge');
        if (privateBadge) {
            if (p.is_private) {
                privateBadge.classList.remove('hidden');
            } else {
                privateBadge.classList.add('hidden');
            }
        }
        
        const avatarContainer = document.getElementById('avatarContainer');
        const detailAvatar = document.getElementById('detailAvatar');
        
        // Hide avatar initially; show only if it loads
        avatarContainer.classList.add('hidden');
        
        if (p.profile_picture_url) {
            detailAvatar.onload = () => {
                detailAvatar.classList.remove('hidden');
                avatarContainer.classList.remove('hidden');
            };
            detailAvatar.onerror = () => {
                avatarContainer.classList.add('hidden');
            };
            detailAvatar.src = p.profile_picture_url;
        }

        const grid = document.getElementById('postsGrid');
        grid.innerHTML = '';
        const latestPostsSection = document.getElementById('latestPostsSection');
        
        if (!data.posts || data.posts.length === 0) {
            latestPostsSection.classList.add('hidden');
        } else {
            latestPostsSection.classList.remove('hidden');
            data.posts.forEach(post => {
                const date = post.timestamp ? new Date(post.timestamp).toLocaleDateString() : 'Unknown date';
                const card = document.createElement('div');
                card.className = "bg-slate-900 border border-slate-700 rounded-lg p-4 shadow-sm hover-lift";
                card.innerHTML = `
                    <div class="flex justify-between text-sm text-slate-400 mb-2">
                        <span><i class="fa-regular fa-clock mr-1"></i>${date}</span>
                    </div>
                    <div class="flex gap-4 mt-4">
                        <div class="text-pink-400 font-semibold"><i class="fa-solid fa-heart mr-1"></i>${post.likes?.toLocaleString() || 0}</div>
                        <div class="text-blue-400 font-semibold"><i class="fa-solid fa-comment mr-1"></i>${post.comments?.toLocaleString() || 0}</div>
                    </div>
                `;
                grid.appendChild(card);
            });
        }
        this.updateTimestamp();
    },

    async loadCompliance() {
        const data = await this.apiFetch('/api/compliance');
        if (!data) return;

        const runsTbody = document.getElementById('runsTableBody');
        if (runsTbody) {
            runsTbody.innerHTML = '';
            data.runs.forEach(r => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-700/50 transition-colors";
                tr.innerHTML = `
                    <td class="px-4 py-3 font-mono text-xs text-slate-400">${r.run_id.substring(0, 8)}...</td>
                    <td class="px-4 py-3 text-sm text-slate-300">${new Date(r.started_at).toLocaleString()}</td>
                    <td class="px-4 py-3 text-sm text-slate-300">${r.completed_at ? new Date(r.completed_at).toLocaleString() : 'In Progress'}</td>
                    <td class="px-4 py-3 text-sm text-center font-semibold text-slate-300">${r.targets_count}</td>
                    <td class="px-4 py-3 text-sm text-center text-green-400 font-bold">${r.success_count}</td>
                `;
                runsTbody.appendChild(tr);
            });
        }

        const auditTbody = document.getElementById('auditTableBody');
        if (auditTbody) {
            auditTbody.innerHTML = '';
            data.audit_events.forEach(e => {
                const tr = document.createElement('tr');
                tr.className = "hover:bg-slate-700/50 transition-colors";
                
                let levelClass = "bg-slate-700 text-slate-300";
                if (e.level === "info") levelClass = "bg-blue-900/50 text-blue-400";
                if (e.level === "warning") levelClass = "bg-yellow-900/50 text-yellow-400";
                if (e.level === "error") levelClass = "bg-red-900/50 text-red-400";

                tr.innerHTML = `
                    <td class="px-4 py-3 text-xs text-slate-500">${e.timestamp}</td>
                    <td class="px-4 py-3"><span class="px-2 py-1 rounded text-xs font-bold uppercase ${levelClass}">${e.level || 'info'}</span></td>
                    <td class="px-4 py-3 text-sm font-medium text-slate-200">${e.event}</td>
                    <td class="px-4 py-3 text-sm text-slate-400">${e.target}</td>
                    <td class="px-4 py-3 text-xs font-mono text-slate-500 overflow-hidden text-ellipsis max-w-xs">${JSON.stringify(e.details)}</td>
                `;
                auditTbody.appendChild(tr);
            });
        }
        this.updateTimestamp();
    }
};

// Sidebar mobile toggle and keyboard navigation
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    
    function toggleSidebar() {
        sidebar.classList.toggle('-translate-x-full');
        sidebar.classList.toggle('absolute');
        sidebar.classList.toggle('z-30');
        sidebar.classList.toggle('h-screen');
    }

    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', toggleSidebar);
        
        // Hide on mobile by default
        if (window.innerWidth < 1024) {
            sidebar.classList.add('-translate-x-full', 'absolute', 'z-30', 'h-screen');
        }

        // Close sidebar on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && window.innerWidth < 1024 && !sidebar.classList.contains('-translate-x-full')) {
                toggleSidebar();
                toggleBtn.focus();
            }
        });
    }

    // Debounced search logic for generic inputs
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        let timeout = null;
        searchInput.addEventListener('keyup', (e) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                Dashboard.changePage(1);
            }, 300);
        });
    }

    // Sort handlers
    const sortBy = document.getElementById('sortBy');
    if (sortBy) {
        sortBy.addEventListener('change', () => Dashboard.changePage(1));
    }
    const sortOrderBtn = document.getElementById('sortOrderBtn');
    if (sortOrderBtn) {
        sortOrderBtn.addEventListener('click', () => {
            const current = sortOrderBtn.dataset.order;
            const newOrder = current === 'desc' ? 'asc' : 'desc';
            sortOrderBtn.dataset.order = newOrder;
            
            const icon = document.getElementById('sortOrderIcon');
            if (newOrder === 'desc') {
                icon.className = 'fa-solid fa-arrow-down-z-a';
            } else {
                icon.className = 'fa-solid fa-arrow-up-a-z';
            }
            Dashboard.changePage(1);
        });
    }
});
