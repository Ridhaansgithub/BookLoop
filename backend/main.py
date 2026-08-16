from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import models
import database
import auth
import books
import chat
import reviews

# Initialize Database tables
models.Base.metadata.create_all(bind=database.engine)
app = FastAPI(title="BookLoop API")

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
os.makedirs(os.path.join(UPLOAD_DIR, "books"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(books.router)
app.include_router(chat.router)
app.include_router(reviews.router)


@app.post("/register", status_code=status.HTTP_201_CREATED)
def register(username: str, email: str, password: str, school_class: str, db: Session = Depends(database.get_db)):
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