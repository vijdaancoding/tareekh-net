from fastapi import Depends
from neo4j import AsyncDriver
from app.db.neo4j_client import get_driver as _get_driver


async def get_neo4j_driver() -> AsyncDriver:
    return await _get_driver()
