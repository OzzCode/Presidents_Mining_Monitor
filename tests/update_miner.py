from core.db import SessionLocal, Miner

def update_miner(ip, model, nominal_ths, efficiency_j_per_th):
    session = SessionLocal()
    try:
        miner = session.query(Miner).filter_by(miner_ip=ip).first()
        if miner:
            print(f"Updating miner {ip}:")
            print(f"  Old - Model: {miner.model}, TH/s: {miner.nominal_ths}, J/TH: {miner.nominal_efficiency_j_per_th}")
            
            # Update the values
            miner.model = model
            miner.nominal_ths = nominal_ths
            miner.nominal_efficiency_j_per_th = efficiency_j_per_th
            
            session.commit()
            
            # Refresh to show updated values
            session.refresh(miner)
            print(f"  New - Model: {miner.model}, TH/s: {miner.nominal_ths}, J/TH: {miner.nominal_efficiency_j_per_th}")
            print("Update successful!")
        else:
            print(f"No miner found with IP {ip}")
    except Exception as e:
        session.rollback()
        print(f"Error updating miner: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    # Update S19 Pro
    update_miner("192.168.1.202", "Antminer S19 Pro", 110.0, 29.5)
