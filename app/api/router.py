from fastapi import APIRouter
from app.api import ingestion, hitl, politicians, chat, graph_data, eval as eval_api

router = APIRouter(prefix="/api/v1")

router.include_router(ingestion.router, tags=["Ingestion"])
router.include_router(hitl.router, tags=["HITL"])
router.include_router(politicians.router, tags=["Politicians"])
router.include_router(chat.router, tags=["Chat"])
router.include_router(graph_data.router, tags=["Graph"])
router.include_router(eval_api.router, tags=["Evaluation"])
