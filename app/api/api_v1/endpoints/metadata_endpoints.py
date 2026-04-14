from typing import Any
from fastapi import APIRouter
from pydantic import AnyHttpUrl

router: APIRouter = APIRouter(tags=["metadata"])


@router.get("/metadata", status_code=200)
async def get_metadata(url: AnyHttpUrl) -> Any:
    print(url)
    return {"ok": "ok"}


@router.post("/metadata", status_code=201)
async def collect_metadata(url: AnyHttpUrl) -> Any:
    print(url)
    return {"ok": "ok"}
