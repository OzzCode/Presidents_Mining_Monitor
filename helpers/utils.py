from __future__ import annotations
from pathlib import Path
import csv
from typing import Dict, Tuple

from config import EFFICIENCY_J_PER_TH, EFFICIENCY_MAP

# Cached ASIC efficiency data loaded from static/ASIC_efficiency.csv
# Map of normalized model name -> (nominal_ths, efficiency_j_per_th)
_ASIC_EFF_CACHE: Dict[str, Tuple[float, float]] | None = None


def _normalize_model(name: str | None) -> str:
    if not name:
        return ''
    # Lower-case, strip vendor prefixes and spaces/symbols to allow loose matching
    s = name.strip().lower()
    # Common vendor prefixes to trim for matching
    prefixes = [
        'bitmain ', 'bitmain antminer ', 'antminer ',
        'microbt ', 'whatsminer ', 'microbt whatsminer ',
        'canaan ', 'canaan avalon ', 'avalon '
    ]
    for p in prefixes:
        if s.startswith(p):
            s = s[len(p):]
            break
    # Remove spaces and plus signs for easier matching
    s = ''.join(ch for ch in s if ch.isalnum())
    return s


def _load_asic_efficiency_csv() -> Dict[str, Tuple[float, float]]:
    global _ASIC_EFF_CACHE
    if _ASIC_EFF_CACHE is not None:
        return _ASIC_EFF_CACHE

    cache: Dict[str, Tuple[float, float]] = {}
    try:
        # static is at project_root/static; helpers is at project_root/helpers
        csv_path = Path(__file__).resolve().parents[1] / 'static' / 'ASIC_efficiency.csv'
        if csv_path.exists():
            with csv_path.open(newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    model = (row.get('Model') or '').strip()
                    ths_str = (row.get('Hashrate (TH/s)') or '').strip()
                    eff_str = (row.get('Efficiency (J/TH)') or '').strip()
                    if not model:
                        continue
                    try:
                        nominal_ths = float(ths_str) if ths_str else 0.0
                    except ValueError:
                        nominal_ths = 0.0
                    try:
                        eff = float(eff_str) if eff_str else 0.0
                    except ValueError:
                        eff = 0.0
                    key = _normalize_model(model)
                    if key:
                        cache[key] = (nominal_ths, eff)
    except Exception:
        # Fail silently; we'll fall back to config map
        cache = {}

    _ASIC_EFF_CACHE = cache
    return cache


def csv_efficiency_for_model(model: str | None) -> Tuple[float, float]:
    """
    Lookup (nominal_ths, efficiency_j_per_th) from CSV by fuzzy model name.
    Returns (0.0, 0.0) if not found or CSV missing.
    """
    model_key = _normalize_model(model)
    if not model_key:
        return 0.0, 0.0
    data = _load_asic_efficiency_csv()
    if model_key in data:
        return data[model_key]
    # Try contains-based match among keys for looser matching
    for k, v in data.items():
        if k in model_key or model_key in k:
            return v
    return 0.0, 0.0


def efficiency_for_model(model: str | None) -> float:
    """
    Return J/TH for a given model prioritizing CSV values; falls back to config map
    and finally the global default EFFICIENCY_J_PER_TH.
    """
    # 1) CSV first
    _, csv_eff = csv_efficiency_for_model(model)
    if csv_eff and csv_eff > 0:
        return csv_eff

    # 2) Config map fuzzy match
    if not model:
        return EFFICIENCY_J_PER_TH

    name = model.strip().lower()
    # try exact-ish keys first
    for key, val in EFFICIENCY_MAP.items():
        if key.lower() == name:
            return val
    # fuzzy contains match (handles 'Antminer S19 Pro', 'S19 Pro 110T', etc.)
    for key, val in EFFICIENCY_MAP.items():
        if key.lower() in name:
            return val

    # 3) Fallback default
    return EFFICIENCY_J_PER_TH
