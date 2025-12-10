from . import db

# Example model - replace with your actual models
class Miner(db.Model):
    __tablename__ = 'miners'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<Miner {self.name}>'
