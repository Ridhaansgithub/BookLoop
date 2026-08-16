from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    school_class = Column(String, nullable=True) # e.g., "Class 9"
    books_for_sale = relationship("Book", back_populates="seller")
    reviews_received = relationship("Review", back_populates="reviewed_user", foreign_keys="[Review.reviewed_user_id]")

class Book(Base):
    __tablename__ = "books"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author = Column(String, nullable=False)
    target_class = Column(String, nullable=False) # e.g., "Class 9"
    price = Column(Float, nullable=False)
    image_url = Column(String, nullable=True) # Paths to uploads/books/
    status = Column(String, default="available") # available, sold
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    seller_id = Column(Integer, ForeignKey("users.id"))
    seller = relationship("User", back_populates="books_for_sale")


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, nullable=False)
    receiver_id = Column(Integer, nullable=False)
    book_id = Column(Integer, nullable=False)
    message = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    reviewer_id = Column(Integer, nullable=False) # The student writing the review
    reviewer_name = Column(String, nullable=False)
    reviewed_user_id = Column(Integer, ForeignKey("users.id"), nullable=False) # The student getting reviewed
    rating = Column(Integer, nullable=False) # e.g., 1 to 5 stars
    comment = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    reviewed_user = relationship("User", back_populates="reviews_received", foreign_keys=[reviewed_user_id])