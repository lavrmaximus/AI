// Global State
let currentUserId = null;
let currentBusinessId = null;
let currentChartData = null;
let selectedMetrics = new Set(['revenue', 'expenses', 'profit']);
let financeChartCurrency = null;
let financeChartCounts = null;
let financeChartPercent = null;

// Telegram WebApp Auth & Init
document.addEventListener('DOMContentLoaded', function() {
    initTelegramAuth();
});

function initTelegramAuth() {
    const tg = window.Telegram.WebApp;
    tg.expand(); // Expand to full height
    
    // Set theme colors based on Telegram theme
    if (tg.themeParams) {
        // We could apply these to CSS variables if we wanted strict native look
        // For now we stick to our Tailwind Dark theme
    }

    // Check if running inside Telegram
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
        const user = tg.initDataUnsafe.user;
        currentUserId = user.id.toString();
        localStorage.setItem('cached_user_id', currentUserId);
        console.log('Logged in as:', user.first_name);
        initializeApp();
    } else {
        // Not in Telegram (or dev mode)
        const cachedId = localStorage.getItem('cached_user_id');
        
        // DEV MODE / Fallback
        if (cachedId) {
            currentUserId = cachedId;
            console.log('Restored session for:', currentUserId);
            initializeApp();
        } else {
            // Access Denied
            document.getElementById('main-app').style.display = 'none';
            const nav = document.querySelector('nav');
            if(nav) nav.style.display = 'none';
            
            const deniedEl = document.getElementById('access-denied');
            if(deniedEl) {
                deniedEl.classList.remove('hidden');
                deniedEl.style.display = 'flex';
            }
        }
    }
}

async function initializeApp() {
    // Load businesses for this user
    await loadUserBusinesses(currentUserId);
    
    // Page specific init
    const path = window.location.pathname;
    if (path === '/') {
        loadSystemStats();
    }
}

// Data Loading Functions
async function loadUserBusinesses(userId) {
    try {
        const response = await fetch(`/api/businesses/${userId}`);
        const data = await response.json();
        
        if (data.success && data.businesses.length > 0) {
            // Populate business selector if it exists (on Dashboard/Analytics)
            const businessSelect = document.getElementById('businessSelect');
            
            if (businessSelect) {
                businessSelect.innerHTML = '';
                data.businesses.forEach(b => {
                    const option = document.createElement('option');
                    option.value = b.business_id;
                    option.textContent = b.business_name || `Бизнес #${b.business_id}`;
                    businessSelect.appendChild(option);
                });
                
                // Select first business by default
                currentBusinessId = data.businesses[0].business_id;
                businessSelect.value = currentBusinessId;
                
                // Load data for this business
                loadBusinessData(currentBusinessId);
                
                // Handle change
                businessSelect.addEventListener('change', (e) => {
                    currentBusinessId = e.target.value;
                    loadBusinessData(currentBusinessId);
                });
            }
        } else {
            console.log('No businesses found for user');
            // Handle empty state if needed
        }
    } catch (error) {
        console.error('Error loading businesses:', error);
    }
}

async function loadBusinessData(businessId) {
    if (!businessId) return;
    
    // Load KPI if on dashboard
    if (document.getElementById('kpiGrid')) {
        await loadKPIMetrics(businessId);
    }
    
    // Load History/Charts
    await loadFinanceHistory(businessId);
    
    // Load AI Analysis if on Analytics page
    if (document.getElementById('aiAnalysisContainer')) {
        await loadAIAnalysis(businessId);
    }
}

async function loadKPIMetrics(businessId) {
    try {
        const response = await fetch(`/api/business-kpi/${businessId}`);
        const data = await response.json();
        if (data.success) {
            updateKPICards(data.kpi);
        }
    } catch (error) {
        console.error('Error loading KPI:', error);
    }
}

async function loadFinanceHistory(businessId) {
    try {
        const response = await fetch(`/api/business-history/${businessId}`);
        const data = await response.json();
        if (data.success) {
            currentChartData = data.data;
            renderFinanceCharts(data.data);
            
            // Update all metrics grid if it exists
            if (document.getElementById('allMetricsGrid')) {
                buildAllMetricCards(data.latest, data.data);
            }
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

async function loadAIAnalysis(businessId) {
    try {
        const container = document.getElementById('aiAnalysisContainer');
        container.innerHTML = '<div class="animate-pulse text-center text-slate-400">Генерация AI анализа...</div>';
        
        const response = await fetch(`/api/business-ai-analysis/${businessId}`);
        const data = await response.json();
        
        if (data.success) {
            renderAIAnalysis(data.analysis);
        } else {
            container.innerHTML = `<div class="text-red-400">Ошибка: ${data.error}</div>`;
        }
    } catch (error) {
        console.error('Error loading AI analysis:', error);
    }
}

async function loadSystemStats() {
    try {
        const response = await fetch('/api/system-stats');
        const data = await response.json();
        if (data.success) {
            const els = {
                'totalUsers': data.stats.total_users,
                'totalAnalyses': data.stats.total_analyses,
                'activeToday': data.stats.active_today
            };
            for (const [id, val] of Object.entries(els)) {
                const el = document.getElementById(id);
                if (el) el.textContent = val;
            }
        }
    } catch (e) {
        console.error('Stats error:', e);
    }
}

// UI Update Functions
function updateKPICards(kpi) {
    const update = (id, val, suffix, change) => {
        const elVal = document.getElementById(`${id}-value`);
        const elChange = document.getElementById(`${id}-change`);
        if (elVal) elVal.textContent = formatNumber(val) + (suffix ? ' ' + suffix : '');
        if (elChange) {
            const sign = change > 0 ? '+' : '';
            elChange.textContent = `${sign}${change}%`;
            
            // Color logic
            let colorClass = 'text-slate-400';
            if (id === 'expenses') {
                colorClass = change > 0 ? 'text-red-400' : (change < 0 ? 'text-green-400' : 'text-slate-400');
            } else {
                colorClass = change > 0 ? 'text-green-400' : (change < 0 ? 'text-red-400' : 'text-slate-400');
            }
            elChange.className = `text-xs font-medium ${colorClass}`;
        }
    };
    
    update('revenue', kpi.revenue.current, '₽', kpi.revenue.change);
    update('expenses', kpi.expenses.current, '₽', kpi.expenses.change);
    update('profit', kpi.profit.current, '₽', kpi.profit.change);
    update('clients', kpi.clients.current, '', kpi.clients.change);
}

function renderAIAnalysis(analysis) {
    const container = document.getElementById('aiAnalysisContainer');
    if (!container) return;
    
    let html = `
        <div class="bg-slate-800 rounded-xl p-4 mb-4 border border-slate-700">
            <h3 class="text-lg font-bold text-blue-400 mb-2">🤖 AI Резюме</h3>
            <p class="text-slate-300 text-sm leading-relaxed">${analysis.summary}</p>
        </div>
        
        <div class="grid grid-cols-1 gap-4 mb-4">
            <div class="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <h4 class="text-sm font-semibold text-slate-400 mb-2">Рекомендации</h4>
                <ul class="space-y-2">
                    ${analysis.recommendations.map(r => `<li class="flex items-start text-sm text-slate-300"><span class="mr-2 text-yellow-400">💡</span>${r}</li>`).join('')}
                </ul>
            </div>
            <div class="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <h4 class="text-sm font-semibold text-slate-400 mb-2">Тренды</h4>
                <ul class="space-y-2">
                    ${analysis.trends.map(t => `<li class="flex items-start text-sm text-slate-300"><span class="mr-2 text-blue-400">📈</span>${t}</li>`).join('')}
                </ul>
            </div>
        </div>
    `;
    
    if (analysis.commentary) {
        html += `
            <div class="bg-slate-800 rounded-xl p-4 border border-slate-700">
                <h4 class="text-sm font-semibold text-slate-400 mb-2">Комментарий эксперта</h4>
                <p class="text-slate-300 text-sm italic">"${analysis.commentary}"</p>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Chart Functions
function renderFinanceCharts(data) {
    // Helper to create chart
    const createChart = (canvasId, type, labelSuffix) => {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return null;
        
        const ctx = canvas.getContext('2d');
        
        // Destroy existing
        if (window[canvasId] instanceof Chart) {
            window[canvasId].destroy();
        }
        
        const datasets = [];
        const keys = Object.keys(data.series);
        const palette = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'];
        let colorIdx = 0;
        
        keys.forEach(key => {
            // Filter based on type
            const isCurrency = ['revenue','expenses','profit','average_check','investments','marketing_costs','ltv','cac'].includes(key);
            const isPercent = ['profit_margin','safety_margin','roi','profitability_index','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate','roe'].includes(key);
            
            let shouldInclude = false;
            if (type === 'currency' && isCurrency) shouldInclude = true;
            if (type === 'counts' && !isCurrency && !isPercent) shouldInclude = true;
            if (type === 'percent' && isPercent) shouldInclude = true;
            
            if (shouldInclude && selectedMetrics.has(key)) {
                const color = palette[colorIdx % palette.length];
                datasets.push({
                    label: getMetricLabelRussian(key),
                    data: data.series[key],
                    borderColor: color,
                    backgroundColor: hexToRgba(color, 0.1),
                    borderWidth: 2,
                    tension: 0.4,
                    pointRadius: 0,
                    fill: true
                });
                colorIdx++;
            }
        });
        
        if (datasets.length === 0) {
            canvas.style.display = 'none';
            return null;
        }
        canvas.style.display = 'block';
        
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.dates,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: 'rgba(30, 41, 59, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 10,
                        displayColors: true
                    }
                },
                scales: {
                    x: { display: false },
                    y: {
                        grid: { color: 'rgba(255, 255, 255, 0.05)' },
                        ticks: { color: '#94a3b8' }
                    }
                }
            }
        });
    };
    
    window.financeChartCurrency = createChart('financeChartCurrency', 'currency', '₽');
    window.financeChartCounts = createChart('financeChartCounts', 'counts', '');
    window.financeChartPercent = createChart('financeChartPercent', 'percent', '%');
}

function buildAllMetricCards(latest, data) {
    const grid = document.getElementById('allMetricsGrid');
    if (!grid) return;
    grid.innerHTML = '';
    
    const keys = Object.keys(data.series);
    
    keys.forEach(key => {
        const label = getMetricLabelRussian(key);
        let unit = '';
        if (['revenue','expenses','profit','average_check','investments','marketing_costs','ltv','cac'].includes(key)) unit = '₽';
        if (['profit_margin','safety_margin','roi','profitability_index','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate','roe'].includes(key)) unit = '%';
        
        const card = document.createElement('div');
        card.className = 'glass-card p-3 rounded-lg flex justify-between items-center';
        
        const isActive = selectedMetrics.has(key);
        
        // Get latest value
        const val = (data.series[key] && data.series[key].length) ?
            data.series[key][data.series[key].length-1] : 0;
            
        card.innerHTML = `
            <div>
                <div class="text-xs text-slate-300">${label}</div>
                <div class="text-sm font-bold text-white">${formatNumber(val)} ${unit}</div>
            </div>
            <button class="w-8 h-8 rounded-full flex items-center justify-center transition-colors ${isActive ? 'bg-blue-600 text-white' : 'bg-slate-700/50 text-slate-400'}"
                onclick="toggleMetric('${key}')">
                ${isActive ? '✓' : '+'}
            </button>
        `;
        grid.appendChild(card);
    });
}

function toggleMetric(key) {
    if (selectedMetrics.has(key)) {
        selectedMetrics.delete(key);
    } else {
        selectedMetrics.add(key);
    }
    // Re-render charts
    if (currentChartData) {
        renderFinanceCharts(currentChartData);
        // Re-render buttons
        buildAllMetricCards(null, { series: currentChartData.series, dates: currentChartData.dates });
    }
}

// Utilities
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(Math.round(num));
}

function hexToRgba(hex, alpha) {
    const res = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!res) return 'rgba(0,0,0,' + alpha + ')';
    const r = parseInt(res[1], 16);
    const g = parseInt(res[2], 16);
    const b = parseInt(res[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function getMetricLabelRussian(key) {
    const map = {
        revenue: 'Выручка', expenses: 'Расходы', profit: 'Прибыль',
        clients: 'Клиенты', average_check: 'Ср. чек', investments: 'Инвестиции',
        marketing_costs: 'Маркетинг', profit_margin: 'Маржа', roi: 'ROI',
        employees: 'Сотрудники', break_even_clients: 'Точка безубыточности',
        safety_margin: 'Запас прочности', profitability_index: 'Индекс приб.',
        ltv: 'LTV', cac: 'CAC', ltv_cac_ratio: 'LTV/CAC',
        customer_profit_margin: 'Маржа клиента', sgr: 'SGR',
        revenue_growth_rate: 'Рост выручки', asset_turnover: 'Оборот активов',
        roe: 'ROE', months_to_bankruptcy: 'Мес. до банкротства',
        financial_health_score: 'Фин. здоровье', growth_health_score: 'Рост',
        efficiency_health_score: 'Эффективность', overall_health_score: 'Общий рейтинг'
    };
    return map[key] || key;
}