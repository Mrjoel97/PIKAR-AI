# Copyright (c) 2024-2026 Pikar AI. All rights reserved.
# Proprietary and confidential. See LICENSE file for details.

"""HubSpotService -- Bidirectional HubSpot CRM sync.

Provides:
- Contact and deal import from HubSpot into Pikar CRM tables
- Push of Pikar CRM changes back to HubSpot
- Webhook handlers for real-time HubSpot event processing
- CRM-aware deal context for agent responses

All HubSpot SDK calls use ``asyncio.to_thread()`` since the official
``hubspot-api-client`` is synchronous.  DB writes use ``AdminService``
(service role) because webhooks carry no user JWT.

Bidirectional sync loop prevention uses short-lived Redis flags
(``pikar:hubspot:skip:{contact_id}``, TTL 30s).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, ClassVar

from app.services.base_service import AdminService, BaseService
from app.services.integration_manager import IntegrationManager
from app.services.supabase_async import execute_async

logger = logging.getLogger(__name__)


class HubSpotService(BaseService):
    """Bidirectional HubSpot CRM sync service.

    Follows the ``StripeSyncService`` pattern: lazy SDK import,
    ``asyncio.to_thread`` for sync API calls, ``AdminService`` for
    service-role DB writes.
    """

    #: Map HubSpot lifecycle stages to Pikar contact_lifecycle_stage enum.
    LIFECYCLE_MAP: ClassVar[dict[str, str]] = {
        "subscriber": "lead",
        "lead": "lead",
        "marketingqualifiedlead": "qualified",
        "salesqualifiedlead": "qualified",
        "opportunity": "opportunity",
        "customer": "customer",
        "evangelist": "customer",
        "other": "lead",
    }

    # ------------------------------------------------------------------
    # HubSpot SDK client helper
    # ------------------------------------------------------------------

    async def _get_client(self, user_id: str) -> Any:
        """Return an authenticated HubSpot SDK client for *user_id*.

        Uses ``IntegrationManager.get_valid_token`` to obtain a fresh
        OAuth access token, then lazily imports and constructs the SDK
        client.

        Args:
            user_id: The owning user's UUID.

        Returns:
            An initialised ``hubspot.HubSpot`` client.

        Raises:
            ValueError: If no HubSpot credential exists for the user.
            RuntimeError: If the hubspot-api-client SDK is not installed.
        """
        mgr = IntegrationManager()
        token = await mgr.get_valid_token(user_id, "hubspot")
        if not token:
            raise ValueError(
                f"No HubSpot connection found for user {user_id}. "
                "Please connect HubSpot in Settings > Integrations."
            )

        # Lazy import -- SDK may not be installed in all environments
        try:
            from hubspot import HubSpot  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "hubspot-api-client is not installed"
            ) from exc

        return HubSpot(access_token=token)

    # ------------------------------------------------------------------
    # Redis skip-flag helpers (sync-loop prevention)
    # ------------------------------------------------------------------

    async def _set_skip_flag(self, object_id: str, ttl: int = 30) -> None:
        """Set a short-lived Redis flag to skip our own echo.

        Args:
            object_id: The HubSpot object ID (contact or deal).
            ttl: Time-to-live in seconds (default 30).
        """
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            redis_client = await cache._get_redis()
            if redis_client is not None:
                key = f"pikar:hubspot:skip:{object_id}"
                await redis_client.setex(key, ttl, "1")
        except Exception:
            logger.warning(
                "Failed to set HubSpot skip flag for %s", object_id
            )

    async def _check_skip_flag(self, object_id: str) -> bool:
        """Check whether the skip flag is set (our own echo).

        Args:
            object_id: The HubSpot object ID.

        Returns:
            ``True`` if the flag is set (should skip processing).
        """
        try:
            from app.services.cache import get_cache_service

            cache = get_cache_service()
            redis_client = await cache._get_redis()
            if redis_client is not None:
                key = f"pikar:hubspot:skip:{object_id}"
                val = await redis_client.get(key)
                return val is not None
        except Exception:
            logger.warning(
                "Failed to check HubSpot skip flag for %s", object_id
            )
        return False

    # ------------------------------------------------------------------
    # Contact sync: HubSpot -> Pikar
    # ------------------------------------------------------------------

    async def sync_contacts(self, user_id: str) -> dict[str, Any]:
        """Import all HubSpot contacts into the Pikar ``contacts`` table.

        Paginates through the HubSpot contacts API, maps each record to
        Pikar's schema, and upserts using the ``(user_id, hubspot_contact_id)``
        composite unique constraint.

        Args:
            user_id: The owning user's UUID.

        Returns:
            ``{"synced": N, "errors": N}`` counts.
        """
        hs_client = await self._get_client(user_id)
        admin = AdminService()

        properties = [
            "email",
            "firstname",
            "lastname",
            "phone",
            "company",
            "lifecyclestage",
            "hs_lastmodifieddate",
        ]

        synced = 0
        errors = 0
        after: str | None = None

        while True:
            # HubSpot SDK is synchronous -- run in thread pool
            def _fetch_page(cursor: str | None = after) -> Any:
                return hs_client.crm.contacts.basic_api.get_page(
                    limit=100,
                    properties=properties,
                    after=cursor,
                )

            try:
                page = await asyncio.to_thread(_fetch_page)
            except Exception:
                logger.exception(
                    "HubSpot contact sync API error for user=%s", user_id
                )
                break

            for contact in page.results:
                try:
                    props = contact.properties or {}
                    firstname = props.get("firstname", "") or ""
                    lastname = props.get("lastname", "") or ""
                    name = f"{firstname} {lastname}".strip() or "Unknown"

                    hs_lifecycle = (
                        props.get("lifecyclestage", "") or ""
                    ).lower()
                    lifecycle_stage = self.LIFECYCLE_MAP.get(
                        hs_lifecycle, "lead"
                    )

                    row = {
                        "user_id": user_id,
                        "hubspot_contact_id": str(contact.id),
                        "name": name,
                        "email": props.get("email"),
                        "phone": props.get("phone"),
                        "company": props.get("company"),
                        "lifecycle_stage": lifecycle_stage,
                        "source": "import",
                        "metadata": {
                            "hubspot_properties": {
                                k: v
                                for k, v in props.items()
                                if k
                                not in {
                                    "email",
                                    "firstname",
                                    "lastname",
                                    "phone",
                                    "company",
                                }
                            },
                        },
                    }

                    await execute_async(
                        admin.client.table("contacts").upsert(
                            row,
                            on_conflict="user_id,hubspot_contact_id",
                        ),
                        op_name="hubspot.sync_contacts.upsert",
                    )
                    synced += 1
                except Exception:
                    logger.exception(
                        "Error syncing HubSpot contact %s", contact.id
                    )
                    errors += 1

            # Pagination
            if page.paging and page.paging.next and page.paging.next.after:
                after = page.paging.next.after
                # Respect HubSpot 190/10s rate limit
                await asyncio.sleep(0.5)
            else:
                break

        # Update sync state
        try:
            mgr = IntegrationManager()
            await mgr.update_sync_state(
                user_id=user_id,
                provider="hubspot",
                last_sync_at=datetime.now(tz=timezone.utc).isoformat(),
                error_count=0 if errors == 0 else errors,
            )
        except Exception:
            logger.warning("Failed to update HubSpot sync state")

        logger.info(
            "HubSpot contact sync: user=%s synced=%d errors=%d",
            user_id,
            synced,
            errors,
        )
        return {"synced": synced, "errors": errors}

    # ------------------------------------------------------------------
    # Deal sync: HubSpot -> Pikar
    # ------------------------------------------------------------------

    async def sync_deals(self, user_id: str) -> dict[str, Any]:
        """Import all HubSpot deals into the ``hubspot_deals`` table.

        Fetches deals with associations to contacts, then upserts into
        ``hubspot_deals`` using the ``(user_id, hubspot_deal_id)``
        composite unique constraint.

        Args:
            user_id: The owning user's UUID.

        Returns:
            ``{"synced": N}`` count.
        """
        hs_client = await self._get_client(user_id)
        admin = AdminService()

        properties = [
            "dealname",
            "pipeline",
            "dealstage",
            "amount",
            "closedate",
            "hs_lastmodifieddate",
        ]

        synced = 0
        after: str | None = None

        while True:
            def _fetch_deals(cursor: str | None = after) -> Any:
                return hs_client.crm.deals.basic_api.get_page(
                    limit=100,
                    properties=properties,
                    associations=["contacts"],
                    after=cursor,
                )

            try:
                page = await asyncio.to_thread(_fetch_deals)
            except Exception:
                logger.exception(
                    "HubSpot deal sync API error for user=%s", user_id
                )
                break

            for deal in page.results:
                try:
                    props = deal.properties or {}

                    # Parse amount
                    raw_amount = props.get("amount")
                    amount = float(raw_amount) if raw_amount else None

                    # Parse close date
                    close_date = props.get("closedate")

                    # Extract associated contact IDs
                    associated_contacts: list[str] = []
                    if (
                        deal.associations
                        and hasattr(deal.associations, "contacts")
                        and deal.associations.contacts
                    ):
                        for assoc in deal.associations.contacts.results:
                            associated_contacts.append(str(assoc.id))

                    # Look up Pikar contact UUIDs from hubspot_contact_id
                    pikar_contact_ids: list[str] = []
                    if associated_contacts:
                        result = await execute_async(
                            admin.client.table("contacts")
                            .select("id")
                            .eq("user_id", user_id)
                            .in_(
                                "hubspot_contact_id",
                                associated_contacts,
                            ),
                            op_name="hubspot.sync_deals.lookup_contacts",
                        )
                        if result.data:
                            pikar_contact_ids = [
                                r["id"] for r in result.data
                            ]

                    row = {
                        "user_id": user_id,
                        "hubspot_deal_id": str(deal.id),
                        "deal_name": props.get("dealname", "Untitled Deal"),
                        "pipeline": props.get("pipeline"),
                        "stage": props.get("dealstage"),
                        "amount": amount,
                        "close_date": close_date,
                        "associated_contacts": pikar_contact_ids,
                        "properties": {
                            k: v
                            for k, v in props.items()
                            if k
                            not in {
                                "dealname",
                                "pipeline",
                                "dealstage",
                                "amount",
                                "closedate",
                            }
                        },
                    }

                    await execute_async(
                        admin.client.table("hubspot_deals").upsert(
                            row,
                            on_conflict="user_id,hubspot_deal_id",
                        ),
                        op_name="hubspot.sync_deals.upsert",
                    )
                    synced += 1
                except Exception:
                    logger.exception(
                        "Error syncing HubSpot deal %s", deal.id
                    )

            # Pagination
            if page.paging and page.paging.next and page.paging.next.after:
                after = page.paging.next.after
                await asyncio.sleep(0.5)
            else:
                break

        logger.info(
            "HubSpot deal sync: user=%s synced=%d", user_id, synced
        )
        return {"synced": synced}

    # ------------------------------------------------------------------
    # Push: Pikar -> HubSpot
    # ------------------------------------------------------------------

    async def push_contact_to_hubspot(
        self, user_id: str, contact_id: str
    ) -> dict[str, Any]:
        """Push a Pikar contact to HubSpot (create or update).

        If the contact already has a ``hubspot_contact_id``, it is updated
        in HubSpot.  Otherwise a new HubSpot contact is created and the
        ``hubspot_contact_id`` is stored back.

        A Redis skip flag is set to prevent the webhook echo from
        triggering a re-import.

        Args:
            user_id: The owning user's UUID.
            contact_id: Pikar contact row UUID.

        Returns:
            Dict with ``hubspot_contact_id`` and ``action`` (created/updated).
        """
        hs_client = await self._get_client(user_id)
        admin = AdminService()

        # Read contact from Pikar DB
        result = await execute_async(
            admin.client.table("contacts")
            .select("*")
            .eq("id", contact_id)
            .eq("user_id", user_id),
            op_name="hubspot.push_contact.read",
        )
        if not result.data:
            raise ValueError(f"Contact {contact_id} not found")

        contact = result.data[0]
        name_parts = (contact.get("name") or "").split(" ", 1)
        firstname = name_parts[0] if name_parts else ""
        lastname = name_parts[1] if len(name_parts) > 1 else ""

        hs_properties = {
            "email": contact.get("email") or "",
            "firstname": firstname,
            "lastname": lastname,
            "phone": contact.get("phone") or "",
            "company": contact.get("company") or "",
        }

        hubspot_contact_id = contact.get("hubspot_contact_id")

        try:
            from hubspot.crm.contacts import (  # type: ignore[import-untyped]
                SimplePublicObjectInput,
            )
        except ImportError as exc:
            raise RuntimeError(
                "hubspot-api-client is not installed"
            ) from exc

        if hubspot_contact_id:
            # Update existing HubSpot contact
            def _update() -> Any:
                return hs_client.crm.contacts.basic_api.update(
                    contact_id=hubspot_contact_id,
                    simple_public_object_input=SimplePublicObjectInput(
                        properties=hs_properties,
                    ),
                )

            await asyncio.to_thread(_update)
            await self._set_skip_flag(hubspot_contact_id)

            logger.info(
                "Updated HubSpot contact %s for user %s",
                hubspot_contact_id,
                user_id,
            )
            return {
                "hubspot_contact_id": hubspot_contact_id,
                "action": "updated",
            }
        else:
            # Create new HubSpot contact
            def _create() -> Any:
                return hs_client.crm.contacts.basic_api.create(
                    simple_public_object_input=SimplePublicObjectInput(
                        properties=hs_properties,
                    ),
                )

            created = await asyncio.to_thread(_create)
            new_hs_id = str(created.id)

            # Store the new hubspot_contact_id back in Pikar
            await execute_async(
                admin.client.table("contacts")
                .update({"hubspot_contact_id": new_hs_id})
                .eq("id", contact_id),
                op_name="hubspot.push_contact.store_hs_id",
            )

            await self._set_skip_flag(new_hs_id)

            logger.info(
                "Created HubSpot contact %s for user %s",
                new_hs_id,
                user_id,
            )
            return {
                "hubspot_contact_id": new_hs_id,
                "action": "created",
            }

    async def push_deal_to_hubspot(
        self,
        user_id: str,
        deal_id: str,
        properties: dict[str, Any],
    ) -> dict[str, Any]:
        """Push deal property updates from Pikar to HubSpot.

        Reads the deal from ``hubspot_deals``, pushes the supplied
        properties to HubSpot, and sets a Redis skip flag.

        Args:
            user_id: The owning user's UUID.
            deal_id: Pikar ``hubspot_deals`` row UUID.
            properties: Dict of HubSpot deal properties to update.

        Returns:
            Dict with ``hubspot_deal_id`` and ``status``.
        """
        hs_client = await self._get_client(user_id)
        admin = AdminService()

        result = await execute_async(
            admin.client.table("hubspot_deals")
            .select("hubspot_deal_id")
            .eq("id", deal_id)
            .eq("user_id", user_id),
            op_name="hubspot.push_deal.read",
        )
        if not result.data:
            raise ValueError(f"Deal {deal_id} not found")

        hubspot_deal_id = result.data[0]["hubspot_deal_id"]

        try:
            from hubspot.crm.deals import (  # type: ignore[import-untyped]
                SimplePublicObjectInput,
            )
        except ImportError as exc:
            raise RuntimeError(
                "hubspot-api-client is not installed"
            ) from exc

        def _update() -> Any:
            return hs_client.crm.deals.basic_api.update(
                deal_id=hubspot_deal_id,
                simple_public_object_input=SimplePublicObjectInput(
                    properties=properties,
                ),
            )

        await asyncio.to_thread(_update)
        await self._set_skip_flag(hubspot_deal_id)

        logger.info(
            "Pushed deal %s to HubSpot for user %s",
            hubspot_deal_id,
            user_id,
        )
        return {
            "hubspot_deal_id": hubspot_deal_id,
            "status": "updated",
        }

    # ------------------------------------------------------------------
    # CRM-aware deal context (for agent responses)
    # ------------------------------------------------------------------

    async def get_deal_context(
        self, user_id: str, contact_name_or_id: str
    ) -> dict[str, Any]:
        """Get deal context for a contact (for CRM-aware agent responses).

        Searches contacts by name or email, finds associated deals, and
        returns a summary suitable for agent tool responses.

        Args:
            user_id: The owning user's UUID.
            contact_name_or_id: Contact name, email, or UUID to search.

        Returns:
            Dict with ``contact``, ``deals``, and ``summary`` keys.
        """
        admin = AdminService()

        # Search by name, email, or id
        contact_result = await execute_async(
            admin.client.table("contacts")
            .select("id, name, email, company, lifecycle_stage, hubspot_contact_id")
            .eq("user_id", user_id)
            .or_(
                f"name.ilike.%{contact_name_or_id}%,"
                f"email.ilike.%{contact_name_or_id}%,"
                f"id.eq.{contact_name_or_id}"
            )
            .limit(1),
            op_name="hubspot.deal_context.find_contact",
        )
        if not contact_result.data:
            return {
                "contact": None,
                "deals": [],
                "summary": f"No contact found matching '{contact_name_or_id}'",
            }

        contact = contact_result.data[0]
        contact_uuid = contact["id"]

        # Find deals associated with this contact
        deals_result = await execute_async(
            admin.client.table("hubspot_deals")
            .select("*")
            .eq("user_id", user_id)
            .contains("associated_contacts", [contact_uuid]),
            op_name="hubspot.deal_context.find_deals",
        )
        deals = deals_result.data or []

        # Build summary
        if deals:
            deal_summaries = []
            for d in deals:
                amount_str = f"${d['amount']:,.2f}" if d.get("amount") else "TBD"
                deal_summaries.append(
                    f"- {d['deal_name']}: {d.get('stage', 'unknown')} stage, "
                    f"{amount_str}, pipeline: {d.get('pipeline', 'default')}"
                )
            summary = (
                f"{contact['name']} ({contact.get('email', 'no email')}) "
                f"at {contact.get('company', 'unknown company')} - "
                f"{contact.get('lifecycle_stage', 'lead')} stage. "
                f"{len(deals)} deal(s):\n" + "\n".join(deal_summaries)
            )
        else:
            summary = (
                f"{contact['name']} ({contact.get('email', 'no email')}) "
                f"at {contact.get('company', 'unknown company')} - "
                f"{contact.get('lifecycle_stage', 'lead')} stage. "
                "No associated deals."
            )

        return {
            "contact": contact,
            "deals": deals,
            "summary": summary,
        }

    # ------------------------------------------------------------------
    # Search contacts via HubSpot API
    # ------------------------------------------------------------------

    async def search_contacts(
        self, user_id: str, query: str
    ) -> list[dict[str, Any]]:
        """Search HubSpot contacts by name, email, or company.

        Uses the HubSpot search API (CRM v3) for server-side filtering.

        Args:
            user_id: The owning user's UUID.
            query: Search string (matched against name, email, company).

        Returns:
            List of matching contact dicts with key properties.
        """
        hs_client = await self._get_client(user_id)

        try:
            from hubspot.crm.contacts import (  # type: ignore[import-untyped]
                Filter,
                FilterGroup,
                PublicObjectSearchRequest,
            )
        except ImportError as exc:
            raise RuntimeError(
                "hubspot-api-client is not installed"
            ) from exc

        # Search across email, firstname, lastname, company
        filter_groups = [
            FilterGroup(
                filters=[
                    Filter(
                        property_name=prop,
                        operator="CONTAINS_TOKEN",
                        value=f"*{query}*",
                    )
                ]
            )
            for prop in ["email", "firstname", "lastname", "company"]
        ]

        search_request = PublicObjectSearchRequest(
            filter_groups=filter_groups,
            properties=[
                "email",
                "firstname",
                "lastname",
                "phone",
                "company",
                "lifecyclestage",
            ],
            limit=20,
        )

        def _search() -> Any:
            return hs_client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request,
            )

        try:
            result = await asyncio.to_thread(_search)
        except Exception:
            logger.exception(
                "HubSpot contact search error for user=%s query=%s",
                user_id,
                query,
            )
            return []

        contacts = []
        for contact in result.results:
            props = contact.properties or {}
            contacts.append({
                "hubspot_id": str(contact.id),
                "email": props.get("email"),
                "name": (
                    f"{props.get('firstname', '')} "
                    f"{props.get('lastname', '')}"
                ).strip(),
                "phone": props.get("phone"),
                "company": props.get("company"),
                "lifecycle_stage": props.get("lifecyclestage"),
            })

        return contacts

    # ------------------------------------------------------------------
    # Webhook handlers
    # ------------------------------------------------------------------

    async def handle_contact_webhook(
        self, user_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Process a HubSpot contact webhook event.

        Handles ``contact.creation`` and ``contact.propertyChange``
        subscription types.  Checks the Redis skip flag to avoid
        processing our own echo.

        For ``propertyChange``, compares ``hs_lastmodifieddate`` for
        conflict detection.  Uses last-write-wins strategy per user
        decision (logged but not blocked).

        Args:
            user_id: Resolved owning user's UUID.
            payload: Single HubSpot webhook event dict.

        Returns:
            ``{"status": "processed"|"skipped", ...}``
        """
        object_id = str(payload.get("objectId", ""))
        subscription_type = payload.get("subscriptionType", "")

        # Check skip flag (our own echo)
        if await self._check_skip_flag(object_id):
            logger.info(
                "Skipping HubSpot contact webhook (own echo): %s",
                object_id,
            )
            return {"status": "skipped", "reason": "own_echo"}

        admin = AdminService()

        if subscription_type in ("contact.creation", "contact.propertyChange"):
            # Fetch full contact from HubSpot API to get all properties
            hs_client = await self._get_client(user_id)

            def _get_contact() -> Any:
                return hs_client.crm.contacts.basic_api.get_by_id(
                    contact_id=object_id,
                    properties=[
                        "email",
                        "firstname",
                        "lastname",
                        "phone",
                        "company",
                        "lifecyclestage",
                        "hs_lastmodifieddate",
                    ],
                )

            try:
                hs_contact = await asyncio.to_thread(_get_contact)
            except Exception:
                logger.exception(
                    "Failed to fetch HubSpot contact %s", object_id
                )
                return {"status": "error", "reason": "fetch_failed"}

            props = hs_contact.properties or {}
            firstname = props.get("firstname", "") or ""
            lastname = props.get("lastname", "") or ""
            name = f"{firstname} {lastname}".strip() or "Unknown"

            hs_lifecycle = (
                props.get("lifecyclestage", "") or ""
            ).lower()
            lifecycle_stage = self.LIFECYCLE_MAP.get(
                hs_lifecycle, "lead"
            )

            # Conflict detection: log if both sides modified recently
            if subscription_type == "contact.propertyChange":
                existing = await execute_async(
                    admin.client.table("contacts")
                    .select("updated_at")
                    .eq("user_id", user_id)
                    .eq("hubspot_contact_id", object_id)
                    .limit(1),
                    op_name="hubspot.webhook.contact.conflict_check",
                )
                if existing.data:
                    logger.info(
                        "HubSpot contact %s propertyChange: "
                        "applying last-write-wins (Pikar updated_at=%s)",
                        object_id,
                        existing.data[0].get("updated_at"),
                    )

            row = {
                "user_id": user_id,
                "hubspot_contact_id": object_id,
                "name": name,
                "email": props.get("email"),
                "phone": props.get("phone"),
                "company": props.get("company"),
                "lifecycle_stage": lifecycle_stage,
                "source": "import",
                "metadata": {
                    "hubspot_properties": {
                        k: v
                        for k, v in props.items()
                        if k
                        not in {
                            "email",
                            "firstname",
                            "lastname",
                            "phone",
                            "company",
                        }
                    },
                },
            }

            await execute_async(
                admin.client.table("contacts").upsert(
                    row,
                    on_conflict="user_id,hubspot_contact_id",
                ),
                op_name="hubspot.webhook.contact.upsert",
            )

            logger.info(
                "Webhook: processed HubSpot contact %s (%s) for user %s",
                object_id,
                subscription_type,
                user_id,
            )
            return {"status": "processed", "contact_id": object_id}

        logger.info(
            "HubSpot contact webhook: unhandled type %s",
            subscription_type,
        )
        return {"status": "ignored", "subscription_type": subscription_type}

    async def handle_deal_webhook(
        self, user_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Process a HubSpot deal webhook event.

        Handles ``deal.creation`` and ``deal.propertyChange``
        subscription types with the same skip-flag and
        last-write-wins patterns as contact webhooks.

        Args:
            user_id: Resolved owning user's UUID.
            payload: Single HubSpot webhook event dict.

        Returns:
            ``{"status": "processed"|"skipped", ...}``
        """
        object_id = str(payload.get("objectId", ""))
        subscription_type = payload.get("subscriptionType", "")

        # Check skip flag (our own echo)
        if await self._check_skip_flag(object_id):
            logger.info(
                "Skipping HubSpot deal webhook (own echo): %s",
                object_id,
            )
            return {"status": "skipped", "reason": "own_echo"}

        admin = AdminService()

        if subscription_type in ("deal.creation", "deal.propertyChange"):
            hs_client = await self._get_client(user_id)

            def _get_deal() -> Any:
                return hs_client.crm.deals.basic_api.get_by_id(
                    deal_id=object_id,
                    properties=[
                        "dealname",
                        "pipeline",
                        "dealstage",
                        "amount",
                        "closedate",
                        "hs_lastmodifieddate",
                    ],
                )

            try:
                hs_deal = await asyncio.to_thread(_get_deal)
            except Exception:
                logger.exception(
                    "Failed to fetch HubSpot deal %s", object_id
                )
                return {"status": "error", "reason": "fetch_failed"}

            props = hs_deal.properties or {}
            raw_amount = props.get("amount")
            amount = float(raw_amount) if raw_amount else None

            row = {
                "user_id": user_id,
                "hubspot_deal_id": object_id,
                "deal_name": props.get("dealname", "Untitled Deal"),
                "pipeline": props.get("pipeline"),
                "stage": props.get("dealstage"),
                "amount": amount,
                "close_date": props.get("closedate"),
                "properties": {
                    k: v
                    for k, v in props.items()
                    if k
                    not in {
                        "dealname",
                        "pipeline",
                        "dealstage",
                        "amount",
                        "closedate",
                    }
                },
            }

            await execute_async(
                admin.client.table("hubspot_deals").upsert(
                    row,
                    on_conflict="user_id,hubspot_deal_id",
                ),
                op_name="hubspot.webhook.deal.upsert",
            )

            logger.info(
                "Webhook: processed HubSpot deal %s (%s) for user %s",
                object_id,
                subscription_type,
                user_id,
            )
            return {"status": "processed", "deal_id": object_id}

        logger.info(
            "HubSpot deal webhook: unhandled type %s",
            subscription_type,
        )
        return {"status": "ignored", "subscription_type": subscription_type}


__all__ = ["HubSpotService"]
