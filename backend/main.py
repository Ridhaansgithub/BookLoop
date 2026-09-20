from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
import hmac
import hashlib
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file in parent directory
# (local development only - won't exist on Render)
ENV_PATH = Path(__file__).parent.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
    print(f"✅ Loaded .env from {ENV_PATH}")
else:
    print(f"ℹ️  .env not found at {ENV_PATH} - using environment variables from system/Render")
    load_dotenv()  # Load from environment variables

import models
import database
import auth
import books
import chat
import reviews

# Initialize Database tables
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI(title="BookLoop API")

# Enable CORS so Streamlit Cloud can call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (you can restrict this later)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "books"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(books.router)
app.include_router(chat.router)
app.include_router(reviews.router)

OTP_SIGNING_SECRET = os.getenv("OTP_SIGNING_SECRET", "").strip()


def validate_registration_assertion(token: str, email: str) -> None:
    if not OTP_SIGNING_SECRET:
        raise HTTPException(status_code=503, detail="OTP_SIGNING_SECRET is not configured on the server.")
    try:
        token_email, expires_at_text, signature = token.split(":", 2)
        expires_at = int(expires_at_text)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Email verification is required before registration.")

    payload = f"{token_email}:{expires_at}"
    expected_signature = hmac.new(
        OTP_SIGNING_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    if (
        not hmac.compare_digest(signature, expected_signature)
        or token_email != email.strip().lower()
        or expires_at < int(datetime.utcnow().timestamp())
    ):
        raise HTTPException(status_code=400, detail="Email verification is required before registration.")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    username: str,
    email: str,
    password: str,
    school_class: str,
    verification_token: str,
    db: Session = Depends(database.get_db),
):
    validate_registration_assertion(verification_token, email)

    # Check if user already exists
    db_user = db.query(models.User).filter((models.User.email == email) | (models.User.username == username)).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Username or Email already registered")

    hashed_pwd = auth.get_password_hash(password)
    new_user = models.User(
        username=username,
        email=email,
        hashed_password=hashed_pwd,
        school_class=school_class
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User registered successfully", "user_id": new_user.id}


@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer", "username": user.username}

@app.get("/users/me")
def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "school_class": current_user.school_class
    }