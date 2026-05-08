from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/eval", summary="Run RAGAS evaluation on the query pipeline")
async def run_eval():
    try:
        from eval.runner import run_evaluation
        result = await run_evaluation()
        return result
    except ImportError as e:
        raise HTTPException(
            status_code=501,
            detail=f"RAGAS dependencies not installed: {e}. Run: uv pip install ragas datasets pandas",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
