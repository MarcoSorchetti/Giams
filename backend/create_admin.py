import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.database import SessionLocal, engine, Base
from app.models.user_sql import User
from app.core.security import get_password_hash

Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        print("Utente admin gia' esistente — nessuna modifica.")
    else:
        admin = User(
            username="admin",
            password_hash=get_password_hash("Admin123!"),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Utente admin creato con successo! (username: admin, password: Admin123!)")
finally:
    db.close()
