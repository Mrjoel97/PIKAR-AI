import type { ActionCtx, MutationCtx, QueryCtx } from "./_generated/server";

type AnyCtx = QueryCtx | MutationCtx | ActionCtx;

// Update typing so the wrapper preserves the exact ctx and args types per handler
export function withErrorHandling<F extends (ctx: any, args: any) => Promise<any>>(fn: F): F {
  return (async (ctx, args) => {
    try {
      return await fn(ctx as any, args as any);
    } catch (err: unknown) {
      const errorObj =
        err instanceof Error
          ? { name: err.name, message: err.message, stack: err.stack }
          : { message: String(err) };

      console.error("[ConvexError]", {
        handler: fn.name || "anonymous",
        args,
        error: errorObj,
      });
      throw err instanceof Error ? err : new Error("Internal error");
    }
  }) as F;
}