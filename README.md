## Project Documentation: Antminer Monitor
### 1. Introduction
The Antminer Monitor is a Python-based dashboard for monitoring Bitmain Antminer ASIC miners. It provides a central location to view miner status, statistics, and logs.
### 2. User Guide
#### 2.1. Getting Started
1. **Setup:**
    - Copy to `.env` and configure the necessary environment variables (see section 3.1 for details). `.env.example`
    - Install dependencies: `pip install -r requirements.txt`
    - Run the application: `python main.py`

2. **Accessing the Dashboard:** Open your web browser and navigate to `http://localhost:5000`.

#### 2.2. Dashboard Overview
The dashboard provides the following views:
- **Home:** A general overview of the monitoring system.
- **Miner List:** Displays a list of connected miners with their status, age, model, IP address, and stale status.
- **Logs:** Displays application logs for debugging and monitoring.

### 3. Developer Guide
#### 3.1. Environment Configuration
The application relies on environment variables for configuration. The following variables are used:
- **(To be populated based on `.env.example` - you need to document these specifically)**. Example: `API_KEY`, `DATABASE_URL`, etc. **Ensure your database connection details are correct in the `.env` file.**


#### 3.2. Project Structure
- : Contains API endpoints. `api/`
- `core/`: Core application logic (e.g., database interaction).
- : Routes and logic for the web dashboard. `dashboard/`
- `db_files/`: Database files (SQLite).
- `templates/`: HTML templates for the dashboard.
- : The main application entry point. `main.py`
- : Background task scheduler. `scheduler.py`

#### 3.3. API Endpoints
- : Returns a JSON list of miners with their status information. **/api/miners**
``` json
    [
      {
        "is_stale": true,
        "age_sec": 120,
        "status": "running",
        "model": "Antminer S19 Pro",
        "ip": "192.168.1.100",
        "last_seen": "2024-09-08T10:00:00"
      },
      {
        "is_stale": false,
        "age_sec": 60,
        "status": "idle",
        "model": "Antminer S17 Pro",
        "ip": "192.168.1.101",
        "last_seen": "2024-09-08T10:01:00"
      }
    ]
```
#### 3.4. Code Details (Based on ) `main.py`
The file serves as the entry point of the application. It handles: `main.py`
- Flask application creation and configuration.
- Registration of API blueprints and dashboard routes.
- Error handling.
- Database initialization.
- Starting the background scheduler.

Key parts of the code:
- : This function initializes the Flask application, registers blueprints, and defines routes. `create_app()`
- route: This endpoint retrieves miner information using the function and returns it as a JSON response. `/api/miners``get_miners()`
- Error handling: The application uses a global error handler to catch unexpected exceptions and return a generic error response.

Here's a more detailed breakdown of the functions in : `main.py`
- : Renders the template. `home()``home.html`
- : Fetches miner data and returns it as JSON. Includes error handling to prevent internal details from being exposed. `api_miners()`
- : Renders the template. `logs()``logs.html`
- `handle_exception()`: Handles unhandled exceptions.

### 4. Contributing

### 5. License
MIT License (See `LICENSE` file for details).
