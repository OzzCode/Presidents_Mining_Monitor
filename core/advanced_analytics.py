"""
Advanced Analytics Module for Mining Fleet Management

This module provides enhanced machine learning capabilities including:
- LSTM-based failure prediction
- Real-time anomaly detection using autoencoders
- Advanced time-series forecasting
"""

import numpy as np
import pandas as pd
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import LSTM, Dense, Dropout, Input, RepeatVector, TimeDistributed
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from sklearn.preprocessing import MinMaxScaler
import joblib
import os
import logging
from typing import Dict, Tuple, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AdvancedAnalyticsEngine:
    """Advanced analytics engine with LSTM and autoencoder models"""

    def __init__(self, model_dir: str = "advanced_models"):
        self.model_dir = model_dir
        self.lstm_model = None
        self.autoencoder = None
        self.scaler = MinMaxScaler()
        self.feature_scaler = MinMaxScaler()
        self.feature_columns = [
            'hashrate', 'temperature', 'fan_speed', 'power_consumption',
            'rejection_rate', 'efficiency', 'temperature_trend',
            'hashrate_stability', 'power_efficiency_trend'
        ]
        self.sequence_length = 24  # Number of time steps to look back
        self.n_features = len(self.feature_columns)
        self.anomaly_threshold = None

        # Create models directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)

        # Load existing models if available
        self._load_models()

    def _load_models(self):
        """Load pre-trained models from disk"""
        try:
            lstm_path = os.path.join(self.model_dir, 'lstm_model.h5')
            autoencoder_path = os.path.join(self.model_dir, 'anomaly_detector.h5')
            scaler_path = os.path.join(self.model_dir, 'advanced_scaler.joblib')

            if os.path.exists(lstm_path):
                # Load model with custom objects if needed
                custom_objects = {
                    'mean_squared_error': 'mean_squared_error',
                    'mean_absolute_error': 'mean_absolute_error'
                }
                # Load the entire model
                self.lstm_model = load_model(
                    lstm_path,
                    custom_objects=custom_objects,
                    compile=True  # Let Keras handle compilation
                )
                logger.info("Loaded LSTM failure prediction model")

            if os.path.exists(autoencoder_path):
                # Load the autoencoder
                self.autoencoder = load_model(
                    autoencoder_path,
                    compile=True  # Autoencoder uses default MSE loss
                )
                logger.info("Loaded anomaly detection autoencoder")

            if os.path.exists(scaler_path):
                scaler_data = joblib.load(scaler_path)
                self.scaler = scaler_data['target_scaler']
                self.feature_scaler = scaler_data['feature_scaler']
                self.anomaly_threshold = scaler_data.get('anomaly_threshold', 0.1)
                logger.info("Loaded feature scalers")

        except Exception as e:
            logger.warning(f"Could not load advanced models: {e}")

    def _save_models(self):
        """Save trained models to disk"""
        try:
            # Ensure model directory exists
            os.makedirs(self.model_dir, exist_ok=True)

            if self.lstm_model:
                # Save the entire model with .h5 extension
                lstm_path = os.path.join(self.model_dir, 'lstm_model.h5')
                self.lstm_model.save(lstm_path, save_format='h5')
                logger.info(f"Saved LSTM model to {lstm_path}")

            if self.autoencoder:
                # Save the autoencoder with .h5 extension
                autoencoder_path = os.path.join(self.model_dir, 'anomaly_detector.h5')
                self.autoencoder.save(autoencoder_path, save_format='h5')
                logger.info(f"Saved autoencoder model to {autoencoder_path}")

            # Save scalers and threshold
            if hasattr(self, 'scaler') and hasattr(self, 'feature_scaler'):
                scaler_data = {
                    'target_scaler': self.scaler,
                    'feature_scaler': self.feature_scaler,
                    'anomaly_threshold': getattr(self, 'anomaly_threshold', 0.1)
                }
                scaler_path = os.path.join(self.model_dir, 'advanced_scaler.joblib')
                joblib.dump(scaler_data, scaler_path)
                logger.info(f"Saved scalers to {scaler_path}")

            logger.info("Advanced models saved successfully")

        except Exception as e:
            logger.error(f"Error saving advanced models: {e}")
            raise  # Re-raise the exception to handle it in the calling function

    def _create_sequences(self, data: np.ndarray, sequence_length: int) -> Tuple[np.ndarray, np.ndarray]:
        """Convert time series data into sequences for LSTM"""
        X, y = [], []
        for i in range(len(data) - sequence_length):
            X.append(data[i:(i + sequence_length), :])
            y.append(data[i + sequence_length - 1, 0])  # Predict next step after sequence
        return np.array(X), np.array(y)

    def train_lstm_model(self, features_df: pd.DataFrame, target_series: pd.Series,
                         epochs: int = 50, batch_size: int = 32, validation_split: float = 0.2):
        """
        Train LSTM model for failure prediction
        
        Args:
            features_df: DataFrame containing the features
            target_series: Target variable (failure risk score 0-1)
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
        """
        try:
            # Prepare data
            features = features_df[self.feature_columns].copy()

            # Scale features
            X_scaled = self.feature_scaler.fit_transform(features)
            y_scaled = self.scaler.fit_transform(target_series.values.reshape(-1, 1))

            # Create sequences for features and targets separately
            X_seq, y_seq = self._create_sequences(
                X_scaled,  # Only include features in sequences
                self.sequence_length
            )

            # Align target with the last element of each sequence
            y_seq = y_scaled[self.sequence_length:]

            # Split into train/validation
            split_idx = int(len(X_seq) * (1 - validation_split))
            X_train, X_val = X_seq[:split_idx], X_seq[split_idx:]
            y_train, y_val = y_seq[:split_idx], y_seq[split_idx:]

            # Compile model with correct input shape
            self.lstm_model = Sequential([
                LSTM(64, input_shape=(self.sequence_length, self.n_features), return_sequences=True),
                Dropout(0.2),
                LSTM(32, return_sequences=False),
                Dropout(0.2),
                Dense(16, activation='relu'),
                Dense(1, activation='sigmoid')
            ])

            # Use string identifiers for metrics to ensure proper serialization
            self.lstm_model.compile(optimizer='adam',
                                    loss='mean_squared_error',
                                    metrics=['mean_absolute_error'])

            # Save initial model architecture with explicit save format
            self.lstm_model.save(
                os.path.join(self.model_dir, 'lstm_initial.h5'),
                save_format='h5',
                include_optimizer=True
            )

            # Callbacks
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
                ModelCheckpoint(
                    os.path.join(self.model_dir, 'lstm_best_model.h5'),
                    save_best_only=True,
                    monitor='val_loss',
                    mode='min'
                )
            ]

            # Train model
            history = self.lstm_model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_data=(X_val, y_val),
                callbacks=callbacks,
                verbose=1
            )

            # Load best model
            self.lstm_model = load_model(os.path.join(self.model_dir, 'lstm_best_model.h5'))

            # Evaluate
            val_loss, val_mae = self.lstm_model.evaluate(X_val, y_val, verbose=0)
            logger.info(f"LSTM model trained. Validation MAE: {val_mae:.4f}")

            # Save models
            self._save_models()

            return history.history

        except Exception as e:
            logger.error(f"Error training LSTM model: {e}")
            raise

    def predict_failure_risk(self, historical_data: pd.DataFrame) -> Dict[str, Any]:
        """
        Predict failure risk using the trained LSTM model
        
        Args:
            historical_data: DataFrame containing historical data for a miner
                            Must include all feature_columns and a 'timestamp' column
                            
        Returns:
            Dictionary containing prediction results
        """
        try:
            if self.lstm_model is None:
                raise ValueError("LSTM model not trained. Call train_lstm_model first.")

            # Prepare features
            features = historical_data[self.feature_columns].copy()

            # Scale features
            X_scaled = self.feature_scaler.transform(features)

            # Create sequence for prediction
            if len(X_scaled) < self.sequence_length:
                # Pad with zeros if not enough history
                padding = np.zeros((self.sequence_length - len(X_scaled), self.n_features))
                X_scaled = np.vstack([padding, X_scaled])
            else:
                # Use only the most recent sequence
                X_scaled = X_scaled[-self.sequence_length:]

            # Reshape for LSTM input (samples, timesteps, features)
            X_seq = X_scaled.reshape(1, self.sequence_length, self.n_features)

            # Make prediction
            prediction_scaled = self.lstm_model.predict(X_seq, verbose=0)[0][0]
            # Ensure the prediction is in the correct shape for inverse transform
            prediction_2d = np.array([[prediction_scaled]])
            risk_score = float(self.scaler.inverse_transform(prediction_2d)[0][0])

            # Get risk level
            if risk_score < 0.2:
                risk_level = 'LOW'
            elif risk_score < 0.5:
                risk_level = 'MEDIUM'
            elif risk_score < 0.8:
                risk_level = 'HIGH'
            else:
                risk_level = 'CRITICAL'

            return {
                'risk_score': min(max(risk_score, 0.0), 1.0),  # Ensure 0-1 range
                'risk_level': risk_level,
                'timestamp': datetime.utcnow().isoformat(),
                'features_used': self.feature_columns,
                'model_type': 'LSTM'
            }

        except Exception as e:
            logger.error(f"Error predicting failure risk: {e}")
            return {
                'error': str(e),
                'risk_score': 0.0,
                'risk_level': 'UNKNOWN',
                'timestamp': datetime.utcnow().isoformat()
            }

    def train_autoencoder(self, normal_data: pd.DataFrame, epochs: int = 100, batch_size: int = 32,
                          validation_split: float = 0.1):
        """
        Train an autoencoder for anomaly detection
        
        Args:
            normal_data: DataFrame containing only normal operation data
            epochs: Number of training epochs
            batch_size: Batch size for training
            validation_split: Fraction of data to use for validation
        """
        try:
            # Prepare and scale data
            data = normal_data[self.feature_columns].copy()
            X_scaled = self.feature_scaler.fit_transform(data)

            # Create sequences
            X_seq, _ = self._create_sequences(
                np.column_stack((np.zeros(len(X_scaled)).reshape(-1, 1), X_scaled)),
                self.sequence_length
            )

            # Build autoencoder
            input_dim = X_seq.shape[2]

            self.autoencoder = Sequential([
                Input(shape=(self.sequence_length, input_dim)),
                LSTM(32, activation='relu', return_sequences=True),
                Dropout(0.2),
                LSTM(16, activation='relu', return_sequences=False),
                RepeatVector(self.sequence_length),
                LSTM(16, activation='relu', return_sequences=True),
                Dropout(0.2),
                LSTM(32, activation='relu', return_sequences=True),
                TimeDistributed(Dense(input_dim))
            ])

            # Compile with string identifier for loss
            self.autoencoder.compile(optimizer='adam',
                                     loss='mean_squared_error')  # Using string identifier

            # Callbacks
            callbacks = [
                EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True),
                ModelCheckpoint(
                    os.path.join(self.model_dir, 'autoencoder_best.h5'),
                    save_best_only=True,
                    monitor='val_loss',
                    mode='min'
                )
            ]

            # Train autoencoder
            history = self.autoencoder.fit(
                X_seq, X_seq,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=validation_split,
                callbacks=callbacks,
                verbose=1
            )

            # Load best model with custom objects
            try:
                self.autoencoder = load_model(
                    os.path.join(self.model_dir, 'autoencoder_best.h5'),
                    compile=True,  # Let Keras handle compilation
                    custom_objects={'mean_squared_error': 'mean_squared_error'}
                )

                # Calculate reconstruction error threshold (95th percentile of training errors)
                reconstructions = self.autoencoder.predict(X_seq, verbose=0)
                mse = np.mean(np.power(X_seq - reconstructions, 2), axis=(1, 2))
                self.anomaly_threshold = np.percentile(mse, 95)
                logger.info(f"Autoencoder trained. Anomaly threshold: {self.anomaly_threshold:.4f}")

                # Save models using our save method
                self._save_models()

                # Clean up the temporary best model file
                best_model_path = os.path.join(self.model_dir, 'autoencoder_best.h5')
                if os.path.exists(best_model_path):
                    os.remove(best_model_path)

            except Exception as e:
                logger.error(f"Error loading or saving autoencoder: {e}")
                raise

            return history.history

        except Exception as e:
            logger.error(f"Error training autoencoder: {e}")
            raise

    def detect_anomalies(self, features_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Detect anomalies in the given data
        
        Args:
            features_df: DataFrame containing the features to analyze
            
        Returns:
            Dictionary containing anomaly detection results
        """
        try:
            if self.autoencoder is None or self.anomaly_threshold is None:
                raise ValueError("Autoencoder not trained. Call train_autoencoder first.")

            # Prepare and scale data
            data = features_df[self.feature_columns].copy()
            X_scaled = self.feature_scaler.transform(data)

            # Create sequences
            X_seq, _ = self._create_sequences(
                np.column_stack((np.zeros(len(X_scaled)).reshape(-1, 1), X_scaled)),
                self.sequence_length
            )

            # Get reconstructions and calculate MSE
            reconstructions = self.autoencoder.predict(X_seq, verbose=0)
            mse = np.mean(np.power(X_seq - reconstructions, 2), axis=(1, 2))

            # Detect anomalies
            is_anomaly = mse > self.anomaly_threshold
            anomaly_scores = (mse / self.anomaly_threshold).clip(0, 3)  # Normalized score, capped at 3x threshold

            # Get most anomalous features for each sequence
            feature_errors = np.mean(np.power(X_seq - reconstructions, 2), axis=1)
            top_anomalous_features = []

            for i in range(len(feature_errors)):
                # Get indices of top 3 features with highest error
                top_indices = np.argsort(feature_errors[i])[-3:][::-1]
                top_features = [(self.feature_columns[j - 1] if j > 0 else 'target',
                                 float(feature_errors[i][j]))
                                for j in top_indices]
                top_anomalous_features.append(top_features)

            # Prepare results
            results = {
                'timestamps': features_df['timestamp'].iloc[self.sequence_length:].tolist(),
                'anomaly_scores': anomaly_scores.tolist(),
                'is_anomaly': is_anomaly.tolist(),
                'anomaly_threshold': float(self.anomaly_threshold),
                'anomaly_details': []
            }

            # Add details for each anomaly
            for i in range(len(is_anomaly)):
                if is_anomaly[i]:
                    results['anomaly_details'].append({
                        'timestamp': features_df['timestamp'].iloc[i + self.sequence_length].isoformat(),
                        'anomaly_score': float(anomaly_scores[i]),
                        'suspected_causes': [
                            {'feature': feat, 'error': err}
                            for feat, err in top_anomalous_features[i]
                        ]
                    })

            return results

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }


# Initialize a global instance of the advanced analytics engine
advanced_analytics_engine = AdvancedAnalyticsEngine()
