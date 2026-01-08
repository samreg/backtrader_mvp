#!/usr/bin/env python3
"""
Test de création d'un indicateur simple avec primitives
"""
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.indicator_base import IndicatorBase
from core.models import IndicatorResult, RectanglePrimitive, LinePrimitive, PointPrimitive
from visualization.chart_viewer import generate_html_content


class SimpleSignalIndicator(IndicatorBase):
    """Indicateur simple : détecte des zones de support/resistance"""

    def __init__(self, params: dict):
        super().__init__(params)
        self.threshold = params.get('threshold', 50)

    def calculate(self, candles: pd.DataFrame) -> IndicatorResult:
        self.validate_candles(candles)
        result = IndicatorResult()

        # Trouver les plus hauts/bas locaux
        highs = candles['high'].values
        lows = candles['low'].values

        # Zones de resistance (hauts significatifs)
        for i in range(10, len(candles) - 10):
            if highs[i] == max(highs[i - 10:i + 10]):
                # DÉCISION VISUELLE : Resistance = rouge transparent
                zone = RectanglePrimitive(
                    id=f"resistance_{i}",
                    time_start_index=i - 5,
                    time_end_index=i + 20,
                    price_low=highs[i] - 10,
                    price_high=highs[i] + 5,
                    color='#ef5350',
                    alpha=0.2,
                    label=f'R {highs[i]:.0f}'
                )
                result.add_primitive(zone)

                # Ligne horizontale au niveau exact
                line = LinePrimitive(
                    id=f"r_line_{i}",
                    time_start_index=i,
                    time_end_index=min(i + 50, len(candles) - 1),
                    price_start=highs[i],
                    price_end=highs[i],
                    color='#ef5350',
                    width=2,
                    style='dashed',
                    label='RESISTANCE'
                )
                result.add_primitive(line)

                # Point de signal
                point = PointPrimitive(
                    id=f"signal_{i}",
                    time_index=i,
                    price=highs[i] + 15,
                    color='#ef5350',
                    shape='arrow_down',
                    size=8
                )
                result.add_primitive(point)

        # Zones de support (bas significatifs)
        for i in range(10, len(candles) - 10):
            if lows[i] == min(lows[i - 10:i + 10]):
                # DÉCISION VISUELLE : Support = vert transparent
                zone = RectanglePrimitive(
                    id=f"support_{i}",
                    time_start_index=i - 5,
                    time_end_index=i + 20,
                    price_low=lows[i] - 5,
                    price_high=lows[i] + 10,
                    color='#26a69a',
                    alpha=0.2,
                    label=f'S {lows[i]:.0f}'
                )
                result.add_primitive(zone)

                # Ligne horizontale
                line = LinePrimitive(
                    id=f"s_line_{i}",
                    time_start_index=i,
                    time_end_index=min(i + 50, len(candles) - 1),
                    price_start=lows[i],
                    price_end=lows[i],
                    color='#26a69a',
                    width=2,
                    style='dashed',
                    label='SUPPORT'
                )
                result.add_primitive(line)

                # Point de signal
                point = PointPrimitive(
                    id=f"signal_{i}",
                    time_index=i,
                    price=lows[i] - 15,
                    color='#26a69a',
                    shape='arrow_up',
                    size=8
                )
                result.add_primitive(point)

        result.add_meta('total_signals', len(result.primitives))

        return result


# Test
if __name__ == "__main__":
    # Créer données test
    dates = pd.date_range('2024-01-01', periods=200, freq='3min')
    base_price = 25000
    trend = np.linspace(0, 300, 200)
    noise = np.cumsum(np.random.randn(200) * 10)
    prices = base_price + trend + noise

    candles = pd.DataFrame({
        'time': dates,
        'open': prices,
        'high': prices + np.random.rand(200) * 20,
        'low': prices - np.random.rand(200) * 20,
        'close': prices + np.random.randn(200) * 5,
        'volume': np.random.randint(100, 1000, 200)
    })

    # Calculer indicateur
    indicator = SimpleSignalIndicator({'threshold': 50})
    result = indicator.calculate(candles)

    print(f"\n✅ Indicateur calculé")
    print(f"   Primitives générées : {len(result.primitives)}")
    print(f"   Types : {set(type(p).__name__ for p in result.primitives)}")


    # Générer HTML
    def generate_test_html(candles, indicators):
        config = {'data': {'symbol': 'TEST', 'main_timeframe': 'M3'}}
        candles_by_tf = {'M3': candles}
        indicator_results = {}
        indicators_config = []

        for ind in indicators:
            indicator_results[ind['name']] = ind['result']
            indicators_config.append({
                'name': ind['name'],
                'panel': 'main',
                'style': {}
            })

        return generate_html_content(config, candles_by_tf, indicator_results, indicators_config)


    html = generate_test_html(candles, [
        {'name': 'simple_signal', 'result': result, 'config': {'panel': 'main'}}
    ])

    # Sauver
    output = Path('output/test_mon_indicateur.html')
    output.write_text(html, encoding='utf-8')

    print(f"\n✅ HTML généré : {output}")
    print(f"\n🌐 Ouvre {output} dans un navigateur !")