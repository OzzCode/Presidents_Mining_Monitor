"""
Predictive Analytics Engine for Mining Fleet Management

This module provides machine learning capabilities for:
- Miner failure prediction
- BTC price forecasting
- Performance optimization recommendations
- Maintenance scheduling
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import logging
from dataclasses import dataclass
from sklearn.ensemble import RandomForestRegressor, IsolationForest
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error
import joblib
import os
from sqlalchemy import text
from core.db import SessionLocal, Miner

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Container for prediction results"""
    prediction: float
    confidence: float
    timestamp: datetime
    model_version: str
    features_used: List[str]


@dataclass
class FailureRiskAssessment:
    """Container for miner failure risk assessment"""
    miner_id: str
    risk_score: float  # 0-1, where 1 is highest risk
    risk_level: str  # 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    predicted_failure_date: Optional[datetime]
    contributing_factors: List[str]
    recommendations: List[str]


@dataclass
class BTCForecast:
    """Container for BTC price forecast"""
    forecast_date: datetime
    predicted_price: float
    confidence_interval_lower: float
    confidence_interval_upper: float
    trend: str  # 'BULLISH', 'BEARISH', 'NEUTRAL'


class PredictiveAnalyticsEngine:
    """Main engine for predictive analytics"""

    def __init__(self):
        self.models_dir = "models"
        self.scaler = StandardScaler()
        self.failure_model = None
        self.btc_model = None
        self.anomaly_detector = None

        # Create models directory if it doesn't exist
        os.makedirs(self.models_dir, exist_ok=True)

        # Load existing models if available
        self._load_models()

    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            failure_model_path = os.path.join(self.models_dir, 'failure_prediction_model.joblib')
            btc_model_path = os.path.join(self.models_dir, 'btc_forecast_model.joblib')
            scaler_path = os.path.join(self.models_dir, 'scaler.joblib')
            anomaly_path = os.path.join(self.models_dir, 'anomaly_detector.joblib')

            if os.path.exists(failure_model_path):
                self.failure_model = joblib.load(failure_model_path)
                logger.info("Loaded failure prediction model")

            if os.path.exists(btc_model_path):
                self.btc_model = joblib.load(btc_model_path)
                logger.info("Loaded BTC forecast model")

            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)
                logger.info("Loaded feature scaler")

            if os.path.exists(anomaly_path):
                self.anomaly_detector = joblib.load(anomaly_path)
                logger.info("Loaded anomaly detector")

        except Exception as e:
            logger.warning(f"Could not load existing models: {e}")

    def _save_models(self):
        """Save trained models to disk"""
        try:
            if self.failure_model:
                joblib.dump(self.failure_model, os.path.join(self.models_dir, 'failure_prediction_model.joblib'))

            if self.btc_model:
                joblib.dump(self.btc_model, os.path.join(self.models_dir, 'btc_forecast_model.joblib'))

            joblib.dump(self.scaler, os.path.join(self.models_dir, 'scaler.joblib'))

            if self.anomaly_detector:
                joblib.dump(self.anomaly_detector, os.path.join(self.models_dir, 'anomaly_detector.joblib'))

            logger.info("Models saved successfully")
        except Exception as e:
            logger.error(f"Error saving models: {e}")

    def get_miner_features(self, miner_id: str, days: int = 30) -> pd.DataFrame:
        """Extract features for a specific miner from historical data"""
        try:
            # Get miner data from the last N days
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Use SessionLocal for database queries
            session = SessionLocal()
            try:
                query = text("""
                             SELECT m.timestamp,
                                    m.hashrate,
                                    m.temperature,
                                    m.avg_fan_rpm as fan_speed,
                                    m.power_consumption,
                                    m.pool_rejected_shares,
                                    m.pool_accepted_shares,
                                    0             as uptime,
                                    mn.model,
                                    mn.firmware_version
                             FROM metrics m
                                      JOIN miners mn ON m.miner_ip = mn.miner_ip
                             WHERE mn.id = :miner_id
                               AND m.timestamp >= :start_date
                               AND m.timestamp <= :end_date
                             ORDER BY m.timestamp
                             """)

                result = session.execute(query, {
                    'miner_id': miner_id,
                    'start_date': start_date,
                    'end_date': end_date
                })

                data = result.fetchall()
                if not data:
                    return pd.DataFrame()
            finally:
                session.close()

            # Convert to DataFrame
            df = pd.DataFrame(data, columns=[
                'timestamp', 'hashrate', 'temperature', 'fan_speed',
                'power_consumption', 'rejected_shares', 'accepted_shares',
                'uptime', 'model', 'firmware_version'
            ])

            # Calculate derived features
            df['rejection_rate'] = df['rejected_shares'] / (df['accepted_shares'] + df['rejected_shares'] + 1e-6)
            df['efficiency'] = df['hashrate'] / (df['power_consumption'] + 1e-6)
            df['temperature_trend'] = df['temperature'].rolling(window=5).mean().diff()
            df['hashrate_stability'] = df['hashrate'].rolling(window=10).std()
            df['power_efficiency_trend'] = df['efficiency'].rolling(window=5).mean().diff()

            # Time-based features
            df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
            df['day_of_week'] = pd.to_datetime(df['timestamp']).dt.dayofweek

            return df.fillna(0)

        except Exception as e:
            logger.error(f"Error extracting features for miner {miner_id}: {e}")
            return pd.DataFrame()

    def train_failure_prediction_model(self, retrain: bool = False):
        """Train the miner failure prediction model"""
        try:
            if self.failure_model and not retrain:
                logger.info("Failure prediction model already exists. Use retrain=True to retrain.")
                return

            logger.info("Training failure prediction model...")

            # Get all miners and their historical data
            # FIX: Use a proper SQLAlchemy session instead of Flask-SQLAlchemy's Miner.query
            session = SessionLocal()
            try:
                miners = session.query(Miner).all()
            finally:
                session.close()

            training_data = []

            for miner in miners:
                features_df = self.get_miner_features(miner.id, days=60)
                if features_df.empty:
                    continue
                # Create labels based on known failures or performance degradation
                # For now, we'll use temperature and hashrate thresholds as proxy for failure risk
                features_df['failure_risk'] = 0
                # High temperature risk
                features_df.loc[features_df['temperature'] > 85, 'failure_risk'] += 0.3
                # Low hashrate risk
                expected_hashrate = features_df['hashrate'].quantile(0.8)
                features_df.loc[features_df['hashrate'] < expected_hashrate * 0.7, 'failure_risk'] += 0.4
                # High rejection rate risk
                features_df.loc[features_df['rejection_rate'] > 0.05, 'failure_risk'] += 0.2
                # Unstable performance risk
                features_df.loc[features_df['hashrate_stability'] > features_df['hashrate_stability'].quantile(
                    0.9), 'failure_risk'] += 0.1
                # Cap at 1.0
                features_df['failure_risk'] = features_df['failure_risk'].clip(0, 1)
                training_data.append(features_df)

            if not training_data:
                logger.warning("No training data available for failure prediction")
                return

            # Combine all data
            combined_df = pd.concat(training_data, ignore_index=True)
            # Select features for training
            feature_columns = [
                'hashrate', 'temperature', 'fan_speed', 'power_consumption',
                'rejection_rate', 'efficiency', 'temperature_trend',
                'hashrate_stability', 'power_efficiency_trend', 'hour', 'day_of_week'
            ]
            X = combined_df[feature_columns].fillna(0)
            y = combined_df['failure_risk']
            # Scale features
            X_scaled = self.scaler.fit_transform(X)
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.2, random_state=42)
            # Train model
            self.failure_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            self.failure_model.fit(X_train, y_train)
            # Evaluate model
            y_pred = self.failure_model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)
            logger.info(f"Failure prediction model trained. MAE: {mae:.4f}, MSE: {mse:.4f}")
            # Train anomaly detector
            self.anomaly_detector = IsolationForest(contamination=0.1, random_state=42)
            self.anomaly_detector.fit(X_train)
            # Save models
            self._save_models()

        except Exception as e:
            logger.error(f"Error training failure prediction model: {e}")

    def predict_miner_failure_risk(self, miner_id: str) -> FailureRiskAssessment:
        """Predict failure risk for a specific miner"""
        try:
            if not self.failure_model:
                self.train_failure_prediction_model()

            if not self.failure_model:
                return FailureRiskAssessment(
                    miner_id=miner_id,
                    risk_score=0.0,
                    risk_level='UNKNOWN',
                    predicted_failure_date=None,
                    contributing_factors=['Model not available'],
                    recommendations=['Train the failure prediction model first']
                )

            # Get recent features
            features_df = self.get_miner_features(miner_id, days=7)
            if features_df.empty:
                return FailureRiskAssessment(
                    miner_id=miner_id,
                    risk_score=0.0,
                    risk_level='NO_DATA',
                    predicted_failure_date=None,
                    contributing_factors=['No recent data available'],
                    recommendations=['Check miner connectivity']
                )

            # Use latest data point
            latest_data = features_df.iloc[-1]

            feature_columns = [
                'hashrate', 'temperature', 'fan_speed', 'power_consumption',
                'rejection_rate', 'efficiency', 'temperature_trend',
                'hashrate_stability', 'power_efficiency_trend', 'hour', 'day_of_week'
            ]

            X = np.array([latest_data[feature_columns].fillna(0).values])
            X_scaled = self.scaler.transform(X)

            # Predict risk score
            risk_score = self.failure_model.predict(X_scaled)[0]
            risk_score = max(0.0, min(1.0, risk_score))  # Ensure 0-1 range

            # Determine risk level
            if risk_score < 0.2:
                risk_level = 'LOW'
            elif risk_score < 0.5:
                risk_level = 'MEDIUM'
            elif risk_score < 0.8:
                risk_level = 'HIGH'
            else:
                risk_level = 'CRITICAL'

            # Identify contributing factors
            contributing_factors = []
            recommendations = []

            if latest_data['temperature'] > 80:
                contributing_factors.append('High temperature')
                recommendations.append('Improve cooling or reduce ambient temperature')

            if latest_data['rejection_rate'] > 0.03:
                contributing_factors.append('High rejection rate')
                recommendations.append('Check network connection and pool settings')

            if latest_data['hashrate_stability'] > features_df['hashrate_stability'].quantile(0.8):
                contributing_factors.append('Unstable hashrate')
                recommendations.append('Check for hardware issues or power fluctuations')

            if latest_data['efficiency'] < features_df['efficiency'].quantile(0.2):
                contributing_factors.append('Poor power efficiency')
                recommendations.append('Consider maintenance or firmware update')

            # Estimate failure date based on risk score
            predicted_failure_date = None
            if risk_score > 0.7:
                days_to_failure = max(1, int(30 * (1 - risk_score)))
                predicted_failure_date = datetime.utcnow() + timedelta(days=days_to_failure)

            return FailureRiskAssessment(
                miner_id=miner_id,
                risk_score=risk_score,
                risk_level=risk_level,
                predicted_failure_date=predicted_failure_date,
                contributing_factors=contributing_factors or ['Normal operation'],
                recommendations=recommendations or ['Continue monitoring']
            )

        except Exception as e:
            logger.error(f"Error predicting failure risk for miner {miner_id}: {e}")
            return FailureRiskAssessment(
                miner_id=miner_id,
                risk_score=0.0,
                risk_level='ERROR',
                predicted_failure_date=None,
                contributing_factors=[f'Prediction error: {str(e)}'],
                recommendations=['Check system logs']
            )

    def get_btc_price_history(self, days: int = 90) -> pd.DataFrame:
        """Get BTC price history from profitability snapshots"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)

            # Use SessionLocal for database queries
            session = SessionLocal()
            try:
                query = text("""
                             SELECT timestamp, btc_price_usd, network_difficulty
                             FROM profitability_snapshots
                             WHERE timestamp >= :start_date
                               AND timestamp <= :end_date
                               AND btc_price_usd IS NOT NULL
                             ORDER BY timestamp
                             """)

                result = session.execute(query, {
                    'start_date': start_date,
                    'end_date': end_date
                })

                data = result.fetchall()
                if not data:
                    return pd.DataFrame()
            finally:
                session.close()

            df = pd.DataFrame(data, columns=['timestamp', 'btc_price', 'network_difficulty'])
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')

            return df

        except Exception as e:
            logger.error(f"Error getting BTC price history: {e}")
            return pd.DataFrame()

    def train_btc_forecast_model(self, retrain: bool = False):
        """Train BTC price forecasting model"""
        try:
            if self.btc_model and not retrain:
                logger.info("BTC forecast model already exists. Use retrain=True to retrain.")
                return

            logger.info("Training BTC price forecast model...")

            # Get historical price data
            price_df = self.get_btc_price_history(days=180)
            if price_df.empty or len(price_df) < 30:
                logger.warning("Insufficient BTC price data for training")
                return

            # Create features
            price_df['price_ma_7'] = price_df['btc_price'].rolling(window=7).mean()
            price_df['price_ma_30'] = price_df['btc_price'].rolling(window=30).mean()
            price_df['price_std_7'] = price_df['btc_price'].rolling(window=7).std()
            price_df['price_change'] = price_df['btc_price'].pct_change()
            price_df['price_change_7d'] = price_df['btc_price'].pct_change(periods=7)
            price_df['difficulty_change'] = price_df['network_difficulty'].pct_change()

            # Time-based features
            price_df['hour'] = price_df.index.hour
            price_df['day_of_week'] = price_df.index.dayofweek
            price_df['day_of_month'] = price_df.index.day

            # Create lagged features
            for lag in [1, 2, 3, 7]:
                price_df[f'price_lag_{lag}'] = price_df['btc_price'].shift(lag)

            # Drop NaN values
            price_df = price_df.dropna()

            if len(price_df) < 20:
                logger.warning("Insufficient clean data for BTC model training")
                return

            # Prepare features and target
            feature_columns = [
                'price_ma_7', 'price_ma_30', 'price_std_7', 'price_change',
                'price_change_7d', 'difficulty_change', 'hour', 'day_of_week',
                'day_of_month', 'price_lag_1', 'price_lag_2', 'price_lag_3', 'price_lag_7'
            ]

            X = price_df[feature_columns].fillna(method='ffill').fillna(0)
            y = price_df['btc_price']

            # Split data (use last 20% for testing)
            split_idx = int(len(X) * 0.8)
            X_train, X_test = X[:split_idx], X[split_idx:]
            y_train, y_test = y[:split_idx], y[split_idx:]

            # Train model
            self.btc_model = RandomForestRegressor(
                n_estimators=100,
                max_depth=15,
                random_state=42,
                n_jobs=-1
            )
            self.btc_model.fit(X_train, y_train)

            # Evaluate model
            y_pred = self.btc_model.predict(X_test)
            mae = mean_absolute_error(y_test, y_pred)
            mse = mean_squared_error(y_test, y_pred)

            logger.info(f"BTC forecast model trained. MAE: ${mae:.2f}, MSE: ${mse:.2f}")

            # Save model
            self._save_models()

        except Exception as e:
            logger.error(f"Error training BTC forecast model: {e}")

    def forecast_btc_price(self, days_ahead: int = 7) -> List[BTCForecast]:
        """Forecast BTC price for the next N days"""
        try:
            if not self.btc_model:
                self.train_btc_forecast_model()

            if not self.btc_model:
                return []

            # Get recent price data
            price_df = self.get_btc_price_history(days=90)
            if price_df.empty:
                return []

            forecasts = []
            current_df = price_df.copy()

            for day in range(1, days_ahead + 1):
                # Prepare features for prediction
                current_df['price_ma_7'] = current_df['btc_price'].rolling(window=7).mean()
                current_df['price_ma_30'] = current_df['btc_price'].rolling(window=30).mean()
                current_df['price_std_7'] = current_df['btc_price'].rolling(window=7).std()
                current_df['price_change'] = current_df['btc_price'].pct_change()
                current_df['price_change_7d'] = current_df['btc_price'].pct_change(periods=7)
                current_df['difficulty_change'] = current_df['network_difficulty'].pct_change()

                # Time features for forecast date
                forecast_date = datetime.utcnow() + timedelta(days=day)
                hour = forecast_date.hour
                day_of_week = forecast_date.weekday()
                day_of_month = forecast_date.day

                # Lagged features
                for lag in [1, 2, 3, 7]:
                    current_df[f'price_lag_{lag}'] = current_df['btc_price'].shift(lag)

                # Get latest features
                latest_data = current_df.iloc[-1]

                feature_columns = [
                    'price_ma_7', 'price_ma_30', 'price_std_7', 'price_change',
                    'price_change_7d', 'difficulty_change', 'price_lag_1',
                    'price_lag_2', 'price_lag_3', 'price_lag_7'
                ]

                X = np.array([[
                    latest_data['price_ma_7'],
                    latest_data['price_ma_30'],
                    latest_data['price_std_7'],
                    latest_data['price_change'],
                    latest_data['price_change_7d'],
                    latest_data['difficulty_change'],
                    hour,
                    day_of_week,
                    day_of_month,
                    latest_data['price_lag_1'],
                    latest_data['price_lag_2'],
                    latest_data['price_lag_3'],
                    latest_data['price_lag_7']
                ]])

                # Handle NaN values
                X = np.nan_to_num(X, nan=0.0)

                # Make prediction
                predicted_price = self.btc_model.predict(X)[0]

                # Calculate confidence interval (simplified)
                price_std = current_df['btc_price'].std()
                confidence_interval = 1.96 * price_std  # 95% confidence interval

                # Determine trend
                recent_change = (predicted_price - current_df['btc_price'].iloc[-1]) / current_df['btc_price'].iloc[-1]
                if recent_change > 0.02:
                    trend = 'BULLISH'
                elif recent_change < -0.02:
                    trend = 'BEARISH'
                else:
                    trend = 'NEUTRAL'

                forecast = BTCForecast(
                    forecast_date=forecast_date,
                    predicted_price=predicted_price,
                    confidence_interval_lower=predicted_price - confidence_interval,
                    confidence_interval_upper=predicted_price + confidence_interval,
                    trend=trend
                )

                forecasts.append(forecast)

                # Add predicted price to dataframe for next iteration
                new_row = pd.DataFrame({
                    'btc_price': [predicted_price],
                    'network_difficulty': [current_df['network_difficulty'].iloc[-1]]
                }, index=[forecast_date])

                current_df = pd.concat([current_df, new_row])

            return forecasts

        except Exception as e:
            logger.error(f"Error forecasting BTC price: {e}")
            return []

    def get_fleet_analytics_summary(self) -> Dict[str, Any]:
        """Get comprehensive analytics summary for the entire fleet"""
        try:
            miners = Miner.query.filter_by(status='active').all()

            # Get failure risk assessments for all miners
            risk_assessments = []
            for miner in miners:
                assessment = self.predict_miner_failure_risk(miner.id)
                risk_assessments.append(assessment)

            # Calculate fleet-wide metrics
            total_miners = len(miners)
            high_risk_miners = len([r for r in risk_assessments if r.risk_level in ['HIGH', 'CRITICAL']])
            avg_risk_score = np.mean([r.risk_score for r in risk_assessments]) if risk_assessments else 0

            # Get BTC forecast
            btc_forecasts = self.forecast_btc_price(days_ahead=7)

            # Calculate maintenance recommendations
            maintenance_needed = len([r for r in risk_assessments if r.risk_level in ['HIGH', 'CRITICAL']])

            return {
                'fleet_summary': {
                    'total_miners': total_miners,
                    'high_risk_miners': high_risk_miners,
                    'average_risk_score': avg_risk_score,
                    'maintenance_needed': maintenance_needed,
                    'fleet_health_score': max(0, 100 - (avg_risk_score * 100))
                },
                'risk_assessments': [
                    {
                        'miner_id': r.miner_id,
                        'risk_score': r.risk_score,
                        'risk_level': r.risk_level,
                        'predicted_failure_date': r.predicted_failure_date.isoformat() if r.predicted_failure_date else None,
                        'contributing_factors': r.contributing_factors,
                        'recommendations': r.recommendations
                    } for r in risk_assessments
                ],
                'btc_forecasts': [
                    {
                        'date': f.forecast_date.isoformat(),
                        'predicted_price': f.predicted_price,
                        'confidence_lower': f.confidence_interval_lower,
                        'confidence_upper': f.confidence_interval_upper,
                        'trend': f.trend
                    } for f in btc_forecasts
                ],
                'recommendations': self._generate_fleet_recommendations(risk_assessments, btc_forecasts)
            }

        except Exception as e:
            logger.error(f"Error generating fleet analytics summary: {e}")
            return {
                'error': str(e),
                'fleet_summary': {},
                'risk_assessments': [],
                'btc_forecasts': [],
                'recommendations': []
            }

    def _generate_fleet_recommendations(self, risk_assessments: List[FailureRiskAssessment],
                                        btc_forecasts: List[BTCForecast]) -> List[str]:
        """Generate actionable recommendations based on analytics"""
        recommendations = []

        # Failure risk recommendations
        critical_miners = [r for r in risk_assessments if r.risk_level == 'CRITICAL']
        high_risk_miners = [r for r in risk_assessments if r.risk_level == 'HIGH']

        if critical_miners:
            recommendations.append(f"URGENT: {len(critical_miners)} miners require immediate attention")

        if high_risk_miners:
            recommendations.append(f"Schedule maintenance for {len(high_risk_miners)} high-risk miners")

        # BTC price recommendations
        if btc_forecasts:
            avg_forecast = np.mean([f.predicted_price for f in btc_forecasts])
            current_price = btc_forecasts[0].predicted_price if btc_forecasts else 0

            if avg_forecast > current_price * 1.05:
                recommendations.append("BTC price trending upward - consider expanding operations")
            elif avg_forecast < current_price * 0.95:
                recommendations.append("BTC price trending downward - optimize for efficiency")

        # General recommendations
        avg_risk = np.mean([r.risk_score for r in risk_assessments]) if risk_assessments else 0
        if avg_risk > 0.6:
            recommendations.append("Fleet health declining - review maintenance schedules")
        elif avg_risk < 0.3:
            recommendations.append("Fleet performing well - maintain current operations")

        return recommendations


# Global instance
analytics_engine = PredictiveAnalyticsEngine()
