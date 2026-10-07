import datetime
from sqlalchemy import Column, Integer, String, Boolean, Numeric, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default="operator")  # admin, operator, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    incidents = relationship("Incident", back_populates="assigned_user")
    comments = relationship("IncidentComment", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    hostname = Column(String(100), unique=True, index=True, nullable=False)
    ip_address = Column(String(45), nullable=False)
    os_type = Column(String(20), nullable=False)  # linux, windows
    environment = Column(String(20), default="production")  # production, staging, development, dr
    status = Column(String(20), default="UNKNOWN", index=True)  # UP, DOWN, WARNING, UNKNOWN
    cpu_cores = Column(Integer, default=4)
    total_ram_gb = Column(Numeric(6, 2), default=16.00)
    total_disk_gb = Column(Numeric(8, 2), default=250.00)
    last_check = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

class MonitoringTarget(Base):
    __tablename__ = "monitoring_targets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    target_type = Column(String(20), nullable=False, index=True)  # host, website, api
    url_or_host = Column(String(255), nullable=False)
    port = Column(Integer, nullable=True)
    check_interval_sec = Column(Integer, default=30)
    expected_status_code = Column(Integer, default=200)
    status = Column(String(20), default="UNKNOWN", index=True)  # UP, DOWN, UNKNOWN
    last_response_time_ms = Column(Numeric(8, 2), nullable=True)
    last_check = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String(64), index=True, nullable=False)
    alert_name = Column(String(100), nullable=False)
    target_name = Column(String(100), nullable=False)
    target_type = Column(String(20), nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low, warning, info
    priority = Column(String(10), nullable=False, index=True)  # P1, P2, P3, P4
    status = Column(String(20), nullable=False, index=True)  # firing, resolved
    summary = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    metric_value = Column(String(50), nullable=True)
    threshold_value = Column(String(50), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    incidents = relationship("Incident", back_populates="alert")

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    incident_number = Column(String(30), unique=True, index=True, nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True)
    fingerprint = Column(String(64), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(10), nullable=False, index=True)  # P1, P2, P3, P4
    severity = Column(String(20), nullable=False)  # Critical, High, Medium, Low
    status = Column(String(20), default="OPEN", index=True, nullable=False)  # OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED
    target_system = Column(String(100), index=True, nullable=False)
    alert_source = Column(String(50), default="Prometheus")
    assigned_to_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    root_cause = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    mttr_seconds = Column(Integer, nullable=True)

    alert = relationship("Alert", back_populates="incidents")
    assigned_user = relationship("User", back_populates="incidents")
    comments = relationship("IncidentComment", back_populates="incident", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="incident", cascade="all, delete-orphan")

class IncidentComment(Base):
    __tablename__ = "incident_comments"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)

    incident = relationship("Incident", back_populates="comments")
    user = relationship("User", back_populates="comments")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=True, index=True)
    channel = Column(String(20), nullable=False)  # email, telegram, local
    recipient = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False, index=True)  # SENT, FAILED, PENDING
    payload = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow)
    error_message = Column(Text, nullable=True)

    incident = relationship("Incident", back_populates="notifications")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.datetime.utcnow, index=True)

    user = relationship("User", back_populates="audit_logs")
