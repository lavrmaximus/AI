"""
Модуль для форматирования отчетов о бизнесе
"""
from typing import Dict, List

def format_business_report(business_data: Dict, metrics: Dict = None, recommendations: List[str] = None) -> str:
    """Единый формат отчета о бизнесе"""
    response = ""
    
    business_name = business_data.get('business_name', 'Бизнес')
    response += f"📊 *ДЕТАЛЬНЫЙ АНАЛИЗ БИЗНЕСА: {business_name}*\n\n"
    
    if metrics:
        health_score = metrics.get('overall_health_score', 0)
        health_assessment = get_health_assessment(health_score)
        emoji = health_assessment.get('emoji', '⚪')
        response += f"🏥 *БИЗНЕС-ЗДОРОВЬЕ: {health_score}/100* {emoji}\n"
        response += f"*{health_assessment.get('message', '')}*\n\n"
    
    response += "💰 *КЛЮЧЕВЫЕ МЕТРИКИ:*\n"
    if metrics:
        response += f"• Рентабельность: {metrics.get('profit_margin', 0):.1f}%\n"
        response += f"• ROI: {metrics.get('roi', 0):.1f}%\n"
        response += f"• LTV/CAC: {metrics.get('ltv_cac_ratio', 0):.2f}\n"
        response += f"• Запас прочности: {metrics.get('safety_margin', 0):.1f}%\n"
        response += f"• Темп роста выручки: {metrics.get('revenue_growth_rate', 0):.1f}%\n"
        response += f"• До банкротства: {metrics.get('months_to_bankruptcy', 0):.0f} мес\n\n"
    else:
        response += "• Рентабельность: _не рассчитано_\n"
        response += "• ROI: _не рассчитано_\n"
        response += "• LTV/CAC: _не рассчитано_\n"
        response += "• Запас прочности: _не рассчитано_\n\n"
    
    response += "📊 *ВСЕ МЕТРИКИ:*\n"
    
    # Сырые данные
    raw_fields = {
        'revenue': '💰 Выручка',
        'expenses': '📊 Расходы', 
        'profit': '📈 Прибыль',
        'clients': '👥 Клиенты',
        'average_check': '💳 Средний чек',
        'investments': '💼 Инвестиции',
        'marketing_costs': '📢 Маркетинг',
        'employees': '🧑‍🤝‍🧑 Сотрудники',
        'new_clients_per_month': '🆕 Новые клиенты/мес',
        'customer_retention_rate': '🔄 Удержание клиентов'
    }
    
    for field, name in raw_fields.items():
        value = business_data.get(field, 0)
        if value and value != 0:
            if field == 'customer_retention_rate':
                response += f"• {name}: {value:.1f}%\n"
            elif field in ['clients', 'employees', 'new_clients_per_month']:
                response += f"• {name}: {value:,.0f}\n"
            else:
                response += f"• {name}: {value:,.0f} руб\n"
        else:
            response += f"• {name}: _отсутствует_\n"
    
    # Рассчитанные метрики если есть
    if metrics:
        calculated_fields = {
            'profit_margin': 'Рентабельность',
            'break_even_clients': 'Точка безубыточности',
            'safety_margin': 'Запас прочности',
            'roi': 'ROI',
            'profitability_index': 'Индекс прибыльности',
            'ltv': 'LTV',
            'cac': 'CAC',
            'ltv_cac_ratio': 'LTV/CAC',
            'customer_profit_margin': 'Маржа на клиента',
            'sgr': 'SGR',
            'revenue_growth_rate': 'Темп роста выручки',
            'asset_turnover': 'Оборачиваемость активов',
            'roe': 'ROE',
            'months_to_bankruptcy': 'До банкротства',
            'financial_health_score': 'Финансовое здоровье',
            'growth_health_score': 'Здоровье роста',
            'efficiency_health_score': 'Эффективность',
            'overall_health_score': 'Общее здоровье'
        }
        
        for field, name in calculated_fields.items():
            value = metrics.get(field, 0)
            if field in ['financial_health_score', 'growth_health_score', 'efficiency_health_score', 'overall_health_score']:
                response += f"• {name}: {value:.0f}\n"
            elif field in ['months_to_bankruptcy']:
                response += f"• {name}: {value:.0f} мес\n"
            elif field in ['profit_margin', 'safety_margin', 'roi', 'revenue_growth_rate', 'roe']:
                response += f"• {name}: {value:.1f}%\n"
            else:
                response += f"• {name}: {value:.2f}\n"
    
    # Рекомендации
    if recommendations:
        response += "\n🎯 *РЕКОМЕНДАЦИИ:*\n"
        for i, rec in enumerate(recommendations, 1):
            response += f"{i}. {rec}\n"
    
    return response

def get_health_assessment(score: int) -> Dict:
    """Получение оценки здоровья бизнеса"""
    if score >= 90:
        return {'emoji': '🟢', 'message': 'Отличное состояние! Продолжайте в том же духе!'}
    elif score >= 75:
        return {'emoji': '🟡', 'message': 'Хорошее состояние. Есть куда расти!'}
    elif score >= 60:
        return {'emoji': '🟠', 'message': 'Среднее состояние. Требуются улучшения.'}
    else:
        return {'emoji': '🔴', 'message': 'Требуются срочные действия!'}
