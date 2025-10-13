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
let chartUpdateTimeout = null;

async function loadFinanceData(userId) {
    try {
        // Отменяем предыдущий запрос если он еще выполняется
        if (chartUpdateTimeout) {
            clearTimeout(chartUpdateTimeout);
        }
        
        // Дебаунс - обновляем не чаще чем раз в 500ms
        chartUpdateTimeout = setTimeout(async () => {
            const response = await fetch(`/api/user-finance-data/${userId}`);
            const data = await response.json();
            
            if (data.success) {
                renderFinanceChart(data.data);
                updateAdditionalMetrics(data.latest, data.data);
            }
        }, 500);
        
    } catch (error) {
        console.error('Ошибка загрузки финансовых данных:', error);
    }
}
let isChartLoading = false;

async function loadUserData() {
    const userId = document.getElementById('userSelect').value;
    if (!userId || isChartLoading) return;
    
    isChartLoading = true;
    
    try {
        await loadKPIMetrics(userId);
        await loadFinanceData(userId);
        await loadAIAnalysis(userId);
    } catch (error) {
        console.error('Ошибка загрузки данных:', error);
    } finally {
        isChartLoading = false;
    }
}
// Обработчик изменения размера окна
let resizeTimeout;
window.addEventListener('resize', function() {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        const userId = document.getElementById('userSelect').value;
        if (userId && financeChart) {
            // Пересоздаем график при изменении размера
            financeChart.destroy();
            financeChart = null;
            loadFinanceData(userId);
        }
    }, 250);
});
function renderFinanceChart(data) {
    const canvas = document.getElementById('financeChart');
    const ctx = canvas.getContext('2d');
    
    // Проверяем данные
    if (!data || !data.dates || data.dates.length === 0) {
        console.log('Нет данных для графика');
        return;
    }
    
    // Уничтожаем предыдущий график
    if (financeChart) {
        financeChart.destroy();
        financeChart = null;
    }
    
    // Определяем мобильное устройство
    const isMobile = window.innerWidth <= 768;
    
    setTimeout(() => {
        try {
            financeChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [
                        {
                            label: 'Выручка',
                            data: data.revenue,
                            borderColor: '#48bb78',
                            backgroundColor: 'rgba(72, 187, 120, 0.1)',
                            borderWidth: isMobile ? 1.5 : 2,
                            tension: 0.4,
                            fill: true
                        },
                        {
                            label: 'Расходы',
                            data: data.expenses,
                            borderColor: '#f56565',
                            backgroundColor: 'rgba(245, 101, 101, 0.1)',
                            borderWidth: isMobile ? 1.5 : 2,
                            tension: 0.4,
                            fill: true
                        },
                        {
                            label: 'Прибыль',
                            data: data.profit,
                            borderColor: '#4299e1',
                            backgroundColor: 'rgba(66, 153, 225, 0.1)',
                            borderWidth: isMobile ? 1.5 : 2,
                            tension: 0.4,
                            fill: true
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: true,
                    plugins: {
                        legend: {
                            position: isMobile ? 'bottom' : 'top',
                            labels: {
                                boxWidth: isMobile ? 12 : 15,
                                font: {
                                    size: isMobile ? 11 : 12
                                },
                                padding: isMobile ? 10 : 15
                            }
                        },
                        title: {
                            display: true,
                            text: 'Динамика за период',
                            font: {
                                size: isMobile ? 14 : 16
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    // Сокращаем числа на мобильных
                                    if (isMobile && value >= 1000) {
                                        return (value / 1000).toFixed(0) + 'k ₽';
                                    }
                                    return value.toLocaleString('ru-RU') + ' ₽';
                                },
                                font: {
                                    size: isMobile ? 10 : 11
                                },
                                maxTicksLimit: isMobile ? 5 : 8
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        },
                        x: {
                            ticks: {
                                font: {
                                    size: isMobile ? 9 : 10
                                },
                                maxTicksLimit: isMobile ? 6 : 10
                            },
                            grid: {
                                color: 'rgba(255,255,255,0.1)'
                            }
                        }
                    },
                    interaction: {
                        intersect: false,
                        mode: 'index'
                    },
                    elements: {
                        point: {
                            radius: isMobile ? 2 : 3,
                            hoverRadius: isMobile ? 4 : 5
                        }
                    }
                }
            });
        } catch (error) {
            console.error('Ошибка создания графика:', error);
        }
    }, 10);
}