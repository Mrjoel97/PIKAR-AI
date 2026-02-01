# Sections

This file defines all sections, their ordering, impact levels, and descriptions.
The section ID (in parentheses) is the filename prefix used to group rules.

---

## 1. Row Level Security (rls)

**Impact:** CRITICAL
**Description:** RLS is the foundation of Supabase security. Properly configured policies ensure data isolation and prevent unauthorized access at the database level. Performance optimizations in RLS policies can yield 99%+ improvements.

## 2. Clerk Integration (clerk)

**Impact:** CRITICAL
**Description:** Secure integration patterns for Clerk authentication with Supabase. Uses Third-Party Auth for asymmetric key validation instead of deprecated JWT templates that share secrets.

## 3. Database Security (db)

**Impact:** HIGH
**Description:** Schema design patterns, migration best practices, and database-level security configurations that prevent data leaks and ensure data integrity.

## 4. Authentication Patterns (auth)

**Impact:** HIGH
**Description:** JWT handling, claims validation, and proper use of user_metadata vs app_metadata for secure authentication flows.

## 5. API Security (api)

**Impact:** HIGH
**Description:** Proper key management, query filtering, and ensuring service role keys never reach client code.

## 6. Storage Security (storage)

**Impact:** MEDIUM-HIGH
**Description:** Bucket configuration, object-level RLS policies, and secure file access patterns using signed URLs.

## 7. Realtime Security (realtime)

**Impact:** MEDIUM
**Description:** Channel authorization, RLS integration with realtime subscriptions, and proper subscription lifecycle management.

## 8. Edge Functions (edge)

**Impact:** MEDIUM
**Description:** JWT verification, CORS handling, and secrets management for serverless functions running at the edge.

## 9. Testing (test)

**Impact:** MEDIUM
**Description:** pgTAP testing patterns for RLS policies, test isolation strategies, and helper functions for comprehensive security testing.

## 10. Performance (perf)

**Impact:** LOW-MEDIUM
**Description:** Query optimization, connection pooling, and caching strategies specific to Supabase infrastructure.
