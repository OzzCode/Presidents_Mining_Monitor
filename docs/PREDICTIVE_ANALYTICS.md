# Predictive Analytics Dashboard

## Overview

The Predictive Analytics Dashboard provides AI-powered insights for your mining fleet, including:

- **Miner Failure Prediction**: Machine learning models that predict which miners are at risk of failure
- **BTC Price Forecasting**: 7-day Bitcoin price predictions with confidence intervals
- **Maintenance Scheduling**: Automated recommendations for preventive maintenance
- **Fleet Health Monitoring**: Real-time assessment of overall fleet condition

## Features

### 🤖 Machine Learning Models

#### Failure Prediction Model
- **Algorithm**: Random Forest Regressor
- **Features Used**:
  - Temperature trends and patterns
  - Hashrate stability and performance
  - Power consumption efficiency
  - Pool rejection rates
  - Fan speed variations
  - Time-based patterns (hour, day of week)

#### BTC Price Forecasting Model
- **Algorithm**: Random Forest Regressor with time series features
- **Features Used**:
  - Moving averages (7-day, 30-day)
  - Price volatility indicators
  - Network difficulty changes
  - Historical price patterns
  - Seasonal factors

#### Anomaly Detection
- **Algorithm**: Isolation Forest
- **Purpose**: Detect unusual miner behavior patterns
- **Applications**: Early warning system for equipment issues

### 📊 Dashboard Components

#### Fleet Health Score
- Overall fleet condition (0-100%)
- Calculated from individual miner risk assessments
- Color-coded status indicators

#### Risk Assessment
- Individual miner failure risk scores (0-1)
- Risk levels: LOW, MEDIUM, HIGH, CRITICAL
- Contributing factors and recommendations

#### Maintenance Schedule
- Automated scheduling based on risk assessments
- Priority-based task ordering
- Estimated maintenance duration

#### BTC Price Forecast
- 7-day price predictions
- Confidence intervals (95%)
- Trend indicators (BULLISH, BEARISH, NEUTRAL)

## API Endpoints

### Fleet Analytics
- `GET /api/analytics/fleet-summary` - Comprehensive fleet analytics
- `GET /api/analytics/high-risk-miners` - List of high-risk miners
- `GET /api/analytics/maintenance-schedule` - Recommended maintenance tasks

### Individual Miner Analysis
- `GET /api/analytics/miner-risk/<miner_id>` - Risk assessment for specific miner

### BTC Forecasting
- `GET /api/analytics/btc-forecast?days=7` - Bitcoin price forecast

### Fleet Health Trends
- `GET /api/analytics/fleet-health-trend?days=30` - Historical health data

### Model Management
- `POST /api/analytics/train-models` - Trigger model training/retraining
- `GET /api/analytics/model-status` - Check model availability and status

## Installation & Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Models
The models will be automatically trained on first use, but you can manually trigger training:

```bash
curl -X POST http://localhost:5000/api/analytics/train-models
```

### 3. Access Dashboard
Navigate to: `http://localhost:5000/dashboard/analytics`

## Model Training

### Automatic Training
- Models are automatically trained when first accessed
- Uses historical data from your mining operations
- Requires at least 30 days of data for optimal performance

### Manual Retraining
```bash
# Retrain all models
curl -X POST http://localhost:5000/api/analytics/train-models \
  -H "Content-Type: application/json" \
  -d '{"retrain": true}'
```

### Data Requirements
- **Minimum**: 7 days of miner data
- **Recommended**: 60+ days for failure prediction
- **Optimal**: 180+ days for BTC price forecasting

## Understanding Risk Scores

### Risk Levels
- **LOW (0.0-0.2)**: Normal operation, routine monitoring
- **MEDIUM (0.2-0.5)**: Increased attention, schedule maintenance
- **HIGH (0.5-0.8)**: Priority maintenance required
- **CRITICAL (0.8-1.0)**: Immediate attention needed

### Contributing Factors
- **High Temperature**: >80°C sustained operation
- **Poor Efficiency**: Below expected power/hashrate ratio
- **High Rejection Rate**: >3% pool share rejection
- **Unstable Performance**: High hashrate variability

## Maintenance Recommendations

### Automated Scheduling
The system automatically generates maintenance schedules based on:
- Risk assessment levels
- Predicted failure dates
- Historical maintenance patterns
- Operational priorities

### Priority Levels
- **URGENT**: Critical risk miners (immediate action)
- **HIGH**: High risk miners (within 7 days)
- **MEDIUM**: Medium risk miners (within 14 days)

## BTC Price Forecasting

### Forecast Accuracy
- **Short-term (1-3 days)**: Generally reliable for trend direction
- **Medium-term (4-7 days)**: Useful for operational planning
- **Confidence Intervals**: 95% statistical confidence bounds

### Use Cases
- **Operational Planning**: Adjust mining intensity based on price trends
- **Maintenance Timing**: Schedule during predicted low-price periods
- **Capacity Planning**: Expansion decisions based on price forecasts

## Performance Optimization

### Model Performance
- Models are stored locally using joblib serialization
- Inference is fast (<100ms per prediction)
- Training occurs in background to avoid blocking operations

### Data Efficiency
- Features are calculated on-demand
- Historical data is cached for performance
- Batch processing for fleet-wide analysis

## Troubleshooting

### Common Issues

#### "No training data available"
- Ensure miners have been logging data for at least 7 days
- Check database connectivity
- Verify miner data collection is working

#### "Model not available"
- Trigger manual model training
- Check for sufficient historical data
- Review error logs for training failures

#### Poor prediction accuracy
- Increase training data duration (60+ days recommended)
- Ensure data quality (no extended outages)
- Consider retraining with retrain=true

### Model Status Check
```bash
curl http://localhost:5000/api/analytics/model-status
```

## Future Enhancements

### Planned Features
- **Deep Learning Models**: LSTM networks for time series prediction
- **Multi-variate Analysis**: Cross-miner correlation analysis
- **Environmental Integration**: Weather data for cooling optimization
- **Pool Performance**: Mining pool efficiency predictions
- **Cost Optimization**: Dynamic power management recommendations

### Integration Opportunities
- **Mobile Notifications**: Push alerts for critical predictions
- **Automated Actions**: Auto-restart/shutdown based on predictions
- **Third-party APIs**: Enhanced market data integration
- **Reporting**: Automated PDF reports for stakeholders

## Technical Architecture

### Components
- `core/predictive_analytics.py`: Main analytics engine
- `api/analytics.py`: REST API endpoints
- `templates/analytics.html`: Dashboard interface
- `models/`: Serialized ML models storage

### Dependencies
- **scikit-learn**: Machine learning algorithms
- **pandas**: Data manipulation and analysis
- **numpy**: Numerical computing
- **joblib**: Model serialization

### Data Flow
1. Historical data extraction from database
2. Feature engineering and preprocessing
3. Model training and validation
4. Prediction generation and caching
5. API response formatting
6. Dashboard visualization

## Support

For issues or questions regarding the Predictive Analytics Dashboard:
1. Check the troubleshooting section above
2. Review application logs for error details
3. Ensure all dependencies are properly installed
4. Verify sufficient historical data is available

The predictive analytics system is designed to improve over time as more data becomes available, providing increasingly accurate insights for your mining operations.
