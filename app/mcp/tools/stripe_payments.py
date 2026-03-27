# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""Stripe Payments MCP Tool.

Provides payment integration capabilities for landing pages and products.
Enables agents to create payment links, checkout sessions, and manage
payment collection.
"""

import html
import logging
import os
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripeMCPTool:
    """Stripe MCP Tool for payment processing."""

    def __init__(self):
        self._stripe = None

    @property
    def stripe(self):
        """Lazy load Stripe SDK."""
        if self._stripe is None:
            try:
                import stripe

                self._stripe = stripe
            except ImportError:
                logger.warning(
                    "Stripe SDK not installed. Install with: pip install stripe"
                )
                return None
        if not self._stripe.api_key:
            self._stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
        return self._stripe

    def is_configured(self) -> bool:
        """Check if Stripe is properly configured."""
        key = os.environ.get("STRIPE_API_KEY", "")
        return bool(key and len(key) > 10)

    async def create_payment_link(
        self,
        product_name: str,
        price_amount: int,
        currency: str = "usd",
        description: str | None = None,
        success_url: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe Payment Link for a product.

        Payment links are shareable URLs that can be embedded in landing pages
        or sent directly to customers.

        Args:
            product_name: Name of the product/service
            price_amount: Price in cents (e.g., 1999 for $19.99)
            currency: Currency code (default: usd)
            description: Product description
            success_url: URL to redirect after successful payment
            metadata: Additional metadata to attach

        Returns:
            Payment link details including URL
        """
        if not self.is_configured():
            return {"error": "Stripe not configured. Please add your STRIPE_API_KEY."}

        if not self.stripe:
            return {"error": "Stripe SDK not available"}

        try:
            # Create product
            product = self.stripe.Product.create(
                name=product_name,
                description=description or f"Payment for {product_name}",
                metadata=metadata or {},
            )

            # Create price
            price = self.stripe.Price.create(
                product=product.id,
                unit_amount=price_amount,
                currency=currency,
            )

            # Create payment link
            payment_link_params = {
                "line_items": [{"price": price.id, "quantity": 1}],
            }

            if success_url:
                payment_link_params["after_completion"] = {
                    "type": "redirect",
                    "redirect": {"url": success_url},
                }

            payment_link = self.stripe.PaymentLink.create(**payment_link_params)

            return {
                "success": True,
                "payment_link_id": payment_link.id,
                "url": payment_link.url,
                "product_id": product.id,
                "price_id": price.id,
                "amount": price_amount,
                "currency": currency,
                "product_name": product_name,
                "message": f"Payment link created for {product_name}",
            }

        except Exception as e:
            logger.error(f"Failed to create payment link: {e}")
            return {"error": str(e)}

    async def create_checkout_session(
        self,
        items: list[dict[str, Any]],
        customer_email: str | None = None,
        success_url: str = "https://example.com/success",
        cancel_url: str = "https://example.com/cancel",
        mode: str = "payment",
        metadata: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Create a Stripe Checkout Session.

        Checkout sessions provide a pre-built, hosted payment page.

        Args:
            items: List of items with name, price (cents), quantity
            customer_email: Pre-fill customer email
            success_url: Redirect URL after payment
            cancel_url: Redirect URL if cancelled
            mode: "payment" for one-time, "subscription" for recurring
            metadata: Additional metadata

        Returns:
            Checkout session with URL
        """
        if not self.is_configured():
            return {"error": "Stripe not configured. Please add your STRIPE_API_KEY."}

        if not self.stripe:
            return {"error": "Stripe SDK not available"}

        try:
            line_items = []

            for item in items:
                line_items.append(
                    {
                        "price_data": {
                            "currency": item.get("currency", "usd"),
                            "product_data": {
                                "name": item["name"],
                                "description": item.get("description", ""),
                            },
                            "unit_amount": item["price"],
                        },
                        "quantity": item.get("quantity", 1),
                    }
                )

            session_params = {
                "line_items": line_items,
                "mode": mode,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "metadata": metadata or {},
            }

            if customer_email:
                session_params["customer_email"] = customer_email

            session = self.stripe.checkout.Session.create(**session_params)

            return {
                "success": True,
                "session_id": session.id,
                "url": session.url,
                "mode": mode,
                "expires_at": session.expires_at,
                "message": "Checkout session created",
            }

        except Exception as e:
            logger.error(f"Failed to create checkout session: {e}")
            return {"error": str(e)}

    async def create_subscription_product(
        self,
        name: str,
        description: str,
        price_amount: int,
        currency: str = "usd",
        interval: str = "month",
        trial_days: int = 0,
    ) -> dict[str, Any]:
        """Create a subscription product with recurring pricing.

        Args:
            name: Product name
            description: Product description
            price_amount: Price per interval in cents
            currency: Currency code
            interval: Billing interval - "day", "week", "month", "year"
            trial_days: Free trial period

        Returns:
            Subscription product details
        """
        if not self.is_configured():
            return {"error": "Stripe not configured. Please add your STRIPE_API_KEY."}

        if not self.stripe:
            return {"error": "Stripe SDK not available"}

        try:
            product = self.stripe.Product.create(
                name=name,
                description=description,
            )

            price_params = {
                "product": product.id,
                "unit_amount": price_amount,
                "currency": currency,
                "recurring": {"interval": interval},
            }

            price = self.stripe.Price.create(**price_params)

            return {
                "success": True,
                "product_id": product.id,
                "price_id": price.id,
                "name": name,
                "amount": price_amount,
                "currency": currency,
                "interval": interval,
                "trial_days": trial_days,
                "message": f"Subscription product '{name}' created",
            }

        except Exception as e:
            logger.error(f"Failed to create subscription: {e}")
            return {"error": str(e)}

    def get_payment_button_html(
        self,
        payment_link_url: str,
        button_text: str = "Pay Now",
        button_style: str = "default",
    ) -> str:
        """Generate HTML for a payment button.

        Returns embeddable HTML for landing pages.

        Args:
            payment_link_url: Stripe payment link URL
            button_text: Button label
            button_style: "default", "primary", "minimal"

        Returns:
            HTML string for the payment button
        """
        styles = {
            "default": "background: #635BFF; color: white; padding: 12px 24px; border: none; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer;",
            "primary": "background: linear-gradient(135deg, #635BFF 0%, #8B5CF6 100%); color: white; padding: 16px 32px; border: none; border-radius: 8px; font-size: 18px; font-weight: 700; cursor: pointer; box-shadow: 0 4px 14px rgba(99, 91, 255, 0.4);",
            "minimal": "background: transparent; color: #635BFF; padding: 12px 24px; border: 2px solid #635BFF; border-radius: 6px; font-size: 16px; font-weight: 600; cursor: pointer;",
        }

        style = styles.get(button_style, styles["default"])

        safe_url = payment_link_url if payment_link_url.startswith("https://") else "#"
        safe_text = html.escape(button_text)

        return f'''
<a href="{safe_url}" target="_blank" rel="noopener noreferrer"
   style="display: inline-block; text-decoration: none;">
    <button style="{style}">{safe_text}</button>
</a>
'''

    async def list_payments(
        self,
        limit: int = 10,
        starting_after: str | None = None,
    ) -> dict[str, Any]:
        """List recent payments/charges.

        Args:
            limit: Number of payments to retrieve
            starting_after: Pagination cursor

        Returns:
            List of recent payments
        """
        if not self.is_configured():
            return {"error": "Stripe not configured"}

        if not self.stripe:
            return {"error": "Stripe SDK not available"}

        try:
            params = {"limit": limit}
            if starting_after:
                params["starting_after"] = starting_after

            charges = self.stripe.Charge.list(**params)

            payments = []
            for charge in charges.data:
                payments.append(
                    {
                        "id": charge.id,
                        "amount": charge.amount,
                        "currency": charge.currency,
                        "status": charge.status,
                        "description": charge.description,
                        "customer_email": charge.billing_details.email
                        if charge.billing_details
                        else None,
                        "created": datetime.fromtimestamp(charge.created).isoformat(),
                    }
                )

            return {
                "success": True,
                "payments": payments,
                "has_more": charges.has_more,
            }

        except Exception as e:
            logger.error(f"Failed to list payments: {e}")
            return {"error": str(e)}


# Singleton instance
_stripe_tool: StripeMCPTool | None = None


def get_stripe_tool() -> StripeMCPTool:
    """Get singleton Stripe tool instance."""
    global _stripe_tool
    if _stripe_tool is None:
        _stripe_tool = StripeMCPTool()
    return _stripe_tool


# ============================================================================
# Agent Tool Functions
# ============================================================================


async def create_payment_link(
    product_name: str,
    price: float,
    currency: str = "usd",
    description: str | None = None,
) -> dict[str, Any]:
    """Create a payment link for a product or service.

    Use this to add payment capabilities to landing pages.
    Returns a shareable URL that customers can use to pay.

    Args:
        product_name: Name of the product (e.g., "Premium Plan")
        price: Price in dollars (e.g., 19.99)
        currency: Currency code (default: usd)
        description: Product description

    Returns:
        Payment link URL and details
    """
    tool = get_stripe_tool()
    price_cents = int(price * 100)  # Convert to cents

    return await tool.create_payment_link(
        product_name=product_name,
        price_amount=price_cents,
        currency=currency,
        description=description,
    )


async def create_checkout(
    items: list[dict[str, Any]],
    customer_email: str | None = None,
    success_url: str | None = None,
) -> dict[str, Any]:
    """Create a checkout session for multiple items.

    Use this for cart-style checkouts with multiple products.

    Args:
        items: List of items, each with "name" and "price" (in dollars)
        customer_email: Pre-fill customer's email
        success_url: Where to redirect after payment

    Returns:
        Checkout URL for the payment page
    """
    tool = get_stripe_tool()

    # Convert prices to cents
    processed_items = []
    for item in items:
        processed_items.append(
            {
                "name": item["name"],
                "price": int(item["price"] * 100),
                "quantity": item.get("quantity", 1),
                "description": item.get("description", ""),
            }
        )

    return await tool.create_checkout_session(
        items=processed_items,
        customer_email=customer_email,
        success_url=success_url or "https://pikar.ai/payment-success",
        cancel_url="https://pikar.ai/payment-cancelled",
    )


async def create_subscription(
    name: str,
    price: float,
    interval: str = "month",
    description: str | None = None,
    trial_days: int = 0,
) -> dict[str, Any]:
    """Create a subscription product with recurring billing.

    Use this for SaaS products, memberships, or recurring services.

    Args:
        name: Subscription name (e.g., "Pro Plan")
        price: Price per interval in dollars
        interval: Billing frequency - "month", "year", "week"
        description: Subscription description
        trial_days: Free trial period in days

    Returns:
        Subscription product details
    """
    tool = get_stripe_tool()
    price_cents = int(price * 100)

    return await tool.create_subscription_product(
        name=name,
        description=description or f"{name} subscription",
        price_amount=price_cents,
        interval=interval,
        trial_days=trial_days,
    )


def get_payment_button(
    payment_link_url: str,
    button_text: str = "Pay Now",
    style: str = "primary",
) -> dict[str, Any]:
    """Get HTML code for a payment button.

    Use this to embed payment buttons in landing pages.

    Args:
        payment_link_url: The Stripe payment link URL
        button_text: Text to display on the button
        style: Button style - "primary", "default", or "minimal"

    Returns:
        HTML code for the payment button
    """
    tool = get_stripe_tool()
    html = tool.get_payment_button_html(
        payment_link_url=payment_link_url,
        button_text=button_text,
        button_style=style,
    )

    return {
        "success": True,
        "html": html,
        "message": "Payment button HTML generated. Embed this in your landing page.",
    }


# ============================================================================
# Export for Agent Registration
# ============================================================================

STRIPE_TOOLS = [
    create_payment_link,
    create_checkout,
    create_subscription,
    get_payment_button,
]

STRIPE_TOOLS_MAP = {
    "create_payment_link": create_payment_link,
    "create_checkout": create_checkout,
    "create_subscription": create_subscription,
    "get_payment_button": get_payment_button,
}
