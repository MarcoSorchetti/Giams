from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_sql import User
from app.models.user import UserCreate, UserUpdate, UserOut
from app.core.security import get_password_hash, get_current_user
from app.services.audit import log_audit


router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")
    return user


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_in: UserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(status_code=400, detail="Username gia' esistente.")
    db_user = User(
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
        is_admin=user_in.is_admin,
    )
    db.add(db_user)
    db.flush()
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="creato", entita="utente", entita_id=db_user.id, codice_entita=db_user.username)
    db.commit()
    db.refresh(db_user)
    return db_user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, user_in: UserUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")
    if user_in.username and user_in.username != user.username:
        if db.query(User).filter(User.username == user_in.username, User.id != user_id).first():
            raise HTTPException(status_code=400, detail="Username gia' esistente.")
        user.username = user_in.username
    if user_in.password:
        user.password_hash = get_password_hash(user_in.password)
    if user_in.is_active is not None:
        user.is_active = user_in.is_active
    if user_in.is_admin is not None:
        user.is_admin = user_in.is_admin
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="modificato", entita="utente", entita_id=user.id, codice_entita=user.username)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato.")
    log_audit(db, user_id=current_user.id, username=current_user.username,
              azione="eliminato", entita="utente", entita_id=user_id, codice_entita=user.username)
    db.delete(user)
    db.commit()
