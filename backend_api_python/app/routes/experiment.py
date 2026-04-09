"""
Experiment orchestration API routes.
"""

import json
import queue
import threading

from flask import Blueprint, Response, g, jsonify, request

from app.services.experiment.runner import ExperimentRunnerService
from app.utils.auth import login_required
from app.utils.logger import get_logger

logger = get_logger(__name__)

experiment_bp = Blueprint('experiment', __name__)
experiment_runner = ExperimentRunnerService()


@experiment_bp.route('/regime/detect', methods=['POST'])
@login_required
def detect_market_regime():
    """Detect the current market regime for a symbol/timeframe/date range."""
    try:
        payload = request.get_json() or {}
        regime = experiment_runner.detect_regime(payload)
        return jsonify({
            'code': 1,
            'msg': 'success',
            'data': regime,
        })
    except Exception as exc:
        logger.error("detect_market_regime failed", exc_info=True)
        return jsonify({
            'code': 0,
            'msg': str(exc),
            'data': None,
        }), 400


@experiment_bp.route('/pipeline/run', methods=['POST'])
@login_required
def run_experiment_pipeline():
    """Legacy grid-search pipeline (kept for backward compat)."""
    try:
        payload = request.get_json() or {}
        if not payload:
            return jsonify({'code': 0, 'msg': 'Request body is required', 'data': None}), 400

        data = experiment_runner.run_pipeline(
            user_id=int(g.user_id or 1),
            payload=payload,
        )
        return jsonify({'code': 1, 'msg': 'success', 'data': data})
    except Exception as exc:
        logger.error("run_experiment_pipeline failed", exc_info=True)
        return jsonify({'code': 0, 'msg': str(exc), 'data': None}), 400


@experiment_bp.route('/ai-optimize', methods=['POST'])
@login_required
def ai_optimize():
    """
    LLM-driven multi-round optimization pipeline with SSE progress streaming.

    The endpoint returns an SSE stream. Each event is one of:
      - event: progress   (partial update per round)
      - event: done       (final result)
      - event: error      (pipeline failure)
    """
    payload = request.get_json() or {}
    if not payload:
        return jsonify({'code': 0, 'msg': 'Request body is required', 'data': None}), 400

    user_id = int(g.user_id or 1)
    progress_queue: queue.Queue = queue.Queue()

    def on_progress(data):
        progress_queue.put(data)

    def run():
        try:
            result = experiment_runner.run_ai_pipeline(
                user_id=user_id,
                payload=payload,
                on_progress=on_progress,
            )
            progress_queue.put({'event': '__final__', 'data': result})
        except Exception as exc:
            logger.error("ai_optimize pipeline failed", exc_info=True)
            progress_queue.put({'event': '__error__', 'msg': str(exc)})

    worker = threading.Thread(target=run, daemon=True)
    worker.start()

    def generate():
        while True:
            try:
                item = progress_queue.get(timeout=600)
            except queue.Empty:
                yield _sse('error', {'msg': 'Pipeline timeout'})
                break

            if item.get('event') == '__final__':
                yield _sse('done', item['data'])
                break
            elif item.get('event') == '__error__':
                yield _sse('error', {'msg': item.get('msg', 'Unknown error')})
                break
            else:
                yield _sse('progress', item)

    return Response(generate(), mimetype='text/event-stream',
                    headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'})


@experiment_bp.route('/ai-optimize-sync', methods=['POST'])
@login_required
def ai_optimize_sync():
    """Non-streaming version (simpler client integration)."""
    payload = request.get_json() or {}
    if not payload:
        return jsonify({'code': 0, 'msg': 'Request body is required', 'data': None}), 400

    try:
        data = experiment_runner.run_ai_pipeline(
            user_id=int(g.user_id or 1),
            payload=payload,
        )
        return jsonify({'code': 1, 'msg': 'success', 'data': data})
    except Exception as exc:
        logger.error("ai_optimize_sync failed", exc_info=True)
        return jsonify({'code': 0, 'msg': str(exc), 'data': None}), 400


@experiment_bp.route('/structured-tune', methods=['POST'])
@login_required
def structured_tune():
    """
    Grid or random search over explicit parameterSpace (no LLM).
    Same response shape as ai-optimize-sync for IDE compatibility.
    """
    payload = request.get_json() or {}
    if not payload:
        return jsonify({'code': 0, 'msg': 'Request body is required', 'data': None}), 400

    try:
        data = experiment_runner.run_structured_tune(
            user_id=int(g.user_id or 1),
            payload=payload,
        )
        return jsonify({'code': 1, 'msg': 'success', 'data': data})
    except ValueError as exc:
        return jsonify({'code': 0, 'msg': str(exc), 'data': None}), 400
    except Exception as exc:
        logger.error("structured_tune failed", exc_info=True)
        return jsonify({'code': 0, 'msg': str(exc), 'data': None}), 400


@experiment_bp.route('/save-strategy', methods=['POST'])
@login_required
def save_experiment_strategy():
    """Save the best experiment candidate as a strategy record."""
    try:
        payload = request.get_json() or {}
        best_output = payload.get('bestOutput') or payload.get('bestStrategyOutput')
        if not best_output:
            return jsonify({'code': 0, 'msg': 'bestOutput is required', 'data': None}), 400

        strategy_name = (payload.get('strategyName') or '').strip()
        if not strategy_name:
            return jsonify({'code': 0, 'msg': 'strategyName is required', 'data': None}), 400

        market_category = payload.get('marketCategory') or 'Crypto'
        strategy_id = experiment_runner.save_as_strategy(
            user_id=int(g.user_id or 1),
            best_output=best_output,
            strategy_name=strategy_name,
            market_category=market_category,
        )
        return jsonify({
            'code': 1,
            'msg': 'Strategy saved',
            'data': {'strategyId': strategy_id},
        })
    except Exception as exc:
        logger.error("save_experiment_strategy failed", exc_info=True)
        return jsonify({'code': 0, 'msg': str(exc), 'data': None}), 400


def _sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, ensure_ascii=False)}\n\n"
