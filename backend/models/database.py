"""
FloodGuard AI — SQLAlchemy database models and session management.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, Text, ForeignKey, JSON, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from backend.config import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ──────────────────────────────────────────────
# User model
# ──────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(200), unique=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    role = Column(String(50), default="citizen")          # citizen | operator | admin
    full_name = Column(String(200))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    reports = relationship("CitizenReport", back_populates="user")


# ──────────────────────────────────────────────
# Citizen Reports
# ──────────────────────────────────────────────
class CitizenReport(Base):
    __tablename__ = "citizen_reports"
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(50), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    city = Column(String(100))
    area = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    category = Column(String(100))        # waterlogging, drain_overflow, road_blockage, etc.
    severity = Column(String(50))         # LOW | MEDIUM | HIGH | CRITICAL
    language = Column(String(50))         # english | hindi | gujarati
    original_text = Column(Text)
    translated_text = Column(Text)
    ai_summary = Column(Text)
    status = Column(String(50), default="OPEN")   # OPEN | ASSIGNED | RESOLVED
    priority = Column(Integer, default=5)          # 1-10
    is_duplicate = Column(Boolean, default=False)
    duplicate_of = Column(String(50), nullable=True)
    image_path = Column(String(500), nullable=True)
    assigned_team = Column(String(200), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="reports")


# ──────────────────────────────────────────────
# Rainfall Data
# ──────────────────────────────────────────────
class RainfallData(Base):
    __tablename__ = "rainfall_data"
    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), index=True)
    area = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    rainfall_1h = Column(Float, default=0.0)
    rainfall_3h = Column(Float, default=0.0)
    rainfall_6h = Column(Float, default=0.0)
    rainfall_24h = Column(Float, default=0.0)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)
    data_source = Column(String(100), default="DEMO")


# ──────────────────────────────────────────────
# Flood Incidents
# ──────────────────────────────────────────────
class FloodIncident(Base):
    __tablename__ = "flood_incidents"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(100))
    area = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    severity = Column(String(50))
    status = Column(String(50), default="ACTIVE")
    rainfall_at_event = Column(Float)
    duration_hours = Column(Float, nullable=True)
    affected_population = Column(Integer, nullable=True)
    description = Column(Text)
    reported_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)
    assigned_team = Column(String(200), nullable=True)
    ai_assessment = Column(Text, nullable=True)


# ──────────────────────────────────────────────
# Drainage Infrastructure
# ──────────────────────────────────────────────
class Drain(Base):
    __tablename__ = "drains"
    id = Column(Integer, primary_key=True, index=True)
    drain_id = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(100))
    area = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    drain_type = Column(String(100))       # storm_drain | open_channel | culvert
    capacity_rating = Column(Float)        # 0-100
    condition = Column(String(50))         # GOOD | FAIR | POOR | CRITICAL
    last_cleaned = Column(DateTime, nullable=True)
    blockage_frequency = Column(Integer, default=0)   # times/year
    near_flood_zone = Column(Boolean, default=False)
    risk_score = Column(Float, default=0.0)
    maintenance_priority = Column(String(50), default="LOW")
    status = Column(String(50), default="OPERATIONAL")


# ──────────────────────────────────────────────
# Risk Predictions
# ──────────────────────────────────────────────
class RiskPrediction(Base):
    __tablename__ = "risk_predictions"
    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(String(50), unique=True, nullable=False, index=True)
    city = Column(String(100))
    area = Column(String(200))
    latitude = Column(Float)
    longitude = Column(Float)
    risk_score = Column(Float)            # 0-100
    risk_level = Column(String(50))       # LOW | MEDIUM | HIGH | CRITICAL
    confidence = Column(Float)            # 0-1
    predicted_time_window = Column(String(200))
    main_reasons = Column(JSON)
    recommended_action = Column(Text)
    feature_importance = Column(JSON)
    model_version = Column(String(100), default="v1.0")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    scenario = Column(String(100), default="LIVE")


# ──────────────────────────────────────────────
# Response Teams
# ──────────────────────────────────────────────
class ResponseTeam(Base):
    __tablename__ = "response_teams"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(String(50), unique=True, nullable=False)
    name = Column(String(200))
    city = Column(String(100))
    team_type = Column(String(100))     # pump_team | emergency | drainage | traffic
    status = Column(String(50), default="AVAILABLE")  # AVAILABLE | DEPLOYED | STANDBY | OFF_DUTY
    current_area = Column(String(200), nullable=True)
    contact = Column(String(200))
    capacity = Column(Integer, default=10)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)


# ──────────────────────────────────────────────
# Alerts
# ──────────────────────────────────────────────
class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String(50), unique=True, nullable=False)
    alert_level = Column(String(50))    # INFO | WARNING | HIGH | CRITICAL
    alert_type = Column(String(50))     # citizen | operator | emergency
    city = Column(String(100))
    area = Column(String(200), nullable=True)
    title = Column(String(300))
    message = Column(Text)
    is_simulated = Column(Boolean, default=True)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


# ──────────────────────────────────────────────
# AI Recommendations
# ──────────────────────────────────────────────
class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    id = Column(Integer, primary_key=True, index=True)
    rec_id = Column(String(50), unique=True, nullable=False, index=True)
    agent = Column(String(100))
    city = Column(String(100))
    area = Column(String(200), nullable=True)
    recommendation = Column(Text)
    reasoning = Column(Text)
    priority = Column(String(50))        # LOW | MEDIUM | HIGH | CRITICAL
    confidence = Column(Float, nullable=True)
    input_context = Column(JSON, nullable=True)
    approval_status = Column(String(50), default="PENDING")  # PENDING | APPROVED | REJECTED
    approved_by = Column(String(200), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    final_action = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# Damage Reports
# ──────────────────────────────────────────────
class DamageReport(Base):
    __tablename__ = "damage_reports"
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String(50), index=True)
    city = Column(String(100))
    area = Column(String(200))
    damage_level = Column(String(50))     # LOW | MEDIUM | HIGH | SEVERE
    affected_infrastructure = Column(JSON)
    estimated_priority = Column(String(50))
    recommended_next_step = Column(Text)
    ai_assessment = Column(Text)
    is_preliminary = Column(Boolean, default=True)
    image_paths = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


# ──────────────────────────────────────────────
# Audit Logs
# ──────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String(200))          # system | username
    agent = Column(String(100), nullable=True)
    action = Column(String(300))
    resource_type = Column(String(100))
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(50), nullable=True)


def create_tables():
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)
