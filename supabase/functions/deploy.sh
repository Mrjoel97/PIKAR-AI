#!/bin/bash
# Deploy all Edge Functions to Supabase

echo "Deploying Edge Functions..."

# Ensure we are in the root directory
if [ ! -d "supabase/functions" ]; then
    echo "Error: Must be run from project root"
    exit 1
fi

supabase functions deploy send-notification
supabase functions deploy execute-workflow
supabase functions deploy cleanup-sessions
supabase functions deploy generate-widget

echo "Deployment complete!"
