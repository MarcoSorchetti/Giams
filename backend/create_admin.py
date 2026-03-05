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
        password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
        admin = User(
            username="admin",
            password_hash=get_password_hash(password),
            is_active=True,
            is_admin=True,
        )
        db.add(admin)
        db.commit()
        if os.environ.get("ADMIN_PASSWORD"):
            print("Utente admin creato con successo! (password da variabile ADMIN_PASSWORD)")
        else:
            print("Utente admin creato con successo! (password default — cambiala al primo accesso)")
finally:
    db.close()
