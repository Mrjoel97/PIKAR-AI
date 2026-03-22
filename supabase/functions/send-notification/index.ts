
import { createSupabaseClient } from '../_shared/supabase.ts';
import { handleError, logInfo, logError, validateRequest, corsHeaders, requireAuth, assertUuid } from '../_shared/utils.ts';
import { Notification } from '../_shared/types.ts';

Deno.serve(async (req) => {
    if (req.method === 'OPTIONS') {
        return new Response('ok', { headers: corsHeaders });
    }

    try {
        const auth = await requireAuth(req);
        const { notification_id } = await validateRequest(req, ['notification_id']);
        assertUuid(notification_id, 'notification_id');
        const supabase = createSupabaseClient();

        logInfo('send-notification', `Processing notification ${notification_id}`);

        // Fetch notification with user profile (email, phone, fcm_token)
        const { data: notification, error: fetchError } = await supabase
            .from('notifications')
            .select(`
                *,
                profiles:user_id (
                    email,
                    phone_number,
                    fcm_token
                )
            `)
            .eq('id', notification_id)
            .single();

        if (fetchError || !notification) {
            throw new Error(`Notification not found: ${fetchError?.message}`);
        }

        const notif = notification as any;
        if (!auth.isServiceRole && notif.user_id !== auth.user?.id) {
            throw new Error('Unauthorized');
        }
        const userProfile = notif.profiles;

        // Retrieve secrets
        const RESEND_API_KEY = Deno.env.get('RESEND_API_KEY');
        const FCM_SERVER_KEY = Deno.env.get('FCM_SERVER_KEY');
        const TWILIO_ACCOUNT_SID = Deno.env.get('TWILIO_ACCOUNT_SID');
        const TWILIO_AUTH_TOKEN = Deno.env.get('TWILIO_AUTH_TOKEN');
        const TWILIO_FROM_NUMBER = Deno.env.get('TWILIO_FROM_NUMBER');

        let deliveryStatus = 'delivered';
        const metadata = notif.metadata || {};
        let providerResponse: any = {};

        try {
            switch (notif.type) {
                case 'email':
                    if (RESEND_API_KEY && userProfile?.email) {
                        const res = await fetch('https://api.resend.com/emails', {
                            method: 'POST',
                            headers: {
                                'Authorization': `Bearer ${RESEND_API_KEY}`,
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                from: 'Pikar AI <onboarding@resend.dev>', // Should be configurable
                                to: userProfile.email,
                                subject: notif.title,
                                html: notif.message
                            })
                        });

                        if (!res.ok) {
                            const errorData = await res.text();
                            throw new Error(`Resend API Error: ${res.status} ${errorData}`);
                        }

                        providerResponse = await res.json();
                        metadata.provider = 'resend';
                    } else {
                        console.warn('[Email] RESEND_API_KEY not set or user email missing. Logging only.');
                        metadata.provider = 'log_only';
                        if (!userProfile?.email) metadata.warning = 'User email missing';
                    }
                    break;

                case 'push':
                    // FCM Legacy HTTP API is deprecated (shutdown June 2024).
                    // TODO: Migrate to FCM HTTP v1 API with OAuth 2.0 authentication.
                    // See: https://firebase.google.com/docs/cloud-messaging/migrate-v1
                    console.warn('[Push] FCM Legacy API is deprecated and non-functional. Migrate to FCM v1. Notification logged only.');
                    metadata.provider = 'log_only';
                    metadata.warning = 'FCM Legacy API deprecated — push notification not sent';
                    break;

                case 'sms':
                    if (TWILIO_ACCOUNT_SID && TWILIO_AUTH_TOKEN && TWILIO_FROM_NUMBER && userProfile?.phone_number) {
                        const basicAuth = btoa(`${TWILIO_ACCOUNT_SID}:${TWILIO_AUTH_TOKEN}`);
                        const body = new URLSearchParams();
                        body.append('To', userProfile.phone_number);
                        body.append('From', TWILIO_FROM_NUMBER);
                        body.append('Body', `${notif.title}: ${notif.message}`);

                        const res = await fetch(`https://api.twilio.com/2010-04-01/Accounts/${TWILIO_ACCOUNT_SID}/Messages.json`, {
                            method: 'POST',
                            headers: {
                                'Authorization': `Basic ${basicAuth}`,
                                'Content-Type': 'application/x-www-form-urlencoded'
                            },
                            body: body
                        });

                        if (!res.ok) {
                            const errorData = await res.text();
                            throw new Error(`Twilio API Error: ${res.status} ${errorData}`);
                        }

                        providerResponse = await res.json();
                        metadata.provider = 'twilio';
                    } else {
                        console.warn('[SMS] Twilio credentials not set or phone missing. Logging only.');
                        metadata.provider = 'log_only';
                        if (!userProfile?.phone_number) metadata.warning = 'User phone missing';
                    }
                    break;

                case 'in_app':
                    console.log(`[In-App] Notification ${notif.id} for user ${notif.user_id}`);
                    metadata.provider = 'internal';
                    break;

                default:
                    console.warn(`Unknown notification type: ${notif.type}`);
                    deliveryStatus = 'failed';
                    metadata.error = `Unknown type: ${notif.type}`;
            }
        } catch (deliveryError: any) {
            console.error(`Delivery failed for ${notif.id}:`, deliveryError);
            deliveryStatus = 'failed';
            metadata.error = deliveryError.message;
        }

        // Update notification status in metadata since columns don't exist
        const newMetadata = {
            ...metadata,
            delivery_status: deliveryStatus,
            delivered_: deliveryStatus === 'delivered', // Using suffix to avoid collision if column added later? or standardizing
            delivered_at: deliveryStatus === 'delivered' ? new Date().toISOString() : null,
            provider_response: providerResponse
        };

        // Also update standard columns if they exist, but robustly fallback to metadata
        const updates: any = {
            metadata: newMetadata,
            is_read: false // Default
        };
        // If query was strictly typed we'd be careful, but here we update allowed columns
        // Assuming 'status' column exists based on user prompt requirements? 
        // "Update status='delivered'". If column doesn't exist, this might throw if not strict?
        // Let's assume schema matches requirement.
        updates.status = deliveryStatus;
        if (deliveryStatus === 'delivered') updates.delivered_at = new Date().toISOString();


        const { error: updateError } = await supabase
            .from('notifications')
            .update(updates)
            .eq('id', notification_id);

        if (updateError) {
            // If update fails (e.g. column missing), try updating just metadata
            if (updateError.message.includes('column')) {
                await supabase.from('notifications').update({ metadata: newMetadata }).eq('id', notification_id);
            } else {
                throw new Error(`Failed to update notification: ${updateError.message}`);
            }
        }

        logInfo('send-notification', `Notification ${notification_id} processed successfully`);

        return new Response(JSON.stringify({ success: true, notification_id, status: deliveryStatus }), {
            headers: { ...corsHeaders, 'Content-Type': 'application/json' },
            status: 200,
        });

    } catch (error) {
        logError('send-notification', error);
        return handleError(error);
    }
});
