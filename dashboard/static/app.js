/**
 * AI Cost Profiler Dashboard – Enhanced JavaScript Client
 * Supports: Chart.js charts, tabs, live feed, model catalog, provider breakdown
 */

// Chart.js defaults
if (typeof Chart !== 'undefined') {
    Chart.defaults.color = '#888888';
    Chart.defaults.borderColor = '#222222';
    Chart.defaults.font.family = "'JetBrains Mono', monospace";
    Chart.defaults.font.size = 10;
}

const CHART_COLORS = [
    '#00FF88', '#0A84FF', '#FF9500', '#BF5AF2',
    '#32D2FF', '#FF3B30', '#FFD60A', '#30D158',
    '#64D2FF', '#FF6961', '#FF9F0A', '#5E5CE6',
];

// ── Utility helpers ──────────────────────────────────────────────────────────

function fmtCost(v) {
    if (v === 0) return '$0.00';
    if (v < 0.000001) return '$' + v.toFixed(10);
    if (v < 0.0001)   return '$' + v.toFixed(8);
    if (v < 0.01)     return '$' + v.toFixed(6);
    if (v < 1)        return '$' + v.toFixed(4);
    return '$' + v.toFixed(2);
}

function fmtTokens(n) {
    if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M';
    if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K';
    return String(n);
}

function fmtNumber(n) {
    return n.toLocaleString();
}

function escapeHtml(s) {
    const d = document.createElement('div');
    d.textContent = s || '';
    return d.innerHTML;
}

function priceClass(v) {
    if (v === 0)   return 'price-free';
    if (v < 1)     return 'price-low';
    if (v < 5)     return 'price-mid';
    return 'price-high';
}

// ── Main Dashboard Class ─────────────────────────────────────────────────────

class CostProfilerDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.timeRange = 24;
        this.charts = {};
        this.catalogData = [];
        this.catalogSortCol = 'input_per_1m';
        this.catalogSortAsc = true;

        this.init();
    }

    init() {
        this.setupTabs();
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadData();
        this.loadCatalog();
    }

    // ── Tabs ──────────────────────────────────────────────────────────────────

    setupTabs() {
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                tab.classList.add('active');
                const id = 'tab-' + tab.dataset.tab;
                document.getElementById(id)?.classList.add('active');

                // Lazy-load tab-specific data
                if (tab.dataset.tab === 'models') this.loadModels();
                if (tab.dataset.tab === 'agents') this.loadAgents();
                if (tab.dataset.tab === 'prompts') this.loadPrompts();
                if (tab.dataset.tab === 'providers') this.loadProvidersTab();
            });
        });
    }

    // ── Event Listeners ───────────────────────────────────────────────────────

    setupEventListeners() {
        const timeSelect = document.getElementById('timeRange');
        if (timeSelect) {
            timeSelect.addEventListener('change', e => {
                this.timeRange = parseInt(e.target.value);
                document.getElementById('trendBadge').textContent = this.timeRange + 'H';
                this.loadData();
            });
        }

        const search = document.getElementById('catalogSearch');
        const provFilter = document.getElementById('catalogProvider');
        if (search)    search.addEventListener('input', () => this.renderCatalog());
        if (provFilter) provFilter.addEventListener('change', () => this.renderCatalog());
    }

    // ── WebSocket ─────────────────────────────────────────────────────────────

    connectWebSocket() {
        const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${proto}//${location.host}/ws/live`);

        this.ws.onopen = () => {
            this.updateConnectionStatus('connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = e => this.handleWsMessage(e.data);

        this.ws.onclose = () => {
            this.updateConnectionStatus('disconnected');
            this.scheduleReconnect();
        };

        this.ws.onerror = () => this.updateConnectionStatus('disconnected');
    }

    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) return;
        this.reconnectAttempts++;
        const delay = Math.min(1000 * 2 ** this.reconnectAttempts, 30000);
        setTimeout(() => this.connectWebSocket(), delay);
    }

    handleWsMessage(raw) {
        if (raw === 'heartbeat' || raw === 'pong') return;
        try {
            const msg = JSON.parse(raw);
            if (msg.type === 'initial' || msg.type === 'refresh') {
                this.updateRealtimeStats(msg.data);
            } else if (msg.type === 'new_record') {
                this.addLiveFeedItem(msg.data);
                this.loadSummary();
            }
        } catch (_) {}
    }

    updateConnectionStatus(status) {
        const el = document.getElementById('connectionStatus');
        if (!el) return;
        el.className = 'connection-status ' + status;
        el.querySelector('.status-text').textContent = status === 'connected' ? 'LIVE' : 'OFFLINE';
    }

    // ── Data Loading ──────────────────────────────────────────────────────────

    async fetchApi(endpoint, params = {}) {
        params.hours = params.hours ?? this.timeRange;
        const qs = new URLSearchParams(params).toString();
        try {
            const r = await fetch(`${endpoint}?${qs}`);
            if (!r.ok) throw new Error('HTTP ' + r.status);
            return await r.json();
        } catch (e) {
            console.error('API error', endpoint, e);
            return null;
        }
    }

    async loadData() {
        await Promise.all([
            this.loadSummary(),
            this.loadOverviewProvider(),
            this.loadTrend(),
            this.loadSuggestions(),
        ]);
        // Also refresh the active tab data
        const activeTab = document.querySelector('.tab.active')?.dataset.tab;
        if (activeTab === 'models')    this.loadModels();
        if (activeTab === 'agents')    this.loadAgents();
        if (activeTab === 'prompts')   this.loadPrompts();
        if (activeTab === 'providers') this.loadProvidersTab();
    }

    async loadSummary() {
        const [data, lat, rt] = await Promise.all([
            this.fetchApi('/api/costs/summary'),
            this.fetchApi('/api/costs/latency'),
            this.fetchApi('/api/realtime'),
        ]);

        if (data) {
            this.setText('totalCost', fmtCost(data.total_cost));
            this.setText('requestCount', fmtNumber(data.request_count));
            this.setText('totalTokens', fmtTokens(data.total_tokens));
            this.setText('avgCost', fmtCost(data.avg_cost_per_request));

            if (data.total_cost > 100) {
                this.showAlert('High Cost Alert',
                    `Spending ${fmtCost(data.total_cost)} in the last ${this.timeRange}h`);
            }
        }

        if (lat && lat.avg_ms != null) {
            this.setText('avgLatency', Math.round(lat.avg_ms) + ' ms');
        }

        if (rt) {
            this.setText('hourCost', fmtCost(rt.last_hour?.cost ?? 0));
        }
    }

    // ── Overview Tab ──────────────────────────────────────────────────────────

    async loadOverviewProvider() {
        const data = await this.fetchApi('/api/costs/by-provider');
        if (!data || !data.length) return;

        const labels = data.map(p => p.provider_icon + ' ' + p.provider_name);
        const values = data.map(p => p.total_cost);

        this.renderDoughnut('providerChart', labels, values);
    }

    async loadTrend() {
        const data = await this.fetchApi('/api/costs/trend');
        if (!data || !data.length) return;

        const labels = data.map(r => r.hour.slice(11, 16));
        const costs  = data.map(r => r.total_cost);
        const reqs   = data.map(r => r.request_count);

        if (this.charts.trend) {
            this.charts.trend.data.labels = labels;
            this.charts.trend.data.datasets[0].data = costs;
            this.charts.trend.data.datasets[1].data = reqs;
            this.charts.trend.update();
            return;
        }

        const ctx = document.getElementById('trendChart');
        if (!ctx) return;

        this.charts.trend = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [
                    {
                        label: 'Cost ($)',
                        data: costs,
                        borderColor: '#00FF88',
                        backgroundColor: 'rgba(0,255,136,0.08)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2,
                        yAxisID: 'y',
                    },
                    {
                        label: 'Requests',
                        data: reqs,
                        borderColor: '#0A84FF',
                        backgroundColor: 'rgba(10,132,255,0.05)',
                        fill: true,
                        tension: 0.4,
                        pointRadius: 2,
                        yAxisID: 'y1',
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { grid: { color: '#1a1a1a' } },
                    y: {
                        type: 'linear', position: 'left',
                        grid: { color: '#1a1a1a' },
                        ticks: { callback: v => '$' + v.toFixed(4) }
                    },
                    y1: {
                        type: 'linear', position: 'right',
                        grid: { drawOnChartArea: false },
                    }
                },
                plugins: { legend: { display: true, position: 'top' } }
            }
        });
    }

    // ── Providers Tab ─────────────────────────────────────────────────────────

    async loadProvidersTab() {
        const data = await this.fetchApi('/api/costs/by-provider');
        const el = document.getElementById('providerBreakdown');
        if (!el || !data) return;

        if (!data.length) {
            el.innerHTML = '<div class="empty-state">No provider data yet</div>';
            return;
        }

        this.setText('providerCount', data.length);
        const maxCost = Math.max(...data.map(p => p.total_cost)) || 1;

        el.innerHTML = data.map(p => `
            <div class="cost-bar-item">
                <div class="cost-bar-header">
                    <span class="cost-bar-name">${escapeHtml(p.provider_icon + ' ' + p.provider_name)}</span>
                    <span class="cost-bar-value">${fmtCost(p.total_cost)}</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill" style="width:${(p.total_cost / maxCost * 100).toFixed(1)}%"></div>
                </div>
                <div class="cost-bar-sub">
                    <span>${fmtNumber(p.request_count)} reqs</span>
                    <span>${fmtTokens(p.total_tokens)} tokens</span>
                    <span>${p.model_count} models</span>
                    ${p.avg_latency_ms ? `<span>${Math.round(p.avg_latency_ms)} ms avg</span>` : ''}
                    ${p.provider_url ? `<a href="${escapeHtml(p.provider_url)}" target="_blank" style="color:var(--accent-blue);">${escapeHtml(p.provider_url)}</a>` : ''}
                </div>
            </div>
        `).join('');
    }

    // ── Models Tab ────────────────────────────────────────────────────────────

    async loadModels() {
        const data = await this.fetchApi('/api/costs/by-model');
        const el = document.getElementById('modelBreakdown');
        if (!el || !data) return;

        if (!data.length) {
            el.innerHTML = '<div class="empty-state">No model data yet</div>';
            return;
        }

        this.setText('modelCount', data.length);
        const maxCost = Math.max(...data.map(m => m.total_cost)) || 1;

        el.innerHTML = `
            <table class="model-table">
                <thead>
                    <tr>
                        <th>MODEL</th>
                        <th>PROVIDER</th>
                        <th style="text-align:right">COST</th>
                        <th style="text-align:right">REQS</th>
                        <th style="text-align:right">TOKENS</th>
                        <th style="text-align:right">AVG LATENCY</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.map(m => `
                    <tr>
                        <td>${escapeHtml(m.model)}</td>
                        <td><span class="provider-badge">${escapeHtml(m.provider_icon)} ${escapeHtml(m.provider_name)}</span></td>
                        <td style="text-align:right;color:var(--accent-green)">${fmtCost(m.total_cost)}</td>
                        <td style="text-align:right;color:var(--text-secondary)">${fmtNumber(m.request_count)}</td>
                        <td style="text-align:right;color:var(--text-secondary)">${fmtTokens(m.total_tokens)}</td>
                        <td style="text-align:right;color:var(--text-muted)">${m.avg_latency_ms ? Math.round(m.avg_latency_ms) + ' ms' : '—'}</td>
                    </tr>`).join('')}
                </tbody>
            </table>`;

        // Update model doughnut chart
        const labels = data.slice(0, 8).map(m => m.model.split('/').pop());
        const values = data.slice(0, 8).map(m => m.total_cost);
        this.renderDoughnut('modelChart', labels, values);
    }

    // ── Agents Tab ────────────────────────────────────────────────────────────

    async loadAgents() {
        const [agents, tasks] = await Promise.all([
            this.fetchApi('/api/costs/by-agent'),
            this.fetchApi('/api/costs/by-task'),
        ]);

        const agentEl = document.getElementById('agentCosts');
        if (agentEl && agents) {
            if (!agents.length) {
                agentEl.innerHTML = '<div class="empty-state">No agent data yet</div>';
            } else {
                const maxCost = Math.max(...agents.map(a => a.total_cost)) || 1;
                agentEl.innerHTML = agents.map(a => `
                    <div class="cost-bar-item">
                        <div class="cost-bar-header">
                            <span class="cost-bar-name">${escapeHtml(a.agent)}</span>
                            <span class="cost-bar-value">${fmtCost(a.total_cost)}</span>
                        </div>
                        <div class="bar-container">
                            <div class="bar-fill" style="width:${(a.total_cost / maxCost * 100).toFixed(1)}%"></div>
                        </div>
                        <div class="cost-bar-sub">
                            <span>${fmtNumber(a.request_count)} reqs</span>
                            <span>${fmtTokens(a.total_tokens)} tokens</span>
                            <span>${fmtCost(a.avg_cost_per_request)}/req</span>
                        </div>
                    </div>`).join('');
            }
        }

        const taskEl = document.getElementById('taskCosts');
        if (taskEl && tasks) {
            if (!tasks.length) {
                taskEl.innerHTML = '<div class="empty-state">No task data yet</div>';
            } else {
                const maxCost = Math.max(...tasks.map(t => t.total_cost)) || 1;
                taskEl.innerHTML = tasks.slice(0, 12).map(t => `
                    <div class="cost-bar-item">
                        <div class="cost-bar-header">
                            <span class="cost-bar-name">${escapeHtml(t.task)}</span>
                            <span class="cost-bar-value">${fmtCost(t.total_cost)}</span>
                        </div>
                        <div class="bar-container">
                            <div class="bar-fill" style="width:${(t.total_cost / maxCost * 100).toFixed(1)}%"></div>
                        </div>
                        <div class="cost-bar-sub">
                            <span>${escapeHtml(t.agent)}</span>
                            <span>${fmtNumber(t.request_count)} reqs</span>
                        </div>
                    </div>`).join('');
            }
        }
    }

    // ── Prompts Tab ───────────────────────────────────────────────────────────

    async loadPrompts() {
        const data = await this.fetchApi('/api/costs/expensive-prompts', { limit: 10 });
        const el = document.getElementById('expensivePrompts');
        if (!el || !data) return;

        if (!data.length) {
            el.innerHTML = '<div class="empty-state">No prompt data yet</div>';
            return;
        }

        el.innerHTML = data.map(p => `
            <div class="prompt-item">
                <div class="prompt-header">
                    <div>
                        <div class="prompt-location">${escapeHtml(p.agent)}/${escapeHtml(p.task)}</div>
                        <div class="prompt-model">${escapeHtml(p.model)}</div>
                    </div>
                    <span class="prompt-ratio">${p.token_ratio_vs_avg.toFixed(1)}× avg</span>
                </div>
                <div class="prompt-preview">${escapeHtml(p.prompt_preview || 'N/A')}</div>
                <div class="prompt-stats">
                    <span>⚡ ${fmtTokens(Math.round(p.avg_tokens))} tokens/call</span>
                    <span>💰 ${fmtCost(p.avg_cost)}/call</span>
                    <span>📊 ${fmtNumber(p.call_count)} calls</span>
                    <span>💸 ${fmtCost(p.total_cost)} total</span>
                </div>
            </div>`).join('');
    }

    // ── Suggestions ───────────────────────────────────────────────────────────

    async loadSuggestions() {
        const data = await this.fetchApi('/api/suggestions', { hours: 720 });
        const el = document.getElementById('suggestions');
        if (!el || !data) return;

        this.setText('suggCount', data.length);

        if (!data.length) {
            el.innerHTML = '<div class="empty-state">✅ No optimisations needed — great job!</div>';
            return;
        }

        const icons = {
            model_switch:       '🔄',
            prompt_optimization:'✏️',
            caching:            '💾',
            batching:           '📦',
            local_alternative:  '🏠',
        };

        el.innerHTML = data.slice(0, 6).map(s => `
            <div class="suggestion-item">
                <div class="suggestion-header">
                    <div class="suggestion-icon ${s.priority}">${icons[s.type] || '💡'}</div>
                    <span class="suggestion-title">${escapeHtml(s.title)}</span>
                </div>
                <div class="suggestion-desc">${escapeHtml(s.description)}</div>
                <div class="suggestion-footer">
                    <span class="suggestion-savings">Save ~${fmtCost(s.estimated_monthly_savings)}</span>
                    <span class="suggestion-priority ${s.priority}">${s.priority.toUpperCase()}</span>
                </div>
            </div>`).join('');
    }

    // ── Model Catalog ─────────────────────────────────────────────────────────

    async loadCatalog() {
        const data = await fetch('/api/models/catalog').then(r => r.ok ? r.json() : null);
        if (!data) return;

        this.catalogData = data;

        // Populate provider filter
        const sel = document.getElementById('catalogProvider');
        if (sel) {
            const providers = [...new Set(data.map(m => m.provider))].sort();
            providers.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p;
                opt.textContent = p;
                sel.appendChild(opt);
            });
        }

        // Sort headers
        document.querySelectorAll('.catalog-table th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.sort;
                if (this.catalogSortCol === col) {
                    this.catalogSortAsc = !this.catalogSortAsc;
                } else {
                    this.catalogSortCol = col;
                    this.catalogSortAsc = true;
                }
                this.renderCatalog();
            });
        });

        this.renderCatalog();
    }

    renderCatalog() {
        const el = document.getElementById('catalogTable');
        if (!el) return;

        const search = (document.getElementById('catalogSearch')?.value || '').toLowerCase();
        const provider = document.getElementById('catalogProvider')?.value || '';

        let data = this.catalogData.filter(m => {
            if (provider && m.provider !== provider) return false;
            if (search && !m.model.toLowerCase().includes(search) &&
                !m.description.toLowerCase().includes(search) &&
                !m.provider.toLowerCase().includes(search)) return false;
            return true;
        });

        // Sort
        const col = this.catalogSortCol;
        data = data.sort((a, b) => {
            const av = a[col] ?? 0, bv = b[col] ?? 0;
            return this.catalogSortAsc
                ? (typeof av === 'string' ? av.localeCompare(bv) : av - bv)
                : (typeof av === 'string' ? bv.localeCompare(av) : bv - av);
        });

        el.innerHTML = `
            <div class="catalog-table-wrap">
            <table class="catalog-table">
                <thead><tr>
                    <th data-sort="model">MODEL ↕</th>
                    <th data-sort="provider">PROVIDER ↕</th>
                    <th data-sort="input_per_1m" style="text-align:right">INPUT/1M ↕</th>
                    <th data-sort="output_per_1m" style="text-align:right">OUTPUT/1M ↕</th>
                    <th data-sort="context_window" style="text-align:right">CONTEXT ↕</th>
                    <th>FEATURES</th>
                    <th>DESCRIPTION</th>
                </tr></thead>
                <tbody>
                ${data.map(m => {
                    const inp = m.input_per_1m === 0 ? '<span class="price-free">FREE</span>'
                        : `<span class="${priceClass(m.input_per_1m)}">$${m.input_per_1m.toFixed(4)}</span>`;
                    const out = m.output_per_1m === 0 ? '<span class="price-free">FREE</span>'
                        : `<span class="${priceClass(m.output_per_1m)}">$${m.output_per_1m.toFixed(4)}</span>`;
                    const ctx = m.context_window >= 1000
                        ? (m.context_window / 1000).toFixed(0) + 'K'
                        : (m.context_window || '?');
                    const feats = (m.supports_vision ? '<span class="feat-badge" title="Vision">👁</span>' : '')
                        + (m.supports_tools ? '<span class="feat-badge" title="Tools/Functions">🔧</span>' : '');
                    return `<tr>
                        <td>${escapeHtml(m.model)}</td>
                        <td><span class="provider-badge">${escapeHtml(m.provider)}</span></td>
                        <td style="text-align:right">${inp}</td>
                        <td style="text-align:right">${out}</td>
                        <td style="text-align:right;color:var(--text-muted)">${ctx}</td>
                        <td>${feats}</td>
                        <td style="color:var(--text-muted);font-size:10px">${escapeHtml(m.description)}</td>
                    </tr>`;
                }).join('')}
                </tbody>
            </table>
            </div>`;

        // Re-attach sort listeners
        el.querySelectorAll('th[data-sort]').forEach(th => {
            th.addEventListener('click', () => {
                const col = th.dataset.sort;
                if (this.catalogSortCol === col) {
                    this.catalogSortAsc = !this.catalogSortAsc;
                } else {
                    this.catalogSortCol = col;
                    this.catalogSortAsc = true;
                }
                this.renderCatalog();
            });
        });
    }

    // ── Charts ────────────────────────────────────────────────────────────────

    renderDoughnut(canvasId, labels, values) {
        const ctx = document.getElementById(canvasId);
        if (!ctx) return;

        if (this.charts[canvasId]) {
            this.charts[canvasId].data.labels = labels;
            this.charts[canvasId].data.datasets[0].data = values;
            this.charts[canvasId].update();
            return;
        }

        this.charts[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels,
                datasets: [{
                    data: values,
                    backgroundColor: CHART_COLORS,
                    borderColor: '#111111',
                    borderWidth: 2,
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '65%',
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { boxWidth: 10, padding: 10 }
                    },
                    tooltip: {
                        callbacks: {
                            label: ctx => ` ${ctx.label}: ${fmtCost(ctx.parsed)}`
                        }
                    }
                }
            }
        });
    }

    // ── Live Feed ─────────────────────────────────────────────────────────────

    updateRealtimeStats(data) {
        if (data.latest_records?.length) {
            const el = document.getElementById('liveFeed');
            if (el) {
                el.innerHTML = data.latest_records.map(r => this.makeFeedItem(r)).join('');
            }
        }

        if (data.latency?.avg_ms != null) {
            this.setText('avgLatency', Math.round(data.latency.avg_ms) + ' ms');
        }

        this.setText('hourCost', fmtCost(data.last_hour?.cost ?? 0));
    }

    addLiveFeedItem(record) {
        const el = document.getElementById('liveFeed');
        if (!el) return;

        el.querySelector('.empty-state')?.remove();

        const div = document.createElement('div');
        div.className = 'feed-item';
        div.innerHTML = this.makeFeedItemContent(record);
        el.insertBefore(div, el.firstChild);

        while (el.children.length > 25) el.removeChild(el.lastChild);
    }

    makeFeedItem(r) {
        return `<div class="feed-item">${this.makeFeedItemContent(r)}</div>`;
    }

    makeFeedItemContent(r) {
        const t = new Date(r.timestamp).toLocaleTimeString();
        const lat = r.latency_ms ? ` · ${r.latency_ms}ms` : '';
        return `
            <div class="feed-left">
                <span class="feed-agent">${escapeHtml(r.agent)}</span>
                <span class="feed-model">${escapeHtml(r.model)} · ${fmtTokens(r.tokens || 0)} tok${lat}</span>
            </div>
            <div class="feed-right">
                <span class="feed-cost">${fmtCost(r.cost)}</span>
                <span class="feed-meta">${t}</span>
            </div>`;
    }

    // ── Utilities ─────────────────────────────────────────────────────────────

    setText(id, val) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }

    showAlert(title, message) {
        const s = document.getElementById('alertsSection');
        if (!s) return;
        this.setText('alertTitle', title);
        this.setText('alertMessage', message);
        s.style.display = 'block';
    }
}

// ── Global helpers ───────────────────────────────────────────────────────────

function dismissAlert() {
    const s = document.getElementById('alertsSection');
    if (s) s.style.display = 'none';
}

// ── Bootstrap ────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CostProfilerDashboard();
});

