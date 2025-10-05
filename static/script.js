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