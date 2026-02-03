// Global State
let currentUserId = null;
let currentBusinessId = null;
let currentChartData = null;
let selectedMetrics = new Set(['revenue', 'expenses', 'profit']);
let mainChart = null;
let currentFilter = 'all';

const metricGroups = {
    'finance': {
        label: 'P&L и Маржинальность',
        metrics: ['revenue', 'expenses', 'profit', 'profit_margin', 'customer_profit_margin']
    },
    'unit': {
        label: 'Юнит-экономика',
        metrics: ['cac', 'ltv', 'average_check', 'ltv_cac_ratio']
    },
    'growth': {
        label: 'Рост и Эффективность',
        metrics: ['roi', 'roe', 'sgr', 'revenue_growth_rate', 'asset_turnover']
    },
    'health': {
        label: 'Здоровье и Безопасность',
        metrics: ['safety_margin', 'months_to_bankruptcy', 'financial_health_score', 'growth_health_score', 'efficiency_health_score', 'overall_health_score']
    },
    'other': {
        label: 'Остальные показатели',
        metrics: ['clients', 'investments', 'marketing_costs', 'employees', 'break_even_clients', 'profitability_index']
    }
};

// Telegram WebApp Auth & Init
document.addEventListener('DOMContentLoaded', function() {
    initTelegramAuth();
    initFilters();
    highlightActiveTab();
});

function initFilters() {
    const filters = document.querySelectorAll('.filter-chip');
    filters.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update UI
            filters.forEach(f => f.classList.remove('active'));
            btn.classList.add('active');
            
            // Update Logic
            const filter = btn.dataset.filter;
            currentFilter = filter;
            applyFilter(filter);
        });
    });
}

function applyFilter(filter) {
    if (!currentChartData) return;

    selectedMetrics.clear();
    
    if (filter === 'all') {
        // Default set for 'All'
        ['revenue', 'expenses', 'profit', 'clients'].forEach(m => selectedMetrics.add(m));
    } else if (metricGroups[filter]) {
        metricGroups[filter].metrics.forEach(m => selectedMetrics.add(m));
    }

    renderFinanceCharts(currentChartData);
    buildAllMetricCards(currentChartData.latest, currentChartData);
}


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
        loadHealthScore();
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
                
                // Select business (Persistence Fix)
                const savedBusinessId = localStorage.getItem('selectedBusinessId');
                let targetBusinessId = data.businesses[0].business_id;

                if (savedBusinessId && data.businesses.find(b => b.business_id == savedBusinessId)) {
                    targetBusinessId = savedBusinessId;
                }

                currentBusinessId = targetBusinessId;
                businessSelect.value = currentBusinessId;
                
                // Load data for this business
                loadBusinessData(currentBusinessId);
                
                // Handle change
                businessSelect.addEventListener('change', (e) => {
                    currentBusinessId = e.target.value;
                    localStorage.setItem('selectedBusinessId', currentBusinessId);
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
    if (document.getElementById('kpiGrid') || document.getElementById('kpiCarousel')) {
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

async function loadHealthScore() {
    if (!currentUserId) return;
    try {
        // Get businesses first
        const response = await fetch(`/api/businesses/${currentUserId}`);
        const data = await response.json();
        
        if (data.success && data.businesses.length > 0) {
            // Find MAX health score across all businesses
            const scores = await Promise.all(data.businesses.map(async (b) => {
                try {
                    const kpiResponse = await fetch(`/api/business-kpi/${b.business_id}`);
                    const kpiData = await kpiResponse.json();
                    if (kpiData.success) {
                        return kpiData.kpi.overall_health_score || 0;
                    }
                } catch (e) {
                    console.error(`Error fetching KPI for ${b.business_id}:`, e);
                }
                return 0;
            }));
            
            const maxScore = Math.max(...scores);
            
            const scoreEl = document.getElementById('health-score-value');
            if (scoreEl) {
                scoreEl.textContent = maxScore;
            }
        }
    } catch (e) {
        console.error('Health score error:', e);
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
                colorClass = change > 0 ? 'text-red-400' : (change < 0 ? 'text-accent' : 'text-slate-400');
            } else {
                colorClass = change > 0 ? 'text-accent' : (change < 0 ? 'text-red-400' : 'text-slate-400');
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
        <div class="glass-card insight-card rounded-xl p-6 mb-6 animate-fade-in">
            <div class="mb-4">
                <span class="neon-badge">AI Резюме</span>
            </div>
            <p class="text-slate-200 text-base leading-relaxed">${analysis.summary}</p>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div class="glass-card insight-card rounded-xl p-6 animate-fade-in delay-100">
                <div class="mb-4">
                    <span class="neon-badge green">Рекомендации</span>
                </div>
                <ul class="space-y-3">
                    ${analysis.recommendations.map(r => `<li class="flex items-start text-sm text-slate-300"><span class="mr-3 text-accent mt-0.5">💡</span><span class="leading-relaxed">${r}</span></li>`).join('')}
                </ul>
            </div>
            <div class="glass-card insight-card rounded-xl p-6 animate-fade-in delay-200">
                <div class="mb-4">
                    <span class="neon-badge purple">Тренды</span>
                </div>
                <ul class="space-y-3">
                    ${analysis.trends.map(t => `<li class="flex items-start text-sm text-slate-300"><span class="mr-3 text-purple-400 mt-0.5">📈</span><span class="leading-relaxed">${t}</span></li>`).join('')}
                </ul>
            </div>
        </div>
    `;
    
    if (analysis.commentary) {
        html += `
            <div class="glass-card insight-card rounded-xl p-6 animate-fade-in delay-300">
                <div class="mb-4">
                    <span class="neon-badge">Комментарий эксперта</span>
                </div>
                <div class="flex items-start">
                    <span class="text-4xl text-slate-600 mr-4 font-serif">"</span>
                    <p class="text-slate-300 text-sm italic leading-relaxed pt-2">${analysis.commentary}</p>
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// Chart Functions
function renderFinanceCharts(data) {
    const canvas = document.getElementById('mainChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing
    if (mainChart instanceof Chart) {
        mainChart.destroy();
    }
    
    const datasets = [];
    // Neon Fintech Palette
    const palette = ['#00E5FF', '#FF1744', '#00FF94', '#FFD600', '#D500F9', '#FF00E5', '#651FFF', '#1DE9B6'];
    let colorIdx = 0;
    
    // Determine which metrics to show
    // We iterate through selectedMetrics
    selectedMetrics.forEach(key => {
        if (!data.series[key]) return;

        const color = palette[colorIdx % palette.length];
        const isPercent = ['profit_margin','safety_margin','roi','profitability_index','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate','roe'].includes(key);
        
        datasets.push({
            label: getMetricLabelRussian(key),
            data: data.series[key],
            borderColor: color,
            backgroundColor: hexToRgba(color, 0.1),
            borderWidth: 2,
            tension: 0.4,
            pointRadius: 0,
            fill: true,
            yAxisID: isPercent ? 'y1' : 'y'
        });
        colorIdx++;
    });
    
    if (datasets.length === 0) {
        return;
    }
    canvas.style.display = 'block';
    
    mainChart = new Chart(ctx, {
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
            events: ['click', 'touchstart', 'touchmove'],
            plugins: {
                legend: {
                    display: true,
                    labels: { color: '#94a3b8', font: { size: 10 } }
                },
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
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                y1: {
                    type: 'linear',
                    display: false,
                    position: 'right',
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });

    // Fix 10: Clear tooltip on release
    canvas.addEventListener('touchend', () => {
        if (mainChart) {
            mainChart.tooltip.setActiveElements([], {x: 0, y: 0});
            mainChart.update();
        }
    });
    canvas.addEventListener('mouseup', () => {
        if (mainChart) {
            mainChart.tooltip.setActiveElements([], {x: 0, y: 0});
            mainChart.update();
        }
    });
}

function buildAllMetricCards(latest, data) {
    const container = document.getElementById('metricsAccordion');
    if (!container) return;
    container.innerHTML = '';
    
    // Helper to create a metric row
    const createMetricRow = (key) => {
        const label = getMetricLabelRussian(key);
        let unit = '';
        if (['revenue','expenses','profit','average_check','investments','marketing_costs','ltv','cac'].includes(key)) unit = '₽';
        if (['profit_margin','safety_margin','roi','profitability_index','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate','roe'].includes(key)) unit = '%';
        
        const isActive = selectedMetrics.has(key);
        const val = (data.series[key] && data.series[key].length) ?
            data.series[key][data.series[key].length-1] : 0;

        return `
            <div class="flex justify-between items-center p-3 hover:bg-white/5 rounded-lg transition-colors">
                <div>
                    <div class="text-xs text-slate-300">${label}</div>
                    <div class="text-sm font-bold text-white">${formatNumber(val)} ${unit}</div>
                </div>
                <button class="w-8 h-8 rounded-full flex items-center justify-center transition-colors ${isActive ? 'bg-primary text-black shadow-[0_0_10px_rgba(0,229,255,0.5)]' : 'bg-slate-700/50 text-slate-400'}"
                    onclick="toggleMetric('${key}')">
                    ${isActive ? '✓' : '+'}
                </button>
            </div>
        `;
    };

    // Iterate groups
    Object.entries(metricGroups).forEach(([groupId, group]) => {
        const details = document.createElement('details');
        details.className = 'glass-card rounded-xl overflow-hidden group';
        // Open by default if current filter matches, or if filter is 'all' and group is 'finance' (Main)
        if (currentFilter === groupId || (currentFilter === 'all' && groupId === 'finance')) details.open = true;

        const summary = document.createElement('summary');
        summary.className = 'p-4 flex justify-between items-center bg-white/5 accordion-header select-none';
        summary.innerHTML = `
            <span class="font-bold text-slate-200">${group.label}</span>
            <span class="text-slate-400 accordion-arrow">▼</span>
        `;

        const content = document.createElement('div');
        content.className = 'p-2 space-y-1 bg-black/20';
        
        let hasMetrics = false;
        group.metrics.forEach(key => {
            if (data.series[key]) {
                content.innerHTML += createMetricRow(key);
                hasMetrics = true;
            }
        });

        if (hasMetrics) {
            details.appendChild(summary);
            details.appendChild(content);
            container.appendChild(details);
        }
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
        // Re-render buttons (to update checkmarks)
        // Note: This re-renders the whole accordion which closes it. 
        // Better to just update the button class.
        updateMetricButton(key);
    }
}

function updateMetricButton(key) {
    // Find all buttons for this key (in case of duplicates, though unlikely)
    // Since we rebuild, we can't easily find the button without ID.
    // But wait, buildAllMetricCards rebuilds everything.
    // To prevent closing accordions, we should save open states or just toggle class.
    
    // Let's just rebuild for now, but restore open states.
    const openDetails = Array.from(document.querySelectorAll('details[open]')).map(d => d.querySelector('summary span').textContent);
    
    buildAllMetricCards(null, currentChartData);
    
    // Restore open
    document.querySelectorAll('details').forEach(d => {
        const title = d.querySelector('summary span').textContent;
        if (openDetails.includes(title)) d.open = true;
    });
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

function highlightActiveTab() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('nav a');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href === currentPath) {
            link.classList.add('text-primary');
            link.classList.remove('text-slate-400');
        } else {
            link.classList.remove('text-primary');
            link.classList.add('text-slate-400');
        }
    });
}