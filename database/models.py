import os
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
import uuid
from datetime import datetime

Base = declarative_base()

class Origin(Base):
    __tablename__ = "origin"
    id_origin = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    origin = Column(String, nullable=True)

class Status(Base):
    __tablename__ = "status"
    id_status = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    status = Column(String, nullable=True)

class Prompt(Base):
    __tablename__ = "prompt"
    id_prompt = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, nullable=False)
    id_origin = Column(String, ForeignKey("origin.id_origin"), nullable=False)
    prompt = Column(String, nullable=True)
    response = Column(String, nullable=True)
    

class Log(Base):
    __tablename__ = "log"
    id_log = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=lambda: datetime.utcnow(), nullable=False)
    id_prompt = Column(String, ForeignKey("prompt.id_prompt"), nullable=False)
    id_status = Column(String, ForeignKey("status.id_status"), nullable=False)
    id_origin = Column(String, ForeignKey("origin.id_origin"), nullable=False)

engine = create_engine("sqlite:///db_logsv2.db")  # Use PostgreSQL or MySQL in production
Base.metadata.create_all(engine)