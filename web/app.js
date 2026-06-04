document.addEventListener('DOMContentLoaded', () => {
    const targetsList = document.getElementById('targets-list');
    const form = document.getElementById('add-target-form');
    const input = document.getElementById('target-username');
    const runBtn = document.getElementById('run-btn');
    const terminal = document.getElementById('terminal-output');

    // Fetch targets on load
    fetchTargets();

    // Form submit handler
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = input.value.trim();
        if (!username) return;

        try {
            const res = await fetch('/api/targets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ target: username, consent: 'false' })
            });
            
            if (res.ok) {
                input.value = '';
                fetchTargets();
            } else {
                const data = await res.json();
                alert(data.detail || 'Error adding target');
            }
        } catch (err) {
            console.error(err);
        }
    });

    // Run scraper handler
    runBtn.addEventListener('click', () => {
        terminal.innerHTML = '<span class="info">Initializing EduIG-Pipeline via Async Subprocess...</span>\n';
        runBtn.disabled = true;
        runBtn.innerHTML = '<span>Running...</span>';

        fetch('/api/run', { method: 'POST' })
            .then(response => {
                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');

                function read() {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            runBtn.disabled = false;
                            runBtn.innerHTML = `
                                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>
                                <span>Run Scraper</span>
                            `;
                            return;
                        }
                        
                        // Parse SSE chunks (data: ...)
                        const chunk = decoder.decode(value, { stream: true });
                        const lines = chunk.split('\n');
                        
                        lines.forEach(line => {
                            if (line.startsWith('data: ')) {
                                const dataStr = line.substring(6);
                                if(dataStr.trim()) {
                                    appendTerminal(dataStr);
                                }
                            }
                        });
                        read();
                    }).catch(err => {
                        appendTerminal(`\n[ERROR] Connection lost: ${err.message}`, 'error');
                        runBtn.disabled = false;
                    });
                }
                read();
            })
            .catch(err => {
                appendTerminal(`\n[ERROR] ${err.message}`, 'error');
                runBtn.disabled = false;
            });
    });

    async function fetchTargets() {
        try {
            const res = await fetch('/api/targets');
            const targets = await res.json();
            renderTargets(targets);
        } catch (err) {
            targetsList.innerHTML = '<div class="error">Failed to load targets. Is the server running?</div>';
        }
    }

    function renderTargets(targets) {
        if (targets.length === 0) {
            targetsList.innerHTML = '<div class="target-item" style="color:var(--text-secondary);justify-content:center;">No targets added yet.</div>';
            return;
        }

        targetsList.innerHTML = targets.map(t => `
            <div class="target-item">
                <span style="font-weight: 500;">${t.target}</span>
                <span class="badge ${t.consent}">${t.consent === 'true' ? 'API Consent' : 'Public Browser'}</span>
                <button class="btn-danger-icon" onclick="deleteTarget('${t.target}')" title="Remove">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                </button>
            </div>
        `).join('');
    }

    window.deleteTarget = async (target) => {
        try {
            await fetch(`/api/targets/${target}`, { method: 'DELETE' });
            fetchTargets();
        } catch (err) {
            console.error(err);
        }
    }

    function appendTerminal(text, type = 'normal') {
        const span = document.createElement('span');
        span.textContent = text + '\n';
        if (type !== 'normal') {
            span.className = type;
        } else {
            // Very simple JSON highlighting if it's a structlog line
            if (text.trim().startsWith('{') && text.includes('event')) {
                span.className = 'info';
            }
        }
        terminal.appendChild(span);
        terminal.scrollTop = terminal.scrollHeight;
    }
});
