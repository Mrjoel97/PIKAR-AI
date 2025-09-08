import { cronJobs } from "convex/server";
import { internal } from "./_generated/api";

const crons = cronJobs();

// Run SLA checks every 15 minutes
crons.interval(
  "sla-checks",
  { minutes: 15 },
  internal.workflowAssignments.checkSLAWarnings
);

// Run approval SLA checks every 30 minutes
crons.interval(
  "approval-sla-checks", 
  { minutes: 30 },
  internal.approvals.checkApprovalSLABreaches
);

// Clean up expired notifications daily at 2 AM
crons.daily(
  "cleanup-notifications",
  { hourUTC: 2, minuteUTC: 0 },
  internal.notifications.cleanupExpiredNotifications
);

// Clean up old telemetry events weekly on Sunday at 3 AM
crons.weekly(
  "cleanup-telemetry",
  { dayOfWeek: "sunday", hourUTC: 3, minuteUTC: 0 },
  internal.init.cleanupOldTelemetryEvents
);

export default crons;