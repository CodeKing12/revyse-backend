from fastapi import APIRouter

router = APIRouter()

@router.post("/uploads/material")
async def upload_material():
    pass