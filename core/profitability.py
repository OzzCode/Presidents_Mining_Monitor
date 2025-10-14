"""Profitability calculation engine for mining operations."""
from __future__ import annotations
import logging
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List, Any
from sqlalchemy import func, and_
from core.db import SessionLocal, ProfitabilitySnapshot, Metric, Miner
from helpers.utils import csv_efficiency_for_model
from config import DEFAULT_POWER_COST

logger = logging.getLogger(__name__)

# Bitcoin network constants
BLOCKS_PER_DAY = 144  # ~10 min per block
BLOCK_REWARD = 3.125  # Current reward after 2024 halving
SATS_PER_BTC = 100_000_000


class ProfitabilityEngine:
    """Calculate mining profitability metrics."""

    def __init__(self, default_power_cost: float = None):
        """
        Initialize profitability engine.
        
        Args:
            default_power_cost: Default electricity cost in USD per kWh
        """
        self.default_power_cost = default_power_cost if default_power_cost is not None else DEFAULT_POWER_COST
        self.session = SessionLocal()
        self._btc_price_cache = None
        self._btc_price_cache_time = None
        self._network_diff_cache = None
        self._network_diff_cache_time = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()

    def calculate_miner_profitability(self, miner_ip: str, btc_price: Optional[float] = None,
                                      network_difficulty: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """
        Calculate profitability for a specific miner.
        
        Returns dict with profitability metrics or None if insufficient data.
        """
        # Get latest metric
        metric = (
            self.session.query(Metric)
            .filter(Metric.miner_ip == miner_ip)
            .order_by(Metric.timestamp.desc())
            .first()
        )

        if not metric or not metric.hashrate_ths or not metric.power_w:
            logger.warning(f"Insufficient metric data for {miner_ip}")
            return None

        # Get miner metadata
        miner = self.session.query(Miner).filter(Miner.miner_ip == miner_ip).first()

        # Get power cost
        power_cost = self.default_power_cost
        if miner and miner.power_price_usd_per_kwh:
            power_cost = miner.power_price_usd_per_kwh

        # Get BTC price
        if btc_price is None:
            btc_price = self.get_btc_price()

        if not btc_price:
            logger.error("Could not fetch BTC price")
            return None

        # Get network difficulty
        if network_difficulty is None:
            network_difficulty = self.get_network_difficulty()

        # Calculate profitability
        result = self._calculate_profitability(
            hashrate_ths=metric.hashrate_ths,
            power_w=metric.power_w,
            btc_price=btc_price,
            power_cost=power_cost,
            network_difficulty=network_difficulty
        )

        result['miner_ip'] = miner_ip
        result['timestamp'] = datetime.utcnow()

        return result

    def calculate_fleet_profitability(self, btc_price: Optional[float] = None,
                                      network_difficulty: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate aggregate profitability for entire fleet.
        
        Returns dict with fleet-wide profitability metrics.
        """
        # Get latest metrics for all miners
        latest_subq = (
            self.session.query(
                Metric.miner_ip.label('ip'),
                func.max(Metric.timestamp).label('last_ts')
            ).group_by(Metric.miner_ip).subquery()
        )

        metrics = (
            self.session.query(Metric)
            .join(latest_subq, and_(
                Metric.miner_ip == latest_subq.c.ip,
                Metric.timestamp == latest_subq.c.last_ts
            ))
            .all()
        )

        if not metrics:
            logger.warning("No metrics found for fleet profitability calculation")
            return {}

        # Get all miner metadata
        miner_ips = [m.miner_ip for m in metrics]
        miners_dict = {}
        if miner_ips:
            miners = self.session.query(Miner).filter(Miner.miner_ip.in_(miner_ips)).all()
            miners_dict = {m.miner_ip: m for m in miners}

        # Get BTC price and difficulty
        if btc_price is None:
            btc_price = self.get_btc_price()
        if network_difficulty is None:
            network_difficulty = self.get_network_difficulty()

        if not btc_price:
            logger.error("Could not fetch BTC price")
            return {}

        # Aggregate metrics
        total_hashrate = 0.0
        total_power = 0.0
        weighted_power_cost = 0.0
        miner_count = 0

        for metric in metrics:
            if not metric.hashrate_ths or not metric.power_w:
                continue

            miner = miners_dict.get(metric.miner_ip)
            power_cost = self.default_power_cost
            if miner and miner.power_price_usd_per_kwh:
                power_cost = miner.power_price_usd_per_kwh

            total_hashrate += metric.hashrate_ths
            total_power += metric.power_w
            weighted_power_cost += metric.power_w * power_cost
            miner_count += 1

        if total_power == 0:
            return {}

        # Calculate average power cost weighted by power consumption
        avg_power_cost = weighted_power_cost / total_power

        # Calculate fleet profitability
        result = self._calculate_profitability(
            hashrate_ths=total_hashrate,
            power_w=total_power,
            btc_price=btc_price,
            power_cost=avg_power_cost,
            network_difficulty=network_difficulty
        )

        result['miner_count'] = miner_count
        result['timestamp'] = datetime.utcnow()

        return result

    def _calculate_profitability(self, hashrate_ths: float, power_w: float,
                                 btc_price: float, power_cost: float,
                                 network_difficulty: Optional[float] = None) -> Dict[str, Any]:
        """
        Core profitability calculation logic.
        
        Args:
            hashrate_ths: Hashrate in TH/s
            power_w: Power consumption in watts
            btc_price: BTC price in USD
            power_cost: Electricity cost in USD per kWh
            network_difficulty: Network difficulty (optional, uses estimate if not provided)
        
        Returns:
            Dict with profitability metrics
        """
        # Convert power to kW for daily cost calculation
        power_kw = power_w / 1000.0
        daily_power_kwh = power_kw * 24
        daily_power_cost = daily_power_kwh * power_cost

        # Estimate daily BTC revenue
        # Formula: (hashrate / network_hashrate) * blocks_per_day * block_reward
        # Network hashrate can be derived from difficulty
        estimated_btc_per_day = 0.0

        if network_difficulty:
            # Network hashrate (TH/s) = difficulty * 2^32 / 600 / 10^12
            network_hashrate_ths = (network_difficulty * (2 ** 32)) / 600 / (10 ** 12)

            # Miner's share of network
            network_share = hashrate_ths / network_hashrate_ths if network_hashrate_ths > 0 else 0

            # Daily BTC reward
            daily_network_btc = BLOCKS_PER_DAY * BLOCK_REWARD
            estimated_btc_per_day = network_share * daily_network_btc
        else:
            # Simplified estimate without difficulty (less accurate)
            # Assume ~500 EH/s network hashrate as rough estimate
            estimated_network_hashrate_ths = 500_000_000  # 500 EH/s
            network_share = hashrate_ths / estimated_network_hashrate_ths
            daily_network_btc = BLOCKS_PER_DAY * BLOCK_REWARD
            estimated_btc_per_day = network_share * daily_network_btc

        # Revenue in USD
        estimated_revenue_usd_per_day = estimated_btc_per_day * btc_price

        # Profitability
        daily_profit_usd = estimated_revenue_usd_per_day - daily_power_cost

        # Profit margin percentage
        profit_margin_pct = 0.0
        if estimated_revenue_usd_per_day > 0:
            profit_margin_pct = (daily_profit_usd / estimated_revenue_usd_per_day) * 100

        # Break-even BTC price (price at which profit = 0)
        break_even_btc_price = 0.0
        if estimated_btc_per_day > 0:
            break_even_btc_price = daily_power_cost / estimated_btc_per_day

        # Efficiency metrics
        efficiency_j_per_th = (power_w / hashrate_ths) if hashrate_ths > 0 else 0

        return {
            'btc_price_usd': btc_price,
            'network_difficulty': network_difficulty,
            'hashrate_ths': hashrate_ths,
            'power_w': power_w,
            'power_cost_usd_per_kwh': power_cost,
            'daily_power_kwh': daily_power_kwh,
            'daily_power_cost_usd': daily_power_cost,
            'estimated_btc_per_day': estimated_btc_per_day,
            'estimated_revenue_usd_per_day': estimated_revenue_usd_per_day,
            'daily_profit_usd': daily_profit_usd,
            'profit_margin_pct': profit_margin_pct,
            'break_even_btc_price': break_even_btc_price,
            'efficiency_j_per_th': efficiency_j_per_th,
            # Extrapolated metrics
            'monthly_profit_usd': daily_profit_usd * 30,
            'yearly_profit_usd': daily_profit_usd * 365,
            'monthly_btc': estimated_btc_per_day * 30,
            'yearly_btc': estimated_btc_per_day * 365
        }

    def get_btc_price(self, force_refresh: bool = False) -> Optional[float]:
        """
        Get current BTC price in USD with caching.
        
        Args:
            force_refresh: Force refresh even if cache is valid
        
        Returns:
            BTC price in USD or None if fetch fails
        """
        # Check cache (5 minute TTL)
        if not force_refresh and self._btc_price_cache and self._btc_price_cache_time:
            age = (datetime.now(timezone.utc) - self._btc_price_cache_time).total_seconds()
            if age < 300:  # 5 minutes
                return self._btc_price_cache

        try:
            # Try CoinGecko first
            response = requests.get(
                'https://api.coingecko.com/api/v3/simple/price',
                params={'ids': 'bitcoin', 'vs_currencies': 'usd'},
                timeout=5
            )

            if response.ok:
                data = response.json()
                price = data.get('bitcoin', {}).get('usd')
                if price:
                    self._btc_price_cache = float(price)
                    self._btc_price_cache_time = datetime.now(timezone.utc)
                    return self._btc_price_cache
        except Exception as e:
            logger.warning(f"CoinGecko API failed: {e}")

        try:
            # Fallback to CoinCap
            response = requests.get(
                'https://api.coincap.io/v2/assets/bitcoin',
                timeout=5
            )

            if response.ok:
                data = response.json()
                price = data.get('data', {}).get('priceUsd')
                if price:
                    self._btc_price_cache = float(price)
                    self._btc_price_cache_time = datetime.now(timezone.utc)
                    return self._btc_price_cache
        except Exception as e:
            logger.warning(f"CoinCap API failed: {e}")

        logger.error("Failed to fetch BTC price from all sources")
        return None

    def get_network_difficulty(self, force_refresh: bool = False) -> Optional[float]:
        """
        Get current Bitcoin network difficulty with caching.
        
        Args:
            force_refresh: Force refresh even if cache is valid
        
        Returns:
            Network difficulty or None if fetch fails
        """
        # Check cache (30 minute TTL - difficulty changes every ~2 weeks)
        if not force_refresh and self._network_diff_cache and self._network_diff_cache_time:
            age = (datetime.now(timezone.utc) - self._network_diff_cache_time).total_seconds()
            if age < 1800:  # 30 minutes
                return self._network_diff_cache

        try:
            # Try blockchain.info
            response = requests.get(
                'https://blockchain.info/q/getdifficulty',
                timeout=5
            )

            if response.ok:
                difficulty = float(response.text.strip())
                self._network_diff_cache = difficulty
                self._network_diff_cache_time = datetime.now(timezone.utc)
                return difficulty
        except Exception as e:
            logger.warning(f"Blockchain.info API failed: {e}")

        try:
            # Fallback to mempool.space
            response = requests.get(
                'https://mempool.space/api/v1/difficulty-adjustment',
                timeout=5
            )

            if response.ok:
                data = response.json()
                difficulty = data.get('currentDifficulty')
                if difficulty:
                    self._network_diff_cache = float(difficulty)
                    self._network_diff_cache_time = datetime.now(timezone.utc)
                    return self._network_diff_cache
        except Exception as e:
            logger.warning(f"Mempool.space API failed: {e}")

        logger.warning("Failed to fetch network difficulty, using estimate")
        return None

    def save_snapshot(self, profitability_data: Dict[str, Any], miner_ip: Optional[str] = None) -> bool:
        """
        Save a profitability snapshot to the database.
        
        Args:
            profitability_data: Dict from calculate_*_profitability methods
            miner_ip: IP address for per-miner snapshot, None for fleet-wide
        
        Returns:
            True if saved successfully
        """
        try:
            snapshot = ProfitabilitySnapshot(
                miner_ip=miner_ip,
                btc_price_usd=profitability_data.get('btc_price_usd'),
                network_difficulty=profitability_data.get('network_difficulty'),
                hashrate_ths=profitability_data.get('hashrate_ths'),
                power_w=profitability_data.get('power_w'),
                power_cost_usd_per_kwh=profitability_data.get('power_cost_usd_per_kwh'),
                daily_power_cost_usd=profitability_data.get('daily_power_cost_usd'),
                estimated_btc_per_day=profitability_data.get('estimated_btc_per_day'),
                estimated_revenue_usd_per_day=profitability_data.get('estimated_revenue_usd_per_day'),
                daily_profit_usd=profitability_data.get('daily_profit_usd'),
                profit_margin_pct=profitability_data.get('profit_margin_pct'),
                break_even_btc_price=profitability_data.get('break_even_btc_price')
            )

            self.session.add(snapshot)
            self.session.commit()
            return True

        except Exception as e:
            logger.exception("Failed to save profitability snapshot", exc_info=e)
            self.session.rollback()
            return False

    def get_profitability_history(self, miner_ip: Optional[str] = None,
                                  days: int = 7) -> List[ProfitabilitySnapshot]:
        """
        Get historical profitability snapshots.

        Args:
            miner_ip: IP address for per-miner history, None for fleet-wide
            days: Number of days of history to retrieve

        Returns:
            List of ProfitabilitySnapshot objects
        """
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = self.session.query(ProfitabilitySnapshot).filter(
            ProfitabilitySnapshot.timestamp >= cutoff
        )

        if miner_ip:
            query = query.filter(ProfitabilitySnapshot.miner_ip == miner_ip)
        else:
            query = query.filter(ProfitabilitySnapshot.miner_ip.is_(None))

        return query.order_by(ProfitabilitySnapshot.timestamp.asc()).all()

    def get_active_miners(self, hours_threshold: int = 1) -> List[str]:
        """
        Get list of miners that have been active within the specified time window.

        Args:
            hours_threshold: Hours within which a miner must have reported data

        Returns:
            List of miner IP addresses that are currently active
        """
        cutoff = datetime.utcnow() - timedelta(hours=hours_threshold)

        # Get miners with recent metrics
        recent_metrics = (
            self.session.query(Metric.miner_ip)
            .filter(Metric.timestamp >= cutoff)
            .distinct()
            .all()
        )

        return [m.miner_ip for m in recent_metrics if m.miner_ip]
