from .user import router as user_router
from .admin import router as admin_router
from .game import router as game_router

__all__ = ["user_router", "admin_router", "game_router"]
