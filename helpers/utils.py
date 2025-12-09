from __future__ import annotations
from pathlib import Path
import csv
from typing import Dict, Tuple
from miner_config import EFFICIENCY_J_PER_TH, EFFICIENCY_MAP

# Cached ASIC efficiency data loaded from static/ASIC_efficiency.csv
# Map of normalized model name -> (nominal_ths, efficiency_j_per_th)
_ASIC_EFF_CACHE: Dict[str, Tuple[float, float]] | None = None


from functools import lru_cache
import re

def _normalize_model(name: str | None, extract_firmware: bool = False) -> str | tuple[str, str | None]:
    """
    Normalize a miner model name for consistent matching and optionally extract firmware version.
    
    Args:
        name: The raw model name (e.g., 'Antminer S19 Pro 110T (Vnish 1.2.6)')
        extract_firmware: If True, return a tuple of (normalized_model, firmware_version)
        
    Returns:
        str: Normalized model name (e.g., 's19 pro') if extract_firmware=False
        tuple: (normalized_model, firmware_version) if extract_firmware=True
    """
    if not name or not isinstance(name, str):
        return ('', None) if extract_firmware else ''
    
    firmware_version = None
    
    # Extract firmware version if present (e.g., '(Vnish 1.2.6)')
    if '(' in name and ')' in name:
        # Removed local 'import re' to avoid shadowing and UnboundLocalError
        fw_match = re.search(r'\(([^)]+)\)', name)
        if fw_match:
            firmware_version = fw_match.group(1).strip()
            # Remove the firmware from the model name for normalization
            name = re.sub(r'\s*\([^)]+\)', '', name).strip()
    
    # Convert to lowercase and strip whitespace
    s = name.strip().lower()
    
    # Remove common vendor prefixes
    prefixes = [
        'bitmain', 'antminer', 'microbt', 'whatsminer', 'canaan', 'avalon',
        'bitmain antminer', 'microbt whatsminer', 'canaan avalon'
    ]
    for prefix in sorted(prefixes, key=len, reverse=True):
        if s.startswith(prefix):
            s = s[len(prefix):].strip()
            break
    
    # Clean up the model string
    s = re.sub(r'[^\w\s]', ' ', s)  # Replace non-word chars with space
    s = re.sub(r'\s+', ' ', s).strip()  # Normalize whitespace
    
    # Common model number patterns (e.g., S19, M30S, A1246)
    model_pattern = r'\b[a-z]?\d+[a-z]*(?:\s*[+x]?\s*\d*[a-z]*)*\b'
    matches = re.findall(model_pattern, s)
    
    if matches:
        # Take the first model number and any subsequent words that are part of the model name
        model_parts = [matches[0]]
        remaining = s.replace(matches[0], '', 1).strip()
        if remaining:
            # Add any words that are likely part of the model name (e.g., 'pro', 'hydro')
            model_keywords = {'pro', 'plus', 'hydro', 'xp', 'j', 's', 't', 'h', 'se', 'le'}
            for word in remaining.split():
                if word in model_keywords or (len(word) <= 3 and word.isalpha()):
                    model_parts.append(word)
                else:
                    break
        normalized_model = ' '.join(model_parts).strip()
    else:
        normalized_model = s.strip()
    
    if extract_firmware:
        return normalized_model, firmware_version
    return normalized_model


@lru_cache(maxsize=1)
def _load_asic_efficiency_csv() -> Dict[str, Tuple[float, float]]:
    """
    Load ASIC efficiency data from CSV file with caching.
    
    Returns:
        Dict mapping normalized model names to (nominal_ths, efficiency_j_per_th) tuples
    """
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


@lru_cache(maxsize=128)
def csv_efficiency_for_model(model: str | None) -> Tuple[float, float]:
    """
    Lookup (nominal_ths, efficiency_j_per_th) from CSV by fuzzy model name.
    
    Args:
        model: The miner model name to look up
        
    Returns:
        Tuple of (nominal_ths, efficiency_j_per_th), or (0.0, 0.0) if not found
    """
    if not model or not isinstance(model, str):
        return 0.0, 0.0
        
    # Get normalized model without firmware version for lookup
    model_key = _normalize_model(model)
    if not model_key:
        return 0.0, 0.0
        
    data = _load_asic_efficiency_csv()
    
    # 1. Exact match
    if model_key in data:
        return data[model_key]
        
    # 2. Try to match with model number variations
    model_parts = set(model_key.split())
    for k, v in data.items():
        key_parts = set(k.split())
        # If all parts of the model key are in the stored key or vice versa
        if model_parts.issubset(key_parts) or key_parts.issubset(model_parts):
            return v
            
    # 3. Try partial matching
    for k, v in data.items():
        if any(part in k for part in model_parts) or any(part in model_key for part in k.split()):
            return v
            
    return 0.0, 0.0


def efficiency_for_model(model: str | None) -> float:
    """
    Get the efficiency (J/TH) for a given miner model.
    
    Args:
        model: The miner model name (can include firmware version in parentheses)
        
    Returns:
        float: Efficiency in J/TH, or the default EFFICIENCY_J_PER_TH if not found
        
    The lookup follows this order:
    1. Check CSV data with fuzzy matching (ignores firmware version)
    2. Check EFFICIENCY_MAP with fuzzy matching (ignores firmware version)
    3. Return EFFICIENCY_J_PER_TH as fallback
    """
    if not model or not isinstance(model, str):
        return EFFICIENCY_J_PER_TH
        
    # 1) Try CSV first (handles firmware version internally)
    _, csv_eff = csv_efficiency_for_model(model)
    if csv_eff and csv_eff > 0:
        return csv_eff
        
    # 2) Fall back to config map with fuzzy matching
    name, _ = _normalize_model(model, extract_firmware=True)  # This will strip firmware version
    if not name:
        return EFFICIENCY_J_PER_TH
        
    # Try exact match first
    for key, val in EFFICIENCY_MAP.items():
        if _normalize_model(key, extract_firmware=True)[0] == name:
            return val
            
    # Try partial matching
    name_parts = set(name.split())
    for key, val in EFFICIENCY_MAP.items():
        key_normalized = _normalize_model(key)
        if not key_normalized:
            continue
            
        # If all parts of the model name are in the key or vice versa
        key_parts = set(key_normalized.split())
        if name_parts.issubset(key_parts) or key_parts.issubset(name_parts):
            return val
            
    # 3) Fall back to default
    return EFFICIENCY_J_PER_TH
