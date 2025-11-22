# Advanced Analytics Module

This module provides advanced analytics capabilities for the Mining Fleet Management system, including LSTM-based failure prediction and real-time anomaly detection using autoencoders.

## Features

1. **LSTM-based Failure Prediction**
   - Predicts potential miner failures using historical time-series data
   - Identifies risk factors contributing to potential failures
   - Provides risk scores and severity levels

2. **Real-time Anomaly Detection**
   - Detects unusual patterns in miner metrics using autoencoders
   - Identifies potential issues before they cause failures
   - Provides anomaly scores and confidence levels

## API Endpoints

### LSTM Model Training
- **POST** `/api/advanced/train/lstm`
  - Train a new LSTM model for failure prediction
  - Parameters:
    - `epochs` (int, optional): Number of training epochs (default: 50)
    - `batch_size` (int, optional): Batch size for training (default: 32)
    - `validation_split` (float, optional): Fraction of data to use for validation (default: 0.2)

### Autoencoder Training
- **POST** `/api/advanced/train/autoencoder`
  - Train a new autoencoder for anomaly detection
  - Parameters:
    - `epochs` (int, optional): Number of training epochs (default: 100)
    - `batch_size` (int, optional): Batch size for training (default: 32)
    - `validation_split` (float, optional): Fraction of data to use for validation (default: 0.1)

### Failure Prediction
- **GET** `/api/advanced/predict/failure-risk/<miner_id>`
  - Get failure risk prediction for a specific miner
  - Returns:
    - `risk_score`: Predicted failure risk (0-1)
    - `risk_level`: Risk level (LOW, MEDIUM, HIGH, CRITICAL)
    - `features_used`: List of features used for prediction
    - `model_type`: Type of model used (LSTM)

### Anomaly Detection
- **GET** `/api/advanced/detect/anomalies/<miner_id>`
  - Detect anomalies in miner metrics
  - Returns:
    - `is_anomaly`: List of boolean values indicating anomalies
    - `anomaly_scores`: List of anomaly scores
    - `threshold`: Threshold used for anomaly detection
    - `features_analyzed`: List of features analyzed

### Status
- **GET** `/api/advanced/status`
  - Get status of the advanced analytics models
  - Returns:
    - `lstm_model`: Whether LSTM model is loaded
    - `autoencoder`: Whether autoencoder is loaded
    - `anomaly_threshold`: Current anomaly threshold
    - `feature_columns`: List of feature columns used
    - `sequence_length`: Sequence length for time-series data

## Usage Example

### Training the Models
```bash
# Train LSTM model
curl -X POST http://localhost:5000/api/advanced/train/lstm \
  -H "Content-Type: application/json" \
  -d '{"epochs": 50, "batch_size": 32}'

# Train Autoencoder
curl -X POST http://localhost:5000/api/advanced/train/autoencoder \
  -H "Content-Type: application/json" \
  -d '{"epochs": 100, "batch_size": 32}'
```

### Getting Predictions
```bash
# Get failure risk prediction
curl http://localhost:5000/api/advanced/predict/failure-risk/192.168.1.100

# Detect anomalies
curl http://localhost:5000/api/advanced/detect/anomalies/192.168.1.100
```

## Model Architecture

### LSTM for Failure Prediction
- Input: Time-series data of miner metrics
- Architecture:
  - LSTM layer (64 units)
  - Dropout (0.2)
  - LSTM layer (32 units)
  - Dropout (0.2)
  - Dense layer (16 units, ReLU)
  - Output layer (1 unit, Sigmoid)
- Loss: Mean Squared Error
- Optimizer: Adam (learning_rate=0.001)

### Autoencoder for Anomaly Detection
- Input: Time-series data of miner metrics
- Architecture:
  - Encoder:
    - LSTM (32 units)
    - LSTM (16 units)
  - Decoder:
    - RepeatVector
    - LSTM (16 units)
    - LSTM (32 units)
    - TimeDistributed Dense
- Loss: Mean Squared Error
- Optimizer: Adam (learning_rate=0.001)

## Data Requirements

For optimal performance, ensure your miner data includes the following metrics:
- hashrate (TH/s)
- temperature (°C)
- fan speed (RPM)
- power consumption (W)
- rejected shares
- accepted shares

Derived features are automatically calculated:
- rejection_rate
- efficiency (hashrate/power)
- temperature_trend
- hashrate_stability
- power_efficiency_trend
