from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select # Needed for select query

from formation_ia_backend.infrastructure.database.session import get_async_db
from formation_ia_backend.application.services.slide_service import SlideService
from formation_ia_backend.domain.schemas.slide import Slide as SlideSchema, SlideNavigationInfo
from formation_ia_backend.application.services.user_service import current_active_user, optional_current_active_user
from formation_ia_backend.domain.schemas.user import UserRead
from formation_ia_backend.domain.models.slide import DbSlide # Import DbSlide for the query

router = APIRouter()

def get_slide_service() -> SlideService:
    return SlideService()

@router.get("/{slide_id}", response_model=SlideSchema)
async def read_slide(
    slide_id: int,
    db: AsyncSession = Depends(get_async_db),
    slide_service: SlideService = Depends(get_slide_service),
    current_user: Optional[UserRead] = Depends(optional_current_active_user)
):
    db_slide = await slide_service.get_slide_by_id(db, slide_id=slide_id) # This returns SlideSchema
    if db_slide is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Slide not found")

    # Rule 1: First slide (order 1) is always public
    # Assuming SlideSchema has an 'order' attribute, which it does from SlideBase
    if db_slide.order == 1:
        return db_slide

    # Rule 2: All other slides require at least authentication
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for this slide."
        )

    # Rule 3: Slides after an "Email" type slide require email verification
    # Query for any 'Email' type slide with an order number less than the current slide's order
    email_slide_exists_before_query = (
        select(DbSlide.id)
        .filter(DbSlide.template_type == "Email", DbSlide.order < db_slide.order)
        .limit(1)
    )
    email_slide_exists_before_result = await db.execute(email_slide_exists_before_query)
    an_email_slide_precedes_current = email_slide_exists_before_result.scalars().first() is not None

    if an_email_slide_precedes_current:
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, # 403 Forbidden as user is authenticated but not authorized
                detail="Email verification required to access this slide."
            )

    # If authenticated and (no preceding Email slide OR email is verified), allow access.
    return db_slide

@router.get("/navigation", response_model=List[SlideNavigationInfo], dependencies=[Depends(current_active_user)])
async def get_slide_navigation(
    db: AsyncSession = Depends(get_async_db),
    slide_service: SlideService = Depends(get_slide_service)
):
    return await slide_service.get_slides_for_navigation(db)
