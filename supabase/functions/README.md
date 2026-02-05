# Supabase Edge Functions

This directory contains the serverless Edge Functions for Pikar AI.

## Functions

1. **send-notification**
   - **Purpose**: Handles asynchronous notification delivery (Email, Push, SMS).
   - **Trigger**: Webhook on `notifications.insert` or manual invocation.
   - **Payload**: `{ notification_id: string }`

2. **execute-workflow**
   - **Purpose**: Orchestrates long-running workflows and phase transitions.
   - **Trigger**: Webhook on `workflow_executions.insert` or manual step approval.
   - **Payload**: `{ execution_id: string, step_action: 'start' | 'advance' | 'retry' }`

3. **cleanup-sessions**
   - **Purpose**: Periodically cleans up old inactive sessions.
   - **Trigger**: Cron job (Daily).
   - **Payload**: None

4. **generate-widget**
   - **Purpose**: Asynchronously generates complex UI widget data.
   - **Trigger**: Manual invocation from AI Agents.
   - **Payload**: `{ user_id: string, widget_type: string, parameters: object }`

## Setup

1. **Install Supabase CLI**: Ensure you have the Supabase CLI installed.
2. **Login**: `supabase login`
3. **Secrets**: Set the following secrets in your Supabase project:
   - `SUPABASE_URL`: Auto-configured in hosted Supabase, required for local.
   - `SUPABASE_SERVICE_ROLE_KEY`: Auto-configured in hosted Supabase, required for local.
   - `RESEND_API_KEY`: Required for sending emails via Resend.
   - `FCM_SERVER_KEY`: Required for sending Push Notifications via Firebase.
   - `TWILIO_ACCOUNT_SID`: Required for SMS via Twilio.
   - `TWILIO_AUTH_TOKEN`: Required for SMS via Twilio.
   - `TWILIO_FROM_NUMBER`: Sender number for SMS.
   - `GOOGLE_CALENDAR_API_KEY`: Required for calendar widget data.

   To set secrets in production:
   ```bash
   supabase secrets set --env-file ./supabase/functions/.env
   # OR individually
   supabase secrets set RESEND_API_KEY=re_123...
   ```

## Deployment

Run the deployment script from the project root:

```bash
./supabase/functions/deploy.sh
```

## Database Webhooks

The Edge Functions can be automatically triggered by database changes using `pg_net` webhooks. The webhook configuration is defined in migration `0023_edge_function_webhooks.sql`.

### How It Works

1. **Triggers**: Database triggers fire on INSERT/UPDATE events
2. **pg_net**: Makes async HTTP POST requests to Edge Functions
3. **Configuration Table**: `_edge_function_config` stores function URLs

### Webhook Triggers

| Function | Table | Event |
|----------|-------|-------|
| `send-notification` | `notifications` | INSERT with `metadata.send_immediately = true` |
| `execute-workflow` | `workflow_executions` | INSERT with status 'pending'/'running', or status changes |

### Configuration

After deploying Edge Functions, update the webhook URLs:

```sql
-- Replace <project-ref> with your Supabase project reference
SELECT update_edge_function_url('send-notification', 'https://<project-ref>.supabase.co/functions/v1/send-notification');
SELECT update_edge_function_url('execute-workflow', 'https://<project-ref>.supabase.co/functions/v1/execute-workflow');
```

### Enable/Disable Webhooks

```sql
-- Disable a webhook
SELECT toggle_edge_function_webhook('send-notification', FALSE);

-- Re-enable
SELECT toggle_edge_function_webhook('send-notification', TRUE);
```

### Service Role Key Configuration

The webhooks use the service role key for authentication. Set it in your database:

```sql
ALTER DATABASE postgres SET app.settings.service_role_key = 'your-service-role-key';
```

Or pass it directly when calling the function:

```sql
SELECT call_edge_function('send-notification', '{"notification_id": "abc123"}'::jsonb, 'your-service-role-key');
```

## Testing

You can test functions locally using:

```bash
supabase functions serve
```

Curl example:
```bash
curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/send-notification' \
    --header 'Authorization: Bearer <your_anon_key>' \
    --header 'Content-Type: application/json' \
    --data '{"notification_id":"<id>"}'
```

## Troubleshooting

### Check Webhook Status
```sql
SELECT * FROM _edge_function_config;
```

### View pg_net Request History
```sql
SELECT * FROM net._http_response ORDER BY created DESC LIMIT 10;
```

### Test Webhook Manually
```sql
SELECT call_edge_function('send-notification', '{"notification_id": "test-id"}'::jsonb);
```
