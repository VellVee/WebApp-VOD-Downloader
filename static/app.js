document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const urlInput = document.getElementById('url-input');
    const delayCb = document.getElementById('delay-cb');
    const delayMins = document.getElementById('delay-mins');
    const vodDate = document.getElementById('vod-date');
    const btnDefault = document.getElementById('btn-default');
    const btnVod = document.getElementById('btn-vod');
    
    const tasksContainer = document.getElementById('tasks-container');
    const btnStopAll = document.getElementById('btn-stop-all');
    const btnClearFinished = document.getElementById('btn-clear-finished');
    
    const modal = document.getElementById('settings-modal');
    const btnHamburger = document.getElementById('hamburger-btn');
    const btnCloseModal = document.getElementById('close-modal');
    const btnSavePaths = document.getElementById('btn-save-paths');
    const btnSavePreferences = document.getElementById('btn-save-preferences');
    const inputDefaultPath = document.getElementById('setting-default-path');
    const inputVodPath = document.getElementById('setting-vod-path');
    const inputPassword = document.getElementById('setting-password');
    const btnTheme = document.getElementById('theme-btn');
    const settingClearAll = document.getElementById('setting-clear-all');

    // Theme initialization
    if(localStorage.getItem('theme') === 'light') {
        document.body.classList.add('light-mode');
    }

    btnTheme.addEventListener('click', () => {
        document.body.classList.toggle('light-mode');
        if(document.body.classList.contains('light-mode')) {
            localStorage.setItem('theme', 'light');
        } else {
            localStorage.setItem('theme', 'dark');
        }
    });

    // Clear-all preference (persisted in localStorage)
    settingClearAll.checked = localStorage.getItem('clearAll') === 'true';
    settingClearAll.addEventListener('change', () => {
        localStorage.setItem('clearAll', settingClearAll.checked);
    });

    // UI state
    let tasksTimer = null;
    let oldTasksData = "{}";

    // Initialize
    const today = new Date().toISOString().split('T')[0];
    vodDate.value = today;

    delayCb.addEventListener('change', () => {
        delayMins.disabled = !delayCb.checked;
    });

    document.getElementById('delay-minus').addEventListener('click', () => {
        if (delayMins.disabled) return;
        const val = parseInt(delayMins.value) || 0;
        delayMins.value = Math.max(1, val - 10);
    });

    document.getElementById('delay-plus').addEventListener('click', () => {
        if (delayMins.disabled) return;
        const val = parseInt(delayMins.value) || 0;
        delayMins.value = Math.min(10000, val + 10);
    });

    btnHamburger.addEventListener('click', () => {
        fetchSettings();
        modal.classList.add('active');
    });

    btnCloseModal.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.remove('active');
    });

    // API calls
    async function fetchSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            inputDefaultPath.value = data.default_path || '';
            inputVodPath.value = data.vod_path || '';
        } catch (e) {
            console.error(e);
        }
    }

    btnSavePaths.addEventListener('click', async () => {
        const payload = {
            default_path: inputDefaultPath.value,
            vod_path: inputVodPath.value,
            password: inputPassword.value
        };
        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            if (res.status === 401) {
                alert('Invalid Admin Password!');
                return;
            }
            alert('Paths saved successfully!');
            inputPassword.value = ''; // clear password field
        } catch (e) {
            console.error(e);
        }
    });

    btnSavePreferences.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    async function startDownload(profile) {
        const url = urlInput.value.trim();
        if (!url) return;

        let dMins = 0;
        if (delayCb.checked) {
            dMins = parseInt(delayMins.value) || 0;
        }
        
        let dateVal = vodDate.value;

        try {
            await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url, profile, delay_mins: dMins, date: dateVal })
            });
            urlInput.value = '';
            fetchTasks();
        } catch (e) {
            console.error(e);
        }
    }

    btnDefault.addEventListener('click', () => startDownload('default'));
    btnVod.addEventListener('click', () => startDownload('vod'));

    btnStopAll.addEventListener('click', async () => {
        await fetch('/api/stop_all', { method: 'POST' });
        fetchTasks();
    });

    btnClearFinished.addEventListener('click', async () => {
        const includeCancelled = localStorage.getItem('clearAll') === 'true';
        await fetch(`/api/clear_finished?include_cancelled=${includeCancelled}`, { method: 'POST' });
        fetchTasks();
    });

    async function stopTask(id) {
        await fetch(`/api/stop/${id}`, { method: 'POST' });
        fetchTasks();
    }

    async function removeTask(id) {
        await fetch(`/api/remove/${id}`, { method: 'POST' });
        fetchTasks();
    }
    
    // Make functions available globally
    window.stopTask = stopTask;
    window.removeTask = removeTask;

    async function fetchTasks() {
        try {
            const res = await fetch('/api/tasks');
            const data = await res.json();
            
            // Check if data changed to avoid unnecessary DOM rebuilds
            const newDataStr = JSON.stringify(data);
            const hasWaiting = Object.values(data).some(t => t.status === 'waiting');
            if(newDataStr === oldTasksData && !hasWaiting) return;
            oldTasksData = newDataStr;

            renderTasks(data);
        } catch (e) {
            console.error(e);
        }
    }

    function renderTasks(data) {
        const escapeHTML = (str) => {
            if (!str) return '';
            return str.toString()
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#039;");
        };

        const tasks = Object.values(data).sort((a, b) => b.created_at - a.created_at);
        tasksContainer.innerHTML = '';
        
        let finished = 0;
        
        tasks.forEach(task => {
            if (task.status === 'finished') finished++;
            
            const logsStr = (task.log && task.log.length > 0) 
                ? task.log.slice(-10).join('<br>') 
                : 'Waiting for output...';
            
            let statusText = task.status;
            if (task.status === 'error (interrupted)') {
                statusText = 'Interrupted';
            } else if (task.status === 'started') {
                statusText = 'downloading';
            } else if (task.status === 'waiting') {
                if (task.target_start_time) {
                    const remainingSeconds = Math.max(0, Math.floor(task.target_start_time - (Date.now() / 1000)));
                    const m = Math.floor(remainingSeconds / 60);
                    const s = remainingSeconds % 60;
                    statusText = `waiting (${m}:${s.toString().padStart(2, '0')})`;
                }
            }
            
            const html = `
                <div class="task-item profile-${escapeHTML(task.profile)} ${task.status === 'finished' ? 'finished' : ''}">
                    <div class="task-header">
                        <div class="task-title" title="${escapeHTML(task.url)}">${escapeHTML(task.title)}</div>
                        <div style="display:flex; gap: 0.5rem; align-items:center;">
                            <span class="task-badge badge-${escapeHTML(task.profile)}">${escapeHTML(task.profile)}</span>
                            ${['waiting', 'started'].includes(task.status) ? 
                                `<button class="btn-small btn-danger" onclick="stopTask('${task.id}')">Stop</button>` 
                                : ''}
                            ${task.status === 'cancelled' || task.status.startsWith('error') ?
                                `<button class="btn-small" onclick="removeTask('${task.id}')">Dismiss</button>`
                                : ''}
                        </div>
                    </div>
                    <div class="task-status-row">
                        <span>${statusText} (${Math.round(task.progress || 0)}%)</span>
                    </div>
                    <div class="progress-wrapper">
                        <div class="progress-bar" style="width: ${task.progress || 0}%"></div>
                    </div>
                    ${['error', 'started', 'waiting', 'error (interrupted)', 'cancelled'].some(s => task.status.startsWith(s)) ? 
                        `<div class="task-log">${logsStr}</div>` : ''}
                </div>
            `;
            tasksContainer.insertAdjacentHTML('beforeend', html);
        });

        // Update document title
        const total = tasks.length;
        if (total > 0) {
            document.title = `[${finished}/${total}] Web Video Downloader`;
        } else {
            document.title = `Web Video Downloader`;
        }
    }

    // Start polling Loop
    fetchTasks();
    tasksTimer = setInterval(fetchTasks, 1500);
});
