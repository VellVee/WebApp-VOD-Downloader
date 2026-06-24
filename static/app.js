document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const urlInput = document.getElementById('url-input');
    const delayCb = document.getElementById('delay-cb');
    const delayMins = document.getElementById('delay-mins');
    const delayUnit = document.getElementById('delay-unit');
    const waitLiveCb = document.getElementById('wait-live-cb');
    const vodDate = document.getElementById('vod-date');
    const btnDefault = document.getElementById('btn-default');
    const btnAudio = document.getElementById('btn-audio');
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
    const inputPort = document.getElementById('setting-port');
    const inputPassword = document.getElementById('setting-password');
    const btnTheme = document.getElementById('theme-btn');
    const settingClearAll = document.getElementById('setting-clear-all');
    const btnRestart = document.getElementById('btn-restart-server');

    // Search and Filter Elements
    const taskSearch = document.getElementById('task-search');
    const filterBtns = document.querySelectorAll('.filter-btn');

    let currentSearch = '';
    let currentFilter = 'all';
    const expandedLogs = new Set();

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
    let lastTasksData = {};

    taskSearch.addEventListener('input', (e) => {
        currentSearch = e.target.value.toLowerCase().trim();
        renderTasks(lastTasksData);
    });

    filterBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            filterBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFilter = btn.dataset.filter;
            renderTasks(lastTasksData);
        });
    });

    window.toggleLogs = (id) => {
        const drawer = document.getElementById(`log-drawer-${id}`);
        const btn = document.getElementById(`log-btn-${id}`);
        if (!drawer || !btn) return;
        if (expandedLogs.has(id)) {
            expandedLogs.delete(id);
            drawer.classList.remove('active');
            btn.classList.remove('active');
        } else {
            expandedLogs.add(id);
            drawer.classList.add('active');
            btn.classList.add('active');
            const pre = drawer.querySelector('pre');
            if (pre) {
                pre.scrollTop = pre.scrollHeight;
            }
        }
    };

    // Initialize
    const today = new Date().toISOString().split('T')[0];
    vodDate.value = today;

    delayCb.addEventListener('change', () => {
        delayMins.disabled = !delayCb.checked;
        delayUnit.disabled = !delayCb.checked;
    });

    document.getElementById('delay-minus').addEventListener('click', () => {
        if (delayMins.disabled) return;
        const val = parseInt(delayMins.value) || 0;
        const step = delayUnit.value === 'hr' ? 1 : 10;
        delayMins.value = Math.max(1, val - step);
    });

    document.getElementById('delay-plus').addEventListener('click', () => {
        if (delayMins.disabled) return;
        const val = parseInt(delayMins.value) || 0;
        const step = delayUnit.value === 'hr' ? 1 : 10;
        delayMins.value = Math.min(10000, val + step);
    });

    let lastUnit = delayUnit.value;
    delayUnit.addEventListener('change', () => {
        const currentUnit = delayUnit.value;
        if (currentUnit === lastUnit) return;

        let val = parseInt(delayMins.value) || 0;
        if (currentUnit === 'hr') {
            // min to hr
            val = Math.max(1, Math.round(val / 60));
        } else {
            // hr to min
            val = Math.max(1, val * 60);
        }
        delayMins.value = val;
        lastUnit = currentUnit;
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
            inputPort.value = data.port || 5557;
        } catch (e) {
            console.error(e);
        }
    }

    const inputNewPassword = document.getElementById('setting-new-password');

    btnSavePaths.addEventListener('click', async () => {
        const payload = {
            default_path: inputDefaultPath.value,
            vod_path: inputVodPath.value,
            port: parseInt(inputPort.value) || 5557,
            password: inputPassword.value,
            new_password: inputNewPassword.value
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
            alert('Settings saved successfully!');
            inputPassword.value = ''; // clear password field
            inputNewPassword.value = ''; 
        } catch (e) {
            console.error(e);
        }
    });

    btnSavePreferences.addEventListener('click', () => {
        modal.classList.remove('active');
    });

    btnRestart.addEventListener('click', async () => {
        const password = prompt("Enter Admin Password to restart server:");
        if (password === null) return;
        
        try {
            const res = await fetch('/api/restart', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ password })
            });
            if (res.status === 401) {
                alert('Invalid Admin Password!');
                return;
            }
            alert('Server is restarting... Page will redirect to the new port in 3 seconds.');
            setTimeout(() => {
                const port = parseInt(inputPort.value) || 5557;
                window.location.href = window.location.protocol + '//' + window.location.hostname + ':' + port + '/';
            }, 3000);
        } catch (e) {
            console.error(e);
            alert('Failed to contact server. It may have already restarted.');
        }
    });

    async function startDownload(profile) {
        const url = urlInput.value.trim();
        if (!url) return;

        let dMins = 0;
        if (delayCb.checked) {
            const val = parseInt(delayMins.value) || 0;
            if (delayUnit.value === 'hr') {
                dMins = val * 60;
            } else {
                dMins = val;
            }
        }
        
        const wLive = waitLiveCb.checked;
        let dateVal = vodDate.value;

        try {
            await fetch('/api/download', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ url, profile, delay_mins: dMins, date: dateVal, wait_for_live: wLive })
            });
            urlInput.value = '';
            waitLiveCb.checked = false;
            fetchTasks();
        } catch (e) {
            console.error(e);
        }
    }

    btnDefault.addEventListener('click', () => startDownload('default'));
    btnAudio.addEventListener('click', () => startDownload('audio'));
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
            
            lastTasksData = data;
            
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
        
        let finished = 0;
        tasks.forEach(t => {
            if (t.status === 'finished') finished++;
        });

        const filteredTasks = tasks.filter(task => {
            const titleMatch = (task.title || '').toLowerCase().includes(currentSearch);
            const urlMatch = (task.url || '').toLowerCase().includes(currentSearch);
            const searchMatch = !currentSearch || titleMatch || urlMatch;
            
            let filterMatch = true;
            if (currentFilter === 'active') {
                filterMatch = ['started'].includes(task.status);
            } else if (currentFilter === 'waiting') {
                filterMatch = ['waiting'].includes(task.status);
            } else if (currentFilter === 'finished') {
                filterMatch = ['finished'].includes(task.status);
            } else if (currentFilter === 'failed') {
                filterMatch = (task.status || '').startsWith('error');
            }
            
            return searchMatch && filterMatch;
        });

        // 1. Remove elements from tasksContainer that are no longer in filteredTasks
        const currentTaskIds = new Set(filteredTasks.map(t => `task-${t.id}`));
        const existingItems = tasksContainer.querySelectorAll('.task-item');
        existingItems.forEach(item => {
            if (!currentTaskIds.has(item.id)) {
                item.remove();
            }
        });

        // 2. Loop through filteredTasks and insert/update in DOM
        filteredTasks.forEach((task, index) => {
            const logsStr = (task.log && task.log.length > 0) 
                ? task.log.slice(-150).join('\n') 
                : 'Waiting for output...';
            
            let statusText = task.status;
            if (task.status === 'error (interrupted)') {
                statusText = 'Interrupted';
            } else if (task.status === 'started') {
                if (task.wait_for_live && (task.progress || 0) === 0) {
                    statusText = 'waiting for live';
                } else {
                    statusText = 'downloading';
                }
            } else if (task.status === 'waiting') {
                if (task.target_start_time) {
                    const remainingSeconds = Math.max(0, Math.floor(task.target_start_time - (Date.now() / 1000)));
                    const h = Math.floor(remainingSeconds / 3600);
                    const m = Math.floor((remainingSeconds % 3600) / 60);
                    const s = remainingSeconds % 60;
                    if (h > 0) {
                        statusText = `waiting (${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')})`;
                    } else {
                        statusText = `waiting (${m}:${s.toString().padStart(2, '0')})`;
                    }
                }
            }

            const isExpanded = expandedLogs.has(task.id);
            let card = document.getElementById(`task-${task.id}`);
            
            if (!card) {
                // Construct the full initial card HTML
                const html = `
                    <div class="task-header">
                        <div class="task-title" title="${escapeHTML(task.url)}">${escapeHTML(task.title)}</div>
                        <div style="display:flex; gap: 0.5rem; align-items:center;">
                            <span class="task-badge badge-${escapeHTML(task.profile)}">${escapeHTML(task.profile)}</span>
                            <div class="task-action-btns">
                                ${['waiting', 'started'].includes(task.status) ? 
                                    `<button class="btn-small btn-danger" onclick="stopTask('${task.id}')">Stop</button>` 
                                    : ''}
                                ${task.status === 'cancelled' || task.status.startsWith('error') ?
                                    `<button class="btn-small" onclick="removeTask('${task.id}')">Dismiss</button>`
                                    : ''}
                            </div>
                        </div>
                    </div>
                    <div class="task-status-row">
                        <span>${statusText} (${Math.round(task.progress || 0)}%)</span>
                    </div>
                    <div class="progress-wrapper">
                        <div class="progress-bar" style="width: ${task.progress || 0}%"></div>
                    </div>
                    <div class="task-meta-container"></div>
                    ${['error', 'started', 'waiting', 'error (interrupted)', 'cancelled'].some(s => task.status.startsWith(s)) ? `
                        <button id="log-btn-${task.id}" class="btn-log-toggle ${isExpanded ? 'active' : ''}" onclick="toggleLogs('${task.id}')">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="9 18 15 12 9 6"></polyline>
                            </svg>
                            Show Terminal Logs
                        </button>
                        <div id="log-drawer-${task.id}" class="task-log-drawer ${isExpanded ? 'active' : ''}">
                            <pre class="task-log-pre">${escapeHTML(logsStr)}</pre>
                        </div>
                    ` : ''}
                `;
                
                card = document.createElement('div');
                card.id = `task-${task.id}`;
                card.className = `task-item profile-${task.profile} ${task.status === 'finished' ? 'finished' : ''}`;
                card.innerHTML = html;
                
                // Insert at the correct sorted index position
                if (index === 0) {
                    tasksContainer.insertBefore(card, tasksContainer.firstChild);
                } else {
                    const sibling = tasksContainer.children[index];
                    if (sibling) {
                        tasksContainer.insertBefore(card, sibling);
                    } else {
                        tasksContainer.appendChild(card);
                    }
                }
            } else {
                // If card exists, update sorting index position if needed
                const currentIdx = Array.from(tasksContainer.children).indexOf(card);
                if (currentIdx !== index) {
                    tasksContainer.removeChild(card);
                    const sibling = tasksContainer.children[index];
                    if (sibling) {
                        tasksContainer.insertBefore(card, sibling);
                    } else {
                        tasksContainer.appendChild(card);
                    }
                }

                // Update theme/finished classes
                const expectedClass = `task-item profile-${task.profile} ${task.status === 'finished' ? 'finished' : ''}`;
                if (card.className !== expectedClass) {
                    card.className = expectedClass;
                }

                // Update Title
                const titleEl = card.querySelector('.task-title');
                if (titleEl && titleEl.textContent !== task.title) {
                    titleEl.textContent = task.title;
                }

                // Update Action Buttons
                const actionBtnsEl = card.querySelector('.task-action-btns');
                if (actionBtnsEl) {
                    const expectedBtnsHtml = `
                        ${['waiting', 'started'].includes(task.status) ? 
                            `<button class="btn-small btn-danger" onclick="stopTask('${task.id}')">Stop</button>` 
                            : ''}
                        ${task.status === 'cancelled' || task.status.startsWith('error') ?
                            `<button class="btn-small" onclick="removeTask('${task.id}')">Dismiss</button>`
                            : ''}
                    `;
                    if (actionBtnsEl.innerHTML.replace(/\s+/g, '') !== expectedBtnsHtml.replace(/\s+/g, '')) {
                        actionBtnsEl.innerHTML = expectedBtnsHtml;
                    }
                }

                // Update Status Text
                const statusSpan = card.querySelector('.task-status-row span');
                const expectedStatusStr = `${statusText} (${Math.round(task.progress || 0)}%)`;
                if (statusSpan && statusSpan.textContent !== expectedStatusStr) {
                    statusSpan.textContent = expectedStatusStr;
                }

                // Update Progress Bar width
                const progressBar = card.querySelector('.progress-bar');
                if (progressBar) {
                    const expectedWidth = `${task.progress || 0}%`;
                    if (progressBar.style.width !== expectedWidth) {
                        progressBar.style.width = expectedWidth;
                    }
                }

                // Update Log Pre textContent (keeps selection & doesn't break scroll height)
                const logPre = card.querySelector('.task-log-pre');
                if (logPre && logPre.textContent !== logsStr) {
                    logPre.textContent = logsStr;
                    if (isExpanded) {
                        logPre.scrollTop = logPre.scrollHeight;
                    }
                }
            }

            // Update Meta Container
            const metaContainer = card.querySelector('.task-meta-container');
            if (metaContainer) {
                let metaHtml = '';
                if (task.status === 'started' || task.status === 'finished') {
                    const speed = task.speed || '';
                    const eta = task.eta || '';
                    const size = task.total_size || '';
                    
                    if (speed || eta || size) {
                        metaHtml = `
                            <div class="task-meta-row">
                                ${size ? `
                                <span class="task-meta-item size" title="Total Size">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
                                        <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
                                        <line x1="12" y1="22.08" x2="12" y2="12"></line>
                                    </svg>
                                    ${escapeHTML(size)}
                                </span>` : ''}
                                ${speed ? `
                                <span class="task-meta-item speed" title="Download Speed">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"></polyline>
                                    </svg>
                                    ${escapeHTML(speed)}
                                </span>` : ''}
                                ${eta ? `
                                <span class="task-meta-item eta" title="Estimated Time Remaining">
                                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <circle cx="12" cy="12" r="10"></circle>
                                        <polyline points="12 6 12 12 16 14"></polyline>
                                    </svg>
                                    ${escapeHTML(eta)}
                                </span>` : ''}
                            </div>
                        `;
                    }
                }
                if (metaContainer.innerHTML !== metaHtml) {
                    metaContainer.innerHTML = metaHtml;
                }
            }
        });

        // Auto-scroll any active log drawers to bottom
        expandedLogs.forEach(id => {
            const drawer = document.getElementById(`log-drawer-${id}`);
            if (drawer) {
                const pre = drawer.querySelector('pre');
                if (pre) {
                    pre.scrollTop = pre.scrollHeight;
                }
            }
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
