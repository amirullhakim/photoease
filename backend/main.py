import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import engine, Base, get_db
import models
from ai_pipeline import process_and_index_folder

# Initialize Database Tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI()

# ==========================================
# 1. CORS CONFIGURATION
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. IMAGE SERVING SETUP
# ==========================================
IMAGE_FOLDER = "C:/Users/User/OneDrive/Documents/iNVENTX/Photoease/sample_database"

if os.path.exists(IMAGE_FOLDER):
    app.mount("/images", StaticFiles(directory=IMAGE_FOLDER), name="images")

# ==========================================
# 3. API ENDPOINTS
# ==========================================

@app.post("/api/index-photos/")
def start_indexing(
    folder_path: str = IMAGE_FOLDER,
    event_id: int = 1,
    db: Session = Depends(get_db)
):
    result = process_and_index_folder(folder_path, event_id, db)
    return result

@app.get("/api/search/{bib_number}")
def search_photos(bib_number: str, db: Session = Depends(get_db)):
 
    # 1. Add wildcards (%) so it searches for anything containing the input
    search_term = f"%{bib_number}%"
    
    # 2. Use .ilike() for case-insensitive partial matching
    tags = db.query(models.BibTag).filter(models.BibTag.bib_number.ilike(search_term)).all()
    
    # 3. Use a set() to prevent duplicate photos from showing up
    photo_urls = set()
    for tag in tags:
        filename = os.path.basename(tag.photo.file_path)
        photo_urls.add(f"http://127.0.0.1:8000/images/{filename}")
        
    return {"bib_number": bib_number, "found_photos": list(photo_urls)}

# --- GALLERY ENDPOINT ---
@app.get("/api/photos/all")
def get_all_photos(db: Session = Depends(get_db)):
    # Query every photo currently in the database
    all_photos = db.query(models.Photo).all()
    
    # CHANGED: Use a set() instead of a list [] to automatically destroy duplicates
    photo_urls = set()
    for photo in all_photos:
        filename = os.path.basename(photo.file_path)
        photo_urls.add(f"http://127.0.0.1:8000/images/{filename}")
        
    # CHANGED: Convert the set back to a list before returning
    return {"photos": list(photo_urls)}