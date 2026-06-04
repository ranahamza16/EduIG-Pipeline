const Charts = {
    instances: {},

    _getChartColor(index) {
        const colors = [
            'rgba(59, 130, 246, 0.8)',   // blue-500
            'rgba(168, 85, 247, 0.8)',   // purple-500
            'rgba(236, 72, 153, 0.8)',   // pink-500
            'rgba(34, 197, 94, 0.8)',    // green-500
            'rgba(245, 158, 11, 0.8)',   // amber-500
        ];
        return colors[index % colors.length];
    },

    _applyDarkDefaults() {
        if (window.Chart) {
            Chart.defaults.color = '#94a3b8'; // slate-400
            Chart.defaults.borderColor = '#334155'; // slate-700
            Chart.defaults.font.family = 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif';
        }
    },

    initFollowerHistogram(containerId, distributionData) {
        this._applyDarkDefaults();
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        if (this.instances[containerId]) {
            this.instances[containerId].destroy();
        }

        const labels = distributionData.map(d => d.bucket);
        const data = distributionData.map(d => d.count);

        this.instances[containerId] = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Profiles',
                    data: data,
                    backgroundColor: 'rgba(59, 130, 246, 0.6)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1,
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1 }
                    }
                }
            }
        });
    },

    initSourcePieChart(containerId, sourceData) {
        this._applyDarkDefaults();
        const ctx = document.getElementById(containerId);
        if (!ctx) return;

        if (this.instances[containerId]) {
            this.instances[containerId].destroy();
        }

        const labels = sourceData.map(d => d.label);
        const data = sourceData.map(d => d.count);
        const bgColors = sourceData.map((_, i) => this._getChartColor(i));

        this.instances[containerId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: bgColors,
                    borderWidth: 2,
                    borderColor: '#1e293b' // slate-900 matches background
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20, boxWidth: 12 }
                    }
                }
            }
        });
    }
};
