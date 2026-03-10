from fastapi import APIRouter, Depends
from neo4j import AsyncDriver
from app.dependencies import get_neo4j_driver
from app.db.queries import get_graph_data

router = APIRouter()


@router.get("/graph")
async def graph(driver: AsyncDriver = Depends(get_neo4j_driver)):
    return await get_graph_data(driver)
