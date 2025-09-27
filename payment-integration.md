# Integracja płatności Stripe

## 1. Stripe Subscription Setup

```javascript
// frontend/src/components/Pricing/SubscriptionPlan.js
import { loadStripe } from '@stripe/stripe-js';

const stripePromise = loadStripe('pk_test_...');

const PricingPlan = () => {
  const handleSubscribe = async (priceId) => {
    const stripe = await stripePromise;

    const response = await fetch('/api/create-checkout-session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ priceId })
    });

    const session = await response.json();
    await stripe.redirectToCheckout({ sessionId: session.id });
  };

  return (
    <div className="pricing-tiers">
      <div className="tier free">
        <h3>Free Trial</h3>
        <p>5 feeds per month</p>
        <p>Basic support</p>
        <button>Start Free</button>
      </div>

      <div className="tier pro">
        <h3>Professional - $49/month</h3>
        <p>Unlimited feeds</p>
        <p>Priority support</p>
        <p>Custom mapping rules</p>
        <button onClick={() => handleSubscribe('price_pro_monthly')}>
          Subscribe
        </button>
      </div>

      <div className="tier enterprise">
        <h3>Enterprise - $199/month</h3>
        <p>Everything in Pro</p>
        <p>White-label solution</p>
        <p>API access</p>
        <p>Dedicated support</p>
        <button onClick={() => handleSubscribe('price_enterprise_monthly')}>
          Subscribe
        </button>
      </div>
    </div>
  );
};
```

## 2. Backend Stripe Integration

```python
# backend/services/stripe_service.py
import stripe
from fastapi import HTTPException
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

class StripeService:
    @staticmethod
    async def create_checkout_session(price_id: str, user_id: int):
        try:
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url='https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}',
                cancel_url='https://yourdomain.com/cancel',
                client_reference_id=str(user_id),
                metadata={'user_id': user_id}
            )
            return session
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @staticmethod
    async def handle_webhook(payload, sig_header):
        endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            raise HTTPException(status_code=400, detail="Invalid signature")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            # Update user subscription status
            await StripeService.activate_subscription(session)

        elif event['type'] == 'invoice.payment_succeeded':
            # Handle successful payment
            pass

        elif event['type'] == 'invoice.payment_failed':
            # Handle failed payment
            pass

        return {"status": "success"}
```

## 3. Usage Limits & Gating

```python
# backend/services/usage_service.py
from models.database import User, Feed
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

class UsageService:
    @staticmethod
    def check_usage_limits(user: User, db: Session) -> dict:
        # Count feeds in current month
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        feeds_this_month = db.query(Feed).filter(
            Feed.user_id == user.id,
            Feed.created_at >= current_month
        ).count()

        # Define limits based on subscription
        limits = {
            'free': 5,
            'pro': float('inf'),
            'enterprise': float('inf')
        }

        user_plan = getattr(user, 'subscription_plan', 'free')
        limit = limits.get(user_plan, 5)

        return {
            'feeds_used': feeds_this_month,
            'feeds_limit': limit,
            'can_upload': feeds_this_month < limit,
            'plan': user_plan
        }

# W routers/feeds.py
@router.post("/upload")
async def upload_feed(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check usage limits
    usage = UsageService.check_usage_limits(current_user, db)

    if not usage['can_upload']:
        raise HTTPException(
            status_code=402,  # Payment Required
            detail={
                "message": "Feed limit exceeded for your plan",
                "usage": usage,
                "upgrade_url": "/pricing"
            }
        )

    # Continue with upload...
```