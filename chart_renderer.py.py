import json
from datetime import datetime, timedelta
import math

class ChartRenderer:
    def __init__(self):
        self.chart_colors = {
            'revenue': {'border': '#48bb78', 'background': 'rgba(72, 187, 120, 0.1)'},
            'expenses': {'border': '#f56565', 'background': 'rgba(245, 101, 101, 0.1)'},
            'profit': {'border': '#4299e1', 'background': 'rgba(66, 153, 225, 0.1)'}
        }
    
    def generate_chart_config(self, data, is_mobile=False, is_fullscreen=False):
        """Генерация конфигурации для Chart.js"""
        if not data or not data.get('dates'):
            return self._get_empty_chart_config()
        
        chart_config = {
            'type': 'line',
            'data': {
                'labels': data['dates'],
                'datasets': self._generate_datasets(data, is_mobile, is_fullscreen)
            },
            'options': self._generate_chart_options(is_mobile, is_fullscreen)
        }
        
        return chart_config
    
    def _generate_datasets(self, data, is_mobile, is_fullscreen):
        """Генерация datasets для графика"""
        datasets = []
        
        datasets_config = [
            ('revenue', 'Выручка', data.get('revenue', [])),
            ('expenses', 'Расходы', data.get('expenses', [])),
            ('profit', 'Прибыль', data.get('profit', []))
        ]
        
        for key, label, values in datasets_config:
            border_width = 3
            point_radius = 4
            point_hover_radius = 6
            
            if is_mobile:
                border_width = 2
                point_radius = 3
                point_hover_radius = 5
            
            if is_fullscreen:
                border_width = 4
                point_radius = 5
                point_hover_radius = 8
            
            datasets.append({
                'label': label,
                'data': values,
                'borderColor': self.chart_colors[key]['border'],
                'backgroundColor': self.chart_colors[key]['background'],
                'borderWidth': border_width,
                'tension': 0.4,
                'fill': True,
                'pointRadius': point_radius,
                'pointHoverRadius': point_hover_radius,
                'pointBorderWidth': 2
            })
        
        return datasets
    
    def _generate_chart_options(self, is_mobile, is_fullscreen):
        """Генерация опций для Chart.js"""
        font_sizes = self._get_font_sizes(is_mobile, is_fullscreen)
        
        options = {
            'responsive': False,
            'maintainAspectRatio': False,
            'plugins': {
                'legend': {
                    'position': 'top',
                    'labels': {
                        'boxWidth': 15,
                        'font': {
                            'size': font_sizes['legend']
                        },
                        'padding': 20,
                        'usePointStyle': True
                    }
                },
                'title': {
                    'display': True,
                    'text': 'Финансовая динамика' + (' - Полноэкранный режим' if is_fullscreen else ''),
                    'font': {
                        'size': font_sizes['title']
                    },
                    'padding': 20
                },
                'tooltip': {
                    'bodyFont': {
                        'size': font_sizes['tooltip_body']
                    },
                    'titleFont': {
                        'size': font_sizes['tooltip_title']
                    },
                    'padding': 12,
                    'backgroundColor': 'rgba(26, 32, 44, 0.95)',
                    'titleColor': '#fff',
                    'bodyColor': '#fff',
                    'borderColor': '#d400ff',
                    'borderWidth': 1
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': True,
                    'ticks': {
                        'callback': 'function(value) { return window.formatChartCurrency(value); }',
                        'font': {
                            'size': font_sizes['y_ticks']
                        },
                        'padding': 10
                    },
                    'grid': {
                        'color': 'rgba(255,255,255,0.1)'
                    },
                    'title': {
                        'display': True,
                        'text': 'Сумма (руб)',
                        'font': {
                            'size': font_sizes['axis_title']
                        }
                    }
                },
                'x': {
                    'ticks': {
                        'font': {
                            'size': font_sizes['x_ticks']
                        },
                        'maxTicksLimit': 20,
                        'padding': 10
                    },
                    'grid': {
                        'color': 'rgba(255,255,255,0.1)'
                    },
                    'title': {
                        'display': True,
                        'text': 'Дата',
                        'font': {
                            'size': font_sizes['axis_title']
                        }
                    }
                }
            },
            'interaction': {
                'intersect': False,
                'mode': 'index'
            },
            'elements': {
                'point': {
                    'radius': font_sizes['point_radius'],
                    'hoverRadius': font_sizes['point_hover_radius']
                }
            },
            'layout': {
                'padding': {
                    'left': 20,
                    'right': 20,
                    'top': 20,
                    'bottom': 20
                }
            }
        }
        
        return options
    
    def _get_font_sizes(self, is_mobile, is_fullscreen):
        """Получение размеров шрифтов в зависимости от платформы"""
        if is_fullscreen:
            return {
                'legend': 16, 'title': 20, 'tooltip_body': 14, 'tooltip_title': 16,
                'y_ticks': 14, 'x_ticks': 12, 'axis_title': 16,
                'point_radius': 4, 'point_hover_radius': 8
            }
        elif is_mobile:
            return {
                'legend': 12, 'title': 16, 'tooltip_body': 12, 'tooltip_title': 13,
                'y_ticks': 11, 'x_ticks': 10, 'axis_title': 12,
                'point_radius': 3, 'point_hover_radius': 5
            }
        else:
            return {
                'legend': 14, 'title': 18, 'tooltip_body': 14, 'tooltip_title': 15,
                'y_ticks': 13, 'x_ticks': 12, 'axis_title': 14,
                'point_radius': 4, 'point_hover_radius': 6
            }
    
    def _get_empty_chart_config(self):
        """Конфигурация для пустого графика"""
        return {
            'type': 'line',
            'data': {
                'labels': [],
                'datasets': []
            },
            'options': {
                'responsive': False,
                'maintainAspectRatio': False,
                'plugins': {
                    'title': {
                        'display': True,
                        'text': 'Нет данных для отображения'
                    }
                }
            }
        }
    
    def calculate_chart_dimensions(self, data_points_count):
        """Расчет размеров графика на основе количества точек данных"""
        min_width = 600
        point_width = 50
        calculated_width = max(min_width, data_points_count * point_width)
        
        return {
            'width': calculated_width,
            'height': 300
        }

# Инициализируем рендерер
chart_renderer = ChartRenderer()