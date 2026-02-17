from fastapi import APIRouter

from app.subscription.schemas import SUBSCRIPTION_PLANS, SubscriptionPlansResponse

router = APIRouter()


@router.get("/plans", response_model=SubscriptionPlansResponse)
async def get_subscription_plans():
    """Returns all available subscription plans with pricing and features."""
    return SubscriptionPlansResponse(plans=SUBSCRIPTION_PLANS)
