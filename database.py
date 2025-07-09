from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://reviews_user:reviews_password@localhost:5436/reviews_db")

# Create engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Branch(Base):
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(String(50), unique=True, index=True, nullable=False)
    branch_name = Column(String(255), nullable=False)
    city = Column(String(100))
    address = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_branch_name", "branch_name"),
        Index("idx_city", "city"),
    )

class Review(Base):
    __tablename__ = "reviews"
    
    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(String(50), index=True, nullable=False)
    branch_name = Column(String(255), nullable=False)
    review_id = Column(String(100), unique=True, index=True, nullable=False)
    user_name = Column(String(255))
    rating = Column(Float)
    text = Column(Text)
    date_created = Column(DateTime)
    date_edited = Column(DateTime)
    is_verified = Column(Boolean, default=False)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index("idx_branch_id", "branch_id"),
        Index("idx_rating", "rating"),
        Index("idx_date_created", "date_created"),
        Index("idx_created_at", "created_at"),
    )

class ParseReport(Base):
    __tablename__ = "parse_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    parse_date = Column(DateTime, default=datetime.utcnow)
    total_branches = Column(Integer, default=0)
    successful_branches = Column(Integer, default=0)
    failed_branches = Column(Integer, default=0)
    total_reviews = Column(Integer, default=0)
    new_reviews = Column(Integer, default=0)
    updated_reviews = Column(Integer, default=0)
    errors = Column(Text)
    duration_seconds = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_db()