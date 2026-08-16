from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
import models
import database
import auth

router = APIRouter(tags=["Chat"])

@router.post("/chat/send")
def send_message(
    receiver_id: int, 
    book_id: int, 
    message: str, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    if current_user.id == receiver_id:
        raise HTTPException(status_code=400, detail="You cannot chat with yourself.")
        
    msg = models.ChatMessage(
        sender_id=current_user.id, 
        receiver_id=receiver_id, 
        book_id=book_id, 
        message=message
    )
    db.add(msg)
    db.commit()
    return {"status": "sent"}

@router.get("/chat/history/{book_id}/{other_user_id}")
def get_chat_history(
    book_id: int, 
    other_user_id: int, 
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.ChatMessage).filter(
        models.ChatMessage.book_id == book_id,
        or_(
            (models.ChatMessage.sender_id == current_user.id) & (models.ChatMessage.receiver_id == other_user_id),
            (models.ChatMessage.sender_id == other_user_id) & (models.ChatMessage.receiver_id == current_user.id)
        )
    ).order_by(models.ChatMessage.timestamp.asc()).all()

@router.get("/chat/channels")
def get_active_chat_channels(
    db: Session = Depends(database.get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    # Pull distinct message threads where the logged-in student is a participant
    messages = db.query(models.ChatMessage).filter(
        or_(models.ChatMessage.sender_id == current_user.id, models.ChatMessage.receiver_id == current_user.id)
    ).all()
    
    channels = []
    seen = set()
    for m in messages:
        partner_id = m.receiver_id if m.sender_id == current_user.id else m.sender_id
        uid = f"{m.book_id}_{partner_id}"
        if uid not in seen:
            seen.add(uid)
            book = db.query(models.Book).filter(models.Book.id == m.book_id).first()
            partner = db.query(models.User).filter(models.User.id == partner_id).first()
            if book and partner:
                channels.append({
                    "book_id": m.book_id, 
                    "book_title": book.title,
                    "partner_id": partner_id, 
                    "partner_name": partner.username
                })
    return channels