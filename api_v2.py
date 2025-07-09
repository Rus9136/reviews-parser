from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import database
from database import Review, Branch, get_db

app = FastAPI(
    title="2GIS Reviews API",
    description="API для доступа к отзывам из 2GIS для сети Сандык Тары",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class ReviewResponse(BaseModel):
    review_id: str
    branch_id: str
    branch_name: str
    user_name: str
    rating: float
    text: str
    date_created: datetime
    date_edited: Optional[datetime]
    is_verified: bool
    likes_count: int
    comments_count: int
    photos_count: int = 0
    photos_urls: List[str] = []
    
    class Config:
        from_attributes = True

class BranchResponse(BaseModel):
    branch_id: str
    branch_name: str
    city: Optional[str]
    address: Optional[str]
    total_reviews: int
    average_rating: float
    
    class Config:
        from_attributes = True

class BranchStats(BaseModel):
    branch_id: str
    branch_name: str
    total_reviews: int
    average_rating: float
    rating_distribution: dict
    verified_count: int
    last_review_date: Optional[datetime]

class ReviewsStats(BaseModel):
    total_reviews: int
    average_rating: float
    total_branches: int
    rating_distribution: dict
    reviews_by_month: dict

@app.get("/", tags=["General"])
async def root():
    """Root endpoint with API information"""
    return {
        "service": "2GIS Reviews API",
        "version": "2.0.0",
        "description": "API для доступа к отзывам из 2GIS",
        "endpoints": {
            "reviews": "/api/v1/reviews",
            "branches": "/api/v1/branches",
            "stats": "/api/v1/stats",
            "docs": "/docs"
        }
    }

@app.get("/health", tags=["General"])
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint"""
    try:
        # Test database connection
        from sqlalchemy import text
        db.execute(text("SELECT 1"))
        reviews_count = db.query(Review).count()
        branches_count = db.query(Branch).count()
        
        return {
            "status": "healthy",
            "database": "connected",
            "reviews_count": reviews_count,
            "branches_count": branches_count,
            "timestamp": datetime.utcnow()
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))

@app.get("/api/v1/branches", response_model=List[BranchResponse], tags=["Branches"])
async def get_branches(
    db: Session = Depends(get_db),
    city: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get list of all branches with statistics"""
    query = db.query(
        Branch.branch_id,
        Branch.branch_name,
        Branch.city,
        Branch.address,
        func.count(Review.id).label("total_reviews"),
        func.coalesce(func.avg(Review.rating), 0).label("average_rating")
    ).outerjoin(
        Review, Branch.branch_id == Review.branch_id
    ).group_by(
        Branch.branch_id,
        Branch.branch_name,
        Branch.city,
        Branch.address
    )
    
    if city:
        query = query.filter(Branch.city.ilike(f"%{city}%"))
    
    branches = query.offset(skip).limit(limit).all()
    
    return [
        BranchResponse(
            branch_id=b.branch_id,
            branch_name=b.branch_name,
            city=b.city,
            address=b.address,
            total_reviews=b.total_reviews,
            average_rating=round(b.average_rating, 2) if b.average_rating else 0
        )
        for b in branches
    ]

@app.get("/api/v1/branches/{branch_id}/stats", response_model=BranchStats, tags=["Branches"])
async def get_branch_stats(branch_id: str, db: Session = Depends(get_db)):
    """Get detailed statistics for a specific branch"""
    branch = db.query(Branch).filter(Branch.branch_id == branch_id).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")
    
    reviews = db.query(Review).filter(Review.branch_id == branch_id).all()
    
    if not reviews:
        return BranchStats(
            branch_id=branch.branch_id,
            branch_name=branch.branch_name,
            total_reviews=0,
            average_rating=0,
            rating_distribution={},
            verified_count=0,
            last_review_date=None
        )
    
    # Calculate rating distribution
    rating_dist = {}
    for i in range(1, 6):
        count = len([r for r in reviews if r.rating and int(r.rating) == i])
        rating_dist[str(i)] = count
    
    # Calculate average rating
    ratings = [r.rating for r in reviews if r.rating]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
    # Count verified reviews
    verified = len([r for r in reviews if r.is_verified])
    
    # Get last review date
    last_review = max(reviews, key=lambda r: r.date_created) if reviews else None
    
    return BranchStats(
        branch_id=branch.branch_id,
        branch_name=branch.branch_name,
        total_reviews=len(reviews),
        average_rating=round(avg_rating, 2),
        rating_distribution=rating_dist,
        verified_count=verified,
        last_review_date=last_review.date_created if last_review else None
    )

@app.get("/api/v1/reviews", response_model=List[ReviewResponse], tags=["Reviews"])
async def get_reviews(
    db: Session = Depends(get_db),
    branch_id: Optional[str] = None,
    rating: Optional[int] = Query(None, ge=1, le=5),
    verified_only: bool = False,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    sort_by: str = Query("date_created", regex="^(date_created|rating|likes_count)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """Get reviews with filtering and pagination"""
    query = db.query(Review)
    
    # Apply filters
    if branch_id:
        query = query.filter(Review.branch_id == branch_id)
    
    if rating:
        query = query.filter(Review.rating == rating)
    
    if verified_only:
        query = query.filter(Review.is_verified == True)
    
    if date_from:
        query = query.filter(Review.date_created >= date_from)
    
    if date_to:
        query = query.filter(Review.date_created <= date_to)
    
    if search:
        query = query.filter(
            func.lower(Review.text).contains(func.lower(search))
        )
    
    # Apply sorting
    sort_column = getattr(Review, sort_by)
    if order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(sort_column)
    
    # Apply pagination
    reviews = query.offset(skip).limit(limit).all()
    
    return reviews

@app.get("/api/v1/reviews/{review_id}", response_model=ReviewResponse, tags=["Reviews"])
async def get_review(review_id: str, db: Session = Depends(get_db)):
    """Get a specific review by ID"""
    review = db.query(Review).filter(Review.review_id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review

@app.get("/api/v1/stats", response_model=ReviewsStats, tags=["Statistics"])
async def get_overall_stats(db: Session = Depends(get_db)):
    """Get overall statistics for all reviews"""
    total_reviews = db.query(Review).count()
    total_branches = db.query(Branch).count()
    
    # Calculate average rating
    avg_rating_result = db.query(func.avg(Review.rating)).scalar()
    avg_rating = float(avg_rating_result) if avg_rating_result else 0
    
    # Rating distribution
    rating_dist = {}
    for i in range(1, 6):
        count = db.query(Review).filter(Review.rating == i).count()
        rating_dist[str(i)] = count
    
    # Reviews by month (last 12 months)
    reviews_by_month = {}
    current_date = datetime.utcnow()
    for i in range(12):
        month_date = current_date - timedelta(days=30*i)
        month_key = month_date.strftime("%Y-%m")
        
        start_date = month_date.replace(day=1)
        if month_date.month == 12:
            end_date = start_date.replace(year=start_date.year + 1, month=1)
        else:
            end_date = start_date.replace(month=start_date.month + 1)
        
        count = db.query(Review).filter(
            and_(
                Review.date_created >= start_date,
                Review.date_created < end_date
            )
        ).count()
        
        reviews_by_month[month_key] = count
    
    return ReviewsStats(
        total_reviews=total_reviews,
        average_rating=round(avg_rating, 2),
        total_branches=total_branches,
        rating_distribution=rating_dist,
        reviews_by_month=reviews_by_month
    )

@app.get("/api/v1/stats/recent", tags=["Statistics"])
async def get_recent_activity(
    db: Session = Depends(get_db),
    days: int = Query(7, ge=1, le=90)
):
    """Get recent review activity"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    recent_reviews = db.query(Review).filter(
        Review.date_created >= cutoff_date
    ).all()
    
    # Group by date
    reviews_by_date = {}
    for review in recent_reviews:
        date_key = review.date_created.strftime("%Y-%m-%d")
        if date_key not in reviews_by_date:
            reviews_by_date[date_key] = {
                "count": 0,
                "average_rating": 0,
                "ratings": []
            }
        reviews_by_date[date_key]["count"] += 1
        if review.rating:
            reviews_by_date[date_key]["ratings"].append(review.rating)
    
    # Calculate averages
    for date_key, data in reviews_by_date.items():
        if data["ratings"]:
            data["average_rating"] = round(
                sum(data["ratings"]) / len(data["ratings"]), 2
            )
        del data["ratings"]
    
    return {
        "period_days": days,
        "total_reviews": len(recent_reviews),
        "reviews_by_date": reviews_by_date
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)