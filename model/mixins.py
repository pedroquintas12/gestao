# models/mixins.py
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy import DateTime
from config.db import db

TZ_RECIFE = ZoneInfo("America/Recife")

class TimestampMixin:
    created_at = db.Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(TZ_RECIFE),   # salva hora local de Recife
        nullable=False
    )
    updated_at = db.Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(TZ_RECIFE),
        onupdate=lambda: datetime.now(TZ_RECIFE),  # atualiza em cada UPDATE
        nullable=False
    )

