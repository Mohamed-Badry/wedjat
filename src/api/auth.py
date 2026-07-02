from fastapi import HTTPException, status, Header, Query
from sqlmodel import Session, select
import os
from loguru import logger

try:
    from .database import get_engine
    from .db_models import ApiKey
except ImportError:
    from database import get_engine
    from db_models import ApiKey

def verify_api_key(
    api_key: str | None = Header(default=None, alias="X-API-Key"),
    api_key_query: str | None = Query(default=None, alias="api_key"),
):
    require_auth = os.getenv("REQUIRE_AUTH", "false").lower() == "true"
    
    if not require_auth:
        return None

    key = api_key or api_key_query

    if not key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API Key header (X-API-Key) or query parameter (api_key)"
        )

    engine = get_engine()
    if not engine:
        logger.warning("DB engine not configured, denying access because REQUIRE_AUTH=true")
        raise HTTPException(status_code=500, detail="Database not configured")
        
    with Session(engine) as session:
        statement = select(ApiKey).where(ApiKey.key == key, ApiKey.is_active == True)
        result = session.exec(statement).first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid or inactive API Key"
            )
        return result

def seed_master_key():
    master_key = os.getenv("MASTER_API_KEY")
    if not master_key:
        return
        
    engine = get_engine()
    if not engine:
        return
        
    with Session(engine) as session:
        statement = select(ApiKey).where(ApiKey.key == master_key)
        result = session.exec(statement).first()
        if not result:
            logger.info("Seeding Master API Key from environment variables.")
            new_key = ApiKey(key=master_key, description="Master API Key (Env injected)", is_active=True)
            session.add(new_key)
            session.commit()
