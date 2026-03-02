from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, Numeric, ARRAY, Float
from sqlalchemy.orm import relationship
from database import Base

class Event(Base):
    __tablename__ = "events"
    event_id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255), nullable=False)
    event_date = Column(Date)
    photos = relationship("Photo", back_populates="event", cascade="all, delete-orphan")

class Photo(Base):
    __tablename__ = "photos"
    photo_id = Column(Integer, primary_key=True, index=True)
    event_id = Column(Integer, ForeignKey("events.event_id"))
    file_path = Column(String(500), nullable=False, unique=True)
    is_processed = Column(Boolean, default=False)
    
    event = relationship("Event", back_populates="photos")
    bib_tags = relationship("BibTag", back_populates="photo", cascade="all, delete-orphan")
    # NEW: Relationship to link one photo to many faces (in case multiple runners are in one shot)
    face_embeddings = relationship("FaceEmbedding", back_populates="photo", cascade="all, delete-orphan")

class BibTag(Base):
    __tablename__ = "bib_tags"
    tag_id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.photo_id", ondelete="CASCADE"))
    bib_number = Column(String(50), nullable=False, index=True) 
    confidence_score = Column(Numeric(4, 3)) 
    photo = relationship("Photo", back_populates="bib_tags")

# --- NEW: FACE EMBEDDING TABLE ---
class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id = Column(Integer, primary_key=True, index=True)
    photo_id = Column(Integer, ForeignKey("photos.photo_id", ondelete="CASCADE"))
    
    # Stores the ArcFace 512-dimensional vector as a list of floats
    embedding = Column(ARRAY(Float), nullable=False) 
    
    photo = relationship("Photo", back_populates="face_embeddings")