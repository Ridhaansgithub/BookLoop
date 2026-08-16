from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, database, auth

router = APIRouter(tags=["Reviews & Profiles"])

@router.post("/reviews")
def leave_review(reviewed_user_id: int, rating: int, comment: str, db: Session = Depends(database.get_db), current_user: models.User = Depends(auth.get_current_user)):
    if current_user.id == reviewed_user_id:
        raise HTTPException(status_code=400, detail="You cannot review yourself.")
    if rating < 1 or rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5 stars.")
        
    new_review = models.Review(
        reviewer_id=current_user.id,
        reviewer_name=current_user.username,
        reviewed_user_id=reviewed_user_id,
        rating=rating,
        comment=comment
    )
    db.add(new_review)
    db.commit()
    return {"message": "Review submitted successfully!"}

@router.get("/users/{user_id}/profile")
def get_user_profile(user_id: int, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    # Calculate average star rating cleanly
    avg_rating = db.query(func.avg(models.Review.rating)).filter(models.Review.reviewed_user_id == user_id).scalar()
    reviews = db.query(models.Review).filter(models.Review.reviewed_user_id == user_id).order_by(models.Review.timestamp.desc()).all()
    
    return {
        "username": user.username,
        "school_class": user.school_class,
        "average_rating": round(avg_rating, 1) if avg_rating else 0.0,
        "reviews": reviews
    }
    
    
