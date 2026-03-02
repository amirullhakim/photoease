import os
import shutil
import numpy as np

# --- NEW: FORCE DEEPFACE TO USE THE LOCAL BACKEND FOLDER ---
# This MUST be placed before importing DeepFace.
# We use .replace('\\', '/') to ensure paths strictly use forward slashes!
os.environ["DEEPFACE_HOME"] = os.path.abspath(os.path.dirname(__file__)).replace('\\', '/')

from fastapi import FastAPI, Depends, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from deepface import DeepFace
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
# Forward slashes maintained perfectly here
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
    search_term = f"%{bib_number}%"
    tags = db.query(models.BibTag).filter(models.BibTag.bib_number.ilike(search_term)).all()
    
    photo_urls = set()
    for tag in tags:
        # Splits the path by forward slash and grabs the last item (the filename)
        filename = tag.photo.file_path.split('/')[-1]
        photo_urls.add(f"http://127.0.0.1:8000/images/{filename}")
        
    return {"bib_number": bib_number, "found_photos": list(photo_urls)}

@app.get("/api/photos/all")
def get_all_photos(db: Session = Depends(get_db)):
    all_photos = db.query(models.Photo).all()
    photo_urls = set()
    for photo in all_photos:
        filename = photo.file_path.split('/')[-1]
        photo_urls.add(f"http://127.0.0.1:8000/images/{filename}")
        
    return {"photos": list(photo_urls)}

@app.get("/api/download/{filename}")
def download_photo(filename: str):
    file_path = f"{IMAGE_FOLDER}/{filename}"
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=f"PhotoEase_{filename}")
    return {"error": "File not found"}

# ==========================================
# 4. NEW: FACE RECOGNITION SEARCH
# ==========================================
@app.post("/api/search-face/")
async def search_by_face(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # 1. Save the uploaded selfie temporarily
    temp_file_path = f"temp_{file.filename}"
    with open(temp_file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 2. Extract the Face Vector (Embedding) from the selfie
        # enforce_detection=False so it doesn't crash the server if the user uploads a picture of a shoe
        face_results = DeepFace.represent(img_path=temp_file_path, model_name="ArcFace", enforce_detection=False)
        
        # If DeepFace returns an empty list or the face couldn't be mapped
        if not face_results or "face_confidence" not in face_results[0]:
            return {"error": "No clear face detected in the uploaded image. Please try another selfie."}
            
        user_embedding = np.array(face_results[0]["embedding"])
        
        # 3. Fetch all stored faces from PostgreSQL
        all_stored_faces = db.query(models.FaceEmbedding).all()
        matched_photo_urls = set()
        
        # 4. Compare the selfie against the database using Cosine Distance
        for face_record in all_stored_faces:
            db_embedding = np.array(face_record.embedding)
            
            # Mathematical calculation for Cosine Similarity -> Distance
            cos_sim = np.dot(user_embedding, db_embedding) / (np.linalg.norm(user_embedding) * np.linalg.norm(db_embedding))
            distance = 1 - cos_sim
            
            # ArcFace threshold: generally distance < 0.68 means it's the same person
            # We use 0.50 to be slightly strict and reduce false positives
            if distance < 0.50:
                filename = face_record.photo.file_path.split('/')[-1]
                matched_photo_urls.add(f"http://127.0.0.1:8000/images/{filename}")
                
        return {"found_photos": list(matched_photo_urls)}

    except Exception as e:
        return {"error": f"Face search failed: {str(e)}"}
        
    finally:
        # 5. Clean up: Delete the temporary selfie file to save space
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)