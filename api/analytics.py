"""
API endpoints for predictive analytics dashboard
"""

from flask import Blueprint, jsonify, request, render_template
from datetime import datetime, timedelta
import logging
from core.predictive_analytics import analytics_engine
from core.db import Miner, Metric, SessionLocal
from sqlalchemy import func, and_

logger = logging.getLogger(__name__)

analytics_bp = Blueprint('analytics', __name__)


@analytics_bp.route('/fleet-summary', methods=['GET'])
def get_fleet_analytics_summary():
    """Get comprehensive fleet analytics summary"""
    try:
        summary = analytics_engine.get_fleet_analytics_summary()
        return jsonify({
            'ok': True,
            'data': summary,
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting fleet analytics summary: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/miner-risk/<miner_id>', methods=['GET'])
def get_miner_risk_assessment(miner_id):
    """Get failure risk assessment for a specific miner"""
    try:
        # Verify miner exists (miner_id can be IP or integer ID)
        with SessionLocal() as session:
            # Try to get by IP first, then by ID
            miner = session.query(Miner).filter(Miner.miner_ip == miner_id).first()
            if not miner:
                # Try by integer ID
                try:
                    miner = session.get(Miner, int(miner_id))
                except (ValueError, TypeError):
                    pass

            if not miner:
                return jsonify({
                    'ok': False,
                    'error': 'Miner not found'
                }), 404

            miner_ip = miner.miner_ip

        assessment = analytics_engine.predict_miner_failure_risk(miner_ip)

        return jsonify({
            'ok': True,
            'data': {
                'miner_id': assessment.miner_id,
                'risk_score': assessment.risk_score,
                'risk_level': assessment.risk_level,
                'predicted_failure_date': assessment.predicted_failure_date.isoformat() if assessment.predicted_failure_date else None,
                'contributing_factors': assessment.contributing_factors,
                'recommendations': assessment.recommendations
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting risk assessment for miner {miner_id}: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/btc-forecast', methods=['GET'])
def get_btc_price_forecast():
    """Get BTC price forecast"""
    try:
        days = request.args.get('days', 7, type=int)
        days = min(max(1, days), 30)  # Limit to 1-30 days

        forecasts = analytics_engine.forecast_btc_price(days_ahead=days)

        forecast_data = []
        for forecast in forecasts:
            forecast_data.append({
                'date': forecast.forecast_date.isoformat(),
                'predicted_price': forecast.predicted_price,
                'confidence_lower': forecast.confidence_interval_lower,
                'confidence_upper': forecast.confidence_interval_upper,
                'trend': forecast.trend
            })

        return jsonify({
            'ok': True,
            'data': {
                'forecasts': forecast_data,
                'days_ahead': days
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting BTC price forecast: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/high-risk-miners', methods=['GET'])
def get_high_risk_miners():
    """Get list of miners with high failure risk"""
    try:
        high_risk_miners = []

        # Get all miners using session
        with SessionLocal() as session:
            miners = session.query(Miner).all()

            for miner in miners:
                assessment = analytics_engine.predict_miner_failure_risk(miner.miner_ip)
                if assessment.risk_level in ['HIGH', 'CRITICAL']:
                    high_risk_miners.append({
                        'miner_id': miner.miner_ip,
                        'miner_name': miner.hostname or miner.miner_ip,
                        'model': miner.model,
                        'risk_score': assessment.risk_score,
                        'risk_level': assessment.risk_level,
                        'predicted_failure_date': assessment.predicted_failure_date.isoformat() if assessment.predicted_failure_date else None,
                        'contributing_factors': assessment.contributing_factors,
                        'recommendations': assessment.recommendations
                    })

        # Sort by risk score (highest first)
        high_risk_miners.sort(key=lambda x: x['risk_score'], reverse=True)

        return jsonify({
            'ok': True,
            'data': {
                'high_risk_miners': high_risk_miners,
                'count': len(high_risk_miners)
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting high risk miners: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/fleet-health-trend', methods=['GET'])
def get_fleet_health_trend():
    """Get fleet health trend over time"""
    try:
        days = request.args.get('days', 30, type=int)
        days = min(max(7, days), 90)  # Limit to 7-90 days

        # For now, we'll calculate current health and simulate trend
        # In a real implementation, you'd store historical health scores
        with SessionLocal() as session:
            # Note: Miner model doesn't have a 'status' field, getting all miners instead
            miners = session.query(Miner).all()

        health_data = []
        current_date = datetime.utcnow()

        # Calculate current fleet health
        total_risk = 0
        active_miners = 0

        for miner in miners:
            try:
                assessment = analytics_engine.predict_miner_failure_risk(miner.miner_ip)
                total_risk += assessment.risk_score
                active_miners += 1
            except:
                continue

        current_health = max(0, 100 - (total_risk / max(1, active_miners) * 100)) if active_miners > 0 else 100

        # Simulate historical trend (in production, use actual historical data)
        for i in range(days):
            date = current_date - timedelta(days=days - i - 1)
            # Add some variation to simulate trend
            variation = (i - days / 2) * 0.5  # Slight trend
            noise = (hash(date.strftime('%Y%m%d')) % 10 - 5) * 0.5  # Random variation
            health_score = int(round(max(0, min(100, current_health + variation + noise))))

            health_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'health_score': round(health_score, 1),
                'active_miners': active_miners
            })

        return jsonify({
            'ok': True,
            'data': {
                'health_trend': health_data,
                'current_health': round(current_health, 1),
                'days': days
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting fleet health trend: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/maintenance-schedule', methods=['GET'])
def get_maintenance_schedule():
    """Get recommended maintenance schedule based on risk assessments"""
    try:
        with SessionLocal() as session:
            # Note: Miner model doesn't have a 'status' field, getting all miners instead
            miners = session.query(Miner).all()
        maintenance_schedule = []

        for miner in miners:
            assessment = analytics_engine.predict_miner_failure_risk(miner.miner_ip)

            # Only include miners that need attention
            if assessment.risk_level in ['MEDIUM', 'HIGH', 'CRITICAL']:
                priority = 1 if assessment.risk_level == 'CRITICAL' else (2 if assessment.risk_level == 'HIGH' else 3)

                # Calculate recommended maintenance date
                if assessment.predicted_failure_date:
                    # Schedule maintenance before predicted failure
                    maintenance_date = assessment.predicted_failure_date - timedelta(days=7)
                else:
                    # Schedule based on risk level
                    days_ahead = 3 if assessment.risk_level == 'CRITICAL' else (
                        7 if assessment.risk_level == 'HIGH' else 14)
                    maintenance_date = datetime.utcnow() + timedelta(days=days_ahead)

                maintenance_schedule.append({
                    'miner_id': miner.miner_ip,
                    'miner_name': miner.hostname or miner.miner_ip,  # Use hostname or IP as name
                    'model': miner.model,
                    'risk_level': assessment.risk_level,
                    'risk_score': assessment.risk_score,
                    'maintenance_date': maintenance_date.isoformat(),
                    'priority': priority,
                    'estimated_duration': '2-4 hours',  # Default estimate
                    'recommended_actions': assessment.recommendations,
                    'urgency': 'URGENT' if assessment.risk_level == 'CRITICAL' else 'HIGH' if assessment.risk_level == 'HIGH' else 'MEDIUM'
                })

        # Sort by priority and then by maintenance date
        maintenance_schedule.sort(key=lambda x: (x['priority'], x['maintenance_date']))

        return jsonify({
            'ok': True,
            'data': {
                'maintenance_schedule': maintenance_schedule,
                'total_items': len(maintenance_schedule),
                'urgent_items': len([item for item in maintenance_schedule if item['urgency'] == 'URGENT'])
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting maintenance schedule: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/train-models', methods=['POST'])
def train_models():
    """Trigger model training/retraining"""
    try:
        retrain = request.json.get('retrain', False) if request.json else False

        # Train failure prediction model
        analytics_engine.train_failure_prediction_model(retrain=retrain)

        # Train BTC forecast model
        analytics_engine.train_btc_forecast_model(retrain=retrain)

        return jsonify({
            'ok': True,
            'message': 'Models trained successfully',
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error training models: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


@analytics_bp.route('/model-status', methods=['GET'])
def get_model_status():
    """Get status of trained models"""
    try:
        import os
        models_dir = "models"

        model_files = {
            'failure_prediction': 'failure_prediction_model.joblib',
            'btc_forecast': 'btc_forecast_model.joblib',
            'scaler': 'scaler.joblib',
            'anomaly_detector': 'anomaly_detector.joblib'
        }

        model_status = {}
        for model_name, filename in model_files.items():
            filepath = os.path.join(models_dir, filename)
            if os.path.exists(filepath):
                stat = os.stat(filepath)
                model_status[model_name] = {
                    'exists': True,
                    'size_bytes': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
            else:
                model_status[model_name] = {
                    'exists': False,
                    'size_bytes': 0,
                    'last_modified': None
                }

        return jsonify({
            'ok': True,
            'data': {
                'models': model_status,
                'analytics_engine_loaded': {
                    'failure_model': analytics_engine.failure_model is not None,
                    'btc_model': analytics_engine.btc_model is not None,
                    'anomaly_detector': analytics_engine.anomaly_detector is not None
                }
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting model status: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


# ============================================================================
# HTML PAGE ROUTE
# ============================================================================

@analytics_bp.route('/page', methods=['GET'])
def analytics_page():
    """Render the predictive analytics dashboard HTML page."""
    return render_template('analytics.html')
