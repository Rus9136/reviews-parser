#!/usr/bin/env python3
"""
Script to migrate reviews from CSV/JSON files to PostgreSQL database
"""
import os
import csv
import json
import glob
from datetime import datetime
from sqlalchemy.orm import Session
from database import engine, Branch, Review, ParseReport, init_db
import pandas as pd

def parse_datetime(date_str):
    """Parse datetime string to datetime object"""
    if not date_str or date_str == 'None':
        return None
    try:
        # Try different datetime formats
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%d"
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    except:
        return None

def migrate_branches_from_csv():
    """Migrate branches from CSV file to database"""
    csv_path = "data/sandyq_tary_branches.csv"
    if not os.path.exists(csv_path):
        print(f"Branches CSV file not found: {csv_path}")
        return 0
    
    session = Session(engine)
    added_count = 0
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if branch already exists
                existing = session.query(Branch).filter_by(
                    branch_id=row.get('2gis_id', '')
                ).first()
                
                if not existing and row.get('2gis_id'):
                    branch = Branch(
                        branch_id=row['2gis_id'],
                        branch_name=row.get('name', ''),
                        city=row.get('city', ''),
                        address=row.get('address', '')
                    )
                    session.add(branch)
                    added_count += 1
        
        session.commit()
        print(f"Added {added_count} new branches")
    except Exception as e:
        session.rollback()
        print(f"Error migrating branches: {e}")
    finally:
        session.close()
    
    return added_count

def migrate_reviews_from_csv(csv_file):
    """Migrate reviews from a single CSV file to database"""
    session = Session(engine)
    added_count = 0
    updated_count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Check if review already exists
                existing = session.query(Review).filter_by(
                    review_id=row.get('review_id', '')
                ).first()
                
                if existing:
                    # Update existing review
                    existing.rating = float(row['rating']) if row.get('rating') else None
                    existing.text = row.get('text', '')
                    existing.likes_count = int(row.get('likes_count', 0))
                    existing.comments_count = int(row.get('comments_count', 0))
                    existing.date_edited = parse_datetime(row.get('date_edited'))
                    updated_count += 1
                else:
                    # Add new review
                    review = Review(
                        branch_id=row.get('branch_id', ''),
                        branch_name=row.get('branch_name', ''),
                        review_id=row.get('review_id', ''),
                        user_name=row.get('user_name', 'Аноним'),
                        rating=float(row['rating']) if row.get('rating') else None,
                        text=row.get('text', ''),
                        date_created=parse_datetime(row.get('date_created')),
                        date_edited=parse_datetime(row.get('date_edited')),
                        is_verified=row.get('is_verified', '').lower() == 'true',
                        likes_count=int(row.get('likes_count', 0)),
                        comments_count=int(row.get('comments_count', 0))
                    )
                    session.add(review)
                    added_count += 1
        
        session.commit()
        print(f"File {csv_file}: Added {added_count} new reviews, updated {updated_count}")
    except Exception as e:
        session.rollback()
        print(f"Error migrating reviews from {csv_file}: {e}")
    finally:
        session.close()
    
    return added_count, updated_count

def migrate_reviews_from_json(json_file):
    """Migrate reviews from a single JSON file to database"""
    session = Session(engine)
    added_count = 0
    updated_count = 0
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            reviews_data = json.load(f)
        
        for row in reviews_data:
            # Check if review already exists
            existing = session.query(Review).filter_by(
                review_id=row.get('review_id', '')
            ).first()
            
            if existing:
                # Update existing review
                existing.rating = row.get('rating')
                existing.text = row.get('text', '')
                existing.likes_count = row.get('likes_count', 0)
                existing.comments_count = row.get('comments_count', 0)
                existing.date_edited = parse_datetime(row.get('date_edited'))
                updated_count += 1
            else:
                # Add new review
                review = Review(
                    branch_id=row.get('branch_id', ''),
                    branch_name=row.get('branch_name', ''),
                    review_id=row.get('review_id', ''),
                    user_name=row.get('user_name', 'Аноним'),
                    rating=row.get('rating'),
                    text=row.get('text', ''),
                    date_created=parse_datetime(row.get('date_created')),
                    date_edited=parse_datetime(row.get('date_edited')),
                    is_verified=row.get('is_verified', False),
                    likes_count=row.get('likes_count', 0),
                    comments_count=row.get('comments_count', 0)
                )
                session.add(review)
                added_count += 1
        
        session.commit()
        print(f"File {json_file}: Added {added_count} new reviews, updated {updated_count}")
    except Exception as e:
        session.rollback()
        print(f"Error migrating reviews from {json_file}: {e}")
    finally:
        session.close()
    
    return added_count, updated_count

def main():
    """Main migration function"""
    print("Starting database migration...")
    start_time = datetime.utcnow()
    
    # Initialize database
    print("Creating database tables...")
    init_db()
    
    # Create output directory if it doesn't exist
    os.makedirs("output", exist_ok=True)
    
    # Migrate branches
    print("\nMigrating branches...")
    branches_count = migrate_branches_from_csv()
    
    # Migrate reviews from CSV files
    print("\nMigrating reviews from CSV files...")
    csv_files = glob.glob("output/reviews_*.csv")
    total_added = 0
    total_updated = 0
    
    for csv_file in csv_files:
        added, updated = migrate_reviews_from_csv(csv_file)
        total_added += added
        total_updated += updated
    
    # Migrate reviews from JSON files
    print("\nMigrating reviews from JSON files...")
    json_files = glob.glob("output/reviews_*.json")
    
    for json_file in json_files:
        # Skip parse report files
        if "parse_report" in json_file:
            continue
        added, updated = migrate_reviews_from_json(json_file)
        total_added += added
        total_updated += updated
    
    # Create migration report
    duration = (datetime.utcnow() - start_time).total_seconds()
    session = Session(engine)
    
    try:
        report = ParseReport(
            parse_date=datetime.utcnow(),
            total_branches=branches_count,
            successful_branches=branches_count,
            failed_branches=0,
            total_reviews=total_added + total_updated,
            new_reviews=total_added,
            updated_reviews=total_updated,
            duration_seconds=duration,
            errors=None
        )
        session.add(report)
        session.commit()
    finally:
        session.close()
    
    print(f"\nMigration completed in {duration:.2f} seconds")
    print(f"Total branches: {branches_count}")
    print(f"Total reviews added: {total_added}")
    print(f"Total reviews updated: {total_updated}")
    
    # Show database statistics
    session = Session(engine)
    try:
        total_branches = session.query(Branch).count()
        total_reviews = session.query(Review).count()
        print(f"\nDatabase statistics:")
        print(f"Total branches in DB: {total_branches}")
        print(f"Total reviews in DB: {total_reviews}")
    finally:
        session.close()

if __name__ == "__main__":
    main()