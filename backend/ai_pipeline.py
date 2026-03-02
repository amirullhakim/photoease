import os

# --- NEW: FORCE DEEPFACE TO USE THE LOCAL BACKEND FOLDER ---
# This MUST be placed before importing DeepFace.
# We use .replace('\\', '/') to ensure paths strictly use forward slashes!
os.environ["DEEPFACE_HOME"] = os.path.abspath(os.path.dirname(__file__)).replace('\\', '/')

import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
from deepface import DeepFace 
from models import Photo, BibTag, Event, FaceEmbedding  
from sqlalchemy.orm import Session

# --- SETTINGS & THRESHOLDS ---
# These numbers control how strict the AI is about quality and size
MIN_BLUR_SCORE = 100       # Higher = stricter (rejects blurry photos)
SIZE_THRESHOLD = 0.5       # Keeps text that is at least 50% as tall as the largest text found
CONFIDENCE_THRESHOLD = 0.4 # Only saves text if the AI is >40% sure it's correct

# Load the AI models into memory once when the server starts
yolo_model = YOLO('best.pt')
reader = easyocr.Reader(['en'], gpu=False)

def process_and_index_folder(folder_path: str, event_id: int, db: Session):
    
    # 1. DATABASE CHECK: Create the Marathon Event if it doesn't exist yet
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        db.add(Event(event_id=event_id, event_name=f"Marathon {event_id}"))
        db.commit()

    processed_count = 0

    # 2. FILE SCANNING: Look at every file inside your folder
    for filename in os.listdir(folder_path):
        # Only look for actual image files
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')): 
            continue
            
        # Manually constructing the path to guarantee forward slashes
        file_path = f"{folder_path}/{filename}"
        
        # 3. DUPLICATE CHECK: Skip this photo if it's already in the database
        if db.query(Photo).filter(Photo.file_path == file_path).first(): 
            continue

        # 4. OPENCV LOAD: Open the image file so the AI can "see" it
        img = cv2.imread(file_path)
        if img is None: 
            continue
        
        # 5. DB SAVE (PHOTO): Register the new photo in the database first
        new_photo = Photo(event_id=event_id, file_path=file_path, is_processed=False)
        db.add(new_photo)
        db.commit() 
        db.refresh(new_photo) # Grabs the unique ID created by PostgreSQL
        
        # ==========================================
        # PASS 1: YOLO BIB DETECTION
        # ==========================================
        
        # 6. YOLO DETECTION: Find where the bib numbers are located in the photo
        results = yolo_model.predict(img, verbose=False)
        
        if len(results[0].boxes) > 0:
            h_img, w_img, _ = img.shape
            
            # Loop through every bib box found in this single photo
            for box in results[0].boxes:
                # Get the X and Y coordinates of the box with safety limits
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_img, x2), min(h_img, y2)

                # CROP: Cut out just the bib area from the big photo
                crop = img[y1:y2, x1:x2]
                if crop.size == 0: 
                    continue

                # 7. BLUR CHECK: Use Laplacian variance to see if the crop is too blurry
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                if blur_score < MIN_BLUR_SCORE: 
                    continue 
                
                # 8. ADAPTIVE LOW-LIGHT CORRECTION: Boost brightness/contrast if too dark
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                avg_brightness = np.mean(hsv[:, :, 2]) 
                if avg_brightness < 80:
                    crop = cv2.convertScaleAbs(crop, alpha=1.5, beta=30)
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

                # 9. PREPROCESSING: Upscale (3x), Denoise, and Apply Otsu's Thresholding
                upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                denoised = cv2.GaussianBlur(upscaled, (5, 5), 0)
                _, processed_crop = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 10. OCR READING: Read text from the processed crop
                raw_results = reader.readtext(processed_crop, detail=1, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                
                detected_parts = []
                if len(raw_results) > 0:
                    # Find height of the largest text detected to filter out small background noise
                    max_h = max([bbox[3][1] - bbox[0][1] for bbox, txt, conf in raw_results])
                    
                    for (bbox, text, prob) in raw_results:
                        h = bbox[3][1] - bbox[0][1]
                        # Filter by relative size and confidence
                        if h >= (max_h * SIZE_THRESHOLD) and prob > CONFIDENCE_THRESHOLD:
                            detected_parts.append((bbox[0][0], text, prob))

                # Sort parts from left to right to build the final bib number correctly
                detected_parts.sort(key=lambda x: x[0])
                
                if detected_parts:
                    final_text = "".join([t[1] for t in detected_parts])
                    avg_conf = sum([t[2] for t in detected_parts]) / len(detected_parts)

                    # 11. DB SAVE (TAG): Save the final bib number to the database!
                    db.add(BibTag(
                        photo_id=new_photo.photo_id,
                        bib_number=final_text,
                        confidence_score=float(avg_conf)
                    ))
        
        # ==========================================
        # PASS 2: DEEPFACE RECOGNITION (NEW)
        # ==========================================
        
        # 12. FACE EXTRACTION: Scan the exact same image for faces and generate ArcFace vectors
        try:
            # represent() finds the face, aligns it, and outputs the vector
            # enforce_detection=True throws an exception if no face is found (which we catch below)
            face_results = DeepFace.represent(img_path=img, model_name="ArcFace", enforce_detection=True)
            
            # Loop through every face found in the image
            for face_data in face_results:
                embedding_vector = face_data["embedding"]
                
                # DB SAVE (FACE): Store the vector in our new database table
                db.add(FaceEmbedding(
                    photo_id=new_photo.photo_id,
                    embedding=embedding_vector
                ))
        except ValueError:
            # Normal for marathon photos shot from behind or far away; ignore and move on
            pass
        except Exception as e:
            print(f"DeepFace Error on {filename}: {e}")
            
        # ==========================================
        # FINALIZE
        # ==========================================
        
        # 13. Mark the photo as fully indexed so we don't process it again
        new_photo.is_processed = True
        db.commit() 
        processed_count += 1
            
    return {"status": "Success", "indexed": processed_count}