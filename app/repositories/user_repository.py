from typing import Optional
from app.repositories.base_repository import BaseRepository
from app.models.user_model import User

from app.di.container import container
from dependency_injector.wiring import inject, Provide
from structlog import get_logger
from typing import Any, Optional

logger = get_logger(__name__)

class UserRepository(BaseRepository[User]):
    @inject
    def __init__(self, database = Provide["database"], cache : Optional[Any] = Provide["cache"]):
        super().__init__(User, database, cache)

    async def findByUsername(self, username: str) -> Optional[User]:
        
        try:
            logger.info("UserRepository: Finding user by username...")
            
            user = await self.findOne(filters={"username": username})
            
            logger.info("UserRepository: Found user by username.")
            
            return user
        
        except Exception as e:
            logger.error("UserRepository: Failed to find user by username.", exc_info=True)
            raise e

    async def findByEmail(self, email: str) -> Optional[User]:
        try:
            logger.info("UserRepository: Finding user by email...")
            
            user = await self.findOne(filters={"email": email})
            
            logger.info("UserRepository: Found user by email.")
            
            return user
        
        except Exception as e:
            logger.error("UserRepository: Failed to find user by email.", exc_info=True)
            raise e
