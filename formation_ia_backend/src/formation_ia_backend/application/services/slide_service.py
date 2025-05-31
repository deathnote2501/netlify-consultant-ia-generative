from typing import List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func # for count

from formation_ia_backend.domain.models.slide import DbSlide
from formation_ia_backend.domain.schemas.slide import Slide as SlideSchema, SlideNavigationInfo, SlideCreate
from formation_ia_backend.domain.schemas.slide import TitleContent, MenuContent, MenuItem, ContentContent, EmailContent, PaymentContent, PaymentPlan, TextElement # Import content types for seeding

class SlideService:
    async def get_slide_by_id(self, db: AsyncSession, slide_id: int) -> Optional[SlideSchema]:
        result = await db.execute(select(DbSlide).filter(DbSlide.id == slide_id))
        db_slide = result.scalars().first()
        if db_slide:
            return SlideSchema.model_validate(db_slide) # Pydantic v2
        return None

    async def get_slides_for_navigation(self, db: AsyncSession) -> List[SlideNavigationInfo]:
        result = await db.execute(select(DbSlide).order_by(DbSlide.order))
        db_slides = result.scalars().all()

        navigation_info_list = []
        for slide in db_slides:
            title = None
            # Attempt to extract title from content based on template_type
            if isinstance(slide.content, dict):
                if slide.template_type in ["Title", "Menu", "Content", "Email", "Payment"]:
                    title = slide.content.get("title")

            navigation_info_list.append(
                SlideNavigationInfo(
                    id=slide.id,
                    order=slide.order,
                    title=title,
                    template_type=slide.template_type
                )
            )
        return navigation_info_list

    async def create_initial_slides(self, db: AsyncSession):
        result = await db.execute(select(func.count(DbSlide.id)))
        count = result.scalar_one_or_none()

        if count == 0:
            # Create initial slides
            initial_slides_data = [
                SlideCreate(
                    order=1, template_type="Title",
                    content=TitleContent(title="Welcome to the Course!", subtitle="Learn amazing things about AI.", background_image_url="https://example.com/images/title_bg.jpg"),
                    specific_prompt="This is the title slide. Introduce the course.",
                    suggested_messages=["What is this course about?", "Tell me more."]),
                SlideCreate(
                    order=2, template_type="Menu",
                    content=MenuContent(title="Course Menu", items=[
                        MenuItem(text="Introduction", target_slide_id=3),
                        MenuItem(text="Core Concepts", target_slide_id=4),
                        MenuItem(text="Stay Informed", target_slide_id=5),
                        MenuItem(text="Get Full Access", target_slide_id=6)
                    ]),
                    specific_prompt="This is the menu. Help the user navigate."),
                SlideCreate(
                    order=3, template_type="Content",
                    content=ContentContent(title="Introduction to AI", elements=[
                        TextElement(type="text", text="AI is transforming the world. This section introduces the basics.")
                    ]),
                    specific_prompt="Focus on introductory concepts of AI."),
                SlideCreate(
                    order=4, template_type="Content",
                    content=ContentContent(title="Core AI Concepts", elements=[
                        TextElement(type="text", text="Explore machine learning, neural networks, and more.")
                    ]),
                    specific_prompt="Explain core AI concepts in simple terms."),
                SlideCreate(
                    order=5, template_type="Email",
                    content=EmailContent(title="Stay Updated", placeholder="Enter your email for news"),
                    specific_prompt="Encourage users to submit their email for updates."),
                SlideCreate(
                    order=6, template_type="Payment",
                    content=PaymentContent(title="Unlock Premium Content", plans=[
                        PaymentPlan(id="price_fake_monthly", name="Monthly Access", price="10€", interval="month"),
                        PaymentPlan(id="price_fake_yearly", name="Yearly Access", price="100€", interval="year")
                    ]),
                    specific_prompt="Explain the benefits of premium access and guide towards a plan.")
            ]

            for slide_data in initial_slides_data:
                # content needs to be a dict for DbSlide.content
                db_slide = DbSlide(
                    order=slide_data.order,
                    template_type=slide_data.template_type,
                    content=slide_data.content.model_dump(), # Pydantic v2
                    specific_prompt=slide_data.specific_prompt,
                    suggested_messages=slide_data.suggested_messages
                )
                db.add(db_slide)

            await db.commit() # Commit all new slides together
