from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from formation_ia_backend.infrastructure.database.session import get_async_db
from formation_ia_backend.application.services.slide_service import SlideService
from formation_ia_backend.domain.schemas.slide import Slide as SlideSchema, SlideNavigationInfo
# Import the new optional dependency and UserRead for type hint
from formation_ia_backend.application.services.user_service import current_active_user, optional_current_active_user
from formation_ia_backend.domain.schemas.user import UserRead

router = APIRouter()

def get_slide_service() -> SlideService:
    return SlideService()

@router.get("/{slide_id}", response_model=SlideSchema)
async def read_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_async_db),
    slide_service: SlideService = Depends(get_slide_service),
    current_user: Optional[UserRead] = Depends(optional_current_active_user) # Use optional dependency
):
    db_slide = await slide_service.get_slide_by_id(db, slide_id=slide_id)
    if db_slide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")

    # Assuming slide ID 1 is the first public slide
    # (Based on seeding order, ID 1 should be the first slide)
    is_first_slide = (db_slide.id == 1)

    if not is_first_slide and current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to view this slide"
            # Can also add: headers={"WWW-Authenticate": "Bearer"}, if desired
        )
    return db_slide

@router.get("/navigation", response_model=List[SlideNavigationInfo], dependencies=[Depends(current_active_user)])
async def get_slide_navigation(
    db: AsyncSession = Depends(get_async_db),
    slide_service: SlideService = Depends(get_slide_service)
    # current_user is implicitly available via the top-level dependency if needed for logic here,
    # but its presence is enforced by `dependencies=[Depends(current_active_user)]`
):
    return await slide_service.get_slides_for_navigation(db)

# Optional CRUD endpoints remain commented out
