import stripe
from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.config import settings
from app.subscription.schemas import (
    SUBSCRIPTION_PLANS,
    CheckoutRequest,
    CheckoutResponse,
    SubscriptionPlansResponse,
)
from app.users.models import User
from app.users.schemas import UserResponse
from app.users.service import UserService

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
    """Create a Stripe Checkout session and update the user's subscription."""
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

    # Update user subscription in DynamoDB
    user_service = UserService()
    user_service.update_subscription(
        user=current_user,
        plan_id=body.plan_id,
        stripe_customer_id=session.customer,
        stripe_subscription_id=session.subscription,
        subscription_status="active",
    )

    return CheckoutResponse(checkout_url=session.url)
