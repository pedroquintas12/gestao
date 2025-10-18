from datetime import datetime, timezone
from sqlalchemy.types import TypeDecorator, DateTime

class UTCDateTime(TypeDecorator):
    """
    Garante que SEMPRE salvamos e lemos em UTC (aware).
    Funciona com SQLite, Postgres, MySQL.
    """
    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        # chamado antes de gravar no banco
        if value is None:
            return None
        if value.tzinfo is None:
            # se vier naive, assume que é hora local e converte para UTC
            value = value.astimezone(timezone.utc) if hasattr(value, "astimezone") else datetime.now(timezone.utc)
            # ou: value = value.replace(tzinfo=timezone.utc)  # se você já garantir que é UTC
        else:
            value = value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        # chamado ao ler do banco
        if value is None:
            return None
        # normaliza para timezone UTC (aware)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
