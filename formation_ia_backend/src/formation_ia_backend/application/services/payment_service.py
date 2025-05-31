from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, status
import stripe # For stripe.Event and stripe.Customer types
from datetime import datetime, timezone # For converting timestamps
import uuid # For uuid.UUID()
import logging

from formation_ia_backend.infrastructure.payment.stripe_adapter import StripeAdapter
from formation_ia_backend.infrastructure.email.brevo_adapter import BrevoEmailAdapter
from formation_ia_backend.domain.models.user import DbUser
from formation_ia_backend.domain.models.subscription import DbSubscription
from formation_ia_backend.core.config import settings

logger = logging.getLogger(__name__)

class PaymentService:
    def __init__(self, stripe_adapter: StripeAdapter, brevo_adapter: BrevoEmailAdapter):
        self.stripe_adapter = stripe_adapter
        self.brevo_adapter = brevo_adapter

    async def create_checkout_session_for_user(
        self,
        db: AsyncSession,
        current_user: DbUser,
        price_id: str
    ) -> str: # Returns the checkout session URL

        stripe_customer_id_to_use = current_user.stripe_customer_id
        user_updated_in_this_step = False

        if not stripe_customer_id_to_use:
            try:
                stripe_customer = await self.stripe_adapter.create_or_retrieve_customer(
                    email=current_user.email,
                    user_id=str(current_user.id)
                )
                stripe_customer_id_to_use = stripe_customer.id
                current_user.stripe_customer_id = stripe_customer_id_to_use
                db.add(current_user)
                await db.commit() # Commit change to user (stripe_customer_id)
                await db.refresh(current_user)
                user_updated_in_this_step = True
            except Exception as e:
                if user_updated_in_this_step: await db.rollback() # Rollback if commit for user failed after an attempt
                logger.error(f"Failed to create/retrieve Stripe customer for user {current_user.id}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process payment customer information.")

        if not stripe_customer_id_to_use:
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Stripe customer ID could not be established.")

        success_url = f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{settings.FRONTEND_URL}/payment/cancel" # Or a more specific product page

        try:
            checkout_session = await self.stripe_adapter.create_checkout_session(
                customer_id=stripe_customer_id_to_use,
                price_id=price_id,
                success_url=success_url,
                cancel_url=cancel_url,
                client_reference_id=str(current_user.id)
            )
        except Exception as e:
            logger.error(f"Failed to create Stripe checkout session for user {current_user.id}, price {price_id}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create payment session.")

        return checkout_session.url


    async def handle_stripe_webhook(self, db: AsyncSession, event: stripe.Event):
        event_type = event.type
        event_data_object = event.data.object

        logger.info(f"Handling Stripe webhook event: {event_type}, Stripe Event ID: {event.id}")

        if event_type == 'checkout.session.completed':
            session = event_data_object
            user_id_str = session.get("client_reference_id")
            stripe_customer_id = session.get("customer")
            stripe_subscription_id = session.get("subscription")

            if not all([user_id_str, stripe_customer_id, stripe_subscription_id]):
                logger.error(f"Webhook checkout.session.completed missing crucial data. Event ID: {event.id}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing data in webhook event.")

            try:
                user_id_uuid = uuid.UUID(user_id_str)
            except ValueError:
                logger.error(f"Invalid UUID format for client_reference_id: {user_id_str}. Event ID: {event.id}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID format in webhook.")

            user = await db.get(DbUser, user_id_uuid)
            if not user:
                logger.error(f"User not found for client_reference_id {user_id_str}. Event ID: {event.id}")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User from webhook not found.") # So Stripe retries

            try:
                stripe_sub_details = await self.stripe_adapter.get_subscription(stripe_subscription_id)
                if not stripe_sub_details:
                    logger.error(f"Could not retrieve Stripe subscription {stripe_subscription_id}. Event ID: {event.id}")
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Could not retrieve Stripe subscription.")
            except Exception as e:
                logger.error(f"Error retrieving Stripe subscription {stripe_subscription_id}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving subscription from Stripe.")

            plan_id = stripe_sub_details.plan.id if stripe_sub_details.plan else None
            if not plan_id:
                logger.error(f"Stripe subscription {stripe_subscription_id} missing plan ID. Event ID: {event.id}")
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subscription plan ID missing.")

            db_subscription = await db.get(DbSubscription, stripe_subscription_id)
            if not db_subscription:
                db_subscription = DbSubscription(id=stripe_subscription_id, user_id=user.id)

            db_subscription.stripe_customer_id = stripe_customer_id
            db_subscription.plan_id = plan_id
            db_subscription.status = stripe_sub_details.status
            db_subscription.current_period_start = datetime.fromtimestamp(stripe_sub_details.current_period_start, tz=timezone.utc)
            db_subscription.current_period_end = datetime.fromtimestamp(stripe_sub_details.current_period_end, tz=timezone.utc)
            db_subscription.cancel_at_period_end = stripe_sub_details.cancel_at_period_end
            db.add(db_subscription)

            user.stripe_customer_id = stripe_customer_id
            user.active_subscription_id = stripe_subscription_id
            user.subscription_tier = plan_id
            user.subscription_expires_at = db_subscription.current_period_end
            db.add(user)

            try:
                await db.commit()
                logger.info(f"Subscription {stripe_subscription_id} processed for user {user.id}.")
                await self.brevo_adapter.send_payment_confirmation_email(
                    to_email=user.email, user_name=user.email, plan_name=plan_id
                )
            except Exception as e:
                await db.rollback()
                logger.error(f"DB/Email error processing checkout.session.completed for sub {stripe_subscription_id}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error finalizing subscription.")

        elif event_type == 'invoice.payment_succeeded':
            invoice = event_data_object
            stripe_subscription_id = invoice.get("subscription")
            if not stripe_subscription_id:
                logger.info(f"Invoice {invoice.id} payment succeeded, no subscription ID. Skipping.")
                return

            db_subscription = await db.get(DbSubscription, stripe_subscription_id)
            if not db_subscription:
                logger.warning(f"Subscription {stripe_subscription_id} not found in DB for invoice.payment_succeeded. Event ID: {event.id}")
                # Consider if this should be an error for Stripe retry
                return

            db_subscription.status = "active"
            db_subscription.current_period_start = datetime.fromtimestamp(invoice.period_start, tz=timezone.utc)
            db_subscription.current_period_end = datetime.fromtimestamp(invoice.period_end, tz=timezone.utc)
            db.add(db_subscription)

            user = await db.get(DbUser, db_subscription.user_id)
            if user:
                user.subscription_expires_at = db_subscription.current_period_end
                user.active_subscription_id = db_subscription.id
                user.subscription_tier = db_subscription.plan_id
                db.add(user)

            try:
                await db.commit()
                logger.info(f"Subscription {stripe_subscription_id} renewed for user {db_subscription.user_id}.")
            except Exception as e:
                await db.rollback()
                logger.error(f"DB error processing invoice.payment_succeeded for sub {stripe_subscription_id}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating subscription renewal.")

        elif event_type in ['customer.subscription.deleted', 'customer.subscription.updated']:
            stripe_sub_details = event_data_object
            stripe_subscription_id = stripe_sub_details.id

            db_subscription = await db.get(DbSubscription, stripe_subscription_id)
            if not db_subscription:
                logger.warning(f"Subscription {stripe_subscription_id} not found in DB for {event_type}. Event ID: {event.id}")
                return

            db_subscription.status = stripe_sub_details.status
            db_subscription.cancel_at_period_end = stripe_sub_details.cancel_at_period_end
            db_subscription.current_period_start = datetime.fromtimestamp(stripe_sub_details.current_period_start, tz=timezone.utc)
            db_subscription.current_period_end = datetime.fromtimestamp(stripe_sub_details.current_period_end, tz=timezone.utc)
            db.add(db_subscription)

            user = await db.get(DbUser, db_subscription.user_id)
            if user:
                is_effectively_cancelled = (db_subscription.status == "canceled") or \
                                         (db_subscription.cancel_at_period_end and datetime.now(timezone.utc) >= db_subscription.current_period_end)

                if is_effectively_cancelled:
                     user.active_subscription_id = None
                     user.subscription_tier = None
                else: # Still active or will be active until period end
                    user.active_subscription_id = db_subscription.id
                    user.subscription_tier = db_subscription.plan_id
                    user.subscription_expires_at = db_subscription.current_period_end
                db.add(user)

            try:
                await db.commit()
                logger.info(f"Subscription {stripe_subscription_id} status updated to {db_subscription.status} for user {db_subscription.user_id}.")
            except Exception as e:
                await db.rollback()
                logger.error(f"DB error processing {event_type} for sub {stripe_subscription_id}: {e}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error updating subscription status.")
        else:
            logger.info(f"Received unhandled Stripe event type: {event_type}. Event ID: {event.id}")
