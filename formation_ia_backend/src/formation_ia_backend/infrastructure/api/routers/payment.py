from fastapi import APIRouter, Depends, HTTPException, status, Request, Header, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, constr, EmailStr # Added EmailStr for consistency if needed elsewhere, not used in this file directly
from typing import Optional, Dict, Any # Added Dict, Any for response_model
import stripe # For stripe.Event type hint

from formation_ia_backend.infrastructure.database.session import get_async_db
from formation_ia_backend.application.services.user_service import UserManager, current_active_verified_user, get_user_manager
from formation_ia_backend.application.services.payment_service import PaymentService
from formation_ia_backend.infrastructure.payment.stripe_adapter import StripeAdapter
from formation_ia_backend.infrastructure.email.brevo_adapter import BrevoEmailAdapter
from formation_ia_backend.domain.models.user import DbUser
from formation_ia_backend.domain.schemas.user import UserRead

router = APIRouter()

class CreateCheckoutSessionRequest(BaseModel):
    price_id: constr(strip_whitespace=True, min_length=1)

# Dependency factories for adapters to handle initialization errors
def get_stripe_adapter() -> StripeAdapter:
    try:
        return StripeAdapter()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Payment system misconfiguration: {str(e)}")

def get_brevo_adapter() -> BrevoEmailAdapter:
    try:
        return BrevoEmailAdapter()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=f"Email system misconfiguration: {str(e)}")

# Dependency to get PaymentService instance
def get_payment_service(
    stripe_adapter: StripeAdapter = Depends(get_stripe_adapter),
    brevo_adapter: BrevoEmailAdapter = Depends(get_brevo_adapter)
) -> PaymentService:
    return PaymentService(stripe_adapter=stripe_adapter, brevo_adapter=brevo_adapter)


@router.post(
    "/create-checkout-session",
    response_model=Dict[str, str], # Returns {"checkout_url": "url_string"}
    dependencies=[Depends(current_active_verified_user)]
)
async def create_checkout_session_endpoint(
    request_body: CreateCheckoutSessionRequest = Body(...),
    db: AsyncSession = Depends(get_async_db),
    current_user_schema: UserRead = Depends(current_active_verified_user),
    user_manager: UserManager = Depends(get_user_manager),
    payment_service: PaymentService = Depends(get_payment_service)
):
    current_user_db_model: Optional[DbUser] = await user_manager.get(current_user_schema.id)
    if not current_user_db_model:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authenticated user not found in database.")

    try:
        checkout_url = await payment_service.create_checkout_session_for_user(
            db=db,
            current_user=current_user_db_model,
            price_id=request_body.price_id
        )
        return {"checkout_url": checkout_url}
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"Error in /create-checkout-session endpoint: {e}") # Log server-side
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while creating payment session.")


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    include_in_schema=False
)
async def stripe_webhook_endpoint(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: AsyncSession = Depends(get_async_db),
    payment_service: PaymentService = Depends(get_payment_service)
):
    if stripe_signature is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Stripe-Signature header.")

    payload = await request.body()

    try:
        event: stripe.Event = await payment_service.stripe_adapter.construct_webhook_event(
            payload=payload,
            sig_header=stripe_signature
        )
    except ValueError as e:
        print(f"Webhook ValueError (payload or config issue): {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid payload or webhook configuration: {str(e)}")
    except stripe.error.SignatureVerificationError as e:
        print(f"Webhook SignatureVerificationError: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid Stripe signature: {str(e)}")
    except Exception as e:
        print(f"Webhook event construction error (other): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error constructing webhook event: {str(e)}")

    try:
        await payment_service.handle_stripe_webhook(db=db, event=event)
        return {"status": "success"}
    except HTTPException as he:
        # If service explicitly raises HTTPException, respect it (e.g. for specific 4xx from service logic)
        print(f"Service HTTPException during webhook processing ({event.type}, {event.id}): {he.detail}")
        raise he
    except Exception as e:
        print(f"Unhandled error processing webhook ({event.type}, {event.id}): {e}")
        # Generic server error, Stripe will retry
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error processing webhook event.")
