import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field

# ------------------------------------------------------------------------------
# Auth & User Schemas
# ------------------------------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    role: str = "operator"
    is_active: bool = True

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# Server Inventory Schemas
# ------------------------------------------------------------------------------
class ServerBase(BaseModel):
    hostname: str
    ip_address: str
    os_type: str  # linux, windows
    environment: str = "production"
    status: str = "UNKNOWN"
    cpu_cores: int = 4
    total_ram_gb: float = 16.0
    total_disk_gb: float = 250.0

class ServerCreate(ServerBase):
    pass

class ServerUpdate(BaseModel):
    ip_address: Optional[str] = None
    status: Optional[str] = None
    environment: Optional[str] = None
    cpu_cores: Optional[int] = None
    total_ram_gb: Optional[float] = None
    total_disk_gb: Optional[float] = None

class ServerResponse(ServerBase):
    id: int
    last_check: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# Synthetic Monitoring Targets
# ------------------------------------------------------------------------------
class MonitoringTargetBase(BaseModel):
    name: str
    target_type: str  # host, website, api
    url_or_host: str
    port: Optional[int] = None
    check_interval_sec: int = 30
    expected_status_code: int = 200
    status: str = "UNKNOWN"
    is_active: bool = True

class MonitoringTargetCreate(MonitoringTargetBase):
    pass

class MonitoringTargetResponse(MonitoringTargetBase):
    id: int
    last_response_time_ms: Optional[float] = None
    last_check: Optional[datetime.datetime] = None
    created_at: datetime.datetime

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# Alertmanager Ingestion Webhook Schemas
# ------------------------------------------------------------------------------
class PrometheusAlertItem(BaseModel):
    status: str  # firing, resolved
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    startsAt: str
    endsAt: Optional[str] = None
    generatorURL: Optional[str] = None
    fingerprint: Optional[str] = None

class AlertmanagerWebhookPayload(BaseModel):
    version: Optional[str] = "4"
    groupKey: Optional[str] = None
    status: str  # firing, resolved
    receiver: Optional[str] = None
    alerts: List[PrometheusAlertItem] = Field(default_factory=list)
    commonLabels: Dict[str, str] = Field(default_factory=dict)
    commonAnnotations: Dict[str, str] = Field(default_factory=dict)
    externalURL: Optional[str] = None

# ------------------------------------------------------------------------------
# Incident Management Schemas
# ------------------------------------------------------------------------------
class IncidentCommentCreate(BaseModel):
    comment: str

class IncidentCommentResponse(BaseModel):
    id: int
    incident_id: int
    user_id: Optional[int] = None
    comment: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True

class IncidentBase(BaseModel):
    title: str
    description: str
    priority: str  # P1, P2, P3, P4
    severity: str  # Critical, High, Medium, Low
    status: str = "OPEN"
    target_system: str
    alert_source: str = "Prometheus"

class IncidentCreate(IncidentBase):
    fingerprint: str
    alert_id: Optional[int] = None

class IncidentUpdate(BaseModel):
    status: Optional[str] = None  # OPEN, ACKNOWLEDGED, IN_PROGRESS, RESOLVED
    assigned_to_user_id: Optional[int] = None
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None

class IncidentResponse(IncidentBase):
    id: int
    incident_number: str
    fingerprint: str
    alert_id: Optional[int] = None
    assigned_to_user_id: Optional[int] = None
    root_cause: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: datetime.datetime
    acknowledged_at: Optional[datetime.datetime] = None
    resolved_at: Optional[datetime.datetime] = None
    mttr_seconds: Optional[int] = None
    comments: List[IncidentCommentResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

# ------------------------------------------------------------------------------
# Operational & Executive Reports
# ------------------------------------------------------------------------------
class ExecutiveSummaryResponse(BaseModel):
    total_servers: int
    servers_up: int
    servers_down: int
    servers_warning: int
    overall_availability_pct: float
    total_incidents: int
    open_incidents: int
    p1_count: int
    p2_count: int
    p3_count: int
    p4_count: int
    avg_mttr_minutes: float
    top_alerting_systems: List[Dict[str, Any]]
