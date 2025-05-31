from datetime import datetime
from typing import Optional # Optional might be needed if some fields in Base become optional later
from uuid import UUID
from pydantic import BaseModel

class SubscriptionBase(BaseModel):
    id: str # Stripe Subscription ID
    user_id: UUID
    stripe_customer_id: str
    plan_id: str # Stripe Price ID
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

    # Timestamps from the model that can be exposed if needed
    created_at: datetime
    updated_at: datetime

class Subscription(SubscriptionBase): # Schema for reading/returning subscription data
    # This schema is primarily for reading. Creation/update might be different.
    model_config = {
        "from_attributes": True # Pydantic V2 for ORM mode
    }

# Example of a schema that might be used for webhook processing (subset of Stripe event data)
# Not creating this as part of the current subtask unless explicitly requested by a future one.
# class StripeSubscriptionWebhookEventData(BaseModel):
#     id: str # Stripe Subscription ID
#     customer: str # Stripe Customer ID
#     status: str
#     current_period_start: int # Stripe sends timestamps as Unix seconds
#     current_period_end: int
#     plan: dict # Contains plan details like id (Price ID)
#     cancel_at_period_end: bool
#     # Add other relevant fields from the Stripe 'data.object' part of the event
