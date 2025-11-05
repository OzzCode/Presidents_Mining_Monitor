"""
Comprehensive test script for Presidents Mining Monitor
Tests all major functions and endpoints using live miner at 192.168.1.96
"""
import requests
import json
import time
from datetime import datetime
from core.miner import MinerClient, MinerError
from core.db import SessionLocal, Metric, Miner, Alert, AlertRule
from config import MINER_IP_RANGE, POLL_INTERVAL

# Test configuration
LIVE_MINER_IP = "192.168.1.194"
BASE_URL = "http://localhost:5000"
TEST_RESULTS = []


class TestResult:
    def __init__(self, category, test_name, status, message="", details=None):
        self.category = category
        self.test_name = test_name
        self.status = status  # "PASS", "FAIL", "WARN"
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.utcnow().isoformat()


def log_result(category, test_name, status, message="", details=None):
    """Log a test result"""
    result = TestResult(category, test_name, status, message, details)
    TEST_RESULTS.append(result)
    
    # Color coding for console output
    colors = {"PASS": "\033[92m", "FAIL": "\033[91m", "WARN": "\033[93m"}
    reset = "\033[0m"
    color = colors.get(status, "")
    
    print(f"{color}[{status}]{reset} {category} - {test_name}: {message}")
    if details:
        print(f"      Details: {json.dumps(details, indent=2)}")


def test_miner_connection():
    """Test direct connection to live miner"""
    print("\n=== Testing Miner Connection ===")
    
    try:
        client = MinerClient(LIVE_MINER_IP, timeout=5.0)
        
        # Test summary command
        try:
            summary = client.get_summary()
            log_result("Miner Connection", "Get Summary", "PASS", 
                      f"Successfully retrieved summary from {LIVE_MINER_IP}",
                      {"summary_keys": list(summary.keys())})
        except Exception as e:
            log_result("Miner Connection", "Get Summary", "FAIL", str(e))
        
        # Test stats command
        try:
            stats = client.get_stats()
            log_result("Miner Connection", "Get Stats", "PASS", 
                      f"Successfully retrieved stats from {LIVE_MINER_IP}",
                      {"stats_keys": list(stats.keys())})
        except Exception as e:
            log_result("Miner Connection", "Get Stats", "FAIL", str(e))
        
        # Test pools command
        try:
            pools = client.get_pools()
            log_result("Miner Connection", "Get Pools", "PASS", 
                      f"Successfully retrieved pools from {LIVE_MINER_IP}",
                      {"pools_count": len(pools.get("POOLS", []))})
        except Exception as e:
            log_result("Miner Connection", "Get Pools", "FAIL", str(e))
        
        # Test version command
        try:
            version = client.get_version()
            log_result("Miner Connection", "Get Version", "PASS", 
                      f"Successfully retrieved version from {LIVE_MINER_IP}",
                      {"version_keys": list(version.keys())})
        except Exception as e:
            log_result("Miner Connection", "Get Version", "FAIL", str(e))
        
        # Test normalized data fetch
        try:
            normalized = client.fetch_normalized()
            log_result("Miner Connection", "Fetch Normalized", "PASS", 
                      "Successfully fetched normalized data",
                      {
                          "hashrate_ths": normalized.get("hashrate_ths"),
                          "avg_temp_c": normalized.get("avg_temp_c"),
                          "power_w": normalized.get("power_w"),
                          "model": normalized.get("model")
                      })
        except Exception as e:
            log_result("Miner Connection", "Fetch Normalized", "FAIL", str(e))
            
    except Exception as e:
        log_result("Miner Connection", "Client Init", "FAIL", str(e))


def test_api_endpoints():
    """Test all Flask API endpoints"""
    print("\n=== Testing API Endpoints ===")
    
    # Test health endpoints
    try:
        resp = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if resp.status_code == 200:
            log_result("API Endpoints", "Health Check", "PASS", 
                      "Health endpoint responding", {"response": resp.json()})
        else:
            log_result("API Endpoints", "Health Check", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Health Check", "FAIL", str(e))
    
    # Test readiness endpoint
    try:
        resp = requests.get(f"{BASE_URL}/readyz", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            log_result("API Endpoints", "Readiness Check", "PASS", 
                      "Readiness endpoint responding", data)
        else:
            log_result("API Endpoints", "Readiness Check", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Readiness Check", "FAIL", str(e))
    
    # Test /api/miners endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/miners", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            miners = data.get("miners", [])
            log_result("API Endpoints", "Get Miners", "PASS", 
                      f"Found {len(miners)} miners", 
                      {"miner_count": len(miners), "sample": miners[0] if miners else None})
        else:
            log_result("API Endpoints", "Get Miners", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Get Miners", "FAIL", str(e))
    
    # Test /api/summary endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/summary", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("API Endpoints", "Get Summary", "PASS", 
                      "Summary endpoint responding", 
                      {
                          "total_hashrate": data.get("total_hashrate_ths"),
                          "total_power": data.get("total_power_w"),
                          "miner_count": data.get("miner_count")
                      })
        else:
            log_result("API Endpoints", "Get Summary", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Get Summary", "FAIL", str(e))
    
    # Test /api/metrics endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/metrics?limit=10", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            metrics = data.get("metrics", [])
            log_result("API Endpoints", "Get Metrics", "PASS", 
                      f"Retrieved {len(metrics)} metrics", 
                      {"count": len(metrics)})
        else:
            log_result("API Endpoints", "Get Metrics", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Get Metrics", "FAIL", str(e))
    
    # Test /api/miners/summary endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/miners/summary", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("API Endpoints", "Get Miners Summary", "PASS", 
                      "Miners summary endpoint responding", 
                      {"miners": len(data.get("miners", []))})
        else:
            log_result("API Endpoints", "Get Miners Summary", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Get Miners Summary", "FAIL", str(e))
    
    # Test /api/miners/current endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/miners/current", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("API Endpoints", "Get Current Miners", "PASS", 
                      "Current miners endpoint responding", 
                      {"miners": len(data.get("miners", []))})
        else:
            log_result("API Endpoints", "Get Current Miners", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("API Endpoints", "Get Current Miners", "FAIL", str(e))


def test_alerts_api():
    """Test alerts and profitability API endpoints"""
    print("\n=== Testing Alerts & Profitability API ===")
    
    # Test alerts endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/alerts", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Alerts API", "Get Alerts", "PASS", 
                      f"Found {len(data.get('alerts', []))} alerts")
        else:
            log_result("Alerts API", "Get Alerts", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Alerts API", "Get Alerts", "FAIL", str(e))
    
    # Test alert rules endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/alerts/rules", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Alerts API", "Get Alert Rules", "PASS", 
                      f"Found {len(data.get('rules', []))} rules")
        else:
            log_result("Alerts API", "Get Alert Rules", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Alerts API", "Get Alert Rules", "FAIL", str(e))
    
    # Test profitability endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/profitability/current", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Profitability API", "Get Profitability", "PASS", 
                      "Profitability endpoint responding",
                      {
                          "daily_revenue": data.get("daily_revenue_usd"),
                          "daily_cost": data.get("daily_cost_usd"),
                          "daily_profit": data.get("daily_profit_usd")
                      })
        else:
            log_result("Profitability API", "Get Profitability", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Profitability API", "Get Profitability", "FAIL", str(e))


def test_analytics_api():
    """Test predictive analytics API endpoints"""
    print("\n=== Testing Predictive Analytics API ===")
    
    # Test fleet summary
    try:
        resp = requests.get(f"{BASE_URL}/api/analytics/fleet-summary", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Analytics API", "Fleet Summary", "PASS", 
                      "Fleet summary endpoint responding",
                      {
                          "fleet_health": data.get("fleet_health_score"),
                          "total_miners": data.get("total_miners"),
                          "high_risk_count": data.get("high_risk_count")
                      })
        else:
            log_result("Analytics API", "Fleet Summary", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Analytics API", "Fleet Summary", "FAIL", str(e))
    
    # Test BTC forecast
    try:
        resp = requests.get(f"{BASE_URL}/api/analytics/btc-forecast", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Analytics API", "BTC Forecast", "PASS", 
                      "BTC forecast endpoint responding",
                      {"forecast_days": len(data.get("forecast", []))})
        else:
            log_result("Analytics API", "BTC Forecast", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Analytics API", "BTC Forecast", "FAIL", str(e))
    
    # Test high-risk miners
    try:
        resp = requests.get(f"{BASE_URL}/api/analytics/high-risk-miners", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Analytics API", "High Risk Miners", "PASS", 
                      f"Found {len(data.get('miners', []))} high-risk miners")
        else:
            log_result("Analytics API", "High Risk Miners", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Analytics API", "High Risk Miners", "FAIL", str(e))


def test_electricity_api():
    """Test electricity cost tracking API"""
    print("\n=== Testing Electricity API ===")
    
    # Test electricity rates
    try:
        resp = requests.get(f"{BASE_URL}/api/electricity/rates", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Electricity API", "Get Rates", "PASS", 
                      f"Found {len(data.get('rates', []))} electricity rates")
        else:
            log_result("Electricity API", "Get Rates", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Electricity API", "Get Rates", "FAIL", str(e))
    
    # Test cost records
    try:
        resp = requests.get(f"{BASE_URL}/api/electricity/costs?limit=10", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Electricity API", "Get Costs", "PASS", 
                      f"Retrieved {len(data.get('costs', []))} cost records")
        else:
            log_result("Electricity API", "Get Costs", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Electricity API", "Get Costs", "FAIL", str(e))


def test_remote_control_api():
    """Test remote control API (non-destructive tests only)"""
    print("\n=== Testing Remote Control API ===")
    
    # Test command history endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/remote/history?limit=10", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Remote Control API", "Get Command History", "PASS", 
                      f"Retrieved {len(data.get('commands', []))} commands")
        else:
            log_result("Remote Control API", "Get Command History", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Remote Control API", "Get Command History", "FAIL", str(e))
    
    # Test power schedules endpoint
    try:
        resp = requests.get(f"{BASE_URL}/api/remote/schedules", timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            log_result("Remote Control API", "Get Power Schedules", "PASS", 
                      f"Found {len(data.get('schedules', []))} schedules")
        else:
            log_result("Remote Control API", "Get Power Schedules", "FAIL", 
                      f"Status code: {resp.status_code}")
    except Exception as e:
        log_result("Remote Control API", "Get Power Schedules", "FAIL", str(e))


def test_database_operations():
    """Test database operations"""
    print("\n=== Testing Database Operations ===")
    
    session = SessionLocal()
    try:
        # Test metrics table
        try:
            metric_count = session.query(Metric).count()
            recent_metrics = session.query(Metric).order_by(Metric.timestamp.desc()).limit(5).all()
            log_result("Database", "Metrics Table", "PASS", 
                      f"Found {metric_count} total metrics",
                      {"recent_count": len(recent_metrics)})
        except Exception as e:
            log_result("Database", "Metrics Table", "FAIL", str(e))
        
        # Test miners table
        try:
            miner_count = session.query(Miner).count()
            miners = session.query(Miner).all()
            log_result("Database", "Miners Table", "PASS", 
                      f"Found {miner_count} miners in database",
                      {"miner_ips": [m.miner_ip for m in miners[:5]]})
        except Exception as e:
            log_result("Database", "Miners Table", "FAIL", str(e))
        
        # Test alerts table
        try:
            alert_count = session.query(Alert).count()
            active_alerts = session.query(Alert).filter(Alert.status == 'active').count()
            log_result("Database", "Alerts Table", "PASS", 
                      f"Found {alert_count} total alerts ({active_alerts} active)")
        except Exception as e:
            log_result("Database", "Alerts Table", "FAIL", str(e))
        
        # Test alert rules table
        try:
            rule_count = session.query(AlertRule).count()
            active_rules = session.query(AlertRule).filter(AlertRule.enabled == True).count()
            log_result("Database", "Alert Rules Table", "PASS", 
                      f"Found {rule_count} rules ({active_rules} enabled)")
        except Exception as e:
            log_result("Database", "Alert Rules Table", "FAIL", str(e))
            
    finally:
        session.close()


def test_web_pages():
    """Test web page accessibility"""
    print("\n=== Testing Web Pages ===")
    
    pages = [
        ("/", "Home Page"),
        ("/dashboard/", "Dashboard"),
        ("/dashboard/miners", "Miners Page"),
        ("/dashboard/logs", "Logs Page"),
        ("/api/alerts/page", "Alerts Page"),
        ("/api/profitability/page", "Profitability Page"),
        ("/api/analytics/page", "Analytics Page"),
        ("/api/electricity/page", "Electricity Page"),
        ("/api/remote/page", "Remote Control Page"),
    ]
    
    for path, name in pages:
        try:
            resp = requests.get(f"{BASE_URL}{path}", timeout=10)
            if resp.status_code == 200:
                log_result("Web Pages", name, "PASS", 
                          f"Page accessible at {path}")
            else:
                log_result("Web Pages", name, "FAIL", 
                          f"Status code: {resp.status_code}")
        except Exception as e:
            log_result("Web Pages", name, "FAIL", str(e))


def generate_report():
    """Generate comprehensive test report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE TEST REPORT")
    print("="*80)
    
    # Count results by status
    pass_count = sum(1 for r in TEST_RESULTS if r.status == "PASS")
    fail_count = sum(1 for r in TEST_RESULTS if r.status == "FAIL")
    warn_count = sum(1 for r in TEST_RESULTS if r.status == "WARN")
    total_count = len(TEST_RESULTS)
    
    print(f"\nTotal Tests: {total_count}")
    print(f"[PASS] Passed: {pass_count} ({pass_count/total_count*100:.1f}%)")
    print(f"[FAIL] Failed: {fail_count} ({fail_count/total_count*100:.1f}%)")
    print(f"[WARN] Warnings: {warn_count} ({warn_count/total_count*100:.1f}%)")
    
    # Group by category
    categories = {}
    for result in TEST_RESULTS:
        if result.category not in categories:
            categories[result.category] = {"PASS": 0, "FAIL": 0, "WARN": 0}
        categories[result.category][result.status] += 1
    
    print("\n" + "-"*80)
    print("Results by Category:")
    print("-"*80)
    for category, counts in sorted(categories.items()):
        total = sum(counts.values())
        print(f"\n{category}:")
        print(f"  [PASS] {counts['PASS']}/{total} passed")
        if counts['FAIL'] > 0:
            print(f"  [FAIL] {counts['FAIL']}/{total} failed")
        if counts['WARN'] > 0:
            print(f"  [WARN] {counts['WARN']}/{total} warnings")
    
    # Show failures
    failures = [r for r in TEST_RESULTS if r.status == "FAIL"]
    if failures:
        print("\n" + "-"*80)
        print("Failed Tests:")
        print("-"*80)
        for result in failures:
            print(f"\n[X] {result.category} - {result.test_name}")
            print(f"  Error: {result.message}")
    
    # Save detailed report to file
    report_file = "../test_report.json"
    with open(report_file, "w") as f:
        json.dump([{
            "category": r.category,
            "test_name": r.test_name,
            "status": r.status,
            "message": r.message,
            "details": r.details,
            "timestamp": r.timestamp
        } for r in TEST_RESULTS], f, indent=2)
    
    print(f"\n\nDetailed report saved to: {report_file}")
    print("="*80)


def main():
    """Run all tests"""
    print("="*80)
    print("PRESIDENTS MINING MONITOR - COMPREHENSIVE TEST SUITE")
    print("="*80)
    print(f"Test started at: {datetime.utcnow().isoformat()}")
    print(f"Live miner IP: {LIVE_MINER_IP}")
    print(f"Base URL: {BASE_URL}")
    print(f"Configured IP range: {MINER_IP_RANGE}")
    print(f"Poll interval: {POLL_INTERVAL}s")
    
    # Run all test suites
    test_miner_connection()
    test_api_endpoints()
    test_alerts_api()
    test_analytics_api()
    test_electricity_api()
    test_remote_control_api()
    test_database_operations()
    test_web_pages()
    
    # Generate final report
    generate_report()


if __name__ == "__main__":
    main()
