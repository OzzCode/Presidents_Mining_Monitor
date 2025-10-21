from core.db import SessionLocal, Miner
from helpers.utils import _normalize_model, efficiency_for_model, csv_efficiency_for_model

def check_miners():
    session = SessionLocal()
    try:
        print("\n=== Miners in Database ===")
        miners = session.query(Miner).all()
        for miner in miners:
            print(f"\nIP: {miner.miner_ip}")
            print(f"Model: {miner.model}")
            print(f"Normalized: {_normalize_model(miner.model)}")
            print(f"Nominal TH/s: {miner.nominal_ths}")
            print(f"Efficiency (J/TH): {miner.nominal_efficiency_j_per_th}")
            
            # Check what our functions would return
            if miner.model:
                csv_ths, csv_eff = csv_efficiency_for_model(miner.model)
                eff = efficiency_for_model(miner.model)
                print(f"CSV Lookup - TH/s: {csv_ths}, J/TH: {csv_eff}")
                print(f"Efficiency Lookup: {eff} J/TH")
    finally:
        session.close()

if __name__ == "__main__":
    check_miners()
