"""
Strategy evolution helpers.
"""

from __future__ import annotations

import copy
import itertools
import random
from typing import Any, Dict, List


class StrategyEvolutionService:
    """Generate strategy variants from structured parameter spaces."""

    def build_variants(
        self,
        *,
        base_snapshot: Dict[str, Any],
        parameter_space: Dict[str, Any] | None = None,
        max_variants: int = 12,
        method: str = 'grid',
    ) -> List[Dict[str, Any]]:
        if not parameter_space:
            return []

        normalized_space = {
            self._normalize_key(path): self._resolve_values(spec)
            for path, spec in parameter_space.items()
            if self._resolve_values(spec)
        }
        if not normalized_space:
            return []

        if method == 'random':
            return self._random_variants(base_snapshot, normalized_space, max_variants=max_variants)
        return self._grid_variants(base_snapshot, normalized_space, max_variants=max_variants)

    def _grid_variants(
        self,
        base_snapshot: Dict[str, Any],
        normalized_space: Dict[str, List[Any]],
        *,
        max_variants: int,
    ) -> List[Dict[str, Any]]:
        keys = list(normalized_space.keys())
        variants: List[Dict[str, Any]] = []
        for idx, values in enumerate(itertools.product(*(normalized_space[key] for key in keys)), start=1):
            snapshot = copy.deepcopy(base_snapshot)
            overrides = {}
            for key, value in zip(keys, values):
                self._set_nested(snapshot, key.split('.'), value)
                overrides[key] = value
            variants.append({
                'name': f'variant_{idx}',
                'snapshot': snapshot,
                'overrides': overrides,
                'source': 'evolution_grid',
            })
            if len(variants) >= max_variants:
                break
        return variants

    def _random_variants(
        self,
        base_snapshot: Dict[str, Any],
        normalized_space: Dict[str, List[Any]],
        *,
        max_variants: int,
    ) -> List[Dict[str, Any]]:
        keys = list(normalized_space.keys())
        variants: List[Dict[str, Any]] = []
        for idx in range(1, max_variants + 1):
            snapshot = copy.deepcopy(base_snapshot)
            overrides = {}
            for key in keys:
                value = random.choice(normalized_space[key])
                self._set_nested(snapshot, key.split('.'), value)
                overrides[key] = value
            variants.append({
                'name': f'variant_{idx}',
                'snapshot': snapshot,
                'overrides': overrides,
                'source': 'evolution_random',
            })
        return variants

    @staticmethod
    def _resolve_values(spec: Any) -> List[Any]:
        if isinstance(spec, list):
            return spec
        if isinstance(spec, tuple):
            return list(spec)
        if isinstance(spec, dict):
            minimum = spec.get('min')
            maximum = spec.get('max')
            step = spec.get('step', 1)
            if minimum is None or maximum is None:
                return []
            values: List[Any] = []
            cursor = minimum
            if step == 0:
                return [minimum]
            while cursor <= maximum:
                values.append(round(cursor, 10) if isinstance(cursor, float) else cursor)
                cursor += step
            return values
        return [spec]

    @staticmethod
    def _normalize_key(path: str) -> str:
        path = str(path or '').strip()
        return path.replace('strategyConfig.', 'strategy_config.')

    @staticmethod
    def _set_nested(target: Dict[str, Any], parts: List[str], value: Any) -> None:
        cursor = target
        for part in parts[:-1]:
            if part not in cursor or not isinstance(cursor[part], dict):
                cursor[part] = {}
            cursor = cursor[part]
        cursor[parts[-1]] = value
