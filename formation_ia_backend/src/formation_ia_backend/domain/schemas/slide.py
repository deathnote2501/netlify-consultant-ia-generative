from typing import List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field

# --- Content Schemas ---
class TitleContent(BaseModel):
    title: str
    subtitle: str
    background_image_url: str

class MenuItem(BaseModel):
    text: str
    target_slide_id: int

class MenuContent(BaseModel):
    title: str
    subtitle: Optional[str] = None
    items: List[MenuItem]

# Base for content elements
class ContentElementData(BaseModel):
    pass # No common fields, type is the discriminator

class SubtitleElement(ContentElementData):
    type: Literal["subtitle"] = "subtitle"
    text: str

class TextElement(ContentElementData):
    type: Literal["text"] = "text"
    text: str # Can contain simple markdown for links

class ListElement(ContentElementData):
    type: Literal["ulist", "olist"]
    items: List[str]

class ImageElement(ContentElementData):
    type: Literal["image"] = "image"
    src: str
    alt: Optional[str] = None

class VideoElement(ContentElementData):
    type: Literal["video"] = "video"
    src: str # URL for embedding (e.g., YouTube iframe src)

ContentElement = Union[
    SubtitleElement,
    TextElement,
    ListElement,
    ImageElement,
    VideoElement
]

class ContentContent(BaseModel):
    title: str
    elements: List[ContentElement] = Field(..., discriminator="type")


class EmailContent(BaseModel):
    title: str = "Restez informé"
    placeholder: str = "Votre email"

class PaymentPlan(BaseModel):
    id: str # Stripe Price ID
    name: str
    price: str # e.g., "10€" or "$10"
    interval: str # e.g., "mois" or "an"

class PaymentContent(BaseModel):
    title: str = "Choisissez votre plan"
    plans: List[PaymentPlan]

# Union of all possible content structures
SlideContentUnion = Union[
    TitleContent,
    MenuContent,
    ContentContent,
    EmailContent,
    PaymentContent,
    dict # Fallback for generic JSON, if needed
]

# --- Slide Schemas ---
class SlideBase(BaseModel):
    order: int
    template_type: str
    content: SlideContentUnion # Use the Union for better validation
    specific_prompt: Optional[str] = None
    suggested_messages: Optional[List[str]] = None

class SlideCreate(SlideBase):
    pass

class SlideUpdate(BaseModel):
    order: Optional[int] = None
    template_type: Optional[str] = None
    content: Optional[SlideContentUnion] = None # Allow partial updates with specific content types
    specific_prompt: Optional[str] = None
    suggested_messages: Optional[List[str]] = None

class Slide(SlideBase):
    id: int

    model_config = {
        "from_attributes": True  # Renamed from orm_mode for Pydantic v2
    }

# --- Navigation Schema ---
class SlideNavigationInfo(BaseModel):
    id: int
    order: int
    title: Optional[str] = None # Title can be extracted from content
    template_type: str # Added to help frontend decide behavior (e.g. locking)
