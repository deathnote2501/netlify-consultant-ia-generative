import stripe
from typing import Optional, Dict, Any, List # For type hints

from formation_ia_backend.core.config import settings
# For true async behavior with the sync Stripe library, you'd use:
# import asyncio
# from fastapi.concurrency import run_in_threadpool

class StripeAdapter:
    def __init__(self):
        if not settings.STRIPE_SECRET_KEY or "YOUR_STRIPE_TEST_SECRET_KEY" in settings.STRIPE_SECRET_KEY:
            raise ValueError("STRIPE_SECRET_KEY is not properly set or is a placeholder in environment variables.")
        if not settings.STRIPE_WEBHOOK_SECRET or "YOUR_STRIPE_TEST_WEBHOOK_SECRET" in settings.STRIPE_WEBHOOK_SECRET:
            # Depending on usage, this might be a critical error or a warning.
            # If webhooks are essential, this should be an error.
            print("Warning: STRIPE_WEBHOOK_SECRET is not properly set or is a placeholder. Webhook verification will fail.")
            # For now, allow initialization but webhook construction will fail later if secret is bad.

        stripe.api_key = settings.STRIPE_SECRET_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    async def create_or_retrieve_customer(self, email: str, user_id: str, name: Optional[str] = None) -> stripe.Customer:
        # Note: Stripe calls are synchronous. For true async, wrap with asyncio.to_thread or run_in_threadpool.
        try:
            existing_customers = stripe.Customer.list(email=email, limit=1) # Sync call
            if existing_customers.data:
                customer = existing_customers.data[0]
                if customer.metadata.get("user_id") != user_id:
                    stripe.Customer.modify(customer.id, metadata={"user_id": user_id}) # Sync call
                return customer
            else:
                customer_params: Dict[str, Any] = {
                    "email": email,
                    "metadata": {"user_id": user_id}
                }
                if name:
                    customer_params["name"] = name

                new_customer = stripe.Customer.create(**customer_params) # Sync call
                return new_customer
        except stripe.error.StripeError as e:
            print(f"Stripe API error in create_or_retrieve_customer: {e}")
            raise Exception(f"Failed to create or retrieve Stripe customer: {str(e)}") from e


    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        client_reference_id: str, # Usually your internal user_id
    ) -> stripe.checkout.Session:
        try:
            checkout_session_params: Dict[str, Any] = {
                "customer": customer_id,
                "payment_method_types": ["card"],
                "line_items": [{"price": price_id, "quantity": 1}],
                "mode": "subscription",
                "success_url": success_url,
                "cancel_url": cancel_url,
                "client_reference_id": client_reference_id,
            }

            checkout_session = stripe.checkout.Session.create(**checkout_session_params) # Sync call
            return checkout_session
        except stripe.error.StripeError as e:
            print(f"Stripe API error in create_checkout_session: {e}")
            raise Exception(f"Failed to create Stripe Checkout session: {str(e)}") from e

    async def construct_webhook_event(self, payload: bytes, sig_header: str) -> stripe.Event:
        if not self.webhook_secret or "YOUR_STRIPE_TEST_WEBHOOK_SECRET" in self.webhook_secret:
             raise ValueError("Stripe webhook secret is not configured correctly, cannot verify event.")
        try:
            # This is a synchronous call
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except ValueError as e:
            print(f"Error verifying webhook payload (ValueError): {e}")
            raise # Re-raise for router to return 400
        except stripe.error.SignatureVerificationError as e:
            print(f"Error verifying webhook signature (SignatureVerificationError): {e}")
            raise # Re-raise for router to return 400
        except Exception as e: # Catch any other unexpected errors during construction
            print(f"Unexpected error during webhook event construction: {e}")
            raise Exception(f"Webhook event construction failed: {str(e)}") from e

    async def get_subscription(self, subscription_id: str) -> Optional[stripe.Subscription]:
        try:
            subscription = stripe.Subscription.retrieve(subscription_id) # Sync call
            return subscription
        except stripe.error.InvalidRequestError as e: # E.g., subscription not found
             if "No such subscription" in str(e):
                 return None
             print(f"Stripe API error retrieving subscription {subscription_id}: {e}")
             raise Exception(f"Failed to retrieve Stripe subscription: {str(e)}") from e
        except stripe.error.StripeError as e:
            print(f"Stripe API error retrieving subscription {subscription_id}: {e}")
            raise Exception(f"Failed to retrieve Stripe subscription: {str(e)}") from e


    async def cancel_subscription_at_period_end(self, subscription_id: str) -> Optional[stripe.Subscription]:
        try:
            subscription = stripe.Subscription.modify(subscription_id, cancel_at_period_end=True) # Sync call
            return subscription
        except stripe.error.StripeError as e:
            print(f"Stripe API error canceling subscription {subscription_id} at period end: {e}")
            # Consider specific error handling, e.g., if already canceled
            raise Exception(f"Failed to cancel Stripe subscription at period end: {str(e)}") from e

    async def cancel_subscription_immediately(self, subscription_id: str) -> Optional[stripe.Subscription]:
        try:
            # Using delete for immediate cancellation as per Stripe docs
            subscription = stripe.Subscription.delete(subscription_id) # Sync call
            return subscription
        except stripe.error.StripeError as e:
            print(f"Stripe API error canceling subscription {subscription_id} immediately: {e}")
            raise Exception(f"Failed to cancel Stripe subscription immediately: {str(e)}") from e
