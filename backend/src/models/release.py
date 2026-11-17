from sqlalchemy import String, Double, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class ModelVersion(Base):
    __tablename__ = 'model_versions'
    __table_args__ = (UniqueConstraint('job_id', name='uq_version_job'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'))
    status: Mapped[str] = mapped_column(String(20), default='pending')
    artifact_path: Mapped[str] = mapped_column(String(240), default='')
    checksum: Mapped[str] = mapped_column(String(64), default='')
    summary: Mapped[dict] = mapped_column(JSON, default=dict)
    note: Mapped[str] = mapped_column(String(500), default='')
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
    published_at: Mapped[float | None] = mapped_column(Double, nullable=True)
class ReleaseConfig(Base):
    __tablename__ = 'release_configs'
    id: Mapped[int] = mapped_column(primary_key=True)
    active_version_id: Mapped[int | None] = mapped_column(ForeignKey('model_versions.id'), nullable=True)
    canary_version_id: Mapped[int | None] = mapped_column(ForeignKey('model_versions.id'), nullable=True)
    canary_ratio: Mapped[int] = mapped_column(Integer, default=0)
    updated_by: Mapped[str] = mapped_column(String(150), default='')
    updated_at: Mapped[float] = mapped_column(Double, default=0)
