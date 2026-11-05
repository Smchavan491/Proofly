"""SQLAlchemy table definitions for Resolve's case workflow."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    capture_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class EvidenceItem(Base):
    __tablename__ = "evidence_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    agent_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    recommendation: Mapped[str] = mapped_column(Text)
    evidence_ids: Mapped[list] = mapped_column(JSON, default=list)


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft")


class Action(Base):
    __tablename__ = "actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    action_type: Mapped[str] = mapped_column(String(64))
    approval_status: Mapped[str] = mapped_column(String(32), default="pending")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    action_id: Mapped[int | None] = mapped_column(ForeignKey("actions.id"), nullable=True)
    result: Mapped[str] = mapped_column(Text)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
