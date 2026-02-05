
import { assertEquals, assertExists } from "https://deno.land/std@0.192.0/testing/asserts.ts";

const FUNCTION_URL = Deno.env.get("SUPABASE_URL") + "/functions/v1/execute-workflow";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") || "";

Deno.test("execute-workflow: should require execution_id", async () => {
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

Deno.test("execute-workflow: should fail with invalid execution_id", async () => {
    const response = await fetch(FUNCTION_URL, {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${SERVICE_KEY}`,
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ execution_id: "00000000-0000-0000-0000-000000000000" })
    });

    assertEquals(response.status, 400);
    const body = await response.json();
    assertExists(body.error);
});

// Integration test: requires a pre-created workflow execution
Deno.test({
    name: "execute-workflow: should handle start action",
    ignore: true, // Enable when test data is seeded
    fn: async () => {
        const TEST_EXECUTION_ID = "YOUR_TEST_EXECUTION_ID";
        const response = await fetch(FUNCTION_URL, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${SERVICE_KEY}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ execution_id: TEST_EXECUTION_ID, step_action: "start" })
        });

        assertEquals(response.status, 200);
        const body = await response.json();
        assertEquals(body.success, true);
    }
});
