from sqlalchemy import String, Double, Integer, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class PredictionOrder(Base):
    __tablename__ = 'prediction_orders'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    version_id: Mapped[int] = mapped_column(ForeignKey('model_versions.id'))
    lane: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default='completed')
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    total_kwh: Mapped[float] = mapped_column(Double, default=0)
    created_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    created_at: Mapped[float] = mapped_column(Double)
class PredictionItem(Base):
    __tablename__ = 'prediction_items'
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey('prediction_orders.id'), index=True)
    day: Mapped[str] = mapped_column(String(10))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    kwh: Mapped[float] = mapped_column(Double)
    flags: Mapped[list] = mapped_column(JSON, default=list)
