"""Optional service entry point; deliberately separate from Warehouse V2 backend."""
from .ai_monitor import create_ai_app
app=create_ai_app()
