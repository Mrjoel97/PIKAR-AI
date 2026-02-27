"""Database models for Pikar AI.

This module defines all SQLAlchemy models for the application.
Used by Alembic for migrations and by application code for type-safe DB operations.
"""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class UserProfile(Base):
    """User profile information."""

    __tablename__ = "users_profile"

    user_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    business_context: Mapped[Optional[str]] = mapped_column(Text)
    persona: Mapped[Optional[str]] = mapped_column(String(50), default="solopreneur")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class UserExecutiveAgent(Base):
    """User executive agent configuration."""

    __tablename__ = "user_executive_agents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("users_profile.user_id"), nullable=False
    )
    agent_name: Mapped[str] = mapped_column(String(255), default="Executive Agent")
    configuration: Mapped[Optional[dict]] = mapped_column(JSON)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (UniqueConstraint("user_id", name="uq_user_agent"),)


class Session(Base):
    """ADK session storage."""

    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    app_name: Mapped[str] = mapped_column(String(255), nullable=False)
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    session_id: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_sessions_app_user", "app_name", "user_id"),
        Index("ix_sessions_session_id", "session_id"),
    )


class SessionEvent(Base):
    """ADK session events for conversation history."""

    __tablename__ = "session_events"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_data: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_session_events_session", "session_id", "event_index"),
    )


class SessionVersionHistory(Base):
    """Version history for session state changes."""

    __tablename__ = "session_version_history"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    session_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    state_diff: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_version_history_session", "session_id", "version"),
    )


class InitiativeTemplate(Base):
    """Predefined initiative templates."""

    __tablename__ = "initiative_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    phases: Mapped[Optional[list]] = mapped_column(JSON)
    default_priority: Mapped[str] = mapped_column(String(20), default="medium")
    persona: Mapped[Optional[str]] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class Initiative(Base):
    """Business initiatives/projects."""

    __tablename__ = "initiatives"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    status: Mapped[str] = mapped_column(String(50), default="active")
    phase: Mapped[str] = mapped_column(String(50), default="ideation")
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_initiatives_user", "user_id"),)


class UserJourney(Base):
    """User journey definitions."""

    __tablename__ = "user_journeys"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    stages: Mapped[Optional[list]] = mapped_column(JSON)
    kpis: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_user_journeys_user", "user_id"),)


class WorkflowTemplate(Base):
    """Workflow template definitions."""

    __tablename__ = "workflow_templates"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    phases: Mapped[Optional[list]] = mapped_column(JSON)
    steps: Mapped[Optional[list]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (UniqueConstraint("name", name="uq_workflow_template_name"),)


class WorkflowExecution(Base):
    """Workflow execution instances."""

    __tablename__ = "workflow_executions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    template_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_templates.id")
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    current_phase: Mapped[Optional[str]] = mapped_column(String(100))
    context: Mapped[Optional[dict]] = mapped_column(JSON)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_workflow_executions_user", "user_id"),
        Index("ix_workflow_executions_template", "template_id"),
    )


class WorkflowStep(Base):
    """Individual steps within workflow executions."""

    __tablename__ = "workflow_steps"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    execution_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False
    )
    step_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_workflow_steps_execution", "execution_id"),)


class ApprovalRequest(Base):
    """Human approval requests for workflow steps."""

    __tablename__ = "approval_requests"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_approval_requests_user", "user_id"),
        Index("ix_approval_requests_token", "token"),
    )


class VaultDocument(Base):
    """Knowledge vault documents."""

    __tablename__ = "vault_documents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    source_type: Mapped[Optional[str]] = mapped_column(String(50))
    source_url: Mapped[Optional[str]] = mapped_column(String(1000))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_vault_documents_user", "user_id"),)


class Embedding(Base):
    """Document embeddings for RAG."""

    __tablename__ = "embeddings"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    document_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault_documents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list] = mapped_column(JSON, nullable=False)
    model: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_embeddings_document", "document_id"),)


class AgentGoogleDoc(Base):
    """Google Docs created by agents."""

    __tablename__ = "agent_google_docs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    google_doc_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500))
    document_url: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_agent_google_docs_user", "user_id"),)


class MediaAsset(Base):
    """Media assets (images, videos)."""

    __tablename__ = "media_assets"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))
    storage_path: Mapped[Optional[str]] = mapped_column(String(1000))
    public_url: Mapped[Optional[str]] = mapped_column(String(1000))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_media_assets_user", "user_id"),)


class LandingPage(Base):
    """Landing page configurations."""

    __tablename__ = "landing_pages"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    html_content: Mapped[Optional[str]] = mapped_column(Text)
    react_content: Mapped[Optional[str]] = mapped_column(Text)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    status: Mapped[str] = mapped_column(String(20), default="draft")
    published_url: Mapped[Optional[str]] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_landing_pages_user", "user_id"),
        Index("ix_landing_pages_status", "status"),
    )


class LandingForm(Base):
    """Forms for landing pages."""

    __tablename__ = "landing_forms"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    page_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_pages.id"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    fields: Mapped[Optional[list]] = mapped_column(JSON)
    config: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_landing_forms_page", "page_id"),)


class FormSubmission(Base):
    """Form submission data."""

    __tablename__ = "form_submissions"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    form_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("landing_forms.id"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    data: Mapped[Optional[dict]] = mapped_column(JSON, default={})
    email_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    crm_synced: Mapped[bool] = mapped_column(Boolean, default=False)
    crm_contact_id: Mapped[Optional[str]] = mapped_column(String(255))
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_form_submissions_form", "form_id"),
        Index("ix_form_submissions_user", "user_id"),
    )


class Department(Base):
    """Business departments."""

    __tablename__ = "departments"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="IDLE")
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_departments_user", "user_id"),)


class Product(Base):
    """Products for inventory management."""

    __tablename__ = "products"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)
    price: Mapped[Optional[float]] = mapped_column(Float)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_products_user", "user_id"),)


class Inventory(Base):
    """Product inventory tracking."""

    __tablename__ = "inventory"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    location: Mapped[Optional[str]] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_inventory_product", "product_id"),)


class Order(Base):
    """Customer orders."""

    __tablename__ = "orders"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_email: Mapped[Optional[str]] = mapped_column(String(255))
    total_amount: Mapped[float] = mapped_column(Float, default=0)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_orders_user", "user_id"),)


class OrderItem(Base):
    """Individual items in orders."""

    __tablename__ = "order_items"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=False
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_order_items_order", "order_id"),)


class Invoice(Base):
    """Invoices for orders."""

    __tablename__ = "invoices"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    order_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (Index("ix_invoices_order", "order_id"),)


class ConnectedAccount(Base):
    """Connected third-party accounts (OAuth)."""

    __tablename__ = "connected_accounts"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_account_id: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token: Mapped[Optional[str]] = mapped_column(Text)
    refresh_token: Mapped[Optional[str]] = mapped_column(Text)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_connected_accounts_user", "user_id"),
        UniqueConstraint(
            "provider", "provider_account_id", name="uq_provider_account"
        ),
    )


class Agent(Base):
    """Agent configurations."""

    __tablename__ = "agents"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    configuration: Mapped[Optional[dict]] = mapped_column(JSON)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_agents_user", "user_id"),)


class Skill(Base):
    """Skill definitions."""

    __tablename__ = "skills"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    knowledge: Mapped[Optional[str]] = mapped_column(Text)
    is_global: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_skills_user", "user_id"),
        UniqueConstraint("name", "user_id", name="uq_skill_name_user"),
    )


class UserConfiguration(Base):
    """User configuration settings."""

    __tablename__ = "user_configurations"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    key: Mapped[str] = mapped_column(String(100), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_user_configurations_user", "user_id"),
        UniqueConstraint("user_id", "key", name="uq_user_config_key"),
    )


class UserReport(Base):
    """Generated reports."""

    __tablename__ = "user_reports"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    report_type: Mapped[str] = mapped_column(String(100))
    content: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (Index("ix_user_reports_user", "user_id"),)


class MCPAuditLog(Base):
    """MCP tool invocation audit logs."""

    __tablename__ = "mcp_audit_logs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    agent_name: Mapped[Optional[str]] = mapped_column(String(255))
    user_id: Mapped[Optional[str]] = mapped_column(String(255))
    session_id: Mapped[Optional[str]] = mapped_column(String(255))
    query_sanitized: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    response_status: Mapped[str] = mapped_column(String(50), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)

    __table_args__ = (
        Index("ix_mcp_audit_logs_user", "user_id"),
        Index("ix_mcp_audit_logs_tool", "tool_name"),
        Index("ix_mcp_audit_logs_timestamp", "timestamp"),
    )


class AgentKnowledge(Base):
    """Agent knowledge for RAG system."""

    __tablename__ = "agent_knowledge"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    knowledge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(255))
    metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("ix_agent_knowledge_user", "user_id"),
        Index("ix_agent_knowledge_type", "knowledge_type"),
    )


class AIJob(Base):
    """Background AI jobs."""

    __tablename__ = "ai_jobs"

    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    user_id: Mapped[str] = mapped_column(String(255), nullable=False)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    input_data: Mapped[Optional[dict]] = mapped_column(JSON)
    result: Mapped[Optional[dict]] = mapped_column(JSON)
    error: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_ai_jobs_user", "user_id"),
        Index("ix_ai_jobs_status", "status"),
    )
