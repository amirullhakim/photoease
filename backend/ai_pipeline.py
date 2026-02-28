import os
import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
from models import Photo, BibTag, Event  
from sqlalchemy.orm import Session

# --- CONFIGURATION (Synced with Streamlit Prototype) ---
MIN_BLUR_SCORE = 100       
SIZE_THRESHOLD = 0.5       
CONFIDENCE_THRESHOLD = 0.4 

# Load the AI models once when the server starts
yolo_model = YOLO('best.pt')
reader = easyocr.Reader(['en'], gpu=False)

def process_and_index_folder(folder_path: str, event_id: int, db: Session):
    
    # 1. DATABASE CHECK: Create Event if missing
    event = db.query(Event).filter(Event.event_id == event_id).first()
    if not event:
        db.add(Event(event_id=event_id, event_name=f"Marathon {event_id}"))
        db.commit()

    processed_count = 0

    # 2. FILE SCANNING
    for filename in os.listdir(folder_path):
        if not filename.lower().endswith(('.jpg', '.jpeg', '.png')): 
            continue
            
        file_path = os.path.join(folder_path, filename)
        
        # 3. DUPLICATE CHECK: Skip if already indexed
        if db.query(Photo).filter(Photo.file_path == file_path).first(): 
            continue

        # 4. LOAD IMAGE
        img = cv2.imread(file_path)
        if img is None: 
            continue
        
        # 5. DB SAVE (PHOTO): Register the photo
        new_photo = Photo(event_id=event_id, file_path=file_path, is_processed=False)
        db.add(new_photo)
        db.commit() 
        db.refresh(new_photo)
        
        # 6. YOLO DETECTION: Finding the bib location
        results = yolo_model.predict(img, verbose=False)
        
        if len(results[0].boxes) > 0:
            h_img, w_img, _ = img.shape
            
            for box in results[0].boxes:
                # Get coordinates
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(w_img, x2), min(h_img, y2)

                # CROP: Extract bib from photo
                crop = img[y1:y2, x1:x2]
                if crop.size == 0: 
                    continue

                # 7. BLUR CHECK (Synced with Prototype)
                gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                if blur_score < MIN_BLUR_SCORE: 
                    continue 
                
                # 8. ADAPTIVE LOW-LIGHT CORRECTION (Synced with Prototype)
                hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
                avg_brightness = np.mean(hsv[:, :, 2]) 
                if avg_brightness < 80:
                    crop = cv2.convertScaleAbs(crop, alpha=1.5, beta=30)
                    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

                # 9. PREPROCESSING: Scaling, Denoising, and Thresholding
                upscaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                denoised = cv2.GaussianBlur(upscaled, (5, 5), 0)
                _, processed_crop = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

                # 10. OCR READING (Synced with Prototype)
                raw_results = reader.readtext(processed_crop, detail=1, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                
                detected_parts = []
                if len(raw_results) > 0:
                    # PROTOTYPE LOGIC: Find height of the largest text detected
                    max_h = max([bbox[3][1] - bbox[0][1] for bbox, txt, conf in raw_results])
                    
                    for (bbox, text, prob) in raw_results:
                        h = bbox[3][1] - bbox[0][1]
                        # PROTOTYPE LOGIC: Filter by relative size and confidence
                        if h >= (max_h * SIZE_THRESHOLD) and prob > CONFIDENCE_THRESHOLD:
                            detected_parts.append((bbox[0][0], text, prob))

                # PROTOTYPE LOGIC: Sort parts from left to right to build final bib number
                detected_parts.sort(key=lambda x: x[0])
                
                if detected_parts:
                    final_text = "".join([t[1] for t in detected_parts])
                    avg_conf = sum([t[2] for t in detected_parts]) / len(detected_parts)

                    # 11. DB SAVE (TAG)
                    db.add(BibTag(
                        photo_id=new_photo.photo_id,
                        bib_number=final_text,
                        confidence_score=float(avg_conf)
                    ))
        
        # Mark photo processing as complete
        new_photo.is_processed = True
        db.commit() 
        processed_count += 1
            
    return {"status": "Success", "indexed": processed_count}