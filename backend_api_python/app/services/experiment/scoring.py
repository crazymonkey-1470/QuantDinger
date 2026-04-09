"""
Strategy scoring service.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List


class StrategyScoringService:
    """Convert backtest results into comparable multi-factor scores."""

    DEFAULT_WEIGHTS = {
        'return': 0.22,
        'annual_return': 0.12,
        'sharpe': 0.18,
        'profit_factor': 0.14,
        'win_rate': 0.09,
        'drawdown': 0.15,
        'stability': 0.10,
    }

    def score_result(self, result: Dict[str, Any], *, regime: Dict[str, Any] | None = None) -> Dict[str, Any]:
        result = result or {}
        total_return = self._as_float(result.get('totalReturn'))
        annual_return = self._as_float(result.get('annualReturn'))
        max_drawdown = abs(self._as_float(result.get('maxDrawdown')))
        sharpe = self._as_float(result.get('sharpeRatio'))
        profit_factor = self._as_float(result.get('profitFactor'))
        win_rate = self._as_float(result.get('winRate'))
        total_trades = int(self._as_float(result.get('totalTrades')))

        components = {
            'returnScore': self._bounded_score(total_return, floor=-20.0, ceiling=80.0),
            'annualReturnScore': self._bounded_score(annual_return, floor=-20.0, ceiling=120.0),
            'sharpeScore': self._bounded_score(sharpe, floor=-1.0, ceiling=3.0),
            'profitFactorScore': self._bounded_score(profit_factor, floor=0.7, ceiling=2.5),
            'winRateScore': self._bounded_score(win_rate, floor=35.0, ceiling=70.0),
            'drawdownScore': self._inverse_score(max_drawdown, floor=5.0, ceiling=45.0),
            'stabilityScore': self._stability_score(result.get('equityCurve') or []),
            'sampleSizeScore': self._bounded_score(total_trades, floor=5.0, ceiling=80.0),
        }

        regime_fit = 50.0
        if regime:
            regime_fit = self._estimate_regime_fit(regime, components)
            components['regimeFitScore'] = regime_fit

        weighted = (
            components['returnScore'] * self.DEFAULT_WEIGHTS['return'] +
            components['annualReturnScore'] * self.DEFAULT_WEIGHTS['annual_return'] +
            components['sharpeScore'] * self.DEFAULT_WEIGHTS['sharpe'] +
            components['profitFactorScore'] * self.DEFAULT_WEIGHTS['profit_factor'] +
            components['winRateScore'] * self.DEFAULT_WEIGHTS['win_rate'] +
            components['drawdownScore'] * self.DEFAULT_WEIGHTS['drawdown'] +
            components['stabilityScore'] * self.DEFAULT_WEIGHTS['stability']
        )

        if total_trades < 5:
            weighted -= 12.0
        elif total_trades < 12:
            weighted -= 5.0

        overall = max(0.0, min(100.0, weighted * 0.88 + regime_fit * 0.12))

        return {
            'overallScore': round(overall, 2),
            'grade': self._score_grade(overall),
            'components': {key: round(value, 2) for key, value in components.items()},
            'summary': {
                'totalTrades': total_trades,
                'riskAdjustedReturn': round((components['sharpeScore'] + components['drawdownScore']) / 2.0, 2),
                'consistency': round((components['stabilityScore'] + components['winRateScore']) / 2.0, 2),
            },
        }

    def rank_results(self, items: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        ranked = list(items)
        ranked.sort(key=lambda item: float(((item.get('score') or {}).get('overallScore')) or 0.0), reverse=True)
        for idx, item in enumerate(ranked, start=1):
            item['rank'] = idx
        return ranked

    def _estimate_regime_fit(self, regime: Dict[str, Any], components: Dict[str, float]) -> float:
        regime_key = str(regime.get('regime') or '')
        if regime_key in ('bull_trend', 'bear_trend'):
            return min(100.0, components['sharpeScore'] * 0.5 + components['returnScore'] * 0.5)
        if regime_key == 'range_compression':
            return min(100.0, components['winRateScore'] * 0.6 + components['stabilityScore'] * 0.4)
        if regime_key == 'high_volatility':
            return min(100.0, components['drawdownScore'] * 0.6 + components['profitFactorScore'] * 0.4)
        return min(100.0, components['stabilityScore'] * 0.5 + components['sharpeScore'] * 0.5)

    @staticmethod
    def _stability_score(equity_curve: List[Dict[str, Any]]) -> float:
        if len(equity_curve) < 3:
            return 45.0
        values = [float((point or {}).get('value') or 0.0) for point in equity_curve]
        positive_steps = 0
        total_steps = 0
        for prev, curr in zip(values, values[1:]):
            total_steps += 1
            if curr >= prev:
                positive_steps += 1
        monotonicity = positive_steps / max(total_steps, 1)
        return max(0.0, min(100.0, monotonicity * 100.0))

    @staticmethod
    def _bounded_score(value: float, *, floor: float, ceiling: float) -> float:
        if ceiling <= floor:
            return 50.0
        ratio = (value - floor) / (ceiling - floor)
        return max(0.0, min(100.0, ratio * 100.0))

    @staticmethod
    def _inverse_score(value: float, *, floor: float, ceiling: float) -> float:
        if ceiling <= floor:
            return 50.0
        ratio = (value - floor) / (ceiling - floor)
        return max(0.0, min(100.0, (1.0 - ratio) * 100.0))

    @staticmethod
    def _score_grade(score: float) -> str:
        if score >= 85:
            return 'A'
        if score >= 72:
            return 'B'
        if score >= 60:
            return 'C'
        if score >= 45:
            return 'D'
        return 'E'

    @staticmethod
    def _as_float(value: Any) -> float:
        try:
            return float(value or 0.0)
        except Exception:
            return 0.0
