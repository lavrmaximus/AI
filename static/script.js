// Базовые функции для сайта
console.log('BusinessAI loaded');

// Форматирование чисел
function formatNumber(num) {
    return new Intl.NumberFormat('ru-RU').format(num);
}

// Форматирование валюты
function formatCurrency(amount) {
    return formatNumber(amount) + ' ₽';
}

// Показ уведомлений
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'error' ? '#f56565' : type === 'success' ? '#48bb78' : '#4299e1'};
        color: white;
        border-radius: 5px;
        z-index: 10000;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}
async function loadAnalyticsData() {
    const userId = document.getElementById('userSelect').value;
    if (!userId) return;

    await loadFinancialAnalysis(userId);
    await loadTrendsAnalysis(userId);
}
// Новый адаптивный график с вертикальным курсором, интерполяцией и фильтрами периода
let currentRange = 'all';
let cursorX = null; // текущее положение курсора (px внутри графика)

function setTimeRange(range) {
    currentRange = range;
    const btns = document.querySelectorAll('.range-btn');
    btns.forEach(b => b.classList.toggle('active', b.dataset.range === range));
    if (window.currentChartData) {
        renderFinanceChart(window.currentChartData);
    }
}

function sliceDataByRange(data) {
    // data: { dates: [], series: {key: [..]} } или старый формат
    const dates = data.dates || [];
    const total = dates.length;
    const map = { day: 1, week: 7, month: 30, quarter: 90, all: total };
    const count = map[currentRange] || total;
    const start = Math.max(0, total - count);
    const sliced = { dates: dates.slice(start) };
    if (data.series) {
        sliced.series = {};
        Object.keys(data.series).forEach(k => {
            sliced.series[k] = (data.series[k] || []).slice(start);
        });
    } else {
        // старый формат
        ['revenue','expenses','profit'].forEach(k => {
            if (data[k]) {
                sliced[k] = data[k].slice(start);
            }
        });
    }
    return sliced;
}

function renderFinanceChart(data) {
	// Три отдельных графика: ₽, штуки, проценты
	const canvasCurrency = document.getElementById('financeChartCurrency');
	const ctxCurrency = canvasCurrency.getContext('2d');
	const canvasCounts = document.getElementById('financeChartCounts');
	const ctxCounts = canvasCounts.getContext('2d');
	const canvasPercent = document.getElementById('financeChartPercent');
	const ctxPercent = canvasPercent.getContext('2d');
	window.currentChartData = data;
	if (!data || !data.dates || data.dates.length === 0) {
		canvasCurrency.style.display = 'none';
		canvasCounts.style.display = 'none';
		canvasPercent.style.display = 'none';
		return;
	}
	canvasCurrency.style.display = 'block';
	canvasCounts.style.display = 'block';
	canvasPercent.style.display = 'block';

	const rangeData = sliceDataByRange(data);

	// Уничтожим прежние инстансы, если есть
	try { if (window.financeChart && typeof window.financeChart.destroy === 'function') window.financeChart.destroy(); } catch(e) {}
	try { if (window.financeChartCurrency && typeof window.financeChartCurrency.destroy === 'function') window.financeChartCurrency.destroy(); } catch(e) {}
	try { if (window.financeChartCounts && typeof window.financeChartCounts.destroy === 'function') window.financeChartCounts.destroy(); } catch(e) {}
	try { if (window.financeChartPercent && typeof window.financeChartPercent.destroy === 'function') window.financeChartPercent.destroy(); } catch(e) {}
	window.financeChart = null;
	window.financeChartCurrency = null;
	window.financeChartCounts = null;
	window.financeChartPercent = null;

	// Построение datasets по типам
	const datasetsCurrency = [];
	const datasetsCounts = [];
	const datasetsPercent = [];
	const palette = [
		'#48bb78','#f56565','#4299e1','#ed8936','#9f7aea','#38b2ac','#ed64a6','#a0aec0',
		'#f6ad55','#68d391','#4fd1c5','#63b3ed','#fc8181','#fbb6ce','#cbd5e0','#e9d8fd',
		'#b794f4','#feb2b2','#81e6d9','#90cdf4','#fbd38d','#f6ad55'
	];
    const keys = data.series ? Object.keys(data.series) : ['revenue','expenses','profit'];
	let colorIdx = 0;
	keys.forEach(k => {
        let shouldShow;
        if (window.selectedMetrics) {
            // Если набор определён, показываем только явно выбранные (включая пустой набор = ничего)
            shouldShow = window.selectedMetrics.has(k);
        } else {
            // Fallback для очень старого сценария
            shouldShow = ['revenue','expenses','profit'].includes(k);
        }
		if (!shouldShow) return;
		const color = palette[colorIdx % palette.length];
		colorIdx++;
		const seriesData = data.series ? rangeData.series[k] : rangeData[k];
		if (!seriesData) return;
		const ds = {
            label: getMetricLabelRussian(k),
			data: seriesData,
			borderColor: color,
			backgroundColor: hexToRgba(color, 0.1),
			borderWidth: 2,
			tension: 0.35,
			fill: true,
			pointRadius: 0
		};
		if (isCurrencyMetric(k)) {
			datasetsCurrency.push(ds);
		} else if (isPercentMetric(k)) {
			datasetsPercent.push(ds);
		} else {
			datasetsCounts.push(ds);
		}
	});

	// Построим графики
    window.financeChartCurrency = new Chart(ctxCurrency, {
		type: 'line',
		data: { labels: rangeData.dates, datasets: datasetsCurrency },
		options: baseChartOptions('₽')
	});
	window.financeChartCounts = new Chart(ctxCounts, {
		type: 'line',
		data: { labels: rangeData.dates, datasets: datasetsCounts },
		options: baseChartOptions('')
	});
	window.financeChartPercent = new Chart(ctxPercent, {
		type: 'line',
		data: { labels: rangeData.dates, datasets: datasetsPercent },
		options: baseChartOptions('%')
	});

    attachCursorHandlers(canvasCurrency, window.financeChartCurrency, 'chartReadoutCurrency', 'cursorLineCurrency');
    attachCursorHandlers(canvasCounts, window.financeChartCounts, 'chartReadoutCounts', 'cursorLineCounts');
    attachCursorHandlers(canvasPercent, window.financeChartPercent, 'chartReadoutPercent', 'cursorLinePercent');
}

function attachCursorHandlers(canvas, chart, readoutId = 'chartReadoutCurrency', lineId = 'cursorLineCurrency') {
	const readout = document.getElementById(readoutId);
	if (!readout) return;
	const domLine = document.getElementById(lineId);
    let isDragging = false;

    const updateFromEvent = (evt) => {
        const rect = canvas.getBoundingClientRect();
        const clientX = (evt.touches && evt.touches[0]) ? evt.touches[0].clientX : evt.clientX;
        if (typeof clientX !== 'number') return;
        cursorX = clientX - rect.left;
        // Обновляем DOM-линию
        if (domLine) {
            domLine.style.display = 'block';
            const x = Math.max(0, Math.min(cursorX, rect.width));
            domLine.style.left = `${x}px`;
        }
        updateReadout(chart, readout);
        chart.draw();
    };

    const clearCursor = () => {
        cursorX = null;
        readout.setAttribute('aria-hidden', 'true');
        readout.textContent = '';
        if (domLine) domLine.style.display = 'none';
        chart.draw();
    };

    canvas.addEventListener('pointerdown', (e) => {
        isDragging = true;
        if (e.pointerId) canvas.setPointerCapture(e.pointerId);
        updateFromEvent(e);
    });
    canvas.addEventListener('pointermove', (e) => {
        if (isDragging || e.buttons === 1 || e.pointerType === 'touch') updateFromEvent(e);
    });
    canvas.addEventListener('pointerup', (e) => {
        isDragging = false;
        updateFromEvent(e);
    });
    canvas.addEventListener('pointercancel', () => { isDragging = false; });
    // Touch-события для iOS/Android
    canvas.addEventListener('touchstart', (e) => { isDragging = true; updateFromEvent(e); }, { passive: true });
    canvas.addEventListener('touchmove', (e) => { updateFromEvent(e); }, { passive: true });
    canvas.addEventListener('touchend', () => { isDragging = false; });
    // Не очищаем курсор при уходе — пусть остаётся видимым
}

function updateReadout(chart, readoutEl) {
    if (cursorX === null) return;
    const { scales, data } = chart;
    const xScale = scales.x;
    if (!xScale) return;
    const px = Math.max(xScale.left, Math.min(cursorX, xScale.right));
    const xValue = xScale.getValueForPixel(px);
    // Интерполяция значений между ближайшими индексами
    const i0 = Math.floor(xValue);
    const i1 = Math.min(i0 + 1, data.labels.length - 1);
    const t = Math.min(1, Math.max(0, xValue - i0));
    const lerp = (a, b, t) => a + (b - a) * t;

    const series = chart.data.datasets.map(ds => {
        const v0 = Number(ds.data[i0] ?? 0);
        const v1 = Number(ds.data[i1] ?? v0);
        return { label: ds.label, value: Math.round(lerp(v0, v1, t)) };
    });

    const date0 = data.labels[i0] ?? '';
    const date1 = data.labels[i1] ?? date0;
    const dateText = (t < 0.5) ? date0 : date1;

    if (series.length === 0) {
        readoutEl.innerHTML = `${dateText}: нет выбранных метрик`;
    } else {
        readoutEl.innerHTML = `${dateText}: ` +
            series.map(s => `${s.label} ${s.value.toLocaleString('ru-RU')}`).join(' · ');
    }
    readoutEl.setAttribute('aria-hidden', 'false');
}

// Функция обновления информации о периоде
function updatePeriodInfo(data) {
    if (!data || !data.dates || data.dates.length === 0) return;
    
    const periodElement = document.getElementById('periodInfo');
    const dates = data.dates;
    
    if (dates.length === 1) {
        periodElement.textContent = dates[0];
    } else {
        periodElement.textContent = `${dates[dates.length - 1]} - ${dates[0]}`;
    }
}


// Обработчик изменения размера окна для прокручиваемого графика
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        const userSelect = document.getElementById('userSelect');
        const userId = userSelect ? userSelect.value : null;
        if (userId && window.financeChart) {
            try {
                if (typeof window.financeChart.destroy === 'function') {
                    window.financeChart.destroy();
                }
            } catch (e) {}
            window.financeChart = null;
            if (typeof window.loadFinanceData === 'function') {
                window.loadFinanceData(userId);
            } else if (typeof window.loadAnalyticsData === 'function') {
                window.loadAnalyticsData();
            }
        }
    }, 250);
});

// Добавляем интерактивность для прокрутки
document.addEventListener('DOMContentLoaded', function() {
    const scrollArea = document.querySelector('.chart-scroll-area');
    if (scrollArea) {
        // Скрываем подсказку прокрутки после первого взаимодействия
        scrollArea.addEventListener('scroll', function() {
            const indicator = document.querySelector('.scroll-indicator');
            if (indicator) {
                indicator.style.opacity = '0';
                setTimeout(() => {
                    indicator.style.display = 'none';
                }, 300);
            }
        });
        
        // Добавляем инерцию прокрутки на мобильных
        let startX;
        let scrollLeft;
        let isDown = false;
        
        scrollArea.addEventListener('mousedown', (e) => {
            isDown = true;
            startX = e.pageX - scrollArea.offsetLeft;
            scrollLeft = scrollArea.scrollLeft;
            scrollArea.style.cursor = 'grabbing';
        });
        
        scrollArea.addEventListener('mouseleave', () => {
            isDown = false;
            scrollArea.style.cursor = 'grab';
        });
        
        scrollArea.addEventListener('mouseup', () => {
            isDown = false;
            scrollArea.style.cursor = 'grab';
        });
        
        scrollArea.addEventListener('mousemove', (e) => {
            if (!isDown) return;
            e.preventDefault();
            const x = e.pageX - scrollArea.offsetLeft;
            const walk = (x - startX) * 2; // Множитель для скорости прокрутки
            scrollArea.scrollLeft = scrollLeft - walk;
        });
        
        // Touch события для мобильных
        scrollArea.addEventListener('touchstart', (e) => {
            isDown = true;
            startX = e.touches[0].pageX - scrollArea.offsetLeft;
            scrollLeft = scrollArea.scrollLeft;
        });
        
        scrollArea.addEventListener('touchend', () => {
            isDown = false;
        });
        
        scrollArea.addEventListener('touchmove', (e) => {
            if (!isDown) return;
            const x = e.touches[0].pageX - scrollArea.offsetLeft;
            const walk = (x - startX) * 2;
            scrollArea.scrollLeft = scrollLeft - walk;
        });
    }
});
// Обработчики для прокрутки графика
document.addEventListener('DOMContentLoaded', function() {
    initChartScroll();
});

function initChartScroll() {
    const scrollArea = document.querySelector('.chart-scroll-area');
    if (!scrollArea) return;

    let isDragging = false;
    let startX, scrollLeft;

    // Скрываем подсказку после первого взаимодействия
    scrollArea.addEventListener('scroll', function() {
        const indicator = document.querySelector('.scroll-indicator');
        if (indicator && indicator.style.opacity !== '0') {
            indicator.style.opacity = '0';
            setTimeout(() => {
                indicator.style.display = 'none';
            }, 300);
        }
    });

    // Desktop dragging
    scrollArea.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.pageX - scrollArea.offsetLeft;
        scrollLeft = scrollArea.scrollLeft;
        scrollArea.style.cursor = 'grabbing';
        scrollArea.style.userSelect = 'none';
    });

    scrollArea.addEventListener('mouseleave', () => {
        if (isDragging) {
            isDragging = false;
            scrollArea.style.cursor = 'grab';
            scrollArea.style.userSelect = 'auto';
        }
    });

    scrollArea.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            scrollArea.style.cursor = 'grab';
            scrollArea.style.userSelect = 'auto';
        }
    });

    scrollArea.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        e.preventDefault();
        const x = e.pageX - scrollArea.offsetLeft;
        const walk = (x - startX) * 2;
        scrollArea.scrollLeft = scrollLeft - walk;
    });

    // Mobile touch events
    scrollArea.addEventListener('touchstart', (e) => {
        isDragging = true;
        startX = e.touches[0].pageX - scrollArea.offsetLeft;
        scrollLeft = scrollArea.scrollLeft;
    });

    scrollArea.addEventListener('touchend', () => {
        isDragging = false;
    });

    scrollArea.addEventListener('touchmove', (e) => {
        if (!isDragging) return;
        const x = e.touches[0].pageX - scrollArea.offsetLeft;
        const walk = (x - startX) * 2;
        scrollArea.scrollLeft = scrollLeft - walk;
    });

    // Устанавливаем начальный курсор
    scrollArea.style.cursor = 'grab';
}

function hexToRgba(hex, alpha) {
    const res = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    if (!res) return 'rgba(0,0,0,' + alpha + ')';
    const r = parseInt(res[1], 16);
    const g = parseInt(res[2], 16);
    const b = parseInt(res[3], 16);
    return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
function baseChartOptions(suffix) {
	return {
		responsive: true,
		maintainAspectRatio: false,
		interaction: { mode: 'index', intersect: false },
		plugins: {
			legend: { display: false }, // отключаем выбор метрик на графике
			tooltip: { enabled: false },
			decimation: { enabled: true, algorithm: 'lttb' },
			verticalCursor: { enabled: true, disabled: false }
		},
		scales: {
			y: {
				beginAtZero: true,
				ticks: {
					callback: function(value) { return suffix ? (value.toLocaleString('ru-RU') + ' ' + suffix) : value.toLocaleString('ru-RU'); }
				}
			},
			x: { display: false }
		},
		layout: { padding: { top: 6, right: 6, bottom: 6, left: 6 } },
		elements: { point: { radius: 0 } },
		aspectRatio: 2
	};
}
function isCurrencyMetric(key) {
	return ['revenue','expenses','profit','average_check','investments','marketing_costs','ltv','cac'].includes(key);
}
function isPercentMetric(key) {
	return ['profit_margin','safety_margin','roi','profitability_index','ltv_cac_ratio','customer_profit_margin','sgr','revenue_growth_rate','roe'].includes(key);
}

function getMetricLabelRussian(key) {
    const map = {
        revenue: 'Выручка',
        expenses: 'Расходы',
        profit: 'Прибыль',
        clients: 'Клиенты',
        average_check: 'Средний чек',
        investments: 'Инвестиции',
        marketing_costs: 'Маркетинг',
        employees: 'Сотрудники',
        profit_margin: 'Маржа прибыли, %',
        break_even_clients: 'Точка безуб., клиенты',
        safety_margin: 'Запас прочности, %',
        roi: 'ROI, %',
        profitability_index: 'Индекс прибыльности',
        ltv: 'LTV',
        cac: 'CAC',
        ltv_cac_ratio: 'LTV/CAC',
        customer_profit_margin: 'Маржа клиента, %',
        sgr: 'Устойчивый рост, %',
        revenue_growth_rate: 'Рост выручки, %',
        asset_turnover: 'Оборачиваемость активов',
        roe: 'ROE, %',
        months_to_bankruptcy: 'Месяцев до банкротства',
        financial_health_score: 'Фин. здоровье',
        growth_health_score: 'Здоровье роста',
        efficiency_health_score: 'Здоровье эффективности',
        overall_health_score: 'Итоговый Health'
    };
    return map[key] || key;
}
// Bottom Navigation Enhancements
document.addEventListener('DOMContentLoaded', function() {
    enhanceBottomNavigation();
});

function enhanceBottomNavigation() {
    const navButtons = document.querySelectorAll('.bottom-nav .nav-btn');
    
    navButtons.forEach(btn => {
        // Добавляем feedback при касании
        btn.addEventListener('touchstart', function() {
            this.style.transform = 'scale(0.95)';
        });
        
        btn.addEventListener('touchend', function() {
            this.style.transform = 'scale(1)';
        });
        
        // Для desktop hover эффектов
        btn.addEventListener('mouseenter', function() {
            if (!this.classList.contains('active')) {
                this.style.background = 'rgba(212, 0, 255, 0.08)';
            }
        });
        
        btn.addEventListener('mouseleave', function() {
            if (!this.classList.contains('active')) {
                this.style.background = 'transparent';
            }
        });
    });
    
    // Плавная прокрутка при переходе между страницами
    const currentPath = window.location.pathname;
    const activeBtn = document.querySelector(`.nav-btn[href="${currentPath}"]`);
    if (activeBtn) {
        setTimeout(() => {
            activeBtn.classList.add('active');
        }, 100);
    }
}

// Предотвращаем zoom при двойном тапе по навигации (только для мобильных)
document.addEventListener('touchstart', function(e) {
    if (e.target.closest('.bottom-nav')) {
        if (e.touches.length > 1) {
            e.preventDefault();
        }
    }
}, { passive: false });

// Оптимизация для iOS Safari
if (navigator.userAgent.match(/iPhone|iPad|iPod/i)) {
    document.documentElement.style.setProperty('--sat', 'env(safe-area-inset-bottom)');
    document.querySelector('.bottom-nav').style.paddingBottom = 'calc(0.5rem + env(safe-area-inset-bottom))';
}