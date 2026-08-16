import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

import models
import database
import auth

router = APIRouter(tags=["Books"])

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads",
    "books"
)

@router.post("/books")
async def add_book(
    title: str = Form(...),
    author: str = Form(...),
    target_class: str = Form(...),
    price: float = Form(...),
    image: UploadFile = File(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    image_url = None

    if image:
        filename = f"{current_user.id}_{image.filename}"
        filepath = os.path.join(UPLOAD_DIR, filename)

        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)

        image_url = filename

    new_book = models.Book(
        title=title,
        author=author,
        target_class=target_class,
        price=price,
        image_url=image_url,
        seller_id=current_user.id
    )

    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return {
        "message": "Book added successfully!",
        "book_id": new_book.id
    }


@router.get("/books")
def get_all_books(db: Session = Depends(database.get_db)):
    return db.query(models.Book).filter(
        models.Book.status == "available"
    ).all()


@router.get("/books/me")
def get_my_books(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    return db.query(models.Book).filter(
        models.Book.seller_id == current_user.id
    ).all()


@router.put("/books/{book_id}/sold")
def mark_book_sold(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    book = db.query(models.Book).filter(
        models.Book.id == book_id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    book.status = "sold"

    db.commit()

    return {"message": "Book marked as sold"}


@router.delete("/books/{book_id}")
def delete_book(
    book_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    book = db.query(models.Book).filter(
        models.Book.id == book_id
    ).first()

    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    if book.seller_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if book.image_url:
        image_path = os.path.join(UPLOAD_DIR, book.image_url)

        if os.path.exists(image_path):
            os.remove(image_path)

    db.delete(book)
    db.commit()

    return {"message": "Book deleted successfully"}