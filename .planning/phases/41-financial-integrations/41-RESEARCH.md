# Phase 41: Financial Integrations - Research

**Researched:** 2026-04-04
**Domain:** Financial data sync (Stripe, Shopify), webhook processing, agent tool integration
**Confidence:** HIGH

## Summary

Phase 41 connects Pikar to real financial data sources. The two pillars are (1) Stripe transaction history import and real-time webhook sync into the existing `financial_records` table, and (2) Shopify e-commerce integration via GraphQL Admin API for orders, products, and inventory with real-time webhooks. Both leverage the Phase 39 integration infrastructure (credential storage, webhook inbound router, sync state tracking) that is fully built and operational.

The existing codebase provides strong foundations: `financial_records` table with `source_type`/`source_id` columns, `FinancialService.get_revenue_stats()` that auto-benefits from new data, the generalized inbound webhook handler at `POST /webhooks/inbound/{provider}`, and `IntegrationManager` for OAuth token lifecycle. The main new work is the sync services (`stripe_sync_service.py`, `shopify_service.py`), Stripe-specific webhook verification (Stripe uses its own `construct_event` rather than generic HMAC), two new database tables (`shopify_orders`, `shopify_products`), schema migration to expand `financial_records`, and agent tools for both integrations.

**Primary recommendation:** Build in three waves: (1) Stripe sync service + schema migration + webhook handler, (2) Shopify service + new tables + webhook handler, (3) Agent tools for both integrations registered on FinancialAnalysisAgent and MarketingAutomationAgent.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Historical import:** Last 12 months of transactions on first connect. Uses `stripe.BalanceTransaction.list()` with `auto_pagination` and `created` filter.
- **Stripe objects to sync:** `balance_transactions` to `financial_records` table. Webhooks: `payment_intent.succeeded`, `charge.refunded`, `payout.paid`.
- **Categorization mapping:** `type: "charge"` -> `transaction_type: "revenue"`, `type: "refund"` -> `transaction_type: "refund"`, `type: "stripe_fee"` -> `transaction_type: "fee"`, `type: "payout"` -> `transaction_type: "payout"`, `type: "adjustment"` -> `transaction_type: "adjustment"`.
- **Idempotency:** Use Stripe `id` as `external_id` in `financial_records` with UNIQUE constraint. Duplicate webhook deliveries silently ignored.
- **Stripe connection:** Use existing Stripe SDK + `STRIPE_API_KEY` env var. Per-user Stripe Connect via Phase 39 credential storage.
- **Manual sync trigger:** `POST /integrations/stripe/sync` endpoint.
- **New service:** `app/services/stripe_sync_service.py` extending BaseService.
- **Shopify OAuth:** Via Phase 39 infrastructure (already in PROVIDER_REGISTRY).
- **Shopify API:** GraphQL Admin API (cost-based throttling).
- **Shopify data:** Orders -> `financial_records` + new `shopify_orders` table. Products -> new `shopify_products` table. Inventory -> `shopify_products.inventory_quantity`.
- **Inventory alerts:** Per-product threshold (default: 10, configurable). Via existing notification_service.
- **Shopify webhooks:** `orders/create`, `orders/updated`, `products/update`, `inventory_levels/update`. HMAC-SHA256 verification with shared secret.
- **Rate limiting:** Token bucket at 800 points/sec (leave 200 headroom).
- **Initial Shopify sync:** All products + last 12 months of orders on first connect.
- **New service:** `app/services/shopify_service.py` extending BaseService.
- **Stripe tools:** `get_stripe_revenue_summary(period?)`, `trigger_stripe_sync()`.
- **Shopify tools:** `get_shopify_orders(period?, status?)`, `get_shopify_products(category?, sort_by?)`, `get_shopify_analytics(period?)`, `get_low_stock_products()`, `set_inventory_alert_threshold(product_id, threshold)`.
- **Registration:** All tools on FinancialAnalysisAgent + MarketingAutomationAgent (for e-commerce analytics).

### Claude's Discretion
- Exact GraphQL queries for Shopify (products, orders, inventory)
- Stripe balance transaction pagination strategy (batch size)
- Shopify product variant handling (flatten vs nested)
- Error handling for Stripe API failures during historical import
- Notification message formatting for inventory alerts
- Whether to add `source` column to `financial_records` or use `metadata` JSONB

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| FIN-01 | Stripe transaction history auto-imported into financial_records table | Stripe BalanceTransaction.list() with auto_paging_iter(), created filter, batch processing pattern documented. Schema migration to add external_id + expand CHECK constraint. |
| FIN-02 | Revenue dashboard shows real Stripe data (payments, invoices, balance) | Existing `FinancialService.get_revenue_stats()` queries financial_records with `transaction_type: "revenue"` -- once Stripe data flows in, dashboard auto-updates. No code changes needed. |
| FIN-03 | Stripe webhook handler creates financial_records on payment_intent.succeeded | Stripe SDK v7 `stripe.Webhook.construct_event()` for verification. Webhook routes via existing `/webhooks/inbound/stripe` or dedicated endpoint. Event-to-record mapping documented. |
| FIN-04 | Transaction categorization (revenue, refund, fee, payout) applied automatically | Mapping from Stripe BalanceTransaction.type to financial_records.transaction_type documented. Requires ALTER CHECK constraint to add 'fee', 'payout', 'unknown' types. |
| FIN-05 | User can trigger manual full sync of Stripe history from configuration page | `POST /integrations/stripe/sync` endpoint. Re-imports last 12 months. Uses same StripeSyncService.sync_history() method. |
| SHOP-01 | User can connect Shopify store via OAuth from configuration page | Shopify already in PROVIDER_REGISTRY with OAuth URLs and scopes. Phase 39 OAuth flow handles the connection. Shopify requires `{shop}` substitution in auth/token URLs. |
| SHOP-02 | Agent can list orders, products, and inventory from Shopify | GraphQL queries for orders (cursor pagination, filtering), products (with variants), inventory documented. Tools registered on FinancialAnalysisAgent. |
| SHOP-03 | Sales analytics (revenue, orders, AOV, top products) available to FinancialAnalysisAgent | Computed from shopify_orders + shopify_products tables. `get_shopify_analytics()` tool performs aggregation queries. |
| SHOP-04 | Inventory alerts when stock falls below configurable threshold | Per-product `low_stock_threshold` column. Webhook `inventory_levels/update` triggers check. NotificationService.create_notification() for alerts. |
| SHOP-05 | Shopify webhook processing for real-time order and inventory updates | HMAC-SHA256 via X-Shopify-Hmac-SHA256 header (base64-encoded). Four webhook topics. Existing inbound webhook router needs Shopify-specific HMAC (base64 vs hex). |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe | >=7.0.0,<8.0.0 | Stripe API SDK (already installed) | Official Python SDK; provides BalanceTransaction.list(), Webhook.construct_event() |
| httpx | >=0.27.0,<1.0.0 | Shopify GraphQL API calls (already installed) | Async HTTP client already used throughout the codebase |
| supabase-py | (already installed) | Database operations | Project standard via BaseService pattern |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| asyncio | stdlib | Concurrency for batch imports | Stripe auto_paging_iter is sync; run in executor |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| httpx for Shopify | shopify-python-api | Extra dependency; httpx already available and GraphQL is just HTTP POST |
| sync stripe SDK calls | async wrapper | Stripe Python SDK v7 is synchronous; wrap in `asyncio.to_thread()` for batch imports |

**Installation:**
```bash
# No new packages needed -- stripe and httpx already in pyproject.toml
```

## Architecture Patterns

### Recommended Project Structure
```
app/
  services/
    stripe_sync_service.py      # NEW: Stripe historical import + webhook-to-record mapping
    shopify_service.py          # NEW: Shopify GraphQL client + order/product sync
  agents/
    tools/
      stripe_tools.py           # NEW: Agent tools for Stripe (get_stripe_revenue_summary, trigger_stripe_sync)
      shopify_tools.py          # NEW: Agent tools for Shopify (orders, products, analytics, inventory)
    financial/
      agent.py                  # MODIFY: Add Stripe + Shopify tools
    marketing/
      agent.py                  # MODIFY: Add Shopify analytics tools
  routers/
    integrations.py             # MODIFY: Add POST /integrations/stripe/sync endpoint
    webhooks.py                 # MODIFY: Add Stripe-specific webhook verification, Shopify HMAC fix
supabase/
  migrations/
    YYYYMMDDHHMMSS_financial_integrations.sql  # NEW: Schema changes
```

### Pattern 1: Stripe Sync Service (BaseService extension)
**What:** Service class encapsulating all Stripe-to-financial_records logic.
**When to use:** For both historical import and webhook-triggered record creation.
**Example:**
```python
# Source: Existing BaseService pattern + Stripe SDK docs
import stripe
from app.services.base_service import BaseService

class StripeSyncService(BaseService):
    """Syncs Stripe balance transactions to financial_records."""

    # Mapping from Stripe BalanceTransaction.type to our transaction_type
    TYPE_MAP = {
        "charge": "revenue",
        "payment": "revenue",
        "refund": "refund",
        "stripe_fee": "fee",
        "payout": "payout",
        "adjustment": "adjustment",
    }

    async def sync_history(self, user_id: str, months_back: int = 12) -> dict:
        """Import last N months of balance transactions."""
        # stripe.BalanceTransaction.list() is synchronous -- run in executor
        import asyncio
        from datetime import datetime, timedelta, timezone

        cutoff = int((datetime.now(timezone.utc) - timedelta(days=months_back * 30)).timestamp())
        transactions = await asyncio.to_thread(
            lambda: list(
                stripe.BalanceTransaction.list(
                    created={"gte": cutoff},
                    limit=100,
                ).auto_paging_iter()
            )
        )
        # Batch upsert into financial_records
        ...

    def _map_transaction(self, bt: dict, user_id: str) -> dict:
        """Map a Stripe BalanceTransaction to a financial_records row."""
        return {
            "user_id": user_id,
            "external_id": bt["id"],
            "transaction_type": self.TYPE_MAP.get(bt["type"], "adjustment"),
            "amount": abs(bt["amount"]) / 100,  # cents to dollars
            "currency": bt["currency"].upper(),
            "description": bt.get("description") or f"Stripe {bt['type']}",
            "source_type": "stripe",
            "source_id": bt.get("source"),
            "transaction_date": datetime.fromtimestamp(bt["created"], tz=timezone.utc).isoformat(),
            "metadata": {"stripe_type": bt["type"], "fee": bt["fee"], "net": bt["net"]},
        }
```

### Pattern 2: Stripe Webhook Verification (construct_event)
**What:** Stripe uses its own signature verification via `stripe.Webhook.construct_event()`, NOT the generic HMAC verifier in webhooks.py.
**When to use:** For all Stripe inbound webhooks.
**Critical difference:** Stripe's Stripe-Signature header uses a timestamp-based scheme (`t=TIMESTAMP,v1=SIGNATURE`), not the simple `sha256=HEX` format the generic handler expects.
**Example:**
```python
# Source: https://docs.stripe.com/webhooks/signature
# Stripe SDK v7 uses stripe.Webhook.construct_event()
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    body = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    endpoint_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

    try:
        event = stripe.Webhook.construct_event(body, sig_header, endpoint_secret)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Route by event type
    if event.type == "payment_intent.succeeded":
        await _handle_payment_succeeded(event.data.object)
    elif event.type == "charge.refunded":
        await _handle_charge_refunded(event.data.object)
    elif event.type == "payout.paid":
        await _handle_payout_paid(event.data.object)
```

### Pattern 3: Shopify GraphQL Client
**What:** Direct GraphQL queries via httpx, with cost-aware rate limiting.
**When to use:** All Shopify data fetching.
**Example:**
```python
# Source: https://shopify.dev/docs/api/admin-graphql/latest/queries/orders
ORDERS_QUERY = """
query ($first: Int!, $after: String, $query: String) {
  orders(first: $first, after: $after, query: $query) {
    edges {
      cursor
      node {
        id
        name
        createdAt
        displayFinancialStatus
        displayFulfillmentStatus
        email
        totalPriceSet {
          shopMoney {
            amount
            currencyCode
          }
        }
        lineItems(first: 50) {
          edges {
            node {
              title
              quantity
              originalUnitPriceSet {
                shopMoney { amount currencyCode }
              }
              sku
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
"""
```

### Pattern 4: Shopify HMAC-SHA256 Verification
**What:** Shopify uses base64-encoded HMAC-SHA256, not hex-encoded like the generic handler.
**Critical difference:** The existing `_verify_inbound_signature()` in webhooks.py strips `sha256=` prefix and compares hex digests. Shopify sends base64 in `X-Shopify-Hmac-SHA256` header.
**Example:**
```python
# Source: https://shopify.dev/docs/apps/build/webhooks/subscribe/https
import base64
import hashlib
import hmac

def verify_shopify_webhook(body: bytes, secret: str, hmac_header: str) -> bool:
    """Verify Shopify webhook with base64-encoded HMAC-SHA256."""
    computed = base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)
```

### Anti-Patterns to Avoid
- **Using generic HMAC verifier for Stripe:** Stripe has its own signature format with timestamps. MUST use `stripe.Webhook.construct_event()`.
- **Using generic HMAC verifier for Shopify as-is:** Shopify uses base64-encoded HMAC, not hex. The existing `_verify_inbound_signature()` uses hex comparison.
- **Synchronous Stripe SDK in async handler:** `stripe.BalanceTransaction.list().auto_paging_iter()` is synchronous. Wrap in `asyncio.to_thread()` to avoid blocking the event loop during batch imports.
- **Storing amounts in cents:** The `financial_records.amount` column is `NUMERIC(15,2)` (dollars). Always divide Stripe amounts by 100.
- **Forgetting the CHECK constraint:** The existing `financial_records.transaction_type` CHECK constraint only allows `('revenue', 'expense', 'refund', 'adjustment')`. Must ALTER to add `'fee'`, `'payout'`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Stripe webhook signature verification | Custom HMAC comparison | `stripe.Webhook.construct_event()` | Handles timestamp tolerance, multiple signatures, replay protection |
| Stripe pagination | Manual cursor tracking | `auto_paging_iter()` on list result | Handles has_more, starting_after automatically |
| OAuth token refresh | Manual refresh flow | `IntegrationManager.get_valid_token()` | Phase 39 built async-locking double-check refresh |
| Notification delivery | Custom email/push system | `NotificationService.create_notification()` | Existing singleton with impersonation guard and optional Edge Function delivery |
| Webhook deduplication | Custom dedup logic | Upsert with `external_id` UNIQUE constraint + `ON CONFLICT DO NOTHING` | Database-level idempotency is race-condition-free |

**Key insight:** Phase 39 built most of the infrastructure we need (credential storage, webhook inbound routing, sync state tracking). This phase is about using that infrastructure with Stripe/Shopify-specific logic, not rebuilding it.

## Common Pitfalls

### Pitfall 1: Stripe Signature Verification Incompatibility
**What goes wrong:** The existing generalized inbound webhook handler (`POST /webhooks/inbound/{provider}`) uses `_verify_inbound_signature()` which expects `sha256=HEX` format. Stripe's `Stripe-Signature` header uses `t=TIMESTAMP,v1=SIGNATURE` format. Attempting to verify Stripe webhooks through the generic handler will ALWAYS fail.
**Why it happens:** Different providers use fundamentally different signature schemes.
**How to avoid:** Create a dedicated `POST /webhooks/stripe` endpoint that uses `stripe.Webhook.construct_event()`. OR add a provider-specific verification bypass in the generic handler.
**Warning signs:** All Stripe webhooks returning 403.

### Pitfall 2: Shopify HMAC Base64 vs Hex Mismatch
**What goes wrong:** Similar to Stripe, but different problem. Shopify sends base64-encoded HMAC in `X-Shopify-Hmac-SHA256`. The generic handler's `_verify_inbound_signature()` compares hex digests.
**Why it happens:** `_verify_inbound_signature()` calls `hmac.new(...).hexdigest()` but Shopify expects `base64.b64encode(hmac.new(...).digest())`.
**How to avoid:** Either add Shopify-specific verification in the generic handler OR create a dedicated Shopify webhook endpoint.
**Warning signs:** All Shopify webhooks returning 403.

### Pitfall 3: CHECK Constraint Blocking Inserts
**What goes wrong:** Inserting `transaction_type: "fee"` or `"payout"` into `financial_records` fails with a CHECK constraint violation.
**Why it happens:** The migration from `20260313103000_schema_truth_alignment.sql` has `CHECK (transaction_type IN ('revenue', 'expense', 'refund', 'adjustment'))`. Later migration `20260322500000` changed the NOT NULL default to `'unknown'` but did NOT update the CHECK constraint.
**How to avoid:** Migration must `DROP CONSTRAINT` on the old CHECK and `ADD CONSTRAINT` with expanded values including `'fee'`, `'payout'`, `'unknown'`.
**Warning signs:** 500 errors on Stripe sync or webhook processing.

### Pitfall 4: Stripe SDK Blocking the Event Loop
**What goes wrong:** Calling `stripe.BalanceTransaction.list().auto_paging_iter()` in an async handler blocks the entire event loop for the duration of the import (could be minutes for 12 months of data).
**Why it happens:** The Stripe Python SDK v7 is entirely synchronous.
**How to avoid:** Wrap in `asyncio.to_thread()`. For very large imports, process in batches with yielding.
**Warning signs:** Server becomes unresponsive during Stripe sync.

### Pitfall 5: Shopify {shop} URL Substitution
**What goes wrong:** The Shopify provider in PROVIDER_REGISTRY has `{shop}` placeholder in auth_url and token_url. The generic OAuth flow in `integrations.py` does not substitute `{shop}`.
**Why it happens:** Shopify is unique among OAuth providers in requiring the shop domain in the URL.
**How to avoid:** The authorize endpoint needs to accept a `shop` parameter and substitute it in the URLs before redirecting.
**Warning signs:** OAuth redirects to literal `{shop}.myshopify.com`.

### Pitfall 6: Shopify GraphQL Rate Limit Throttling
**What goes wrong:** Initial product/order import fires too many queries too fast, gets throttled with 429s.
**Why it happens:** Shopify standard plans have 50 points/second restore rate, 1000 point bucket. Complex queries with nested connections cost more points.
**How to avoid:** Track `extensions.cost.throttleStatus.currentlyAvailable` in responses. Pause when below 200 points. Keep individual query costs under 100 points by limiting `first` to 50 for top-level and 10-20 for nested connections.
**Warning signs:** 429 responses, empty data in sync results.

### Pitfall 7: Amounts in Cents vs Dollars
**What goes wrong:** Stripe amounts are in cents (integer). If stored directly in `financial_records.amount` (NUMERIC(15,2)), values are 100x too large.
**Why it happens:** Different systems use different amount conventions.
**How to avoid:** Always divide Stripe amounts by 100 before inserting. Document this in the mapping function.
**Warning signs:** Revenue dashboard showing $9,900 instead of $99.

## Code Examples

### Financial Records Schema Migration
```sql
-- Source: Existing schema analysis + CONTEXT.md requirements

-- 1. Add external_id column for Stripe/Shopify idempotency
ALTER TABLE public.financial_records
    ADD COLUMN IF NOT EXISTS external_id TEXT;

-- Unique constraint for idempotency (allow NULL for manual records)
CREATE UNIQUE INDEX IF NOT EXISTS idx_financial_records_external_id
    ON public.financial_records (external_id) WHERE external_id IS NOT NULL;

-- 2. Expand transaction_type CHECK constraint
-- Must drop the existing unnamed CHECK and re-add with new values
ALTER TABLE public.financial_records
    DROP CONSTRAINT IF EXISTS financial_records_transaction_type_check;

ALTER TABLE public.financial_records
    ADD CONSTRAINT financial_records_transaction_type_check
    CHECK (transaction_type IN ('revenue', 'expense', 'refund', 'adjustment', 'fee', 'payout', 'unknown'));

-- 3. Index for source_type queries (Stripe vs Shopify vs manual)
CREATE INDEX IF NOT EXISTS idx_financial_records_source_type
    ON public.financial_records (user_id, source_type, transaction_date DESC)
    WHERE source_type IS NOT NULL;
```

### Shopify Orders Table
```sql
-- Source: CONTEXT.md decisions
CREATE TABLE IF NOT EXISTS public.shopify_orders (
    id              uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id         uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shopify_order_id TEXT       NOT NULL,
    order_number    TEXT,
    email           TEXT,
    financial_status TEXT,
    fulfillment_status TEXT,
    total_price     NUMERIC(15, 2) NOT NULL DEFAULT 0,
    subtotal_price  NUMERIC(15, 2) NOT NULL DEFAULT 0,
    currency        TEXT        NOT NULL DEFAULT 'USD',
    line_items      JSONB       NOT NULL DEFAULT '[]'::jsonb,
    customer        JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at_shopify TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_shopify_orders_user_order
        UNIQUE (user_id, shopify_order_id)
);

ALTER TABLE public.shopify_orders ENABLE ROW LEVEL SECURITY;
-- RLS policies for user_id = auth.uid() (SELECT, INSERT, UPDATE, DELETE)
-- Service role bypass for webhook processing
```

### Shopify Products Table
```sql
-- Source: CONTEXT.md decisions
CREATE TABLE IF NOT EXISTS public.shopify_products (
    id                  uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id             uuid        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    shopify_product_id  TEXT        NOT NULL,
    title               TEXT        NOT NULL,
    vendor              TEXT,
    product_type        TEXT,
    status              TEXT,
    variants            JSONB       NOT NULL DEFAULT '[]'::jsonb,  -- [{id, title, price, sku, inventory_quantity}]
    image_url           TEXT,
    inventory_quantity  INTEGER     NOT NULL DEFAULT 0,  -- sum across variants
    low_stock_threshold INTEGER     NOT NULL DEFAULT 10,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_shopify_products_user_product
        UNIQUE (user_id, shopify_product_id)
);

ALTER TABLE public.shopify_products ENABLE ROW LEVEL SECURITY;
-- RLS policies for user_id = auth.uid() (SELECT, INSERT, UPDATE, DELETE)
-- Service role bypass for webhook processing
```

### Stripe Webhook Event-to-Record Mapping
```python
# Source: Stripe API docs + CONTEXT.md decisions
async def handle_payment_intent_succeeded(event_data: dict, user_id: str):
    """Map payment_intent.succeeded to a financial_record."""
    pi = event_data  # PaymentIntent object
    record = {
        "user_id": user_id,
        "external_id": f"pi_{pi['id']}",
        "transaction_type": "revenue",
        "amount": pi["amount_received"] / 100,  # cents to dollars
        "currency": pi["currency"].upper(),
        "description": pi.get("description") or "Stripe payment",
        "source_type": "stripe",
        "source_id": pi["id"],
        "transaction_date": datetime.fromtimestamp(pi["created"], tz=timezone.utc).isoformat(),
        "metadata": {"stripe_event": "payment_intent.succeeded"},
    }
    # Upsert with ON CONFLICT (external_id) DO NOTHING for idempotency
    ...
```

### Shopify GraphQL Products Query
```graphql
# Source: https://shopify.dev/docs/api/admin-graphql/latest/queries/products
query ($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    edges {
      cursor
      node {
        id
        title
        vendor
        productType
        status
        totalInventory
        featuredMedia {
          preview {
            image {
              url
            }
          }
        }
        variants(first: 20) {
          edges {
            node {
              id
              title
              price
              sku
              inventoryQuantity
            }
          }
        }
      }
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

### NotificationService Usage for Inventory Alerts
```python
# Source: app/notifications/notification_service.py
from app.notifications.notification_service import (
    NotificationType,
    get_notification_service,
)

async def send_low_stock_alert(user_id: str, product_title: str, qty: int, threshold: int):
    svc = get_notification_service()
    await svc.create_notification(
        user_id=user_id,
        title="Low Stock Alert",
        message=f"{product_title} is low on stock ({qty} remaining, threshold: {threshold})",
        type=NotificationType.WARNING,
        link="/dashboard/inventory",
        metadata={"alert_type": "low_stock", "product_title": product_title, "quantity": qty},
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `stripe.Webhook.construct_event()` | `StripeClient.parse_event_notification()` | Stripe SDK v14+ | Project uses v7; stick with `construct_event()` |
| Shopify REST Admin API (2 req/sec) | GraphQL Admin API (cost-based throttling) | Shopify 2019+ | GraphQL is 10-50x more efficient for bulk queries |
| Shopify REST inventory endpoint | GraphQL `inventoryItems` / `inventoryLevel` | 2023+ | GraphQL provides atomic multi-location inventory |

**Deprecated/outdated:**
- Shopify REST Admin API: Still works but GraphQL is strongly preferred for new integrations. REST has a hard 2 requests/second rate limit vs GraphQL's cost-based system.
- `stripe.Event` legacy constructor: Use `stripe.Webhook.construct_event()` for proper signature verification.

## Discretion Recommendations

### Stripe Batch Size for Historical Import
**Recommendation:** Use `limit=100` per page (maximum allowed by Stripe). With `auto_paging_iter()`, this is handled automatically. For 12 months of a typical small business (~500-2000 transactions), the full import completes in under 30 seconds.

### Shopify Product Variant Handling
**Recommendation:** Flatten variants into a JSONB array on the `shopify_products` row. Store `inventory_quantity` as the sum across all variants at the product level (for quick threshold checks). Store individual variant details in the `variants` JSONB column.
**Rationale:** A separate `shopify_variants` table adds complexity without benefit -- agents query at the product level, and variant details are accessed infrequently.

### Error Handling for Stripe Historical Import
**Recommendation:** Wrap the full import in a try/except. On Stripe API errors (rate limit, auth failure), update `integration_sync_state` with error_count and last_error. Use the existing `sync_cursor` JSONB to store the last successfully processed `starting_after` cursor so imports can resume from where they left off.

### Source Column vs Metadata JSONB
**Recommendation:** Use the existing `source_type` column (already TEXT, nullable) to store `"stripe"` or `"shopify"`. Use `source_id` to store the Stripe transaction ID or Shopify order ID. This enables efficient indexed queries (`WHERE source_type = 'stripe'`) without JSONB path queries.

### Notification Message Formatting
**Recommendation:** Use the pattern: `"{Product name} is low on stock ({current_qty} remaining, threshold: {threshold})"` as specified in CONTEXT.md. Notification type should be `WARNING`. Include link to a dashboard/inventory page.

## Open Questions

1. **Stripe Connect vs Platform API Key**
   - What we know: CONTEXT.md says "use existing Stripe SDK + STRIPE_API_KEY env var" for the platform, and Phase 39 credential storage for per-user Stripe Connect accounts.
   - What's unclear: Whether the MVP supports Stripe Connect (multi-user) or just the platform's own Stripe account.
   - Recommendation: Start with platform's own STRIPE_API_KEY (simpler). The architecture supports per-user Connect accounts via IntegrationManager.get_valid_token() but skip that for initial implementation.

2. **Shopify {shop} Substitution in OAuth Flow**
   - What we know: PROVIDER_REGISTRY has `{shop}` placeholder in URLs.
   - What's unclear: Whether the Phase 39 OAuth authorize endpoint handles shop-specific URL substitution.
   - Recommendation: The authorize endpoint in integrations.py likely needs modification to accept a `shop` query parameter and substitute it. Research the existing callback flow to confirm.

3. **Webhook User Resolution**
   - What we know: Stripe webhooks are platform-level (not per-user). Shopify webhooks include the shop domain.
   - What's unclear: How to resolve which user_id a Stripe webhook belongs to (for the platform API key scenario).
   - Recommendation: For platform-key mode, the STRIPE_API_KEY owner is the single user. Store user_id in webhook endpoint config or derive from the payment metadata.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | pyproject.toml (pytest section) |
| Quick run command | `uv run pytest tests/unit/test_stripe_sync.py tests/unit/test_shopify_service.py -x` |
| Full suite command | `uv run pytest tests/unit/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FIN-01 | Stripe history import maps transactions to financial_records | unit | `uv run pytest tests/unit/test_stripe_sync.py::test_sync_history -x` | Wave 0 |
| FIN-02 | Revenue dashboard reflects Stripe data | unit | `uv run pytest tests/unit/test_financial_service.py -x` | Existing (passes once data flows in) |
| FIN-03 | Stripe webhook creates financial_record | unit | `uv run pytest tests/unit/test_stripe_sync.py::test_webhook_payment_succeeded -x` | Wave 0 |
| FIN-04 | Transaction categorization mapping | unit | `uv run pytest tests/unit/test_stripe_sync.py::test_type_mapping -x` | Wave 0 |
| FIN-05 | Manual sync endpoint triggers import | unit | `uv run pytest tests/unit/test_stripe_sync.py::test_manual_sync -x` | Wave 0 |
| SHOP-01 | Shopify OAuth connection (via Phase 39) | manual-only | N/A -- requires real Shopify app credentials | N/A |
| SHOP-02 | Agent can list orders/products | unit | `uv run pytest tests/unit/test_shopify_service.py::test_list_orders -x` | Wave 0 |
| SHOP-03 | Sales analytics computed correctly | unit | `uv run pytest tests/unit/test_shopify_service.py::test_analytics -x` | Wave 0 |
| SHOP-04 | Inventory alert fires below threshold | unit | `uv run pytest tests/unit/test_shopify_service.py::test_inventory_alert -x` | Wave 0 |
| SHOP-05 | Shopify webhook processes order/inventory | unit | `uv run pytest tests/unit/test_shopify_service.py::test_webhook_order_create -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/unit/test_stripe_sync.py tests/unit/test_shopify_service.py -x`
- **Per wave merge:** `uv run pytest tests/unit/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/unit/test_stripe_sync.py` -- covers FIN-01, FIN-03, FIN-04, FIN-05
- [ ] `tests/unit/test_shopify_service.py` -- covers SHOP-02, SHOP-03, SHOP-04, SHOP-05

## Sources

### Primary (HIGH confidence)
- [Stripe BalanceTransaction Object](https://docs.stripe.com/api/balance_transactions/object) -- All fields, type enum values (40+ types)
- [Stripe BalanceTransaction List](https://docs.stripe.com/api/balance_transactions/list) -- Pagination params, created filter, limit 1-100
- [Stripe Auto-Pagination](https://docs.stripe.com/api/pagination/auto) -- Python `auto_paging_iter()` usage
- [Stripe Webhook Signature Verification](https://docs.stripe.com/webhooks/signature) -- `construct_event()` params, exceptions
- [Stripe Webhook Events](https://docs.stripe.com/webhooks) -- Event payload structure, Python Flask example
- [Shopify GraphQL Orders Query](https://shopify.dev/docs/api/admin-graphql/latest/queries/orders) -- Fields, filters, pagination
- [Shopify GraphQL Products Query](https://shopify.dev/docs/api/admin-graphql/latest/queries/products) -- Fields, variants, pagination
- [Shopify API Rate Limits](https://shopify.dev/docs/api/usage/limits) -- Cost points, bucket sizes, restore rates
- [Shopify Webhook HTTPS Delivery](https://shopify.dev/docs/apps/build/webhooks/subscribe/https) -- HMAC-SHA256 verification (base64)

### Secondary (MEDIUM confidence)
- [Stripe Python SDK GitHub](https://github.com/stripe/stripe-python/blob/master/examples/webhooks.py) -- Webhook example confirming `Webhook.construct_event()` for v7
- Existing codebase analysis: `app/mcp/tools/stripe_payments.py`, `app/services/financial_service.py`, `app/routers/webhooks.py`, `app/services/integration_manager.py`, `app/config/integration_providers.py`, `app/notifications/notification_service.py`

### Tertiary (LOW confidence)
- Shopify GraphQL cost point estimation (50 pts/sec standard plan) -- varies by Shopify plan; needs runtime verification

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- All libraries already installed and used in codebase
- Architecture: HIGH -- Follows established BaseService pattern, Phase 39 infrastructure verified
- Pitfalls: HIGH -- Verified through direct analysis of existing code (CHECK constraint, HMAC format differences, sync vs async SDK)
- Shopify rate limits: MEDIUM -- Plan-dependent; runtime throttle header monitoring recommended
- Stripe SDK v7 specifics: HIGH -- Confirmed `>=7.0.0,<8.0.0` in pyproject.toml; `construct_event()` verified

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable APIs, no breaking changes expected)
