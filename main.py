from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.neo4j_client import get_driver, close_driver
from app.db.schema import init_schema
from app.api.router import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    driver = await get_driver()
    await init_schema(driver)
    yield
    await close_driver()


app = FastAPI(
    title="Tareekh Net",
    description="Pakistani Politicians GraphRAG System",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
