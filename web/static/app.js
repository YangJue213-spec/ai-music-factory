// Music Factory Web UI JavaScript

const API_BASE = '';

// Tab switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        
        // Update active states
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        btn.classList.add('active');
        document.getElementById(tab).classList.add('active');
        
        // Load data for specific tabs
        if (tab === 'files') loadFiles();
        if (tab === 'dedup') loadDedup();
        if (tab === 'logs') loadLogs();
        if (tab === 'settings') loadSettings();
        if (tab === 'sources') loadSources();
        if (tab === 'singers') loadSingers();
    });
});

// Load settings
async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/settings`);
        const data = await response.json();
        
        if (data.success && data.settings) {
            const settings = data.settings;
            
            // Set title mode
            const titleMode = settings.title_mode || 'original';
            document.querySelectorAll('input[name="title-mode"]').forEach(radio => {
                radio.checked = (radio.value === titleMode);
            });
            
            // Set cover style
            const coverStyle = settings.cover_style || 'realistic';
            document.querySelectorAll('input[name="cover-style"]').forEach(radio => {
                radio.checked = (radio.value === coverStyle);
            });
            
            // Set cover figure
            const coverFigure = settings.cover_include_figure !== false;
            document.getElementById('cover-figure').checked = coverFigure;
        }
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

// Save settings
document.getElementById('btn-save-settings').addEventListener('click', async () => {
    const titleMode = document.querySelector('input[name="title-mode"]:checked')?.value || 'original';
    const coverStyle = document.querySelector('input[name="cover-style"]:checked')?.value || 'realistic';
    const coverFigure = document.getElementById('cover-figure').checked;
    
    const settings = {
        title_mode: titleMode,
        cover_style: coverStyle,
        cover_include_figure: coverFigure
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        const statusEl = document.getElementById('settings-save-status');
        
        if (data.success) {
            statusEl.textContent = '✅ 设置已保存';
            statusEl.style.color = 'var(--success)';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        } else {
            statusEl.textContent = '❌ 保存失败: ' + data.error;
            statusEl.style.color = 'var(--danger)';
        }
    } catch (error) {
        const statusEl = document.getElementById('settings-save-status');
        statusEl.textContent = '❌ 保存失败: ' + error.message;
        statusEl.style.color = 'var(--danger)';
    }
});

// Load configuration on page load
async function loadConfig() {
    try {
        const response = await fetch(`${API_BASE}/api/config`);
        const data = await response.json();
        
        if (data.success) {
            // Update API status indicators
            for (const [provider, cfg] of Object.entries(data.apis)) {
                const statusEl = document.getElementById(`status-${provider}`);
                const inputEl = document.getElementById(`api-${provider}`);
                const editBtn = document.querySelector(`.btn-edit[data-provider="${provider}"]`);
                const apiItem = document.querySelector(`.api-item[data-provider="${provider}"]`);
                
                if (statusEl && inputEl && editBtn) {
                    if (cfg.configured) {
                        statusEl.textContent = '已配置';
                        statusEl.classList.add('configured');
                        // 隐藏输入框，显示修改按钮
                        inputEl.style.display = 'none';
                        editBtn.style.display = 'inline-block';
                        // 添加已配置的样式
                        apiItem.classList.add('api-configured');
                    } else {
                        statusEl.textContent = '未配置';
                        statusEl.classList.remove('configured');
                        // 显示输入框，隐藏修改按钮
                        inputEl.style.display = 'block';
                        editBtn.style.display = 'none';
                        // 移除已配置的样式
                        apiItem.classList.remove('api-configured');
                    }
                }
            }
        }
    } catch (error) {
        console.error('Failed to load config:', error);
    }
}

// 编辑按钮点击事件
document.querySelectorAll('.btn-edit').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const provider = e.target.dataset.provider;
        const inputEl = document.getElementById(`api-${provider}`);
        const editBtn = e.target;
        
        // 显示输入框，隐藏修改按钮
        inputEl.style.display = 'block';
        inputEl.value = ''; // 清空输入框
        inputEl.placeholder = `输入新的 ${provider} API Key`;
        editBtn.style.display = 'none';
        
        // 更新状态为编辑模式
        const statusEl = document.getElementById(`status-${provider}`);
        if (statusEl) {
            statusEl.textContent = '编辑中';
            statusEl.classList.remove('configured');
        }
        
        // 聚焦到输入框
        inputEl.focus();
    });
});

// Save configuration
document.getElementById('btn-save-config').addEventListener('click', async () => {
    const apis = {
        deepseek: document.getElementById('api-deepseek').value,
        openai: document.getElementById('api-openai').value,
        suno: document.getElementById('api-suno').value,
        siliconflow: document.getElementById('api-siliconflow').value
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/config`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ apis })
        });
        
        const data = await response.json();
        if (data.success) {
            alert('✅ 配置已保存！');
            loadConfig();
        } else {
            alert('❌ 保存失败: ' + data.error);
        }
    } catch (error) {
        alert('❌ 保存失败: ' + error.message);
    }
});

// Start pipeline
document.getElementById('btn-start').addEventListener('click', async () => {
    const count = parseInt(document.getElementById('song-count').value) || null;
    
    try {
        const response = await fetch(`${API_BASE}/api/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ max_songs: count })
        });
        
        const data = await response.json();
        if (data.success) {
            updateStatus('running');
            startStatusPolling();
        } else {
            alert('❌ 启动失败: ' + data.error);
        }
    } catch (error) {
        alert('❌ 启动失败: ' + error.message);
    }
});

// Stop pipeline
document.getElementById('btn-stop').addEventListener('click', async () => {
    try {
        await fetch(`${API_BASE}/api/stop`, { method: 'POST' });
        updateStatus('stopped');
    } catch (error) {
        console.error('Failed to stop:', error);
    }
});

// Status polling
let statusInterval = null;

function startStatusPolling() {
    if (statusInterval) clearInterval(statusInterval);
    statusInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/status`);
            const data = await response.json();
            
            updateStatusUI(data);
            
            if (!data.running && data.status !== 'idle') {
                clearInterval(statusInterval);
            }
        } catch (error) {
            console.error('Status poll failed:', error);
        }
    }, 1000);
}

function updateStatusUI(data) {
    const statusText = document.getElementById('status-text');
    const statusIndicator = document.querySelector('.status-indicator');
    const progressBar = document.getElementById('progress-bar');
    const currentStage = document.getElementById('current-stage');
    const btnStart = document.getElementById('btn-start');
    const btnStop = document.getElementById('btn-stop');
    
    // Update status text and indicator
    statusText.textContent = data.message || data.status;
    statusIndicator.className = 'status-indicator ' + data.status;
    
    // Update progress - 优先使用后端传来的 progress，否则根据 step/total_steps 计算
    let progress = 0;
    if (data.progress !== undefined && data.progress !== null) {
        // 后端传来的精确进度（如逐首生成阶段的动态进度）
        progress = data.progress;
    } else if (data.step && data.total_steps) {
        // 根据阶段计算（前3个阶段各占20%，第4阶段占60%，第5阶段占20%）
        if (data.step <= 3) {
            progress = (data.step / 5) * 100 * 0.6; // 前3阶段共占60%，每阶段20%
        } else if (data.step === 4) {
            progress = 60; // 第4阶段开始是60%
        } else if (data.step === 5) {
            progress = 80 + (20 / 5); // 第5阶段从80%到100%
        }
    }
    progressBar.style.width = progress + '%';
    
    // Update stage
    if (data.stage) {
        currentStage.textContent = `当前阶段: ${data.stage}`;
        document.getElementById('stat-stage').textContent = data.stage;
    }
    
    // Update buttons
    btnStart.disabled = data.running;
    btnStop.disabled = !data.running;
    
    // Update stats if available
    if (data.fetched !== undefined) {
        document.getElementById('stat-fetched').textContent = data.fetched;
    }
    if (data.cleaned !== undefined) {
        document.getElementById('stat-cleaned').textContent = data.cleaned;
    }
    if (data.generated !== undefined) {
        document.getElementById('stat-generated').textContent = data.generated;
    }
}

function updateStatus(status) {
    const statusText = document.getElementById('status-text');
    const statusIndicator = document.querySelector('.status-indicator');
    
    statusText.textContent = status;
    statusIndicator.className = 'status-indicator ' + status;
}

// Load files
async function loadFiles() {
    const container = document.getElementById('file-list');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/files`);
        const data = await response.json();
        
        if (data.success) {
            renderFiles(data.files);
        } else {
            container.innerHTML = '<div class="loading">加载失败: ' + data.error + '</div>';
        }
    } catch (error) {
        container.innerHTML = '<div class="loading">加载失败: ' + error.message + '</div>';
    }
}

function renderFiles(fileGroups) {
    const container = document.getElementById('file-list');
    
    if (fileGroups.length === 0) {
        container.innerHTML = '<div class="loading">暂无生成文件</div>';
        return;
    }
    
    let html = '';
    for (const group of fileGroups) {
        html += `
            <div class="file-date-group">
                <h3>${group.date} (${group.files.length} 个文件)</h3>
        `;
        
        for (const file of group.files) {
            const size = formatFileSize(file.size);
            html += `
                <div class="file-item">
                    <span class="file-name">${file.name}</span>
                    <span class="file-size">${size}</span>
                    <div class="file-actions-inline">
                        <button class="btn btn-primary" onclick="downloadFile('${file.path}')">下载</button>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function downloadFile(path) {
    window.open(`${API_BASE}/api/files/download/${path}`, '_blank');
}

// Load deduplication status
async function loadDedup() {
    try {
        const response = await fetch(`${API_BASE}/api/deduplication`);
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('dedup-count').textContent = data.total_fingerprints;
            
            const samplesEl = document.getElementById('dedup-samples');
            if (data.sample.length > 0) {
                samplesEl.innerHTML = data.sample.map(s => `<li>${s}</li>`).join('');
            } else {
                samplesEl.innerHTML = '<li>暂无已生成歌曲</li>';
            }
        }
    } catch (error) {
        console.error('Failed to load dedup:', error);
    }
}

// Load logs
async function loadLogs() {
    try {
        const response = await fetch(`${API_BASE}/api/logs`);
        const data = await response.json();
        
        if (data.success) {
            const content = document.getElementById('log-content');
            content.textContent = data.logs.join('');
            // Auto scroll to bottom
            const container = document.getElementById('log-container');
            container.scrollTop = container.scrollHeight;
        }
    } catch (error) {
        console.error('Failed to load logs:', error);
    }
}

// Environment check
document.getElementById('btn-check-env').addEventListener('click', async () => {
    const resultDiv = document.getElementById('env-check-result');
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div class="loading">正在检查环境...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/check`);
        const data = await response.json();
        
        if (data.success) {
            let html = '<div class="env-check-list">';
            for (const [key, check] of Object.entries(data.checks)) {
                const icon = check.status ? '●' : '●';
                const nameMap = {
                    'python': 'Python 版本',
                    'dependencies': '依赖包',
                    'api_config': 'API 配置',
                    'folders': '文件夹结构'
                };
                html += `
                    <div class="env-check-item ${check.status ? 'ok' : 'error'}">
                        <span class="env-check-icon">${icon}</span>
                        <span class="env-check-name">${nameMap[key]}</span>
                        <span class="env-check-msg">${check.message}</span>
                    </div>
                `;
            }
            html += '</div>';
            
            if (data.ready) {
                html += `<div class="env-check-success">环境检查全部通过！可以开始运行</div>`;
            } else {
                html += `<div class="env-check-warning">请根据上方提示修复问题后再运行</div>`;
            }
            
            resultDiv.innerHTML = html;
        } else {
            resultDiv.innerHTML = `<div class="env-check-error">检查失败: ${data.error}</div>`;
        }
    } catch (error) {
        resultDiv.innerHTML = `<div class="env-check-error">检查失败: ${error.message}</div>`;
    }
});

// Refresh buttons
document.getElementById('btn-refresh-files').addEventListener('click', loadFiles);
document.getElementById('btn-refresh-logs').addEventListener('click', loadLogs);

document.getElementById('btn-clear-logs').addEventListener('click', () => {
    document.getElementById('log-content').textContent = '日志已清空...';
});

document.getElementById('btn-open-folder').addEventListener('click', () => {
    // This would need a backend endpoint to open folder
    alert('请手动打开 output/musics/ 文件夹查看生成的文件');
});

// 归档功能
document.getElementById('btn-archive').addEventListener('click', async () => {
    const count = parseInt(document.getElementById('archive-count').value) || 0;
    const statusEl = document.getElementById('archive-status');
    const resultEl = document.getElementById('archive-result');
    
    statusEl.textContent = '正在归档...';
    statusEl.style.color = 'var(--accent-primary)';
    resultEl.style.display = 'none';
    
    try {
        const response = await fetch(`${API_BASE}/api/archive`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count: count })
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusEl.textContent = '归档完成';
            statusEl.style.color = 'var(--accent-success)';
            
            // 显示详细结果
            let html = `
                <div class="archive-summary">
                    <h4>归档结果</h4>
                    <p><strong>日期文件夹:</strong> ${data.date_folder}</p>
                    <p><strong>目标路径:</strong> ${data.target_dir}</p>
                    <p><strong>归档数量:</strong> ${data.archived} 首</p>
            `;
            
            if (data.failed > 0) {
                html += `<p><strong>失败:</strong> ${data.failed} 首</p>`;
            }
            
            if (data.files && data.files.length > 0) {
                html += `<div class="archive-files"><strong>已归档文件:</strong><ul>`;
                data.files.forEach(file => {
                    html += `<li>${file}</li>`;
                });
                html += `</ul></div>`;
            }
            
            html += `</div>`;
            resultEl.innerHTML = html;
            resultEl.style.display = 'block';
            
            // 刷新文件列表
            loadFiles();
        } else {
            statusEl.textContent = '归档失败: ' + data.error;
            statusEl.style.color = 'var(--accent-danger)';
        }
    } catch (error) {
        statusEl.textContent = '归档失败: ' + error.message;
        statusEl.style.color = 'var(--accent-danger)';
    }
});

// 控制面板快速设置
document.getElementById('btn-save-settings-control').addEventListener('click', async () => {
    const titleMode = document.querySelector('input[name="title-mode-control"]:checked')?.value || 'original';
    const coverStyle = document.querySelector('input[name="cover-style-control"]:checked')?.value || 'realistic';
    const coverFigure = document.getElementById('cover-figure-control').checked;
    
    const settings = {
        title_mode: titleMode,
        cover_style: coverStyle,
        cover_include_figure: coverFigure
    };
    
    try {
        const response = await fetch(`${API_BASE}/api/settings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(settings)
        });
        
        const data = await response.json();
        const statusEl = document.getElementById('settings-save-status-control');
        
        if (data.success) {
            statusEl.textContent = '设置已保存';
            statusEl.style.color = 'var(--accent-success)';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        } else {
            statusEl.textContent = '保存失败: ' + data.error;
            statusEl.style.color = 'var(--accent-danger)';
        }
    } catch (error) {
        const statusEl = document.getElementById('settings-save-status-control');
        statusEl.textContent = '保存失败: ' + error.message;
        statusEl.style.color = 'var(--accent-danger)';
    }
});

// 加载快速设置
async function loadQuickSettings() {
    try {
        const response = await fetch(`${API_BASE}/api/settings`);
        const data = await response.json();
        
        if (data.success && data.settings) {
            const settings = data.settings;
            
            // Set title mode
            const titleMode = settings.title_mode || 'original';
            document.querySelectorAll('input[name="title-mode-control"]').forEach(radio => {
                radio.checked = (radio.value === titleMode);
            });
            
            // Set cover style
            const coverStyle = settings.cover_style || 'realistic';
            document.querySelectorAll('input[name="cover-style-control"]').forEach(radio => {
                radio.checked = (radio.value === coverStyle);
            });
            
            // Set cover figure
            const coverFigure = settings.cover_include_figure !== false;
            document.getElementById('cover-figure-control').checked = coverFigure;
        }
    } catch (error) {
        console.error('Failed to load quick settings:', error);
    }
}

// 音乐源管理
let currentSources = {
    monitored_artists: [],
    chart_sources: []
};

async function loadSources() {
    try {
        const response = await fetch(`${API_BASE}/api/sources`);
        const data = await response.json();
        
        if (data.success) {
            currentSources = data.sources;
            renderSources();
        }
    } catch (error) {
        console.error('Failed to load sources:', error);
        document.getElementById('monitored-artists').innerHTML = '<div class="error">加载失败</div>';
        document.getElementById('chart-sources').innerHTML = '<div class="error">加载失败</div>';
    }
}

function renderSources() {
    // 渲染监控艺人
    const artistsContainer = document.getElementById('monitored-artists');
    if (currentSources.monitored_artists.length === 0) {
        artistsContainer.innerHTML = '<div class="empty">暂无监控艺人</div>';
    } else {
        artistsContainer.innerHTML = currentSources.monitored_artists.map((artist, index) => `
            <div class="source-item">
                <input type="checkbox" id="artist-${index}" ${artist.enabled ? 'checked' : ''} 
                       onchange="toggleArtist(${index})">
                <label for="artist-${index}">${artist.name}</label>
                <button class="btn btn-small btn-delete" onclick="deleteArtist(${index})">🗑️</button>
            </div>
        `).join('');
    }
    
    // 渲染榜单
    const chartsContainer = document.getElementById('chart-sources');
    if (currentSources.chart_sources.length === 0) {
        chartsContainer.innerHTML = '<div class="empty">暂无榜单监控</div>';
    } else {
        chartsContainer.innerHTML = currentSources.chart_sources.map((chart, index) => `
            <div class="source-item">
                <input type="checkbox" id="chart-${index}" ${chart.enabled ? 'checked' : ''}
                       onchange="toggleChart(${index})">
                <label for="chart-${index}">${chart.name}</label>
                <button class="btn btn-small btn-delete" onclick="deleteChart(${index})">🗑️</button>
            </div>
        `).join('');
    }
}

function toggleArtist(index) {
    currentSources.monitored_artists[index].enabled = !currentSources.monitored_artists[index].enabled;
}

function deleteArtist(index) {
    currentSources.monitored_artists.splice(index, 1);
    renderSources();
}

function toggleChart(index) {
    currentSources.chart_sources[index].enabled = !currentSources.chart_sources[index].enabled;
}

function deleteChart(index) {
    currentSources.chart_sources.splice(index, 1);
    renderSources();
}

// 添加艺人
document.getElementById('btn-add-artist').addEventListener('click', () => {
    const name = document.getElementById('new-artist-name').value.trim();
    if (!name) return;
    
    currentSources.monitored_artists.push({
        name: name,
        enabled: true
    });
    
    document.getElementById('new-artist-name').value = '';
    renderSources();
});

// 添加榜单
document.getElementById('btn-add-chart').addEventListener('click', () => {
    const name = document.getElementById('new-chart-name').value.trim();
    const url = document.getElementById('new-chart-url').value.trim();
    if (!name) return;
    
    currentSources.chart_sources.push({
        name: name,
        url: url,
        enabled: true
    });
    
    document.getElementById('new-chart-name').value = '';
    document.getElementById('new-chart-url').value = '';
    renderSources();
});

// 保存音乐源
document.getElementById('btn-save-sources').addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/api/sources`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentSources)
        });
        
        const data = await response.json();
        const statusEl = document.getElementById('sources-save-status');
        
        if (data.success) {
            statusEl.textContent = '音乐源已保存';
            statusEl.style.color = 'var(--accent-success)';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        } else {
            statusEl.textContent = '保存失败: ' + data.error;
            statusEl.style.color = 'var(--accent-danger)';
        }
    } catch (error) {
        const statusEl = document.getElementById('sources-save-status');
        statusEl.textContent = '保存失败: ' + error.message;
        statusEl.style.color = 'var(--accent-danger)';
    }
});

// 歌手库管理
let currentSingers = {
    male: [],
    female: []
};

async function loadSingers() {
    try {
        const response = await fetch(`${API_BASE}/api/singers`);
        const data = await response.json();
        
        if (data.success) {
            currentSingers = data.singers;
            renderSingers();
        }
    } catch (error) {
        console.error('Failed to load singers:', error);
        document.getElementById('male-singers').innerHTML = '<div class="error">加载失败</div>';
        document.getElementById('female-singers').innerHTML = '<div class="error">加载失败</div>';
    }
}

function renderSingers() {
    // 男歌手
    const maleContainer = document.getElementById('male-singers');
    maleContainer.innerHTML = currentSingers.male.map((singer, index) => `
        <div class="singer-tag">
            ${singer}
            <button class="btn btn-small btn-delete-singer" onclick="deleteSinger('male', ${index})">✕</button>
        </div>
    `).join('');
    
    // 女歌手
    const femaleContainer = document.getElementById('female-singers');
    femaleContainer.innerHTML = currentSingers.female.map((singer, index) => `
        <div class="singer-tag">
            ${singer}
            <button class="btn btn-small btn-delete-singer" onclick="deleteSinger('female', ${index})">✕</button>
        </div>
    `).join('');
}

function deleteSinger(gender, index) {
    currentSingers[gender].splice(index, 1);
    renderSingers();
}

// 添加歌手按钮
document.querySelectorAll('.btn-add-singer').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const gender = e.target.dataset.gender;
        document.getElementById(`add-${gender}-form`).style.display = 'flex';
        e.target.style.display = 'none';
    });
});

// 确认添加歌手
document.querySelectorAll('.btn-confirm-add').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const gender = e.target.dataset.gender;
        const input = document.querySelector(`#add-${gender}-form .new-singer-input`);
        const name = input.value.trim();
        
        if (name) {
            currentSingers[gender].push(name);
            renderSingers();
        }
        
        // 重置表单
        input.value = '';
        document.getElementById(`add-${gender}-form`).style.display = 'none';
        document.querySelector(`.btn-add-singer[data-gender="${gender}"]`).style.display = 'inline-block';
    });
});

// 取消添加歌手
document.querySelectorAll('.btn-cancel-add').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const gender = e.target.dataset.gender;
        document.getElementById(`add-${gender}-form`).style.display = 'none';
        document.querySelector(`.btn-add-singer[data-gender="${gender}"]`).style.display = 'inline-block';
    });
});

// 保存歌手库
document.getElementById('btn-save-singers').addEventListener('click', async () => {
    try {
        const response = await fetch(`${API_BASE}/api/singers`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentSingers)
        });
        
        const data = await response.json();
        const statusEl = document.getElementById('singers-save-status');
        
        if (data.success) {
            statusEl.textContent = '歌手库已保存';
            statusEl.style.color = 'var(--accent-success)';
            setTimeout(() => {
                statusEl.textContent = '';
            }, 3000);
        } else {
            statusEl.textContent = '保存失败: ' + data.error;
            statusEl.style.color = 'var(--accent-danger)';
        }
    } catch (error) {
        const statusEl = document.getElementById('singers-save-status');
        statusEl.textContent = '保存失败: ' + error.message;
        statusEl.style.color = 'var(--accent-danger)';
    }
});

// Initialize - 页面加载时自动读取所有 YAML 配置
document.addEventListener('DOMContentLoaded', async () => {
    console.log('初始化 Web 界面，加载配置...');
    
    // 并行加载所有配置
    await Promise.all([
        loadConfig(),
        loadQuickSettings(),
        loadSettings(),
        loadSources(),
        loadSingers()
    ]);
    
    console.log('所有配置加载完成');
    startStatusPolling();
});
