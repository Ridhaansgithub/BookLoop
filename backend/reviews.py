from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
import models, database, auth

router = APIRouter(tags=["Reviews & Profiles"])

@router.post("/reviews")
def leave_review(
    rating: int,
    comment: str = "",
    reviewed_username: str | None = None,
    reviewed_user_id: int | None = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    if reviewed_username is not None and reviewed_user_id is not None:
        raise HTTPException(status_code=400, detail="Provide a username or user ID, not both.")
    if reviewed_username is not None:
        reviewed_user = db.query(models.User).filter(
            models.User.username == reviewed_username.strip()
        ).first()
    elif reviewed_user_id is not None:
        reviewed_user = db.query(models.User).filter(
            models.User.id == reviewed_user_id
        ).first()
    else:
        raise HTTPException(status_code=400, detail="A username is required.")

    if not reviewed_user:
        raise HTTPException(status_code=404, detail="User not found.")
    reviewed_user_id = reviewed_user.id
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

    return build_user_profile(user, user_id, db)


@router.get("/users/by-username/{username}/profile")
def get_user_profile_by_username(username: str, db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User profile not found")

    return build_user_profile(user, user.id, db)


def build_user_profile(user: models.User, user_id: int, db: Session):
    # Calculate average star rating cleanly
    avg_rating = db.query(func.avg(models.Review.rating)).filter(models.Review.reviewed_user_id == user_id).scalar()
    reviews = db.query(models.Review).filter(models.Review.reviewed_user_id == user_id).order_by(models.Review.timestamp.desc()).all()
    listed_count = db.query(func.count(models.Book.id)).filter(models.Book.seller_id == user_id).scalar()
    sold_count = db.query(func.count(models.Book.id)).filter(
        models.Book.seller_id == user_id,
        models.Book.status == "sold"
    ).scalar()
    bought_count = db.query(func.count(models.BookPurchase.id)).filter(
        models.BookPurchase.buyer_id == user_id
    ).scalar()
    
    return {
        "username": user.username,
        "school_class": user.school_class,
        "average_rating": round(avg_rating, 1) if avg_rating else 0.0,
        "books_listed": listed_count,
        "books_sold": sold_count,
        "books_bought": bought_count,
        "reviews": reviews
    }
    
    
