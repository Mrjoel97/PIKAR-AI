# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import asyncpg
import pytest

# This test is designed to verify that the 11 system agents have been
# provisioned in the database.
#
# To run this test, you will need to have a running Supabase instance and
# provide the database credentials as environment variables:
#
# SUPABASE_DB_HOST
# SUPABASE_DB_PORT
# SUPABASE_DB_USER
# SUPABASE_DB_PASSWORD
# SUPABASE_DB_NAME
#
# The test is skipped if these environment variables are not set.

@pytest.mark.skipif(
    not all(
        os.environ.get(var)
        for var in [
            "SUPABASE_DB_HOST",
            "SUPABASE_DB_PORT",
            "SUPABASE_DB_USER",
            "SUPABASE_DB_PASSWORD",
            "SUPABASE_DB_NAME",
        ]
    ),
    reason="Database credentials not provided in environment variables.",
)
async def test_verify_agent_provisioning():
    """
    Connects to the database and verifies that there are 11 agents
    in the 'agents' table.
    """
    conn = None
    try:
        conn = await asyncpg.connect(
            host=os.environ.get("SUPABASE_DB_HOST"),
            port=os.environ.get("SUPABASE_DB_PORT"),
            user=os.environ.get("SUPABASE_DB_USER"),
            password=os.environ.get("SUPABASE_DB_PASSWORD"),
            database=os.environ.get("SUPABASE_DB_NAME"),
        )
        
        # Query the database for the number of agents
        agent_count = await conn.fetchval("SELECT COUNT(*) FROM agents WHERE is_system = true")
        
        # Assert that there are 11 system agents
        assert agent_count == 11, f"Expected 11 system agents, but found {agent_count}."

    finally:
        if conn:
            await conn.close()
