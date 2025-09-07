/* eslint-disable */
/**
 * Generated `api` utility.
 *
 * THIS CODE IS AUTOMATICALLY GENERATED.
 *
 * To regenerate, run `npx convex dev`.
 * @module
 */

import type {
  ApiFromModules,
  FilterApi,
  FunctionReference,
} from "convex/server";
import type * as aiAgents from "../aiAgents.js";
import type * as auth_emailOtp from "../auth/emailOtp.js";
import type * as auth from "../auth.js";
import type * as businesses from "../businesses.js";
import type * as diagnostics from "../diagnostics.js";
import type * as http from "../http.js";
import type * as initiatives from "../initiatives.js";
import type * as openai from "../openai.js";
import type * as seed from "../seed.js";
import type * as users from "../users.js";
import type * as utils from "../utils.js";
import type * as workflows from "../workflows.js";

/**
 * A utility for referencing Convex functions in your app's API.
 *
 * Usage:
 * ```js
 * const myFunctionReference = api.myModule.myFunction;
 * ```
 */
declare const fullApi: ApiFromModules<{
  aiAgents: typeof aiAgents;
  "auth/emailOtp": typeof auth_emailOtp;
  auth: typeof auth;
  businesses: typeof businesses;
  diagnostics: typeof diagnostics;
  http: typeof http;
  initiatives: typeof initiatives;
  openai: typeof openai;
  seed: typeof seed;
  users: typeof users;
  utils: typeof utils;
  workflows: typeof workflows;
}>;
export declare const api: FilterApi<
  typeof fullApi,
  FunctionReference<any, "public">
>;
export declare const internal: FilterApi<
  typeof fullApi,
  FunctionReference<any, "internal">
>;
