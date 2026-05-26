from typing import Any, List, Optional, Type, TypeVar, Generic, Dict, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, func, select, update, delete
import json
from structlog import get_logger

T = TypeVar("T")
logger = get_logger(__name__)

class BaseRepository(Generic[T]):
    def __init__(self, model: Type[T], database, cache):
        self.model = model
        self.database = database
        self.cache = cache

    async def findById(
        self, 
        id: Any, 
        use_cache: bool = False, 
        cache_key: str = None,
        ttl: int = 3600
    ) -> Optional[T]:
        """single item detail page"""
        try:
            logger.info("BaseRepository: Finding by id...")

            if use_cache and self.cache and cache_key:
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    return cached_data

            async with self.database.get_session("read") as session:
                stmt = select(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                db_item = result.scalar_one_or_none()
                
                if db_item and use_cache and self.cache and cache_key:
                    await self.cache.set(cache_key, db_item, ttl=ttl)
                    logger.info(f"BaseRepository: Found by id. {db_item}")
                    
                return db_item
        
        except Exception as e:
            logger.error("BaseRepository: Failed to find by id.", exc_info=True)
            raise e
    
    async def findAll(
        self, 
        filters: Dict[str, Any] = None, 
        use_cache: bool = False, 
        cache_key: str = None,
        ttl: int = 3600
    ) -> List[T]:
        """filtered/searched lists (with cache!)"""
        try:
            logger.info("BaseRepository: Find by All")

            if use_cache and self.cache and cache_key:
                cached_data = await self.cache.get(cache_key)
                if cached_data:
                    return cached_data

            async with self.database.get_session("read") as session:
                stmt = select(self.model)
                if filters:
                    for key, value in filters.items():
                        stmt = stmt.where(getattr(self.model, key) == value)
                
                result = await session.execute(stmt)
                results = result.scalars().all()

                if use_cache and self.cache and cache_key:
                    await self.cache.set(cache_key, results, ttl=ttl)

                logger.info(f"BaseRepository: Found by All. {results}")
                
                return list(results)

        except Exception as e:
            logger.error("BaseRepository: Failed to find by All.", exc_info=True)
            raise e

    async def findAndCountAll(
        self, 
        filters: Dict[str, Any] = None, 
        offset: int = 0, 
        limit: int = 10
    ) -> Dict[str, Any]:
        """paginated tables"""
        try:
            logger.info("BaseRepository: Find and Count All")

            async with self.database.get_session("read") as session:
                # Count query
                count_stmt = select(func.count()).select_from(self.model)
                if filters:
                    for key, value in filters.items():
                        count_stmt = count_stmt.where(getattr(self.model, key) == value)
                
                count_result = await session.execute(count_stmt)
                total_count = count_result.scalar()
                
                # Data query
                stmt = select(self.model)
                if filters:
                    for key, value in filters.items():
                        stmt = stmt.where(getattr(self.model, key) == value)
                
                stmt = stmt.offset(offset).limit(limit)
                result = await session.execute(stmt)
                rows = result.scalars().all()
                
                logger.info(f"BaseRepository: Found by All. {rows}")
                
                return {
                    "total": total_count,
                    "rows": list(rows),
                    "offset": offset,
                    "limit": limit
                }
        except Exception as e:
            logger.error("BaseRepository: Failed to find and count all.", exc_info=True)
            raise e

    async def create(self, data: Union[Dict[str, Any], T]) -> T:
        """normal insert"""
        try:
            logger.info("BaseRepository: Create")
            
            async with self.database.get_session("write") as session:
                if isinstance(data, dict):
                    db_item = self.model(**data)
                else:
                    db_item = data
                
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
                
                logger.info(f"BaseRepository: Created. {db_item}")
                
                return db_item

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to create.", exc_info=True)
            raise e

    async def update(self, id: Any, data: Dict[str, Any]) -> Optional[T]:
        """normal update"""
        try:
            logger.info("BaseRepository: Update")
            
            async with self.database.get_session("write") as session:
                stmt = select(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                db_item = result.scalar_one_or_none()
                
                if not db_item:
                    return None
            
                for key, value in data.items():
                    setattr(db_item, key, value)
            
                session.add(db_item)
                await session.commit()
                await session.refresh(db_item)
                
                logger.info(f"BaseRepository: Updated. {db_item}")
    
                return db_item

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to update.", exc_info=True)
            raise e

    async def delete(self, id: Any) -> bool:
        """normal delete"""
        try:
            logger.info("BaseRepository: Delete")
            
            async with self.database.get_session("write") as session:
                stmt = select(self.model).where(self.model.id == id)
                result = await session.execute(stmt)
                db_item = result.scalar_one_or_none()
                
                if not db_item:
                    return False
            
                await session.delete(db_item)
                await session.commit()
                
                logger.info(f"BaseRepository: Deleted. {db_item}")
                
                return True

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to delete.", exc_info=True)
            raise e

    async def count(self, filters: Dict[str, Any] = None) -> int:
        """stats"""
        try:
            logger.info("BaseRepository: Count")
            
            async with self.database.get_session("read") as session:
                stmt = select(func.count()).select_from(self.model)
                if filters:
                    for key, value in filters.items():
                        stmt = stmt.where(getattr(self.model, key) == value)
                
                result = await session.execute(stmt)
                count = result.scalar()
                
                logger.info(f"BaseRepository: Counted. {count}")
                
                return count

        except Exception as e:
            logger.error("BaseRepository: Failed to count.", exc_info=True)
            raise e

    async def exists(self, filters: Dict[str, Any]) -> bool:
        """validations"""
        try:
            logger.info("BaseRepository: Exists")
            
            count = await self.count(filters)
            
            logger.info(f"BaseRepository: Exists. {count}")
            
            return count > 0

        except Exception as e:
            logger.error("BaseRepository: Failed to exists.", exc_info=True)
            raise e

    async def findOne(self, filters: Dict[str, Any]) -> Optional[T]:
        try:
            logger.info("BaseRepository: Find One")
            
            async with self.database.get_session("read") as session:
                stmt = select(self.model)
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
                
                result = await session.execute(stmt)
                db_item = result.scalar_one_or_none()
                
                logger.info(f"BaseRepository: Found one. {db_item}")
                
                return db_item

        except Exception as e:
            logger.error("BaseRepository: Failed to find one.", exc_info=True)
            raise e

    async def bulkCreate(self, data_list: List[Dict[str, Any]]) -> List[T]:
        try:
            logger.info("BaseRepository: Bulk Create")
            
            async with self.database.get_session("write") as session:
                db_items = [self.model(**data) for data in data_list]
                session.add_all(db_items)
                await session.commit()
                for item in db_items:
                    await session.refresh(item)
                
                logger.info(f"BaseRepository: Bulk Created. {db_items}")
                
                return db_items

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to bulk create.", exc_info=True)
            raise e

    async def updateWhere(self, filters: Dict[str, Any], data: Dict[str, Any]) -> int:
        try:
            logger.info("BaseRepository: Update Where")
            
            async with self.database.get_session("write") as session:
                stmt = update(self.model).values(**data)
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
                result = await session.execute(stmt)
                await session.commit()
                
                logger.info(f"BaseRepository: Updated where. {result.rowcount}")
                
                return result.rowcount

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to update where.", exc_info=True)
            raise e

    async def deleteWhere(self, filters: Dict[str, Any]) -> int:
        try:
            logger.info("BaseRepository: Delete Where")
            
            async with self.database.get_session("write") as session:
                stmt = delete(self.model)
                for key, value in filters.items():
                    stmt = stmt.where(getattr(self.model, key) == value)
                result = await session.execute(stmt)
                await session.commit()
                
                logger.info(f"BaseRepository: Deleted where. {result.rowcount}")
                
                return result.rowcount

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to delete where.", exc_info=True)
            raise e

    async def executeQuery(self, query: str, params: Dict[str, Any] = None) -> Any:
        try:
            logger.info("BaseRepository: Execute Query")
            
            async with self.database.get_session("write") as session:
                result = await session.execute(text(query), params or {})
                if query.strip().lower().startswith("select"):
                    return result.fetchall()
                await session.commit()
                
                logger.info(f"BaseRepository: Executed query. {result}")
                
                return result.rowcount

        except Exception as e:
            await session.rollback()
            logger.error("BaseRepository: Failed to execute query.", exc_info=True)
            raise e
