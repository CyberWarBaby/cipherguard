from typing import Dict, Any, List, Optional
from app.db.client import (
    get_supabase_client,
    db_record_event as insert_integration_event,
    db_list_events as fetch_recent_events
)
from app.config import settings

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY

__all__ = ["get_supabase_client", "insert_integration_event", "fetch_recent_events", "SUPABASE_URL", "SUPABASE_KEY"]
