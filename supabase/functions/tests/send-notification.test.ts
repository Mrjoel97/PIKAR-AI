import { assertEquals, assertExists } from "https://deno.land/std@0.192.0/testing/asserts.ts";

const FUNCTION_URL = Deno.env.get("SUPABASE_URL") + "/functions/v1/send-notification";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";

Deno.test("send-notification: should fail without notification_id", async () => {
    const response = await fetch(FUNCTION_URL, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${SERVICE_KEY}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({})
    });

    assertEquals(response.status, 400);
    const body = await response.json();
    assertExists(body.error);
});

Deno.test("send-notification: should fail with invalid notification_id", async () => {
    const response = await fetch(FUNCTION_URL, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${SERVICE_KEY}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ notification_id: "00000000-0000-0000-0000-000000000000" })
    });

    // Expect error because notification doesn't exist
    assertEquals(response.status, 400);
    const body = await response.json();
    assertExists(body.error);
});

// Integration test: requires a pre-created notification ID
Deno.test({
    name: "send-notification: should process valid notification",
    ignore: true, // Enable when test data is seeded
    fn: async () => {
        const TEST_NOTIFICATION_ID = "YOUR_TEST_NOTIFICATION_ID";
        const response = await fetch(FUNCTION_URL, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${SERVICE_KEY}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ notification_id: TEST_NOTIFICATION_ID })
        });

        assertEquals(response.status, 200);
        const body = await response.json();
        assertEquals(body.success, true);
    }
});
