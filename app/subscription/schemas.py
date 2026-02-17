from pydantic import BaseModel


class PlanFeature(BaseModel):
    text: str
    included: bool = True


class PricingPlan(BaseModel):
    id: str
    name: str
    price: int | None  # None for custom/enterprise pricing
    currency: str = "USD"
    billing_period: str = "month"
    description: str
    cta_label: str
    cta_action: str  # "free_trial" | "book_demo" | "contact_sales"
    is_popular: bool = False
    features: list[PlanFeature]


class SubscriptionPlansResponse(BaseModel):
    plans: list[PricingPlan]


SUBSCRIPTION_PLANS: list[dict] = [
    {
        "id": "subscription-1",
        "name": "Starter",
        "price": 299,
        "currency": "USD",
        "billing_period": "month",
        "description": "For small teams ready to automate calls and chat",
        "cta_label": "Start Free Trial",
        "cta_action": "free_trial",
        "is_popular": False,
        "features": [
            {"text": "1,000 AI conversations/month", "included": True},
            {"text": "WhatsApp & Web Chat", "included": True},
            {"text": "Basic RAG training (10 documents)", "included": True},
            {"text": "Email support", "included": True},
            {"text": "Usage analytics dashboard", "included": True},
        ],
    },
    {
        "id": "subscription-2",
        "name": "Pro",
        "price": 799,
        "currency": "USD",
        "billing_period": "month",
        "description": "For growing businesses that need every channel and full control",
        "cta_label": "Book a Demo",
        "cta_action": "book_demo",
        "is_popular": True,
        "features": [
            {"text": "10,000 AI conversations/month", "included": True},
            {"text": "All channels (WhatsApp, Meta, Web, Voice)", "included": True},
            {"text": "Advanced RAG training (unlimited)", "included": True},
            {"text": "Human-in-the-loop support", "included": True},
            {"text": "Custom system prompts & temperature", "included": True},
            {"text": "Priority support", "included": True},
            {"text": "Advanced analytics", "included": True},
        ],
    },
    {
        "id": "subscription-3",
        "name": "Enterprise",
        "price": None,
        "currency": "USD",
        "billing_period": "month",
        "description": "Custom-built for teams that need private deployment and SLAs",
        "cta_label": "Contact Sales",
        "cta_action": "contact_sales",
        "is_popular": False,
        "features": [
            {"text": "Unlimited AI conversations", "included": True},
            {"text": "All Pro features", "included": True},
            {"text": "Private cloud deployment", "included": True},
            {"text": "Dedicated account manager", "included": True},
            {"text": "Custom integrations", "included": True},
            {"text": "SLA guarantee", "included": True},
            {"text": "White-label options", "included": True},
        ],
    },
]
