from sqlalchemy import Column, String, Integer, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Repository(Base):
    __tablename__ = 'repositories'

    id = Column(String, primary_key=True) # e.g., 'test_run_lodash'
    name = Column(String, nullable=False)
    clone_url = Column(String, nullable=False)
    indexed_at = Column(DateTime, default=datetime.utcnow)

    # Relationship linking back down to individual files
    files = relationship("FileMetadata", back_populates="repository", cascade="all, delete-orphan")

class FileMetadata(Base):
    __tablename__ = 'file_metadata'

    id = Column(Integer, primary_key=True, autoincrement=True)
    repository_id = Column(String, ForeignKey('repositories.id'), nullable=False)
    relative_path = Column(String, nullable=False) # e.g., 'src/utils.js'
    file_extension = Column(String, nullable=False)
    
    repository = relationship("Repository", back_populates="files")