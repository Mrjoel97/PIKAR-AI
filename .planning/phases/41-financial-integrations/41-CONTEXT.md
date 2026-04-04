# Phase 41: Financial Integrations - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

Connect Pikar to real financial data sources: auto-import Stripe transaction history into financial_records with categorization, process Stripe webhooks for real-time updates, connect Shopify stores via OAuth for order/product/inventory sync with real-time webhooks and per-product inventory alerts. The financial agent works with actual numbers, not manually entered data.

</domain>

<decisions>
## Implementation Decisions

### Stripe Revenue Sync
- **Historical import:** Last 12 months of transactions on first connect. Uses `stripe.BalanceTransaction.list()` with `auto_pagination` and `created` filter.
- **Stripe objects to sync:**
  - `balance_transactions` → `financial_records` table (primary data source — includes charges, refunds, fees, payouts, adjustments)
  - `payment_intent.succeeded` webhook → creates new financial_record automatically
  - `charge.refunded` webhook → creates refund record
  - `payout.paid` webhook → creates payout record
- **Categorization mapping:**
  - `type: "charge"` → `transaction_type: "revenue"`
  - `type: "refund"` → `transaction_type: "refund"`
  - `type: "stripe_fee"` → `transaction_type: "fee"`
  - `type: "payout"` → `transaction_type: "payout"`
  - `type: "adjustment"` → `transaction_type: "adjustment"`
- **Idempotency:** Use Stripe `id` as `external_id` in `financial_records` with UNIQUE constraint. Duplicate webhook deliveries silently ignored.
- **Stripe connection:** Use existing Stripe SDK + `STRIPE_API_KEY` env var (already configured). For per-user Stripe Connect accounts, use Phase 39 credential storage with Stripe OAuth.
- **Revenue dashboard:** `FinancialService.get_revenue_stats()` already queries `financial_records` — no change needed. Once Stripe data flows in, the dashboard automatically shows real numbers.
- **Manual sync trigger:** `POST /integrations/stripe/sync` endpoint — re-imports last 12 months. Useful if user suspects missing transactions.
- **New service:** `app/services/stripe_sync_service.py` extending BaseService

### Shopify E-commerce Connector
- **OAuth connection:** Via Phase 39 infrastructure — Shopify is already in PROVIDER_REGISTRY
- **API:** Shopify GraphQL Admin API (1000 cost points/second — more efficient than REST's 2 req/sec)
- **Data to sync:**
  - **Orders** → mapped to `financial_records` (revenue from orders) + new `shopify_orders` table for order details (line items, fulfillment status, customer)
  - **Products** → new `shopify_products` table (id, title, vendor, product_type, variants with prices, inventory_quantity, image_url)
  - **Inventory** → stored on `shopify_products.inventory_quantity`, updated via webhooks
- **New tables:** `shopify_orders` and `shopify_products` in Supabase migration, RLS per user
- **Sales analytics for FinancialAnalysisAgent:**
  - Revenue by period (from orders)
  - Average order value (AOV)
  - Top products by revenue
  - Order count trends
  - All computed by querying `shopify_orders` + `shopify_products`
- **Inventory alerts:**
  - Per-product threshold (default: 10 units, configurable per product)
  - Stored in `shopify_products.low_stock_threshold` column
  - When webhook updates inventory below threshold → notification via existing notification_service
  - Alert format: "{Product name} is low on stock ({current_qty} remaining, threshold: {threshold})"
- **Shopify webhooks (via Phase 39 inbound infrastructure):**
  - `orders/create` → insert to shopify_orders + financial_records
  - `orders/updated` → update shopify_orders
  - `products/update` → update shopify_products (including inventory)
  - `inventory_levels/update` → update inventory_quantity, check threshold
  - Webhook verification: Shopify HMAC-SHA256 with shared secret
- **Rate limiting:** Token bucket at 800 points/sec (leave 200 points headroom from 1000 limit)
- **Initial sync:** On first connect, import all products and last 12 months of orders
- **New service:** `app/services/shopify_service.py` extending BaseService

### Agent Tools
- **Stripe tools for FinancialAnalysisAgent:**
  - `get_stripe_revenue_summary(period?)` — queries financial_records where source=stripe
  - `trigger_stripe_sync()` — triggers manual sync
- **Shopify tools for FinancialAnalysisAgent:**
  - `get_shopify_orders(period?, status?)` — queries shopify_orders
  - `get_shopify_products(category?, sort_by?)` — queries shopify_products
  - `get_shopify_analytics(period?)` — computed: revenue, AOV, top products, order trends
  - `get_low_stock_products()` — products below threshold
  - `set_inventory_alert_threshold(product_id, threshold)` — updates per-product threshold
- **Registration:** All tools on FinancialAnalysisAgent + MarketingAutomationAgent (for e-commerce analytics)

### Claude's Discretion
- Exact GraphQL queries for Shopify (products, orders, inventory)
- Stripe balance transaction pagination strategy (batch size)
- Shopify product variant handling (flatten vs nested)
- Error handling for Stripe API failures during historical import
- Notification message formatting for inventory alerts
- Whether to add `source` column to `financial_records` or use `metadata` JSONB

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `app/mcp/tools/stripe_payments.py`: Existing Stripe SDK integration (payment links, customer creation)
- `app/services/financial_service.py`: `get_revenue_stats()` queries `financial_records` — auto-benefits from Stripe data
- `app/services/integration_manager.py`: Phase 39 credential storage + token refresh
- `app/routers/webhooks.py`: Phase 39 generalized inbound webhook with HMAC verification
- `app/config/integration_providers.py`: Shopify already registered in PROVIDER_REGISTRY
- `app/services/webhook_delivery_service.py`: Phase 39 outbound delivery + event catalog
- `app/services/notification_service.py`: Existing notification delivery for alerts

### Established Patterns
- Stripe SDK via `import stripe; stripe.api_key = settings.STRIPE_API_KEY`
- Financial records use `transaction_type` field for categorization
- Webhook processing via `webhook_events` table → `ai_jobs` queue (Phase 39)
- Integration credentials with Fernet encryption (Phase 39)
- BaseService with RLS-scoped Supabase queries

### Integration Points
- `app/agents/financial/agent.py`: Add Stripe sync + Shopify tools
- `app/agents/marketing/agent.py`: Add Shopify analytics tools
- `app/agents/tools/tool_registry.py`: Register new tool groups
- `app/routers/webhooks.py`: Add Stripe + Shopify webhook handlers
- `app/fast_api_app.py`: Mount any new routers
- `supabase/migrations/`: New tables (shopify_orders, shopify_products) + financial_records changes

</code_context>

<specifics>
## Specific Ideas

- Stripe sync should be "connect and forget" — once connected, financial data just flows in automatically
- Shopify data should make the FinancialAnalysisAgent genuinely useful for e-commerce businesses — not just showing numbers but providing AI-powered insights on real sales data
- Inventory alerts are the kind of practical, actionable feature that makes solopreneurs love a tool

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 41-financial-integrations*
*Context gathered: 2026-04-04*
