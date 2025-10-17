import logging
from typing import Dict, List, Optional
from database import db
from metrics_calculator import metrics_calculator

logger = logging.getLogger(__name__)

class BusinessAnalyzer:
    """
    Единый анализатор бизнеса для Telegram бота и веб-сайта
    """
    
    def __init__(self):
        self.calculator = metrics_calculator
    
    async def analyze_business_data(self, raw_data: Dict, user_id: str, business_id: int = None) -> Dict:
        """
        Комплексный анализ бизнеса с 22 метриками
        """
        try:
            # ЕСЛИ НЕТ business_id - СОЗДАЕМ НОВЫЙ БИЗНЕС!
            if not business_id:
                business_name = raw_data.get('business_name', 'Основной бизнес')
                business_id = await db.create_business(user_id, business_name)
                logger.info(f"🆕 Создан бизнес: {business_id}")

            # 1. Расчет всех 22 метрик
            previous_data = await self._get_previous_business_data(business_id)
            metrics = self.calculator.calculate_all_metrics(raw_data, previous_data)
            
            # 2. Базовый AI-анализ текстового описания
            ai_description = self._format_data_for_ai(raw_data)
            ai_basic_analysis = await self._get_basic_ai_analysis(ai_description, user_id)
            
            # 3. Сохраняем в базу данных
            snapshot_id = await db.add_business_snapshot(business_id, raw_data, metrics)
            logger.info(f"✅ Снимок бизнеса сохранен: {snapshot_id}")
            
            # 4. Формирование ответа
            response = self._format_analysis_response(raw_data, metrics, ai_basic_analysis)
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Ошибка анализа бизнеса: {e}")
            return {'error': str(e)}
    
    async def _get_previous_business_data(self, business_id: int) -> Optional[Dict]:
        """Получение предыдущих данных для расчета роста"""
        if not business_id:
            return None
            
        try:
            history = await db.get_business_history(business_id, limit=2)
            if len(history) > 1:
                # Возвращаем предыдущий снепшот как сырые данные
                prev_snapshot = history[1]
                return {
                    'revenue': prev_snapshot.get('revenue', 0),
                    'expenses': prev_snapshot.get('expenses', 0),
                    'profit': prev_snapshot.get('profit', 0),
                    'clients': prev_snapshot.get('clients', 0),
                    'average_check': prev_snapshot.get('average_check', 0),
                    'investments': prev_snapshot.get('investments', 0),
                    'marketing_costs': prev_snapshot.get('marketing_costs', 0)
                }
            return None
        except:
            return None
    
    async def _get_basic_ai_analysis(self, description: str, user_id: str) -> Dict:
        """
        Получение базового AI-анализа - только комментарий и рекомендации
        """
        try:
            from ai import general_chat
            
            # Простой промпт для получения комментариев
            prompt = f"""Проанализируй этот бизнес дай краткий комментарий и 3 рекомендации:
            
            {description}
            
            Формат ответа:
            КOММЕНТАРИЙ: [tekст]
            СОВЕТ1: [совет]
            СОВЕТ2: [совет] 
            СОВЕТ3: [совет]
            СОВЕТ4: [совет]
            """
            
            response = await general_chat(prompt, user_id)
            
            # Парсим ответ
            result = {'КОММЕНТАРИЙ': '', 'СОВЕТЫ': []}
            
            if 'КОММЕНТАРИЙ:' in response:
                parts = response.split('КОММЕНТАРИЙ:')
                if len(parts) > 1:
                    comment_part = parts[1].split('СОВЕТ')[0] if 'СОВЕТ' in parts[1] else parts[1]
                    result['КОММЕНТАРИЙ'] = comment_part.strip()
            
            # Ищем советы
            import re
            # Ищем метки вида "СОВЕТ1:", "СОВЕТ 2 -", и т.п.
            advice_pattern = r"СОВЕТ\s*\d*\s*[:\-]\s*(.+?)(?=\n\s*СОВЕТ|\Z)"
            matches = re.findall(advice_pattern, response, re.IGNORECASE | re.DOTALL)
            result['СОВЕТЫ'] = [match.strip() for match in matches[:4]]
            
            # Если не найдено стандартных советов, ищем просто нумерованные списки
            if not result['СОВЕТЫ']:
                lines = response.split('\n')
                for line in lines:
                    if line.strip().startswith(('1.', '2.', '3.', '•', '-')):
                        result['СОВЕТЫ'].append(line.strip().lstrip('123.- ').strip())
                    if len(result['СОВЕТЫ']) >= 4:
                        break
            
            return result
            
        except Exception as e:
            logger.error(f"Ошибка базового AI-анализа: {e}")
            return {'КОММЕНТАРИЙ': 'Анализ выполнен успешно', 'СОВЕТЫ': []}
    
    def _format_data_for_ai(self, raw_data: Dict) -> str:
        """Форматирование данных для AI-анализа"""
        parts = []
        
        if raw_data.get('business_name'):
            parts.append(f"Бизнес: {raw_data['business_name']}")
        if raw_data.get('revenue'):
            parts.append(f"выручка {raw_data['revenue']:,.0f} руб")
        if raw_data.get('expenses'):
            parts.append(f"расходы {raw_data['expenses']:,.0f} руб")
        if raw_data.get('profit'):
            parts.append(f"прибыль {raw_data['profit']:,.0f} руб")
        if raw_data.get('clients'):
            parts.append(f"клиентов {raw_data['clients']:,.0f}")
        if raw_data.get('average_check'):
            parts.append(f"средний чек {raw_data['average_check']:,.0f} руб")
        if raw_data.get('investments'):
            parts.append(f"инвестиции {raw_data['investments']:,.0f} руб")
        if raw_data.get('marketing_costs'):
            parts.append(f"маркетинг {raw_data['marketing_costs']:,.0f} руб")
        
        return ", ".join(parts)
    
    def _format_analysis_response(self, raw_data: Dict, metrics: Dict, ai_analysis: Dict) -> Dict:
        """Форматирование ответа для бота"""
        
        health_assessment = self.calculator.get_health_assessment(
            metrics.get('overall_health_score', 0)
        )
        
        response = {
            'health_score': metrics.get('overall_health_score', 0),
            'health_assessment': health_assessment,
            'key_metrics': self._extract_key_metrics(metrics),
            'ai_commentary': ai_analysis.get('КОММЕНТАРИЙ', ''),
            'ai_advice': ai_analysis.get('СОВЕТЫ', []),
            'detailed_metrics': metrics
        }
        
        return response
    
    def _extract_key_metrics(self, metrics: Dict) -> Dict:
        """Извлечение ключевых метрик для отображения"""
        return {
            'profit_margin': metrics.get('profit_margin', 0),
            'roi': metrics.get('roi', 0),
            'ltv_cac_ratio': metrics.get('ltv_cac_ratio', 0),
            'safety_margin': metrics.get('safety_margin', 0),
            'revenue_growth_rate': metrics.get('revenue_growth_rate', 0),
            'months_to_bankruptcy': metrics.get('months_to_bankruptcy', 0)
        }
    
    async def get_business_metrics(self, business_id: int, period: str = 'all') -> Dict:
        """
        Получение метрик бизнеса для веб-сайта
        """
        try:
            history = await db.get_business_history(business_id)
            
            if not history:
                return {'error': 'Бизнес не найден'}
            
            # Агрегация данных за период
            aggregated_data = self._aggregate_period_data(history, period)
            
            # Расчет трендов
            trends = self._calculate_trends(history)
            
            return {
                'business_id': business_id,
                'period': period,
                'current_metrics': history[0] if history else {},
                'history': history,
                'trends': trends,
                'aggregated_data': aggregated_data
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения метрик: {e}")
            return {'error': str(e)}
    
    async def generate_business_report(self, business_id: int) -> Dict:
        """
        Генерация полного отчета для бизнеса
        """
        try:
            history = await db.get_business_history(business_id)
            
            if not history:
                return {'error': 'Бизнес не найден'}
            
            current_data = history[0]
            metrics = current_data  # В истории уже есть рассчитанные метрики
            
            # Health assessment
            health_assessment = self.calculator.get_health_assessment(
                metrics.get('overall_health_score', 0)
            )
            
            # Benchmark report
            benchmark_report = self.calculator.generate_benchmark_report(
                metrics, 
                'other'  # Можно добавить поле industry в бизнес
            )
            
            # Рекомендации
            recommendations = self._generate_recommendations(metrics, health_assessment)
            
            return {
                'business_id': business_id,
                'health_score': metrics.get('overall_health_score', 0),
                'health_assessment': health_assessment,
                'key_metrics': self._extract_key_metrics(metrics),
                'all_metrics': metrics,
                'benchmark_report': benchmark_report,
                'recommendations': recommendations,
                'trends': self._calculate_trends(history)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации отчета: {e}")
            return {'error': str(e)}
    
    def _aggregate_period_data(self, history: List[Dict], period: str) -> Dict:
        """Агрегация данных за период"""
        if not history:
            return {}
        
        # Простая агрегация - можно улучшить
        return {
            'avg_revenue': sum(h.get('revenue', 0) for h in history) / len(history),
            'avg_profit': sum(h.get('profit', 0) for h in history) / len(history),
            'avg_health_score': sum(h.get('overall_health_score', 0) for h in history) / len(history),
            'period_count': len(history)
        }
    
    def _calculate_trends(self, history: List[Dict]) -> Dict:
        """Расчет трендов на основе истории"""
        if len(history) < 2:
            return {'trend': 'stable', 'change': 0}
        
        current = history[0]
        previous = history[1]
        
        revenue_change = 0
        if previous.get('revenue', 0) > 0:
            revenue_change = ((current.get('revenue', 0) - previous.get('revenue', 0)) / previous.get('revenue', 0)) * 100
        
        health_change = current.get('overall_health_score', 0) - previous.get('overall_health_score', 0)
        
        return {
            'revenue_change': revenue_change,
            'health_change': health_change,
            'trend': 'up' if revenue_change > 5 else 'down' if revenue_change < -5 else 'stable'
        }
    
    def _generate_recommendations(self, metrics: Dict, health_assessment: Dict) -> List[str]:
        """Генерация рекомендаций на основе метрик"""
        recommendations = []
        
        profit_margin = metrics.get('profit_margin', 0)
        ltv_cac_ratio = metrics.get('ltv_cac_ratio', 0)
        safety_margin = metrics.get('safety_margin', 0)
        
        if profit_margin < 10:
            recommendations.append("Увеличить рентабельность за счет оптимизации расходов")
        
        if ltv_cac_ratio < 2:
            recommendations.append("Улучшить LTV/CAC ratio: снизить стоимость привлечения или увеличить ценность клиента")
        
        if safety_margin < 20:
            recommendations.append("Увеличить запас финансовой прочности для снижения рисков")
        
        if health_assessment['level'] == 'critical':
            recommendations.append("СРОЧНО: Разработать план финансового оздоровления")
        
        return recommendations[:5]  # Не более 5 рекомендаций

# Глобальный экземпляр анализатора
business_analyzer = BusinessAnalyzer()