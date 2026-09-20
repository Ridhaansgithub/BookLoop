from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from email.message import EmailMessage
from datetime import datetime, timedelta
import secrets
import re
import smtplib
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

OTP_EXPIRY_MINUTES = 10
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
otp_challenges = {}
verified_registrations = {}


def validate_registration_email(email: str, is_under_18: bool) -> str:
    normalized_email = email.strip().lower()
    if not EMAIL_PATTERN.fullmatch(normalized_email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address.")
    if is_under_18 and not normalized_email.endswith("@gmail.com"):
        raise HTTPException(status_code=400, detail="Parental consent requires a Gmail address.")
    return normalized_email


def send_otp_email(recipient: str, otp: str) -> None:
    smtp_host = os.getenv("SMTP_HOST", "").strip()
    try:
        smtp_port = int(os.getenv("SMTP_PORT", "587").strip())
    except ValueError as error:
        raise HTTPException(status_code=503, detail="SMTP_PORT must be a valid number on the server.") from error
    smtp_username = os.getenv("SMTP_USERNAME", "").strip()
    smtp_password = re.sub(r"\s+", "", os.getenv("SMTP_PASSWORD", ""))
    if not all((smtp_host, smtp_username, smtp_password)):
        raise HTTPException(status_code=503, detail="Email verification is not configured on the server.")

    message = EmailMessage()
    message["Subject"] = "Your BookLoop verification code"
    message["From"] = smtp_username
    message["To"] = recipient
    message.set_content(f"Your BookLoop verification code is {otp}. It expires in {OTP_EXPIRY_MINUTES} minutes.")
    try:
        smtp_connection = smtplib.SMTP_SSL if smtp_port == 465 else smtplib.SMTP
        with smtp_connection(smtp_host, smtp_port, timeout=15) as smtp:
            if smtp_port != 465:
                smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as error:
        print(f"SMTP delivery failed: {error}")
        raise HTTPException(
            status_code=503,
            detail="The email verification service is unavailable. Please try again shortly.",
        ) from error


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
    registration = verified_registrations.pop(verification_token, None)
    if not registration or registration["expires_at"] < datetime.utcnow() or registration["email"] != email.strip().lower():
        raise HTTPException(status_code=400, detail="Email verification is required before registration.")

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


@app.post("/register/request-otp")
def request_registration_otp(email: str, is_under_18: bool):
    normalized_email = validate_registration_email(email, is_under_18)
    challenge_id = secrets.token_urlsafe(24)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    otp_challenges[challenge_id] = {
        "email": normalized_email,
        "otp": otp,
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
        "attempts": 0,
    }
    try:
        send_otp_email(normalized_email, otp)
    except Exception:
        otp_challenges.pop(challenge_id, None)
        raise
    return {"challenge_id": challenge_id, "message": "A verification code was sent to the email address."}


@app.post("/register/verify-otp")
def verify_registration_otp(challenge_id: str, otp: str):
    challenge = otp_challenges.get(challenge_id)
    if not challenge or challenge["expires_at"] < datetime.utcnow():
        otp_challenges.pop(challenge_id, None)
        raise HTTPException(status_code=400, detail="This verification code has expired. Request a new code.")
    challenge["attempts"] += 1
    if challenge["attempts"] > 5 or not secrets.compare_digest(challenge["otp"], otp.strip()):
        if challenge["attempts"] > 5:
            otp_challenges.pop(challenge_id, None)
        raise HTTPException(status_code=400, detail="Incorrect verification code.")

    otp_challenges.pop(challenge_id, None)
    verification_token = secrets.token_urlsafe(24)
    verified_registrations[verification_token] = {
        "email": challenge["email"],
        "expires_at": datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES),
    }
    return {"verification_token": verification_token}

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