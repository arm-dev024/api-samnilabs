import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.dependencies import get_current_user
from app.config import settings
from app.subscription.schemas import (
    SUBSCRIPTION_PLANS,
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionPlansResponse,
)
from app.users.models import User

router = APIRouter()

stripe.api_key = settings.stripe.secret_key.get_secret_value()


def _get_plan_by_id(plan_id: str) -> dict | None:
    """Look up a subscription plan by its ID."""
    for plan in SUBSCRIPTION_PLANS:
        if plan["id"] == plan_id:
            return plan
    return None


@router.get("/plans", response_model=SubscriptionPlansResponse)
async def get_subscription_plans():
    """Returns all available subscription plans with pricing and features."""
    return SubscriptionPlansResponse(plans=SUBSCRIPTION_PLANS)


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    body: CheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for the given plan."""
    plan = _get_plan_by_id(body.plan_id)

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription plan '{body.plan_id}' not found",
        )

    if plan.get("stripe_price_id") is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan '{plan['name']}' does not support online checkout. Please contact sales.",
        )

    try:
        # Check if the Stripe price is recurring or one-time to set the correct mode
        price = stripe.Price.retrieve(plan["stripe_price_id"])
        mode = "subscription" if price.recurring else "payment"

        session = stripe.checkout.Session.create(
            mode=mode,
            line_items=[{"price": plan["stripe_price_id"], "quantity": 1}],
            customer_email=current_user.email,
            success_url=settings.stripe.success_url
            + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=settings.stripe.cancel_url,
            metadata={
                "user_id": current_user.id,
                "plan_id": body.plan_id,
            },
        )
    except stripe.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe error: {str(e)}",
        )

    return CheckoutResponse(checkout_url=session.url)


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook events (e.g. checkout.session.completed)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe.webhook_secret.get_secret_value(),
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"].get("user_id")
        plan_id = session["metadata"].get("plan_id")
        subscription_id = session.get("subscription")
        customer_id = session.get("customer")
        print(
            f"[Stripe] Checkout completed: user_id={user_id}, "
            f"plan_id={plan_id}, subscription_id={subscription_id}, "
            f"customer_id={customer_id}"
        )
        # TODO: Update user record with subscription details

    elif event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        print(
            f"[Stripe] Subscription updated: {subscription['id']}, status={subscription['status']}"
        )
        # TODO: Handle plan changes / status updates

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        print(f"[Stripe] Subscription cancelled: {subscription['id']}")
        # TODO: Handle cancellation

    return {"status": "ok"}
