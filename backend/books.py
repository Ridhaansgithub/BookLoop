import os
from html import escape
from io import BytesIO
from uuid import uuid4
from PIL import Image, ImageOps, UnidentifiedImageError
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, HTMLResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import database
import auth

router = APIRouter(tags=["Books"])
BOOKLOOP_APP_URL = os.getenv(
    "BOOKLOOP_APP_URL",
    "https://bookloop.streamlit.app",
).rstrip("/")

UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "uploads",
    "books"
)


def normalize_book_image(image: UploadFile) -> bytes:
    try:
        uploaded_image = Image.open(image.file)
        normalized_image = ImageOps.fit(uploaded_image.convert("RGB"), (600, 600))
        image_buffer = BytesIO()
        normalized_image.save(image_buffer, format="JPEG", quality=90)
    except (UnidentifiedImageError, OSError):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image.")
    return image_buffer.getvalue()


@router.post("/books")
async def add_book(
    title: str = Form(...),
    author: str = Form(...),
    target_class: str = Form(...),
    price: float = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    filename = f"{current_user.id}_{uuid4().hex}.jpg"
    image_data = normalize_book_image(image)
    db.add(
        models.BookImage(
            filename=filename,
            image_data=image_data,
            content_type="image/jpeg",
        )
    )

    new_book = models.Book(
        title=title,
        author=author,
        target_class=target_class,
        price=price,
        image_url=filename,
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


@router.put("/books/{book_id}/image")
async def update_book_image(
    book_id: int,
    image: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    book = db.query(models.Book).filter(
        models.Book.id == book_id,
        models.Book.seller_id == current_user.id,
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    filename = f"{current_user.id}_{uuid4().hex}.jpg"
    image_data = normalize_book_image(image)
    previous_filename = book.image_url

    db.add(
        models.BookImage(
            filename=filename,
            image_data=image_data,
            content_type="image/jpeg",
        )
    )
    if previous_filename:
        db.query(models.BookImage).filter(
            models.BookImage.filename == previous_filename
        ).delete()
    book.image_url = filename
    db.commit()

    if previous_filename:
        legacy_path = os.path.join(UPLOAD_DIR, os.path.basename(previous_filename))
        if os.path.isfile(legacy_path):
            os.remove(legacy_path)

    return {"message": "Book photo updated successfully", "image_url": filename}


@router.get("/books/{book_id}")
def get_book(book_id: int, db: Session = Depends(database.get_db)):
    book = db.query(models.Book).filter(
        models.Book.id == book_id,
        models.Book.status == "available",
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.get("/uploads/books/{filename}")
def get_book_image(filename: str, db: Session = Depends(database.get_db)):
    safe_filename = os.path.basename(filename)
    image = db.query(models.BookImage).filter(
        models.BookImage.filename == safe_filename
    ).first()
    if image:
        return Response(
            content=image.image_data,
            media_type=image.content_type,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    legacy_path = os.path.join(UPLOAD_DIR, safe_filename)
    if os.path.isfile(legacy_path):
        return FileResponse(legacy_path, media_type="image/jpeg")

    placeholder = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" '
        'viewBox="0 0 600 600"><rect width="600" height="600" fill="#e8f1f5"/>'
        '<path d="M150 175q75-35 150 0v245q-75-35-150 0zm300 0q-75-35-150 0v245'
        'q75-35 150 0z" fill="none" stroke="#51755a" stroke-width="18" '
        'stroke-linejoin="round"/><text x="300" y="490" text-anchor="middle" '
        'font-family="sans-serif" font-size="24" fill="#425467">Photo unavailable</text></svg>'
    )
    return Response(
        content=placeholder,
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/book/{book_id}", response_class=HTMLResponse)
def get_product_page(book_id: int, db: Session = Depends(database.get_db)):
    book = db.query(models.Book).filter(
        models.Book.id == book_id,
        models.Book.status == "available",
    ).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    seller = db.query(models.User).filter(models.User.id == book.seller_id).first()
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")

    reviews = db.query(models.Review).filter(
        models.Review.reviewed_user_id == seller.id
    ).order_by(models.Review.timestamp.desc()).all()
    average_rating = db.query(func.avg(models.Review.rating)).filter(
        models.Review.reviewed_user_id == seller.id
    ).scalar()
    review_cards = "".join(
        "<article class='review'>"
        f"<h3>{escape(review.reviewer_name)} · {review.rating} / 5 stars</h3>"
        f"<p>{escape(review.comment or '')}</p>"
        "</article>"
        for review in reviews
    ) or "<p class='muted'>This seller hasn't received any reviews yet.</p>"

    image_filename = (
        os.path.basename(str(book.image_url).replace("\\", "/"))
        if book.image_url
        else None
    )
    photo = (
        f"<img src='/uploads/books/{escape(image_filename, quote=True)}' "
        "alt='Book cover photo' loading='eager' decoding='async'>"
        if image_filename
        else "<div class='photo-placeholder' role='img' aria-label='No book photo'>"
        "No photo</div>"
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(book.title)} | Zuvyo</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 2rem; color: #0f172a;
      background: linear-gradient(145deg,#fbfcfe 0%,#f1f6fb 58%,#fdf8f4 100%);
      font: 16px/1.5 system-ui,-apple-system,sans-serif; }}
    main {{ max-width: 1100px; margin: 0 auto; }}
    .back {{ display: inline-block; margin-bottom: 1.25rem; padding: .55rem .85rem;
      border: 1px solid #dfe7ec; border-radius: 8px; background: #fff;
      color: #315d43; font-weight: 600; text-decoration: none; }}
    .back:hover {{ background: #edf4ef; }}
    .product {{ display: grid; grid-template-columns: minmax(0,1fr) minmax(0,1fr);
      gap: 2rem; align-items: start; padding: 1.25rem; border: 1px solid #dfe7ec;
      border-radius: 16px; background: #fff; box-shadow: 0 8px 24px #101c3b0d; }}
    .photo {{ width: 100%; aspect-ratio: 1; overflow: hidden; border-radius: 12px;
      background: #e8f1f5; }}
    .photo img,.photo-placeholder {{ display: grid; width: 100%; height: 100%;
      object-fit: contain; place-items: center; font-size: 4rem; }}
    h1 {{ margin: .25rem 0 1.25rem; font-size: clamp(1.8rem,4vw,2.8rem);
      line-height: 1.1; }}
    .price {{ font-size: 1.6rem; font-weight: 700; }}
    .muted {{ color: #53657a; }}
    .reviews {{ margin-top: 2rem; }}
    .review {{ margin: .75rem 0; padding: 1rem; border: 1px solid #dfe7ec;
      border-radius: 12px; background: #fff; }}
    .review h3 {{ margin: 0 0 .5rem; font-size: 1rem; }}
    .review p {{ margin: 0; white-space: pre-wrap; }}
    @media (max-width: 700px) {{
      body {{ padding: 1rem; }}
      .product {{ grid-template-columns: 1fr; gap: 1.25rem; }}
    }}
  </style>
</head>
<body><main>
  <a class="back" href="{escape(BOOKLOOP_APP_URL, quote=True)}">← Back to listings</a>
  <section class="product">
    <div class="photo">{photo}</div>
    <div>
      <h1>{escape(book.title)}</h1>
      <p><strong>Author:</strong> {escape(book.author)}</p>
      <p><strong>Class / Course:</strong> {escape(book.target_class)}</p>
      <p class="price">${book.price:.2f}</p>
      <p><strong>Seller:</strong> {escape(seller.username)}</p>
      <p><strong>Seller rating:</strong> {f"{average_rating:.1f}" if average_rating else "No ratings yet"} / 5</p>
    </div>
  </section>
  <section class="reviews">
    <h2>Seller reviews</h2>
    {review_cards}
  </section>
</main></body>
</html>"""
    return HTMLResponse(content=page)


@router.put("/books/{book_id}/sold")
def mark_book_sold(
    book_id: int,
    buyer_username: str,
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

    if not buyer_username.strip():
        raise HTTPException(status_code=400, detail="Buyer username is required.")

    buyer = db.query(models.User).filter(
        models.User.username == buyer_username.strip()
    ).first()
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    if buyer.id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot mark yourself as the buyer.")

    book.status = "sold"
    db.add(models.BookPurchase(book_id=book.id, buyer_id=buyer.id))

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

    image_path = None
    if book.image_url:
        db.query(models.BookImage).filter(
            models.BookImage.filename == book.image_url
        ).delete()
        image_filename = os.path.basename(
            str(book.image_url).replace("\\", "/")
        )
        image_path = os.path.join(UPLOAD_DIR, image_filename)

    db.query(models.BookPurchase).filter(
        models.BookPurchase.book_id == book.id
    ).delete(synchronize_session=False)
    db.query(models.ChatMessage).filter(
        models.ChatMessage.book_id == book.id
    ).delete(synchronize_session=False)
    db.delete(book)
    db.commit()

    if image_path and os.path.isfile(image_path):
        os.remove(image_path)

    return {"message": "Book deleted successfully"}