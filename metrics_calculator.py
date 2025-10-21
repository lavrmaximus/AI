import logging
from typing import Dict, List, Optional
from datetime import datetime
import math

logger = logging.getLogger(__name__)

class MetricsCalculator:
    """
    Калькулятор 22 финансовых метрик и Business Health Score
    """
    
    def __init__(self):
        self.industry_benchmarks = {
            'retail': {
                'profit_margin': 15.0,
                'ltv_cac_ratio': 3.0,
                'roi': 25.0
            },
            'service': {
                'profit_margin': 20.0,
                'ltv_cac_ratio': 4.0,
                'roi': 30.0
            },
            'ecommerce': {
                'profit_margin': 10.0,
                'ltv_cac_ratio': 2.5,
                'roi': 20.0
            },
            'manufacturing': {
                'profit_margin': 12.0,
                'ltv_cac_ratio': 2.8,
                'roi': 22.0
            },
            'other': {
                'profit_margin': 15.0,
                'ltv_cac_ratio': 3.0,
                'roi': 25.0
            }
        }
    
    def calculate_all_metrics(self, raw_data: Dict, previous_data: Dict = None) -> Dict:
        """
        Расчет всех 22 метрик на основе сырых данных
        """
        try:
            metrics = {}
            
            # 1. Базовые финансовые метрики
            metrics.update(self._calculate_financial_metrics(raw_data))
            
            # 2. Клиентские метрики
            metrics.update(self._calculate_customer_metrics(raw_data))
            
            # 3. Метрики роста и эффективности
            metrics.update(self._calculate_growth_metrics(raw_data, previous_data))
            
            # 4. Health Score
<<<<<<< HEAD
            metrics.update(self._calculate_health_scores(metrics))
=======
            metrics.update(self._calculate_health_scores(metrics, raw_data.get('industry', 'other')))
>>>>>>> af05edb342387241e2637791569c0d066bd31b10
            
            logger.info(f"✅ Рассчитано {len(metrics)} метрик")
            return metrics
            
        except Exception as e:
            logger.error(f"❌ Ошибка расчета метрик: {e}")
            return {}
    
    def _calculate_financial_metrics(self, data: Dict) -> Dict:
        """Финансовые метрики"""
        metrics = {}
        
        try:
            revenue = data.get('revenue', 0)
            expenses = data.get('expenses', 0)
<<<<<<< HEAD
            # Прибыль всегда рассчитывается как выручка минус расходы
            profit = revenue - expenses
            investments = data.get('investments', 0)
            marketing_costs = data.get('marketing_costs', 0)
            clients = data.get('clients', 0)
            
            # Рассчитываем средний чек автоматически
            average_check = revenue / clients if clients > 0 else 0
=======
            profit = data.get('profit', 0) or (revenue - expenses)
            investments = data.get('investments', 0)
            marketing_costs = data.get('marketing_costs', 0)
            average_check = data.get('average_check', 0)
>>>>>>> af05edb342387241e2637791569c0d066bd31b10
            
            # 1. Рентабельность продаж
            if revenue > 0:
                metrics['profit_margin'] = (profit / revenue) * 100
            else:
                metrics['profit_margin'] = 0
            
            # 2. Точка безубыточности (в клиентах)
            if average_check > 0 and expenses > 0:
                metrics['break_even_clients'] = expenses / average_check
            else:
                metrics['break_even_clients'] = 0
            
            # 3. Запас финансовой прочности
            if revenue > 0 and metrics['break_even_clients'] > 0:
                break_even_revenue = metrics['break_even_clients'] * average_check
                metrics['safety_margin'] = ((revenue - break_even_revenue) / revenue) * 100
            else:
                metrics['safety_margin'] = 0
            
            # 4. ROI (Return on Investment)
            if investments > 0:
                metrics['roi'] = ((profit - investments) / investments) * 100
            else:
                metrics['roi'] = 0
            
            # 5. Индекс прибыльности
            if investments > 0:
                annual_profit = profit * 12
                metrics['profitability_index'] = annual_profit / investments
            else:
                metrics['profitability_index'] = 0
            
            # 6. Рентабельность активов (упрощенная)
            total_assets = investments + revenue * 0.5  # примерная оценка
            if total_assets > 0:
                metrics['roe'] = (profit / total_assets) * 100
            else:
                metrics['roe'] = 0
            
            # 7. До банкротства (месяцев)
            monthly_loss = expenses - revenue
            if monthly_loss > 0 and investments > 0:
                metrics['months_to_bankruptcy'] = investments / monthly_loss
            else:
                metrics['months_to_bankruptcy'] = 999  # неограниченно
            
<<<<<<< HEAD
            # Добавляем рассчитанный средний чек в метрики
            metrics['average_check'] = average_check
            
=======
>>>>>>> af05edb342387241e2637791569c0d066bd31b10
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка финансовых метрик: {e}")
            return {}
    
    def _calculate_customer_metrics(self, data: Dict) -> Dict:
        """Клиентские метрики"""
        metrics = {}
        
        try:
            revenue = data.get('revenue', 0)
            clients = data.get('clients', 0)
            marketing_costs = data.get('marketing_costs', 0)
            new_clients = data.get('new_clients', clients * 0.3)  # оценка если нет данных
            average_check = data.get('average_check', 0)
            profit = data.get('profit', 0)
            
            # 8. LTV (Lifetime Value)
            if clients > 0:
                metrics['ltv'] = revenue / clients
            else:
                metrics['ltv'] = 0
            
            # 9. CAC (Customer Acquisition Cost)
            if new_clients > 0:
                metrics['cac'] = marketing_costs / new_clients
            else:
                metrics['cac'] = 0
            
            # 10. LTV/CAC Ratio
            if metrics['cac'] > 0:
                metrics['ltv_cac_ratio'] = metrics['ltv'] / metrics['cac']
            else:
                metrics['ltv_cac_ratio'] = 0
            
            # 11. Маржа на клиента
            if clients > 0:
                metrics['customer_profit_margin'] = profit / clients
            else:
                metrics['customer_profit_margin'] = 0
            
            # 12. Оборачиваемость активов (упрощенная)
            total_assets = data.get('investments', 0) + revenue * 0.5
            if total_assets > 0:
                metrics['asset_turnover'] = revenue / total_assets
            else:
                metrics['asset_turnover'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка клиентских метрик: {e}")
            return {}
    
    def _calculate_growth_metrics(self, data: Dict, previous_data: Dict = None) -> Dict:
        """Метрики роста и эффективности"""
        metrics = {}
        
        try:
            revenue = data.get('revenue', 0)
            profit = data.get('profit', 0)
            investments = data.get('investments', 0)
            
            # 13. SGR (Sustainable Growth Rate)
            if investments > 0 and profit > 0:
                retention_ratio = 0.6  # 60% реинвестиций
                metrics['sgr'] = (profit / investments) * 100 * retention_ratio
            else:
                metrics['sgr'] = 0
            
            # 14. Темп роста выручки
            if previous_data and previous_data.get('revenue', 0) > 0:
                previous_revenue = previous_data['revenue']
                metrics['revenue_growth_rate'] = ((revenue - previous_revenue) / previous_revenue) * 100
            else:
                metrics['revenue_growth_rate'] = 0
            
            return metrics
            
        except Exception as e:
            logger.error(f"Ошибка метрик роста: {e}")
            return {}
    
<<<<<<< HEAD
    def _calculate_health_scores(self, metrics: Dict) -> Dict:
        """Расчет Health Score по 100-балльной шкале"""
        
        benchmark = self.industry_benchmarks['other']  # Используем общий бенчмарк
=======
    def _calculate_health_scores(self, metrics: Dict, industry: str = 'other') -> Dict:
        """Расчет Health Score по 100-балльной шкале"""
        
        benchmark = self.industry_benchmarks.get(industry, self.industry_benchmarks['other'])
>>>>>>> af05edb342387241e2637791569c0d066bd31b10
        
        # 15-17. Компоненты Health Score
        financial_score = self._calculate_financial_health_score(metrics, benchmark)
        growth_score = self._calculate_growth_health_score(metrics, benchmark)
        efficiency_score = self._calculate_efficiency_health_score(metrics, benchmark)
        
        # 18. Общий Health Score
        overall_score = int((financial_score + growth_score + efficiency_score) / 3)
        
        return {
            'financial_health_score': financial_score,
            'growth_health_score': growth_score,
            'efficiency_health_score': efficiency_score,
            'overall_health_score': overall_score
        }
    
    def _calculate_financial_health_score(self, metrics: Dict, benchmark: Dict) -> int:
        """Здоровье финансов (0-100 баллов)"""
        score = 0
        
        # Рентабельность (макс 40 баллов)
        profit_margin = metrics.get('profit_margin', 0)
        target_margin = benchmark.get('profit_margin', 15)
        margin_score = min(40, (profit_margin / target_margin) * 40) if target_margin > 0 else 0
        score += margin_score
        
        # Запас прочности (макс 30 баллов)
        safety_margin = metrics.get('safety_margin', 0)
        if safety_margin > 30:
            score += 30
        elif safety_margin > 20:
            score += 20
        elif safety_margin > 10:
            score += 10
        elif safety_margin > 0:
            score += 5
        
        # До банкротства (макс 30 баллов)
        months_to_bankruptcy = metrics.get('months_to_bankruptcy', 999)
        if months_to_bankruptcy > 12:
            score += 30
        elif months_to_bankruptcy > 6:
            score += 20
        elif months_to_bankruptcy > 3:
            score += 10
        elif months_to_bankruptcy > 0:
            score += 5
        
        return min(100, int(score))
    
    def _calculate_growth_health_score(self, metrics: Dict, benchmark: Dict) -> int:
        """Здоровье роста (0-100 баллов)"""
        score = 0
        
        # ROI (макс 40 баллов)
        roi = metrics.get('roi', 0)
        target_roi = benchmark.get('roi', 25)
        roi_score = min(40, (roi / target_roi) * 40) if target_roi > 0 else 0
        score += roi_score
        
        # Темп роста (макс 30 баллов)
        growth_rate = metrics.get('revenue_growth_rate', 0)
        if growth_rate > 20:
            score += 30
        elif growth_rate > 10:
            score += 20
        elif growth_rate > 5:
            score += 15
        elif growth_rate > 0:
            score += 10
        
        # SGR (макс 30 баллов)
        sgr = metrics.get('sgr', 0)
        if sgr > 15:
            score += 30
        elif sgr > 10:
            score += 20
        elif sgr > 5:
            score += 10
        
        return min(100, int(score))
    
    def _calculate_efficiency_health_score(self, metrics: Dict, benchmark: Dict) -> int:
        """Эффективность операций (0-100 баллов)"""
        score = 0
        
        # LTV/CAC Ratio (макс 50 баллов)
        ltv_cac_ratio = metrics.get('ltv_cac_ratio', 0)
        target_ratio = benchmark.get('ltv_cac_ratio', 3.0)
        
        if ltv_cac_ratio > target_ratio * 1.5:
            score += 50
        elif ltv_cac_ratio > target_ratio:
            score += 40
        elif ltv_cac_ratio > target_ratio * 0.7:
            score += 30
        elif ltv_cac_ratio > target_ratio * 0.5:
            score += 20
        elif ltv_cac_ratio > 1.0:
            score += 10
        
        # Оборачиваемость активов (макс 30 баллов)
        asset_turnover = metrics.get('asset_turnover', 0)
        if asset_turnover > 2.0:
            score += 30
        elif asset_turnover > 1.5:
            score += 20
        elif asset_turnover > 1.0:
            score += 15
        elif asset_turnover > 0.5:
            score += 10
        
        # Индекс прибыльности (макс 20 баллов)
        profitability_index = metrics.get('profitability_index', 0)
        if profitability_index > 2.0:
            score += 20
        elif profitability_index > 1.5:
            score += 15
        elif profitability_index > 1.0:
            score += 10
        elif profitability_index > 0.5:
            score += 5
        
        return min(100, int(score))
    
    def get_health_assessment(self, health_score: int) -> Dict:
        """Оценка здоровья бизнеса по баллам"""
        if health_score >= 90:
            return {
                'level': 'excellent',
                'emoji': '🟢',
                'message': 'Отличное состояние! Масштабируйтесь!',
                'color': 'green'
            }
        elif health_score >= 70:
            return {
                'level': 'good', 
                'emoji': '🟡',
                'message': 'Хорошее состояние. Есть куда расти!',
                'color': 'yellow'
            }
        elif health_score >= 50:
            return {
                'level': 'stable',
                'emoji': '🟠', 
                'message': 'Стабильно. Наблюдайте за рисками.',
                'color': 'orange'
            }
        else:
            return {
                'level': 'critical',
                'emoji': '🔴',
                'message': 'Требуются срочные действия!',
                'color': 'red'
            }
    
<<<<<<< HEAD
    def generate_benchmark_report(self, metrics: Dict) -> Dict:
        """Сравнение с бенчмарками индустрии"""
        benchmark = self.industry_benchmarks['other']  # Используем общий бенчмарк
        
        report = {
            'industry': 'other',  # Всегда используем общий бенчмарк
=======
    def generate_benchmark_report(self, metrics: Dict, industry: str = 'other') -> Dict:
        """Сравнение с бенчмарками индустрии"""
        benchmark = self.industry_benchmarks.get(industry, self.industry_benchmarks['other'])
        
        report = {
            'industry': industry,
>>>>>>> af05edb342387241e2637791569c0d066bd31b10
            'comparisons': []
        }
        
        # Сравнение ключевых метрик
        key_metrics = ['profit_margin', 'roi', 'ltv_cac_ratio']
        
        for metric in key_metrics:
            actual = metrics.get(metric, 0)
            target = benchmark.get(metric, 0)
            
            if target > 0:
                percentage = (actual / target) * 100
                status = 'above' if percentage >= 100 else 'below'
            else:
                percentage = 0
                status = 'no_benchmark'
            
            report['comparisons'].append({
                'metric': metric,
                'actual': actual,
                'benchmark': target,
                'percentage': percentage,
                'status': status
            })
        
        return report

# Глобальный экземпляр калькулятора
metrics_calculator = MetricsCalculator()