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
    const total = data.dates.length;
    const map = { day: 1, week: 7, month: 30, quarter: 90, all: total };
    const count = map[currentRange] || total;
    const end = 0; // последние значения в начале массива согласно prepare_chart_data
    const start = Math.min(total, count);
    // берем последние N точек (с 0 по N-1) исходя из формата данных (последняя запись первая)
    return {
        dates: data.dates.slice(0, start).slice().reverse(),
        revenue: data.revenue.slice(0, start).slice().reverse(),
        expenses: data.expenses.slice(0, start).slice().reverse(),
        profit: data.profit.slice(0, start).slice().reverse()
    };
}

function renderFinanceChart(data) {
    const canvas = document.getElementById('financeChart');
    const ctx = canvas.getContext('2d');
    window.currentChartData = data;
    if (!data || !data.dates || data.dates.length === 0) {
        canvas.style.display = 'none';
        return;
    }
    canvas.style.display = 'block';

    const rangeData = sliceDataByRange(data);

    if (window.financeChart && typeof window.financeChart.destroy === 'function') {
        window.financeChart.destroy();
    }
    window.financeChart = null;

    // Убираем плагин Chart.js, вместо него используем DOM-линию поверх canvas

    window.financeChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: rangeData.dates,
            datasets: [
                {
                    label: 'Выручка',
                    data: rangeData.revenue,
                    borderColor: '#48bb78',
                    backgroundColor: 'rgba(72, 187, 120, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 0
                },
                {
                    label: 'Расходы',
                    data: rangeData.expenses,
                    borderColor: '#f56565',
                    backgroundColor: 'rgba(245, 101, 101, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 0
                },
                {
                    label: 'Прибыль',
                    data: rangeData.profit,
                    borderColor: '#4299e1',
                    backgroundColor: 'rgba(66, 153, 225, 0.1)',
                    borderWidth: 2,
                    tension: 0.35,
                    fill: true,
                    pointRadius: 0
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { position: 'top' },
                tooltip: { enabled: false }, // используем свой рид-аут
                decimation: { enabled: true, algorithm: 'lttb' },
                // Явно задаём объект опций для нашего плагина, чтобы Chart.js не обращался к undefined.disabled
                verticalCursor: { enabled: true, disabled: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) { return value.toLocaleString('ru-RU') + ' ₽'; }
                    }
                },
                x: { display: false } // скрываем подписи дат на оси X для экономии места
            },
            layout: { padding: { top: 6, right: 6, bottom: 6, left: 6 } },
            elements: { point: { radius: 0 } },
            aspectRatio: 2 // заставляет график ужиматься по ширине при ограничении высоты
        },
        plugins: []
    });

    attachCursorHandlers(canvas, window.financeChart);
}

function attachCursorHandlers(canvas, chart) {
    const readout = document.getElementById('chartReadout');
    if (!readout) return;
    const domLine = document.getElementById('cursorLine');
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

    readoutEl.innerHTML = `${dateText}: ` +
        series.map(s => `${s.label} ${s.value.toLocaleString('ru-RU')} ₽`).join(' · ');
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

// Функция экспорта основного графика
function exportChart() {
    if (!financeChart) {
        alert('Сначала загрузите данные графика');
        return;
    }
    
    const link = document.createElement('a');
    link.download = `business-chart-${new Date().toISOString().split('T')[0]}.png`;
    link.href = financeChart.toBase64Image();
    link.click();
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