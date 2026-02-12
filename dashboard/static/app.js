/**
 * AI Cost Profiler Dashboard - JavaScript Client
 */

class CostProfilerDashboard {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.timeRange = 24;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.loadData();
    }

    setupEventListeners() {
        const timeSelect = document.getElementById('timeRange');
        if (timeSelect) {
            timeSelect.addEventListener('change', (e) => {
                this.timeRange = parseInt(e.target.value);
                this.loadData();
            });
        }
    }

    // WebSocket connection
    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/live`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus('connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            this.handleWebSocketMessage(event.data);
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateConnectionStatus('disconnected');
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('disconnected');
        };
    }

    attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
            setTimeout(() => this.connectWebSocket(), delay);
        }
    }

    handleWebSocketMessage(data) {
        try {
            if (data === 'heartbeat' || data === 'pong') {
                return;
            }

            const message = JSON.parse(data);

            switch (message.type) {
                case 'initial':
                case 'refresh':
                    this.updateRealtimeStats(message.data);
                    break;
                case 'new_record':
                    this.addLiveFeedItem(message.data);
                    this.loadData(); // Refresh all data
                    break;
            }
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
        }
    }

    updateConnectionStatus(status) {
        const elem = document.getElementById('connectionStatus');
        if (elem) {
            elem.className = `connection-status ${status}`;
            elem.querySelector('.status-text').textContent =
                status === 'connected' ? 'LIVE' : 'OFFLINE';
        }
    }

    // Data loading
    async loadData() {
        await Promise.all([
            this.loadSummary(),
            this.loadAgentCosts(),
            this.loadExpensivePrompts(),
            this.loadSuggestions()
        ]);
    }

    async fetchApi(endpoint) {
        try {
            const response = await fetch(`${endpoint}?hours=${this.timeRange}`);
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${endpoint}:`, error);
            return null;
        }
    }

    async loadSummary() {
        const data = await this.fetchApi('/api/costs/summary');
        if (!data) return;

        this.animateValue('totalCost', `$${data.total_cost.toFixed(2)}`);
        this.animateValue('requestCount', this.formatNumber(data.request_count));
        this.animateValue('totalTokens', this.formatNumber(data.total_tokens));
        this.animateValue('avgCost', `$${data.avg_cost_per_request.toFixed(4)}`);

        // Check for high cost alert
        if (data.total_cost > 100) {
            this.showAlert(
                'High Cost Alert',
                `Spending $${data.total_cost.toFixed(2)} in the last ${this.timeRange} hours`
            );
        }
    }

    async loadAgentCosts() {
        const data = await this.fetchApi('/api/costs/by-agent');
        const container = document.getElementById('agentCosts');
        if (!container || !data) return;

        if (data.length === 0) {
            container.innerHTML = '<div class="empty-state">No agent data yet</div>';
            return;
        }

        const maxCost = Math.max(...data.map(a => a.total_cost));

        container.innerHTML = data.map(agent => `
            <div class="agent-bar">
                <div class="agent-bar-header">
                    <span class="agent-name">${agent.agent}</span>
                    <span class="agent-cost">$${agent.total_cost.toFixed(4)}</span>
                </div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${(agent.total_cost / maxCost * 100)}%"></div>
                </div>
                <div class="agent-meta">
                    <span>${agent.request_count} requests</span>
                    <span>${this.formatNumber(agent.total_tokens)} tokens</span>
                </div>
            </div>
        `).join('');
    }

    async loadExpensivePrompts() {
        const data = await this.fetchApi('/api/costs/expensive-prompts');
        const container = document.getElementById('expensivePrompts');
        if (!container || !data) return;

        if (data.length === 0) {
            container.innerHTML = '<div class="empty-state">No prompt data yet</div>';
            return;
        }

        container.innerHTML = data.slice(0, 5).map(prompt => `
            <div class="prompt-item">
                <div class="prompt-header">
                    <span class="prompt-location">${prompt.agent}/${prompt.task}</span>
                    <span class="prompt-ratio">${prompt.token_ratio_vs_avg.toFixed(1)}x avg</span>
                </div>
                <div class="prompt-preview">${this.escapeHtml(prompt.prompt_preview || 'N/A')}</div>
                <div class="prompt-stats">
                    <span>⚡ ${this.formatNumber(Math.round(prompt.avg_tokens))} tokens</span>
                    <span>💰 $${prompt.avg_cost.toFixed(4)}/call</span>
                    <span>📊 ${prompt.call_count} calls</span>
                </div>
            </div>
        `).join('');
    }

    async loadSuggestions() {
        const response = await fetch('/api/suggestions?hours=720');
        const data = response.ok ? await response.json() : null;
        const container = document.getElementById('suggestions');
        if (!container || !data) return;

        if (data.length === 0) {
            container.innerHTML = '<div class="empty-state">No optimization suggestions - you\'re doing great!</div>';
            return;
        }

        const icons = {
            'model_switch': '🔄',
            'prompt_optimization': '✏️',
            'caching': '💾',
            'batching': '📦'
        };

        container.innerHTML = data.slice(0, 5).map(suggestion => `
            <div class="suggestion-item">
                <div class="suggestion-header">
                    <div class="suggestion-icon ${suggestion.priority}">${icons[suggestion.type] || '💡'}</div>
                    <span class="suggestion-title">${suggestion.title}</span>
                </div>
                <div class="suggestion-desc">${suggestion.description}</div>
                <div class="suggestion-savings">Save ~$${suggestion.estimated_monthly_savings.toFixed(2)}/month</div>
            </div>
        `).join('');
    }

    updateRealtimeStats(data) {
        // Update feed with latest records
        if (data.latest_records) {
            const container = document.getElementById('liveFeed');
            if (container && data.latest_records.length > 0) {
                container.innerHTML = data.latest_records.map(r => this.createFeedItem(r)).join('');
            }
        }
    }

    addLiveFeedItem(record) {
        const container = document.getElementById('liveFeed');
        if (!container) return;

        // Remove empty state if present
        const emptyState = container.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Add new item at the top
        const item = document.createElement('div');
        item.className = 'feed-item';
        item.innerHTML = this.createFeedItemContent(record);
        item.style.animation = 'fadeIn 0.3s ease';

        container.insertBefore(item, container.firstChild);

        // Keep only last 20 items
        while (container.children.length > 20) {
            container.removeChild(container.lastChild);
        }
    }

    createFeedItem(record) {
        return `<div class="feed-item">${this.createFeedItemContent(record)}</div>`;
    }

    createFeedItemContent(record) {
        const time = new Date(record.timestamp);
        const timeStr = time.toLocaleTimeString();

        return `
            <div class="feed-left">
                <span class="feed-agent">${record.agent}</span>
                <span class="feed-task">${record.task} • ${record.model}</span>
            </div>
            <div class="feed-right">
                <span class="feed-cost">$${record.cost.toFixed(6)}</span>
                <span class="feed-time">${timeStr}</span>
            </div>
        `;
    }

    // Utilities
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    animateValue(elementId, newValue) {
        const elem = document.getElementById(elementId);
        if (elem) {
            elem.textContent = newValue;
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showAlert(title, message) {
        const section = document.getElementById('alertsSection');
        const titleElem = document.getElementById('alertTitle');
        const messageElem = document.getElementById('alertMessage');

        if (section && titleElem && messageElem) {
            titleElem.textContent = title;
            messageElem.textContent = message;
            section.style.display = 'block';
        }
    }
}

function dismissAlert() {
    const section = document.getElementById('alertsSection');
    if (section) {
        section.style.display = 'none';
    }
}

// Add fadeIn animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

// Initialize dashboard
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new CostProfilerDashboard();
});
