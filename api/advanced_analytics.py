"""
Advanced Analytics API Endpoints

This module provides API endpoints for advanced analytics features including:
- LSTM-based failure prediction
- Real-time anomaly detection
- Model training and management
"""

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
from core.advanced_analytics import advanced_analytics_engine
from core.db import SessionLocal, Miner, Metric as MinerMetrics, ProfitabilitySnapshot

logger = logging.getLogger(__name__)
advanced_bp = Blueprint('advanced_analytics', __name__)


def get_training_parameters(request_data, defaults):
    """Extract and validate training parameters from request"""
    try:
        if request.is_json:
            params = request_data.get_json()
        else:
            params = request_data.form.to_dict()

        return {
            'epochs': int(params.get('epochs', defaults.get('epochs', 50))),
            'batch_size': int(params.get('batch_size', defaults.get('batch_size', 32))),
            'validation_split': float(params.get('validation_split', defaults.get('validation_split', 0.2)))
        }
    except (ValueError, TypeError) as e:
        raise ValueError(f'Invalid parameter format: {str(e)}')


def get_miner_metrics_data(session, miner, days=90):
    """Get and process metrics data for a miner"""
    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get metrics and profit data
    metrics = (session.query(MinerMetrics)
               .filter(MinerMetrics.miner_ip == miner.miner_ip)
               .filter(MinerMetrics.timestamp >= cutoff)
               .order_by(MinerMetrics.timestamp).all())

    if not metrics:
        return None

    profit_data = (session.query(ProfitabilitySnapshot)
                   .filter(ProfitabilitySnapshot.miner_ip == miner.miner_ip)
                   .filter(ProfitabilitySnapshot.timestamp >= cutoff)
                   .order_by(ProfitabilitySnapshot.timestamp).all())

    # Process metrics with profit data
    metrics_data = []
    for m in metrics:
        profit_match = next((p for p in profit_data
                             if p.timestamp.date() == m.timestamp.date()), None)

        rejection_rate = 0.0
        if (profit_match and hasattr(profit_match, 'shares_rejected') and
                hasattr(profit_match, 'shares_accepted')):
            total = profit_match.shares_accepted + profit_match.shares_rejected
            rejection_rate = profit_match.shares_rejected / total if total > 0 else 0.0

        metrics_data.append({
            'timestamp': m.timestamp,
            'hashrate': m.hashrate_ths,
            'temperature': m.avg_temp_c,
            'fan_speed': m.avg_fan_rpm,
            'power_consumption': m.power_w,
            'rejection_rate': rejection_rate,
            'efficiency': m.hashrate_ths / (m.power_w + 1e-6) if m.power_w and m.power_w > 0 else 0.0,
        })

    df = pd.DataFrame(metrics_data)
    if len(df) < advanced_analytics_engine.sequence_length + 1:
        return None

    # Calculate derived features
    df['temperature_trend'] = df['temperature'].diff().rolling(window=min(5, len(df))).mean()
    df['hashrate_stability'] = df['hashrate'].rolling(window=min(10, len(df))).std()
    df['power_efficiency_trend'] = df['efficiency'].diff().rolling(window=min(5, len(df))).mean()

    # Drop rows with NaN values
    df = df.dropna()

    if len(df) < advanced_analytics_engine.sequence_length + 1:
        return None

    return df


@advanced_bp.route('/train/lstm', methods=['POST'])
def train_lstm_model():
    """Train the LSTM failure prediction model"""
    try:
        # Get parameters
        try:
            params = get_training_parameters(request, {
                'epochs': 50,
                'batch_size': 32,
                'validation_split': 0.2
            })
        except ValueError as e:
            return jsonify({
                'ok': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        with SessionLocal() as session:
            miners = session.query(Miner).all()
            all_features = []
            all_targets = []

            for miner in miners:
                df = get_miner_metrics_data(session, miner, days=90)
                if df is None:
                    continue

                # Create target variable (failure risk)
                df['failure_risk'] = 0.0
                df.loc[df['temperature'] > 80, 'failure_risk'] += 0.3
                df.loc[df['rejection_rate'] > 0.05, 'failure_risk'] += 0.2
                df.loc[df['hashrate'] < df['hashrate'].quantile(0.2), 'failure_risk'] += 0.3
                df['failure_risk'] = df['failure_risk'].clip(0, 1)

                all_features.append(df[advanced_analytics_engine.feature_columns])
                all_targets.append(df['failure_risk'])

            if not all_features:
                return jsonify({
                    'ok': False,
                    'error': 'Insufficient training data',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Train model
            history = advanced_analytics_engine.train_lstm_model(
                features_df=pd.concat(all_features, ignore_index=True),
                target_series=pd.concat(all_targets, ignore_index=True),
                **params
            )

            return jsonify({
                'ok': True,
                'message': 'LSTM model trained successfully',
                'history': history,
                'timestamp': datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error training LSTM model: {e}")
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@advanced_bp.route('/train/autoencoder', methods=['POST'])
def train_autoencoder():
    """Train the anomaly detection autoencoder"""
    try:
        # Get parameters
        try:
            params = get_training_parameters(request, {
                'epochs': 100,
                'batch_size': 32,
                'validation_split': 0.1
            })
        except ValueError as e:
            return jsonify({
                'ok': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 400

        with SessionLocal() as session:
            miners = session.query(Miner).all()
            all_normal_data = []

            for miner in miners:
                df = get_miner_metrics_data(session, miner, days=60)
                if df is not None:
                    all_normal_data.append(df)

            if not all_normal_data:
                return jsonify({
                    'ok': False,
                    'error': 'Insufficient normal operation data',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Train autoencoder
            normal_data = pd.concat(all_normal_data, ignore_index=True)
            history = advanced_analytics_engine.train_autoencoder(
                normal_data=normal_data,
                **params
            )

            return jsonify({
                'ok': True,
                'message': 'Autoencoder trained successfully',
                'history': history,
                'anomaly_threshold': advanced_analytics_engine.anomaly_threshold,
                'timestamp': datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error training autoencoder: {e}")
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@advanced_bp.route('/predict/failure-risk/<miner_id>', methods=['GET'])
def predict_failure_risk(miner_id: str):
    """Get failure risk prediction for a specific miner"""
    try:
        with SessionLocal() as session:
            # Try to get by IP first, then by ID
            miner = session.query(Miner).filter(Miner.miner_ip == miner_id).first()
            if not miner:
                try:
                    miner = session.get(Miner, int(miner_id))
                except (ValueError, TypeError):
                    pass

            if not miner:
                return jsonify({
                    'ok': False,
                    'error': 'Miner not found',
                    'timestamp': datetime.utcnow().isoformat()
                }), 404

            # Get recent metrics
            cutoff = datetime.utcnow() - timedelta(days=7)
            metrics = (session.query(MinerMetrics)
                       .filter(MinerMetrics.miner_ip == miner.miner_ip)
                       .filter(MinerMetrics.timestamp >= cutoff)
                       .order_by(MinerMetrics.timestamp).all())

            if not metrics:
                return jsonify({
                    'ok': False,
                    'error': 'No metrics available for this miner',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Process metrics
            df = get_miner_metrics_data(session, miner, days=7)
            if df is None or len(df) == 0:
                return jsonify({
                    'ok': False,
                    'error': 'Insufficient data for prediction',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Ensure we have enough data points for prediction
            if len(df) < advanced_analytics_engine.sequence_length:
                return jsonify({
                    'ok': False,
                    'error': f'Insufficient data points. Need at least {advanced_analytics_engine.sequence_length} data points.',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Ensure we only pass the required features (excluding timestamp from features)
            features_df = df[advanced_analytics_engine.feature_columns].copy()
            
            # Get prediction using the historical data
            prediction = advanced_analytics_engine.predict_failure_risk(
                historical_data=features_df
            )

            return jsonify({
                'ok': True,
                'miner_id': miner_id,
                'prediction': prediction,
                'timestamp': datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error predicting failure risk: {e}")
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@advanced_bp.route('/detect-anomalies/<miner_id>', methods=['GET'])
def detect_anomalies(miner_id: str):
    """Detect anomalies in miner metrics"""
    try:
        with SessionLocal() as session:
            # Try to get by IP first, then by ID
            miner = session.query(Miner).filter(Miner.miner_ip == miner_id).first()
            if not miner:
                try:
                    miner = session.get(Miner, int(miner_id))
                except (ValueError, TypeError):
                    pass

            if not miner:
                return jsonify({
                    'ok': False,
                    'error': 'Miner not found',
                    'timestamp': datetime.utcnow().isoformat()
                }), 404

            # Get recent metrics
            cutoff = datetime.utcnow() - timedelta(days=7)
            metrics = (session.query(MinerMetrics)
                       .filter(MinerMetrics.miner_ip == miner.miner_ip)
                       .filter(MinerMetrics.timestamp >= cutoff)
                       .order_by(MinerMetrics.timestamp).all())

            if not metrics:
                return jsonify({
                    'ok': False,
                    'error': 'No metrics available for this miner',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Process metrics
            df = get_miner_metrics_data(session, miner, days=7)
            if df is None or len(df) == 0:
                return jsonify({
                    'ok': False,
                    'error': 'Insufficient data for anomaly detection',
                    'timestamp': datetime.utcnow().isoformat()
                }), 400

            # Detect anomalies
            anomalies = advanced_analytics_engine.detect_anomalies(
                miner_id=miner_id,
                features_df=df[advanced_analytics_engine.feature_columns]
            )

            return jsonify({
                'ok': True,
                'miner_id': miner_id,
                'anomalies': anomalies,
                'timestamp': datetime.utcnow().isoformat()
            })

    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500


@advanced_bp.route('/status', methods=['GET'])
def get_analytics_status():
    """Get status of the advanced analytics models"""
    try:
        # Check if models are loaded
        lstm_loaded = advanced_analytics_engine.lstm_model is not None
        autoencoder_loaded = advanced_analytics_engine.autoencoder is not None

        # Get model info
        model_info = {
            'lstm': {
                'loaded': lstm_loaded,
                'last_trained': advanced_analytics_engine.lstm_last_trained.isoformat() if lstm_loaded else None
            },
            'autoencoder': {
                'loaded': autoencoder_loaded,
                'last_trained': advanced_analytics_engine.autoencoder_last_trained.isoformat() if autoencoder_loaded else None,
                'anomaly_threshold': float(advanced_analytics_engine.anomaly_threshold) if autoencoder_loaded else None
            }
        }

        return jsonify({
            'ok': True,
            'models': model_info,
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"Error getting analytics status: {e}")
        return jsonify({
            'ok': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
