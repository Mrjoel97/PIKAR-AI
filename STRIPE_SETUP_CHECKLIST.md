# Stripe Setup Checklist for Pikar AI

## ✅ Completed
- [x] Stripe test keys added to Vercel environment variables
- [x] stripe-webhook function deployed with verify_jwt = OFF
- [x] Supabase billing schema created (billing_products, billing_prices, user_subscriptions)
- [x] Payment link integration in /pricing page
- [x] Admin billing panel at /admin/billing

## 🔄 Next Steps

### 1. Deploy stripe-sync function
```bash
# From your repo root with Supabase CLI
supabase functions deploy stripe-sync

# Set function secrets
supabase secrets set --env prod \
<<<<<<< HEAD
  STRIPE_SECRET_KEY=sk_test_REDACTED \
=======
  STRIPE_SECRET_KEY=sk_test_xxx \
>>>>>>> 9671bcf (chore: redact Stripe test secret from docs to satisfy GitHub push protection)
  SUPABASE_URL=https://iztyrtapoctlnhxsgooe.supabase.co \
  SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 2. Run stripe-sync to populate payment links
```bash
# Invoke the function once to create Stripe products/prices/payment links
curl https://iztyrtapoctlnhxsgooe.functions.supabase.co/stripe-sync

# Verify billing_prices.payment_link_url is populated
# Check in Supabase Dashboard -> Table Editor -> billing_prices
```

### 3. Configure Stripe webhook
- Stripe Dashboard -> Developers -> Webhooks -> Add endpoint
- URL: `https://iztyrtapoctlnhxsgooe.functions.supabase.co/stripe-webhook`
- Events: `checkout.session.completed`, `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
- Copy the Signing Secret (whsec_...) and set it in Supabase function secrets:
```bash
supabase secrets set --env prod STRIPE_WEBHOOK_SECRET=whsec_REDACTED
```

### 4. Test end-to-end
1. Visit /pricing on your deployed app
2. Click "Subscribe" button (should open Stripe Payment Link)
3. Complete test checkout with card `4242 4242 4242 4242`
4. Verify webhook updates user_subscriptions and profiles.tier in Supabase
5. Check /billing page shows subscription status

## Environment Variables Summary

### Vercel (Frontend)
- `VITE_SUPABASE_URL`
- `VITE_SUPABASE_ANON_KEY` 
- `VITE_STRIPE_PUBLIC_KEY=pk_test_REDACTED`

### Supabase Functions (stripe-webhook)
<<<<<<< HEAD
- `STRIPE_SECRET_KEY=sk_test_REDACTED`
=======
- `STRIPE_SECRET_KEY=sk_test_xxx`
>>>>>>> 9671bcf (chore: redact Stripe test secret from docs to satisfy GitHub push protection)
- `STRIPE_WEBHOOK_SECRET=whsec_...` (from Stripe webhook config)
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`

### Supabase Functions (stripe-sync)
<<<<<<< HEAD
- `STRIPE_SECRET_KEY=sk_test_REDACTED`
=======
- `STRIPE_SECRET_KEY=sk_test_xxx`
>>>>>>> 9671bcf (chore: redact Stripe test secret from docs to satisfy GitHub push protection)
- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`

## Troubleshooting

### stripe-sync returns 404
- Function not deployed yet. Run `supabase functions deploy stripe-sync`

### stripe-webhook returns 401
- verify_jwt is still enabled. Disable in Supabase Dashboard or set `verify_jwt = false` in config.toml

### Subscribe buttons disabled on /pricing
- payment_link_url is null in billing_prices. Run stripe-sync function to populate links

### Webhook events not processing
- Check Stripe webhook endpoint URL points to Supabase function, not Vercel app
- Verify STRIPE_WEBHOOK_SECRET matches the signing secret from Stripe Dashboard
