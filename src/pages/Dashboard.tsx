import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";
import { useQuery, useMutation, useAction } from "convex/react";
import { motion } from "framer-motion";
import { 
  Bot, 
  BarChart3, 
  Target, 
  Users, 
  Plus,
  Settings,
  TrendingUp,
  Activity,
  Zap,
  LogOut,
  Workflow,
  Eye,
  ArrowUp,
  ArrowDown,
  Pause,
  RotateCcw
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { useNavigate } from "react-router";
import { useLocation } from "react-router";
import { useEffect, useState, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Play } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import {
  SidebarProvider,
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInput,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
  SidebarTrigger,
} from "@/components/ui/sidebar";
import { Home, Layers, Bot as BotIcon, Workflow as WorkflowIcon, Settings as SettingsIcon } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Search } from "lucide-react";
import { Slider } from "@/components/ui/slider";

// ... keep existing code (types local to this file)
type Business = {
  _id: string;
  name: string;
  tier: "solopreneur" | "startup" | "sme" | "enterprise";
  industry: string;
};

// Add: Quality & Compliance types
type Incident = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  severity: "low" | "medium" | "high" | "critical";
  category?: string;
  status?: "open" | "investigating" | "resolved";
  reportedBy?: string;
  createdAt?: number;
};

type Risk = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  score?: number;
  owner?: string;
  status?: "open" | "mitigating" | "closed";
};

type Nonconformity = {
  _id: string;
  businessId: string;
  title: string;
  description?: string;
  severity?: "low" | "medium" | "high" | "critical";
  status?: "open" | "investigating" | "resolved";
};

type Sop = {
  _id: string;
  businessId: string;
  name: string;
  version?: string;
  url?: string;
};

type ComplianceCheck = {
  _id: string;
  businessId: string;
  subject?: string;
  status?: "pass" | "fail" | "warning";
  issues?: Array<{ code: string; message: string }>;
  createdAt?: number;
};

type AuditLog = {
  _id: string;
  businessId: string;
  action: string;
  actor?: string;
  metadata?: any;
  createdAt?: number;
};

type Initiative = {
  _id: string;
  title: string;
  status: "draft" | "active" | "paused" | "completed";
  priority: "low" | "medium" | "high" | "urgent";
  metrics: { targetROI: number; currentROI: number; completionRate: number };
};

type Agent = {
  _id: string;
  name: string;
  type: string;
  isActive: boolean;
};

type Workflow = {
  _id: string;
  name: string;
  description: string;
  isActive: boolean;
  // stats from listWorkflows
  runCount?: number;
  completedRuns?: number;
  lastRunStatus?: string | null;
};

// Add: MMRPolicy type
type MMRPolicy = {
  sensitive: number; // % human review for sensitive content
  drafts: number;    // % human review for drafts
  default: number;   // % human review default
  notes?: string;
};

// Add: Objective type
type Objective = {
  id: string;
  title: string;
  timeframe: "Q1" | "Q2" | "Q3" | "Q4" | "This Month" | "This Quarter" | "This Year";
  createdAt: number;
  progress?: number; // aggregate from KRs later
};

// Add: SnapTask type
type SnapTask = {
  id: string;
  title: string;
  priority: number; // higher = more important (S.N.A.P normalized)
  due?: number | null;
  status: "todo" | "done";
  createdAt: number;
};

// Add: InitiativeFeedback type
type InitiativeFeedback = {
  id: string;
  initiativeId: string;
  phase: "Discovery" | "Planning" | "Build" | "Test" | "Launch";
  note: string;
  createdAt: number;
};

// Add: Initiative Journey phases model (Phase 0–6)
const journeyPhases: Array<{
  id: number;
  title: string;
  description: string;
  actions: Array<{ label: string; onClick: () => void }>;
}> = [
  {
    id: 0,
    title: "Onboarding",
    description:
      "Define industry, model, goals. Connect social, email, e‑commerce, finance to tailor your setup.",
    actions: [
      { label: "Guided Onboarding", onClick: () => navigate("/onboarding") },
    ],
  },
  {
    id: 1,
    title: "Discovery",
    description:
      "Analyze current signals (web/social). Clarify target customers via quick surveys & link to Strategy.",
    actions: [
      { label: "Open Analytics", onClick: () => navigate("/analytics") },
      {
        label: "Strategy Agent",
        onClick: () => navigate("/ai-agents"),
      },
    ],
  },
  {
    id: 2,
    title: "Planning & Design",
    description:
      "Auto-draft strategy from Discovery. Mind‑map ideas. Add DTFL checkpoints and test assumptions.",
    actions: [
      { label: "SNAP Tasks", onClick: () => scrollToSection("tasks-section") },
      { label: "OKRs", onClick: () => scrollToSection("okrs-section") },
    ],
  },
  {
    id: 3,
    title: "Foundation",
    description:
      "Baseline setup: social accounts, email domain, brand assets, CRM & payments. Check SEO readiness.",
    actions: [
      { label: "Onboarding Checks", onClick: () => navigate("/onboarding") },
      { label: "Open Workflows", onClick: () => navigate("/workflows") },
    ],
  },
  {
    id: 4,
    title: "Execution",
    description:
      "Run campaigns with Orchestrate. Get live status and assign tasks. Human review via MMR.",
    actions: [
      { label: "Orchestrate", onClick: () => navigate("/workflows") },
      { label: "MMR Settings", onClick: () => scrollToSection("mmr-section") },
    ],
  },
  {
    id: 5,
    title: "Scale",
    description:
      "Duplicate winners for new markets, translate content, and simulate network effects.",
    actions: [
      { label: "Workflows", onClick: () => navigate("/workflows") },
      { label: "Analytics", onClick: () => navigate("/analytics") },
    ],
  },
  {
    id: 6,
    title: "Sustainability",
    description:
      "Continuous improvement: track metrics, schedule QMS audits, and log learnings in KnowledgeHub.",
    actions: [
      { label: "Compliance", onClick: () => scrollToSection("compliance-section") },
      { label: "OKRs", onClick: () => scrollToSection("okrs-section") },
    ],
  },
];

export default function Dashboard() {
  // local helpers to avoid undefined references and keep things simple
  const navigate = (path: string) => {
    window.location.href = path;
  };
  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  // Add navigate for programmatic routing
  const navigate = useNavigate();
  const { isLoading: authLoading, isAuthenticated, user, signIn, signOut } = useAuth();
  const [signOutOpen, setSignOutOpen] = useState(false);

  // Add: Report Incident dialog state
  const [reportOpen, setReportOpen] = useState(false);
  // Add: severity selection state for Report Incident
  const [severity, setSeverity] = useState<Incident["severity"]>("low");

  const userBusinesses = useQuery(api.businesses.getUserBusinesses, {});
  const [selectedBusinessId, setSelectedBusinessId] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [workflowSearch, setWorkflowSearch] = useState("");
  const [workflowsTab, setWorkflowsTab] = useState<"all" | "templates">("all");

  // Voice Brain Dump state (solopreneur feature)
  const [isRecording, setIsRecording] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [voiceReply, setVoiceReply] = useState("");
  const recognitionRef = useRef<any>(null);

  // Add: audio recording refs and sessions state
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Array<Blob>>([]);
  // Add: recording timing & cleanup
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const recordTimerRef = useRef<number | null>(null);
  // Add: start time ref to fix undefined reference
  const recordStartAtRef = useRef<number | null>(null);
  const MAX_RECORD_SECONDS = 5 * 60; // 5 minutes hard stop

  type VoiceSession = {
    id: string;
    createdAt: number;
    transcript: string;
    audioDataUrl?: string; // base64 data URL for playback/persistence
  };
  const [sessions, setSessions] = useState<Array<VoiceSession>>([]);

  // Add: load sessions from localStorage on mount
  useEffect(() => {
    try {
      const raw = localStorage.getItem("voice_sessions_v1");
      if (raw) {
        const parsed = JSON.parse(raw) as Array<VoiceSession>;
        setSessions(parsed.sort((a, b) => b.createdAt - a.createdAt));
      }
    } catch {
      // If corrupted, clear
      localStorage.removeItem("voice_sessions_v1");
    }
  }, []);

  // Add: persist sessions whenever changed
  useEffect(() => {
    try {
      localStorage.setItem("voice_sessions_v1", JSON.stringify(sessions));
    } catch (e) {
      // storage may fail (quota/private mode)
    }
  }, [sessions]);

  // Cleanup on unmount to avoid dangling media/recognition
  useEffect(() => {
    return () => {
      try {
        if (recognitionRef.current?.stop) recognitionRef.current.stop();
      } catch {}
      try {
        const mr = mediaRecorderRef.current;
        if (mr && mr.state !== "inactive") mr.stop();
      } catch {}
      if (recordTimerRef.current) {
        window.clearInterval(recordTimerRef.current);
        recordTimerRef.current = null;
      }
    };
  }, []);

  // Dashboard tier override (preview different tier dashboards)
  const [tierOverride, setTierOverride] = useState<Business["tier"] | null>(null);
  const [switcherOpen, setSwitcherOpen] = useState(false);

  // Initialize tier override from URL or localStorage
  useEffect(() => {
    try {
      const url = new URL(window.location.href);
      const tierParam = url.searchParams.get("tier");
      const allowed = new Set<Business["tier"]>(["solopreneur", "startup", "sme", "enterprise"]);
      if (tierParam && allowed.has(tierParam as Business["tier"])) {
        setTierOverride(tierParam as Business["tier"]);
        localStorage.setItem("dashboard_tier_override", tierParam);
      } else {
        const stored = localStorage.getItem("dashboard_tier_override") as Business["tier"] | null;
        if (stored && allowed.has(stored)) {
          setTierOverride(stored);
        }
      }
    } catch {
      // ignore
    }
  }, []);

  // Helper: save a session
  const saveSession = (transcript: string, audioBlob?: Blob) => {
    const id = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    const createdAt = Date.now();

    const addSession = (audioDataUrl?: string) => {
      const next: VoiceSession = { id, createdAt, transcript, audioDataUrl };
      setSessions((prev) => [next, ...prev]);
      toast("Saved voice session.");
    };

    if (audioBlob) {
      const reader = new FileReader();
      reader.onloadend = () => addSession(reader.result as string);
      reader.onerror = () => {
        toast("Saved transcript, but audio failed to save.");
        addSession(undefined);
      };
      reader.readAsDataURL(audioBlob);
    } else {
      addSession(undefined);
    }
  };

  // Start voice capture
  const startVoiceDump = async () => {
    try {
      // Guard: browser support checks
      if (!("mediaDevices" in navigator) || !navigator.mediaDevices?.getUserMedia) {
        toast("Microphone not supported in this browser.");
        return;
      }

      let stream: MediaStream | null = null;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch {
        toast("Microphone access denied. Please enable mic permissions.");
        return;
      }

      // Setup MediaRecorder (audio capture) if available
      audioChunksRef.current = [];
      try {
        if (typeof MediaRecorder === "undefined") {
          toast("Audio recording not supported. Only transcript will be saved.");
        } else {
          const mr = new MediaRecorder(stream);
          mediaRecorderRef.current = mr;
          mr.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) audioChunksRef.current.push(e.data);
          };
          mr.onerror = () => {
            toast("Audio recorder error. Only transcript will be saved.");
          };
          mr.start();
        }
      } catch {
        toast("Audio recording failed. Only transcript will be saved.");
      }

      // Setup speech recognition (transcript)
      const SR = (window as any).webkitSpeechRecognition;
      if (!SR) {
        toast("Voice not supported on this browser. Try Chrome.");
        setIsRecording(false);
        try {
          // stop audio tracks if we started them
          stream?.getTracks().forEach((t) => t.stop());
        } catch {}
        return;
      }
      const rec = new SR();
      rec.continuous = true;
      rec.interimResults = true;
      rec.lang = "en-US";

      let interimText = "";
      rec.onresult = (e: any) => {
        try {
          let finalText = "";
          for (let i = e.resultIndex; i < e.results.length; i++) {
            const chunk = e.results[i][0].transcript;
            finalText += chunk;
          }
          interimText = finalText;
          setVoiceTranscript(finalText.trim());
        } catch {
          // swallow parse errors
        }
      };
      rec.onerror = (e: any) => {
        toast(e?.error === "no-speech" ? "No speech detected." : (e?.error || "Voice capture error"));
        setIsRecording(false);
        try {
          mediaRecorderRef.current?.stop();
        } catch {}
        try {
          stream?.getTracks().forEach((t) => t.stop());
        } catch {}
        if (recordTimerRef.current) {
          window.clearInterval(recordTimerRef.current);
          recordTimerRef.current = null;
        }
      };
      rec.onend = async () => {
        // Recognition stopped (user or system)
        setIsRecording(false);
        if (recordTimerRef.current) {
          window.clearInterval(recordTimerRef.current);
          recordTimerRef.current = null;
        }
        setElapsedSeconds(0);
        // Stop audio and save session
        let audioBlob: Blob | undefined;
        try {
          const mr = mediaRecorderRef.current;
          if (mr && mr.state !== "inactive") {
            await new Promise<void>((resolve) => {
              const handleStop = () => resolve();
              mr.addEventListener("stop", handleStop, { once: true });
              mr.stop();
            });
          }
          if (audioChunksRef.current.length > 0) {
            audioBlob = new Blob(audioChunksRef.current, { type: "audio/webm" });
          }
          // stop all tracks on stream
          stream?.getTracks().forEach((t) => t.stop());
        } catch {
          // ignore
        }
        const finalText = (voiceTranscript || interimText || "").trim();
        if (finalText) {
          saveSession(finalText, audioBlob);
        }
      };

      recognitionRef.current = rec;
      rec.start();
      setIsRecording(true);
      setVoiceReply("");
      // Start timer
      recordStartAtRef.current = Date.now();
      setElapsedSeconds(0);
      if (recordTimerRef.current) {
        window.clearInterval(recordTimerRef.current);
        recordTimerRef.current = null;
      }
      recordTimerRef.current = window.setInterval(() => {
        const started = recordStartAtRef.current ?? Date.now();
        const elapsed = Math.floor((Date.now() - started) / 1000);
        setElapsedSeconds(elapsed);
        if (elapsed >= MAX_RECORD_SECONDS) {
          toast("Auto-stopped after 5 minutes.");
          try {
            recognitionRef.current?.stop?.();
          } catch {}
        }
      }, 1000);
    } catch (e: any) {
      toast(e?.message || "Failed to start recording");
      setIsRecording(false);
      try {
        mediaRecorderRef.current?.stop();
      } catch {}
      if (recordTimerRef.current) {
        window.clearInterval(recordTimerRef.current);
        recordTimerRef.current = null;
      }
    }
  };

  // Stop voice capture
  const stopVoiceDump = () => {
    try {
      recognitionRef.current?.stop?.();
      // Safety: also stop recorder & tracks if recognition fails to fire onend
      try {
        const mr = mediaRecorderRef.current;
        if (mr && mr.state !== "inactive") mr.stop();
      } catch {}
      if (recordTimerRef.current) {
        window.clearInterval(recordTimerRef.current);
        recordTimerRef.current = null;
      }
      setIsRecording(false);
    } catch {
      toast("Failed to stop. Try again.");
    }
  };

  // Simple client-side AI tip generator
  const analyzeVoiceDump = () => {
    const text = voiceTranscript.trim();
    if (!text) {
      toast("Record or type something first.");
      return;
    }
    const lower = text.toLowerCase();
    const reply =
      lower.includes("brand") || lower.includes("audience")
        ? "Brand tip: Define a 1‑liner value prop, outline 3 audience segments, and create a weekly content cadence (2 long, 5 short)."
        : lower.includes("cash") || lower.includes("pricing")
        ? "Cash flow tip: Offer a 3‑tier plan, annual at 15% discount, and a founder plan for early adopters. Track MRR, churn, CAC payback."
        : lower.includes("product") || lower.includes("mvp")
        ? "MVP tip: Ship a single outcome. Measure activation → retention in 2-week cohorts. Add 1 automation that saves >30 min/week."
        : "Execution tip: Prioritize 3 outcomes this week. Timebox to 90‑minute sprints. Review metrics every Friday and iterate.";
    setVoiceReply(reply);
    toast("AI insight generated.");
  };

  // Add: utilities for sessions
  const downloadText = (s: VoiceSession) => {
    try {
      const blob = new Blob([s.transcript], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const date = new Date(s.createdAt).toISOString().slice(0, 19).replace(/[:T]/g, "-");
      a.download = `voice-session-${date}.txt`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast("Failed to download transcript.");
    }
  };

  const reuseTranscript = (s: VoiceSession) => {
    setVoiceTranscript(s.transcript);
    toast("Transcript loaded.");
  };

  const deleteSession = (id: string) => {
    setSessions((prev) => prev.filter((x) => x.id !== id));
    toast("Session deleted.");
  };

  // Local keys helper
  const storageKey = (k: string) => {
    const biz = selectedBusinessId || "global";
    return `${k}_v1_${biz}`;
  };

  // MMR policy state
  const [mmr, setMmr] = useState<MMRPolicy>({ sensitive: 100, drafts: 20, default: 30, notes: "" });
  // OKR state
  const [okrs, setOkrs] = useState<Array<Objective>>([]);
  const [newOkrTitle, setNewOkrTitle] = useState("");
  const [newOkrTimeframe, setNewOkrTimeframe] = useState<Objective["timeframe"]>("This Quarter");
  // SNAP tasks
  const [tasks, setTasks] = useState<Array<SnapTask>>([]);
  const [newTaskTitle, setNewTaskTitle] = useState("");
  const [newTaskPriority, setNewTaskPriority] = useState<number>(80);
  // DTFL feedback dialog
  const [feedbackOpen, setFeedbackOpen] = useState(false);
  const [feedbackPhase, setFeedbackPhase] = useState<InitiativeFeedback["phase"]>("Discovery");
  const [feedbackNote, setFeedbackNote] = useState("");
  const [feedbackInitId, setFeedbackInitId] = useState<string | null>(null);

  // Load per-business local data
  useEffect(() => {
    try {
      const mmrRaw = localStorage.getItem(storageKey("mmr_policy"));
      if (mmrRaw) setMmr({ ...mmr, ...(JSON.parse(mmrRaw) as MMRPolicy) });
    } catch {}
    try {
      const okrRaw = localStorage.getItem(storageKey("okrs"));
      if (okrRaw) setOkrs(JSON.parse(okrRaw) as Array<Objective>);
    } catch {}
    try {
      const taskRaw = localStorage.getItem(storageKey("snap_tasks"));
      if (taskRaw) setTasks(JSON.parse(taskRaw) as Array<SnapTask>);
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedBusinessId]);

  // Persistors
  useEffect(() => {
    try {
      localStorage.setItem(storageKey("mmr_policy"), JSON.stringify(mmr));
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mmr, selectedBusinessId]);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey("okrs"), JSON.stringify(okrs));
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [okrs, selectedBusinessId]);

  useEffect(() => {
    try {
      localStorage.setItem(storageKey("snap_tasks"), JSON.stringify(tasks));
    } catch {}
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tasks, selectedBusinessId]);

  // Handlers
  const addOkr = () => {
    const title = newOkrTitle.trim();
    if (!title) {
      toast("Enter an objective title.");
      return;
    }
    const obj: Objective = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      title,
      timeframe: newOkrTimeframe,
      createdAt: Date.now(),
      progress: 0,
    };
    setOkrs((prev) => [obj, ...prev]);
    setNewOkrTitle("");
    toast("Objective added.");
  };
  const removeOkr = (id: string) => setOkrs((prev) => prev.filter((o) => o.id !== id));

  const addTask = () => {
    const title = newTaskTitle.trim();
    if (!title) {
      toast("Enter a task.");
      return;
    }
    const t: SnapTask = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      title,
      priority: Math.max(0, Math.min(100, Number(newTaskPriority) || 0)),
      due: null,
      status: "todo",
      createdAt: Date.now(),
    };
    setTasks((prev) => [t, ...prev].sort((a, b) => b.priority - a.priority));
    setNewTaskTitle("");
    toast("Task added.");
  };
  const toggleTask = (id: string) => {
    setTasks((prev) =>
      prev
        .map((t) => {
          if (t.id !== id) return t;
          const nextStatus: SnapTask["status"] = t.status === "todo" ? "done" : "todo";
          return { ...t, status: nextStatus };
        })
        .sort((a, b) => b.priority - a.priority)
    );
  };
  const bumpTask = (id: string, delta: number) => {
    setTasks((prev) =>
      prev
        .map((t) => (t.id === id ? { ...t, priority: Math.max(0, Math.min(100, t.priority + delta)) } : t))
        .sort((a, b) => b.priority - a.priority)
    );
  };
  const removeTask = (id: string) => setTasks((prev) => prev.filter((t) => t.id !== id));

  const openFeedback = (initiativeId: string) => {
    setFeedbackInitId(initiativeId);
    setFeedbackPhase("Discovery");
    setFeedbackNote("");
    setFeedbackOpen(true);
  };
  const saveFeedback = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!feedbackInitId) {
      setFeedbackOpen(false);
      return;
    }
    const entry: InitiativeFeedback = {
      id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
      initiativeId: feedbackInitId,
      phase: feedbackPhase,
      note: feedbackNote.trim(),
      createdAt: Date.now(),
    };
    try {
      const key = storageKey("dtfl_feedback");
      const raw = localStorage.getItem(key);
      const list: Array<InitiativeFeedback> = raw ? JSON.parse(raw) : [];
      list.unshift(entry);
      localStorage.setItem(key, JSON.stringify(list));
      toast("Feedback saved.");
    } catch {
      toast("Failed to save feedback.");
    }
    setFeedbackOpen(false);
  };

  // Derived MMR suggestion for display
  const mmrSuggestion = (kind: "sensitive" | "drafts" | "default"): string => {
    const pct = mmr[kind];
    if (pct >= 90) return "Full human review recommended";
    if (pct >= 60) return "High human oversight";
    if (pct >= 30) return "Balanced human + AI";
    return "AI-leaning autonomy";
  };

  const businessesLoaded = userBusinesses !== undefined;
  const hasBusinesses = (userBusinesses?.length || 0) > 0;

  // Select first business when loaded
  useEffect(() => {
    if (!selectedBusinessId && hasBusinesses) {
      setSelectedBusinessId(userBusinesses![0]._id);
    }
  }, [hasBusinesses, selectedBusinessId, userBusinesses]);

  const initiatives = useQuery(
    api.initiatives.getByBusiness,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );
  const agents = useQuery(
    api.aiAgents.getByBusiness,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );
  const workflows = useQuery(
    api.workflows.listWorkflows,
    selectedBusinessId ? { businessId: selectedBusinessId as any } : ("skip" as any)
  );

  // Add: Quality & Compliance data queries (guarded by selectedBusinessId)
  const risks = useQuery(
    api.workflows.listRisks,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<Risk> | undefined;

  const incidents = useQuery(
    api.workflows.listIncidents,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<Incident> | undefined;

  const nonconformities = useQuery(
    api.workflows.listNonconformities,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<Nonconformity> | undefined;

  const sops = useQuery(
    api.workflows.listSops,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<Sop> | undefined;

  const complianceChecks = useQuery(
    api.workflows.listComplianceChecks,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<ComplianceCheck> | undefined;

  const auditLogs = useQuery(
    api.workflows.listAuditLogs,
    selectedBusinessId ? ({ businessId: selectedBusinessId } as any) : ("skip" as any)
  ) as Array<AuditLog> | undefined;

  const createBusiness = useMutation(api.businesses.create);
  const seedAgents = useMutation(api.aiAgents.seedEnhancedForBusiness);
  const seedTemplates = useMutation(api.workflows.seedTemplates);
  const runWorkflow = useAction(api.workflows.runWorkflow);

  // Helper to scroll to a section by id safely
  const scrollToSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "start", inline: "nearest" });
    }
  };

  if (authLoading) {
    return (
      <div className="max-w-6xl mx-auto p-6">
        <div className="animate-pulse h-8 w-40 rounded bg-muted mb-4" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
          <div className="h-28 rounded-lg bg-muted" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center px-6">
        <Card className="max-w-md w-full">
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
            <CardDescription>Sign in to view your dashboard.</CardDescription>
          </CardHeader>
          <CardContent className="flex gap-3">
            <Button onClick={() => navigate("/auth")}>Sign In</Button>
            <Button variant="outline" onClick={() => navigate("/")}>Go Home</Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  const handleQuickCreateBusiness = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const fd = new FormData(e.currentTarget);
    const name = String(fd.get("name") || "").trim();
    const industry = String(fd.get("industry") || "").trim();
    const tier = (String(fd.get("tier") || "startup") as Business["tier"]);
    if (!name || !industry) {
      toast("Please provide a name and industry.");
      return;
    }
    try {
      const id = await createBusiness({
        name,
        tier,
        industry,
        description: undefined,
        website: undefined,
      } as any);
      toast("Business created");
      setSelectedBusinessId(id as any);
    } catch (err: any) {
      toast(err.message || "Failed to create business");
    }
  };

  const handleSeedAgents = async () => {
    if (!selectedBusinessId) return;
    try {
      await seedAgents({ businessId: selectedBusinessId as any });
      toast("AI agents seeded");
    } catch (e: any) {
      toast(e.message || "Failed to seed agents");
    }
  };

  const handleSeedTemplates = async () => {
    try {
      await seedTemplates({});
      toast("Workflow templates seeded");
    } catch (e: any) {
      toast(e.message || "Failed to seed templates");
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      toast("Signed out");
      navigate("/");
    } catch (e: any) {
      toast(e?.message || "Failed to sign out");
    } finally {
      setSignOutOpen(false);
    }
  };

  // Add: CSV export helper
  const exportAuditCsv = async () => {
    if (!selectedBusinessId) {
      toast("Select a business first.");
      return;
    }
    try {
      const url = `/api/audit/export?businessId=${encodeURIComponent(selectedBusinessId)}`;
      const res = await fetch(url, { method: "GET" });
      if (!res.ok) {
        throw new Error(`Export failed (${res.status})`);
      }
      const blob = await res.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = href;
      a.download = `audit_logs_${selectedBusinessId}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(href);
      toast("Audit CSV exported.");
    } catch (e: any) {
      toast(e?.message || "Failed to export audit CSV");
    }
  };

  // Add: Report Incident submit handler
  const submitIncident = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!selectedBusinessId) {
      toast("Select a business first.");
      return;
    }
    const fd = new FormData(e.currentTarget);
    const title = String(fd.get("title") || "").trim();
    const description = String(fd.get("description") || "").trim();
    const category = String(fd.get("category") || "").trim();
    if (!title) {
      toast("Please provide a title.");
      return;
    }
    try {
      const res = await fetch("/api/incidents/report", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          businessId: selectedBusinessId,
          title,
          description,
          severity,
          category,
          reportedBy: user?._id,
        }),
      });
      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt || "Failed to report incident");
      }
      toast("Incident reported, CAPA initiated.");
      setReportOpen(false);
    } catch (e: any) {
      toast(e?.message || "Failed to report incident");
    }
  };

  const selectedBusiness = userBusinesses?.find((b: any) => b._id === selectedBusinessId) as Business | undefined;

  const normalizedQuery = searchQuery.trim().toLowerCase();

  const filteredInitiatives = (() => {
    const list = initiatives || [];
    if (!normalizedQuery) return list;
    return list.filter((i: Initiative) =>
      [i.title, i.status, i.priority].some((f) => String(f).toLowerCase().includes(normalizedQuery))
    );
  })();

  const filteredAgents = (() => {
    const list = agents || [];
    if (!normalizedQuery) return list;
    return list.filter((a: Agent) =>
      [a.name, a.type, a.isActive ? "active" : "inactive"].some((f) =>
        String(f).toLowerCase().includes(normalizedQuery)
      )
    );
  })();

  const filteredWorkflows = (() => {
    const list = workflows || [];
    const globalQuery = normalizedQuery;
    const localQuery = workflowSearch.trim().toLowerCase();

    // If neither query is provided, return full list
    if (!globalQuery && !localQuery) return list;

    const matches = (w: Workflow, q: string) =>
      [w.name, w.description, w.isActive ? "active" : "inactive"].some((f) =>
        String(f).toLowerCase().includes(q)
      );

    return list.filter((w) => {
      const okGlobal = globalQuery ? matches(w as any, globalQuery) : true;
      const okLocal = localQuery ? matches(w as any, localQuery) : true;
      return okGlobal && okLocal;
    });
  })();

  const effectiveTier: Business["tier"] = (tierOverride || selectedBusiness?.tier || "solopreneur") as Business["tier"];

  const stats = [
    { label: "Initiatives", value: initiatives?.length ?? 0 },
    { label: "AI Agents", value: agents?.length ?? 0 },
    { label: "Workflows", value: workflows?.length ?? 0 },
  ];

  // Add: pricing helper mapping
  const tierPrice = (tier: Business["tier"] | undefined): string => {
    switch (tier) {
      case "solopreneur":
        return "$99/mo";
      case "startup":
        return "$297/mo";
      case "sme":
        return "$597/mo";
      case "enterprise":
        return "Custom";
      default:
        return "$99/mo";
    }
  };

  // Feature bullets per tier (sidebar section)
  const tierFeatureMap: Record<Business["tier"], Array<string>> = {
    solopreneur: [
      "3 Core Agents",
      "Complete Solo Biz Toolkit",
      "Personal Brand Builder",
      "Task Automation Suite",
      "Learning Center: Solopreneur Courses",
      "Templates & Market Research",
      "Email Support",
    ],
    startup: [
      "5 Team Agents",
      "Founders Dashboard",
      "Acquisition & Activation Playbooks",
      "Weekly Metrics & Alerts",
      "Simple CRM & Pipeline",
      "Email + Chat Support",
    ],
    sme: [
      "10+ Department Agents",
      "Ops & Finance Automations",
      "Team Workflows & Approvals",
      "Advanced Analytics",
      "SLA Support",
      "Integration Library",
    ],
    enterprise: [
      "Custom Agents & Governance",
      "SSO & RBAC",
      "Dedicated Infrastructure",
      "Enterprise Integrations",
      "Compliance & Audit Trails",
      "24/7 Priority Support",
    ],
  };

  const handleSelectTier = (tier: Business["tier"]) => {
    setTierOverride(tier);
    try {
      localStorage.setItem("dashboard_tier_override", tier);
      const url = new URL(window.location.href);
      url.searchParams.set("tier", tier);
      window.history.replaceState(null, "", url.toString());
    } catch {}
    toast(`Switched to ${tier} dashboard`);
    setSwitcherOpen(false);
  };

  const clearTierOverride = () => {
    setTierOverride(null);
    try {
      localStorage.removeItem("dashboard_tier_override");
      const url = new URL(window.location.href);
      url.searchParams.delete("tier");
      window.history.replaceState(null, "", url.toString());
    } catch {}
    toast("Using business tier");
    setSwitcherOpen(false);
  };

  return (
    <SidebarProvider>
      <Sidebar variant="inset" collapsible="offcanvas" className="bg-gradient-to-b from-emerald-700 via-emerald-800 to-teal-900 text-white shadow-xl">
        <SidebarHeader>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-white/70" aria-hidden />
            <SidebarInput
              placeholder="Search (Initiatives, Agents, Workflows)…"
              aria-label="Search"
              value={searchQuery}
              onChange={(e: any) => setSearchQuery(e.target.value)}
              className="pl-9 pr-3 h-9 bg-white text-emerald-900 placeholder-emerald-600 border-transparent rounded-full focus-visible:ring-2 focus-visible:ring-emerald-400/50 focus-visible:border-emerald-300 transition-shadow shadow-sm"
            />
          </div>
        </SidebarHeader>

        <SidebarContent>
          <SidebarGroup>
            <SidebarGroupLabel className="text-emerald-200/90 uppercase tracking-wide">Menu</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("overview")}
                    tooltip="Overview"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <Home />
                    <span>Dashboard</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("initiatives-section")}
                    tooltip="Initiatives"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <Layers />
                    <span>Initiatives</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => navigate("/ai-agents")}
                    tooltip="AI Agents"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <BotIcon />
                    <span>AI Agents</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => navigate("/workflows")}
                    tooltip="Workflows"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <WorkflowIcon />
                    <span>Workflows</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {/* Add: direct shortcut to open Templates tab */}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => navigate("/workflows/templates")}
                    tooltip="Workflow Templates"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <WorkflowIcon />
                    <span>Workflow Templates</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                {/* Add: Compliance menu item */}
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("compliance-section")}
                    tooltip="Quality & Compliance"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <SettingsIcon />
                    <span>Compliance</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("mmr-section")}
                    tooltip="MMR Calculator"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <SettingsIcon />
                    <span>MMR</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("tasks-section")}
                    tooltip="SNAP Tasks"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <Layers />
                    <span>Tasks</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("okrs-section")}
                    tooltip="OKRs"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <BarChart3 />
                    <span>OKRs</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator className="bg-white/15" />

          <SidebarGroup>
            <SidebarGroupLabel className="text-emerald-200/90 uppercase tracking-wide">Organization</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => scrollToSection("business-info")}
                    tooltip="Business Info"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <SettingsIcon />
                    <span>Business Info</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    onClick={() => navigate("/analytics")}
                    tooltip="Analytics"
                    className="text-white hover:bg-white/10 active:bg-white/15 focus-visible:ring-emerald-400/40 rounded-xl"
                  >
                    <BarChart3 />
                    <span>Analytics</span>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>

          <SidebarSeparator className="bg-white/15" />

          <SidebarGroup>
            <SidebarGroupLabel className="text-emerald-200/90 uppercase tracking-wide">
              {effectiveTier.charAt(0).toUpperCase() + effectiveTier.slice(1)} — {tierPrice(effectiveTier)}
            </SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {/* Tier features */}
                {tierFeatureMap[effectiveTier].map((feature) => (
                  <SidebarMenuItem key={feature}>
                    <SidebarMenuButton
                      asChild
                      className="text-white/90 hover:bg-white/10 rounded-xl cursor-default"
                    >
                      <div className="flex items-center gap-2">
                        <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-300" aria-hidden />
                        <span>{feature}</span>
                      </div>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        </SidebarContent>

        <SidebarFooter>
          {/* Premium profile card with plan and status; optimized for mobile */}
          <div className="rounded-2xl bg-white/10 px-3 py-3 ring-1 ring-white/15 space-y-3 sm:px-4 sm:py-4">
            <div className="flex items-center gap-3">
              <div className="relative">
                <Avatar className="h-10 w-10 sm:h-11 sm:w-11 border border-white/30 ring-2 ring-emerald-600/60">
                  <AvatarFallback className="bg-emerald-700 text-white text-sm">
                    {String(user?.companyName || user?.email || "U")
                      .split(" ")
                      .map((s: string) => s[0])
                      .join("")
                      .slice(0, 2)
                      .toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <span
                  className="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-900"
                  aria-label="Online"
                />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-semibold truncate text-white">
                  {user?.companyName || "Your Organization"}
                </div>
                <div className="text-xs text-white/80 truncate">
                  {user?.email || "user@example.com"}
                </div>
              </div>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-emerald-100/90 bg-emerald-700/40 border border-white/15 px-2 py-1 rounded-full">
                {`${effectiveTier} • ${tierPrice(effectiveTier)}`}
              </span>
              <span className="text-xs text-emerald-100/90 flex items-center gap-1 bg-emerald-700/40 border border-white/15 px-2 py-1 rounded-full">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                Online
              </span>
            </div>
          </div>
        </SidebarFooter>
        <SidebarRail />
      </Sidebar>

      <Dialog open={signOutOpen} onOpenChange={setSignOutOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Sign out</DialogTitle>
            <DialogDescription>
              You'll be signed out of your session on this device. You can sign in again anytime.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSignOutOpen(false)}>Cancel</Button>
            <Button variant="destructive" onClick={handleSignOut}>Sign Out</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Add: Report Incident Dialog */}
      <Dialog open={reportOpen} onOpenChange={setReportOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Report Incident</DialogTitle>
            <DialogDescription>Create an incident. A CAPA workflow will be initiated automatically.</DialogDescription>
          </DialogHeader>
          <form onSubmit={submitIncident} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="title">Title</Label>
                <Input id="title" name="title" placeholder="Short incident title" />
              </div>
              <div>
                <Label htmlFor="category">Category</Label>
                <Input id="category" name="category" placeholder="e.g., Quality, Security, Privacy" />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="severity">Severity</Label>
                <Select value={severity} onValueChange={(v) => setSeverity(v as Incident["severity"])}> 
                  <SelectTrigger id="severity"><SelectValue placeholder="Severity" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="critical">Critical</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea id="description" name="description" placeholder="What happened? Context, impact, affected systems..." className="h-24" />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setReportOpen(false)}>Cancel</Button>
              <Button type="submit">Submit Incident</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={feedbackOpen} onOpenChange={setFeedbackOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Phase Feedback</DialogTitle>
            <DialogDescription>Design Thinking Feedback Loop — capture findings at the end of each phase.</DialogDescription>
          </DialogHeader>
          <form onSubmit={saveFeedback} className="space-y-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label htmlFor="phase">Phase</Label>
                <Select value={feedbackPhase} onValueChange={(v) => setFeedbackPhase(v as any)}>
                  <SelectTrigger id="phase"><SelectValue placeholder="Phase" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="Discovery">Discovery</SelectItem>
                    <SelectItem value="Planning">Planning</SelectItem>
                    <SelectItem value="Build">Build</SelectItem>
                    <SelectItem value="Test">Test</SelectItem>
                    <SelectItem value="Launch">Launch</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="note">Feedback</Label>
              <Textarea
                id="note"
                value={feedbackNote}
                onChange={(e) => setFeedbackNote(e.target.value)}
                placeholder="What did we learn? What to iterate next?"
                className="h-24"
              />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setFeedbackOpen(false)}>Cancel</Button>
              <Button type="submit">Save</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <SidebarInset>
        <div id="overview" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-2">
              <SidebarTrigger />
              <div>
                <h1 className="text-2xl font-semibold">Dashboard</h1>
                <p className="text-sm text-muted-foreground">Welcome back{user?.companyName ? `, ${user.companyName}` : ""}.</p>
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              {businessesLoaded && hasBusinesses ? (
                <Select
                  value={selectedBusinessId ?? ""}
                  onValueChange={(v) => setSelectedBusinessId(v)}
                >
                  <SelectTrigger className="w-full sm:min-w-56">
                    <SelectValue placeholder="Select business" />
                  </SelectTrigger>
                  <SelectContent>
                    {userBusinesses!.map((b: Business) => (
                      <SelectItem key={b._id} value={b._id}>
                        {b.name} <span className="text-muted-foreground">• {b.tier}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : null}
              <Button variant="outline" onClick={() => navigate("/onboarding")}>Onboarding</Button>
              <Button onClick={() => setSwitcherOpen(true)}>Switch Dashboard</Button>
            </div>
          </div>

          {tierOverride && (
            <div className="mt-2">
              <span className="inline-flex items-center gap-2 text-xs px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Viewing as: {tierOverride} • {tierPrice(tierOverride)}
                <Button size="sm" variant="ghost" className="h-7 px-2" onClick={clearTierOverride}>
                  Clear
                </Button>
              </span>
            </div>
          )}

          {!businessesLoaded ? (
            <Card className="bg-white">
              <CardContent className="p-6">
                <div className="animate-pulse h-6 w-44 rounded bg-muted" />
              </CardContent>
            </Card>
          ) : !hasBusinesses ? (
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>Create your first business</CardTitle>
                <CardDescription>Get started by creating a business profile.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleQuickCreateBusiness} className="grid grid-cols-1 md:grid-cols-5 gap-3">
                  <Input name="name" placeholder="Business name" className="md:col-span-2" />
                  <Input name="industry" placeholder="Industry" className="md:col-span-2" />
                  <Select name="tier" defaultValue="startup" onValueChange={() => {}}>
                    <SelectTrigger><SelectValue placeholder="Tier" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="solopreneur">Solopreneur</SelectItem>
                      <SelectItem value="startup">Startup</SelectItem>
                      <SelectItem value="sme">SME</SelectItem>
                      <SelectItem value="enterprise">Enterprise</SelectItem>
                    </SelectContent>
                  </Select>
                  <div className="md:col-span-5 flex gap-2">
                    <Button type="submit">Create</Button>
                    <Button type="button" variant="outline" onClick={() => navigate("/onboarding")}>
                      Use guided onboarding
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {stats.map((s) => (
                  <Card key={s.label} className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>{s.label}</CardDescription>
                      <CardTitle className="text-2xl">{s.value}</CardTitle>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="text-xs text-muted-foreground">Updated in real time</div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2 bg-white" id="initiatives-section">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>Initiatives</CardTitle>
                      <CardDescription>Track ROI and completion.</CardDescription>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="w-full overflow-x-auto">
                      <Table className="min-w-[600px]">
                        <TableHeader>
                          <TableRow>
                            <TableHead>Title</TableHead>
                            <TableHead>Status</TableHead>
                            <TableHead>Priority</TableHead>
                            <TableHead className="text-right">ROI</TableHead>
                            <TableHead className="text-right">Feedback</TableHead>
                          </TableRow>
                        </TableHeader>
                        <TableBody>
                          {(filteredInitiatives || []).map((i: Initiative) => (
                            <TableRow key={i._id}>
                              <TableCell className="max-w-[220px] truncate">{i.title}</TableCell>
                              <TableCell>
                                <Badge variant="secondary">{i.status}</Badge>
                              </TableCell>
                              <TableCell>
                                <Badge variant={i.priority === "urgent" || i.priority === "high" ? "destructive" : "outline"}>
                                  {i.priority}
                                </Badge>
                              </TableCell>
                              <TableCell className="text-right">
                                {Math.round(i.metrics.currentROI)}% / {Math.round(i.metrics.targetROI)}%
                              </TableCell>
                              <TableCell className="text-right">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => openFeedback(i._id)}
                                >
                                  Add
                                </Button>
                              </TableCell>
                            </TableRow>
                          ))}
                          {((filteredInitiatives || []).length === 0) && (
                            <TableRow>
                              <TableCell colSpan={5} className="text-muted-foreground">
                                {normalizedQuery ? "No results match your search." : "No initiatives yet."}
                              </TableCell>
                            </TableRow>
                          )}
                        </TableBody>
                      </Table>
                    </div>
                  </CardContent>
                </Card>

                <div className="space-y-6">
                  {/* Voice Brain Dump – Solopreneur only */}
                  {effectiveTier === "solopreneur" && (
                    <Card className="bg-white">
                      <CardHeader className="flex flex-row items-center justify-between">
                        <div>
                          <CardTitle>Voice Brain Dump</CardTitle>
                          <CardDescription>Speak your thoughts. Get instant guidance.</CardDescription>
                        </div>
                        {/* Recording status pill */}
                        <div className="flex items-center gap-2">
                          <span
                            className={`inline-flex items-center gap-2 text-xs px-2 py-1 rounded-full border ${
                              isRecording ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-muted text-muted-foreground"
                            }`}
                          >
                            <span
                              className={`h-2.5 w-2.5 rounded-full ${
                                isRecording ? "bg-red-500 animate-pulse" : "bg-gray-300"
                              }`}
                              aria-hidden
                            />
                            {isRecording ? `Recording ${Math.floor(elapsedSeconds / 60)}:${String(elapsedSeconds % 60).padStart(2, "0")}` : "Idle"}
                          </span>
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        {/* Controls row */}
                        <div className="flex flex-wrap items-center gap-2">
                          <Button
                            onClick={isRecording ? stopVoiceDump : startVoiceDump}
                            variant={isRecording ? "outline" : "default"}
                          >
                            {isRecording ? "Stop Recording" : "Start Recording"}
                          </Button>
                          <span
                            className={`text-xs px-2 py-1 rounded-full ${
                              isRecording ? "bg-emerald-100 text-emerald-700" : "bg-muted text-muted-foreground"
                            }`}
                          >
                            {isRecording ? "Listening…" : "Idle"}
                          </span>
                          <Button
                            variant="outline"
                            disabled={!voiceTranscript.trim()}
                            onClick={() => {
                              setVoiceTranscript("");
                              setVoiceReply("");
                              toast("Transcript cleared.");
                            }}
                          >
                            Clear
                          </Button>
                        </div>

                        {/* Transcript and actions */}
                        <Textarea
                          placeholder="Transcript will appear here…"
                          value={voiceTranscript}
                          onChange={(e) => setVoiceTranscript(e.target.value)}
                          className="h-28"
                        />
                        <div className="flex flex-wrap gap-2 items-center justify-between">
                          <span className="text-xs text-muted-foreground">Private, processed locally in your browser</span>
                          <div className="flex gap-2">
                            <Button variant="outline" onClick={analyzeVoiceDump} disabled={!voiceTranscript.trim()}>
                              Generate AI Insight
                            </Button>
                            <Button
                              variant="outline"
                              onClick={() => {
                                const txt = voiceTranscript.trim();
                                if (!txt) {
                                  toast("Nothing to save. Add a transcript first.");
                                  return;
                                }
                                saveSession(txt, undefined);
                              }}
                            >
                              Save Transcript
                            </Button>
                          </div>
                        </div>

                        {voiceReply && (
                          <div className="rounded-lg border p-3 text-sm">
                            <span className="font-medium">AI Insight:</span>{" "}
                            <span className="text-muted-foreground">{voiceReply}</span>
                          </div>
                        )}

                        {/* Sessions list */}
                        <div className="pt-2 space-y-2">
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium">Recent Sessions</p>
                            {sessions.length > 0 && (
                              <span className="text-xs text-muted-foreground">{sessions.length} saved</span>
                            )}
                          </div>
                          {sessions.length === 0 ? (
                            <div className="text-sm text-muted-foreground">
                              No saved sessions yet. Record or save a transcript to keep it here.
                            </div>
                          ) : (
                            <div className="space-y-3 max-h-72 overflow-auto pr-1">
                              {sessions.map((s) => (
                                <div
                                  key={s.id}
                                  className="rounded-lg border p-3 bg-white/60 space-y-2"
                                >
                                  <div className="flex items-center justify-between gap-3">
                                    <span className="text-xs text-muted-foreground">
                                      {new Date(s.createdAt).toLocaleString()}
                                    </span>
                                    <div className="flex gap-2">
                                      <Button size="sm" variant="outline" onClick={() => reuseTranscript(s)}>
                                        Reuse
                                      </Button>
                                      <Button size="sm" variant="outline" onClick={() => downloadText(s)}>
                                        Download Text
                                      </Button>
                                      <Button size="sm" variant="outline" onClick={() => deleteSession(s.id)}>
                                        Delete
                                      </Button>
                                    </div>
                                  </div>
                                  {s.audioDataUrl ? (
                                    <audio controls className="w-full">
                                      <source src={s.audioDataUrl} type="audio/webm" />
                                      Your browser does not support the audio element.
                                    </audio>
                                  ) : (
                                    <div className="text-xs text-muted-foreground">No audio captured</div>
                                  )}
                                  <div className="text-sm text-foreground line-clamp-4">{s.transcript}</div>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )}

                  <Card className="bg-white">
                    <CardHeader className="flex flex-row items-center justify-between">
                      <div>
                        <CardTitle>Quick actions</CardTitle>
                        <CardDescription>Seed useful data for demos.</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent className="flex flex-wrap gap-2">
                      <Button onClick={handleSeedAgents}>Seed AI Agents</Button>
                      <Button variant="outline" onClick={handleSeedTemplates}>Seed Workflow Templates</Button>
                    </CardContent>
                  </Card>

                  <Card id="business-info" className="bg-white">
                    <CardHeader>
                      <CardTitle>Business</CardTitle>
                      <CardDescription>{selectedBusiness?.name}</CardDescription>
                    </CardHeader>
                    <CardContent className="text-sm text-muted-foreground space-y-1">
                      <div>Tier: <span className="text-foreground font-medium">{effectiveTier}</span></div>
                      <div>Price: <span className="text-foreground font-medium">{tierPrice(effectiveTier)}</span></div>
                      <div>Industry: <span className="text-foreground font-medium">{selectedBusiness?.industry}</span></div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </>
          )}

          {/* Initiative Journey — Phase 0 to 6 */}
          <div className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-4">
            <Card className="bg-white">
              <CardHeader className="flex items-center justify-between flex-row">
                <div>
                  <CardTitle>Initiative Journey</CardTitle>
                  <CardDescription>
                    Guided phases from Onboarding → Sustainability with contextual tools.
                  </CardDescription>
                </div>
                <div className="hidden md:block text-xs text-muted-foreground">
                  Orchestrate-ready • MMR-aware
                </div>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                  {journeyPhases.map((p) => (
                    <div key={p.id} className="rounded-xl border p-4 bg-white/80 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-emerald-100 text-emerald-700 text-xs font-semibold">
                            {p.id}
                          </span>
                          <h3 className="font-medium">{p.title}</h3>
                        </div>
                        <Badge variant="outline" className="text-xs">
                          {p.id === 0 ? "One‑time" : "Iterative"}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">{p.description}</p>
                      <div className="flex flex-wrap gap-2">
                        {p.actions.map((a, i) => (
                          <Button
                            key={i}
                            size="sm"
                            variant={i === 0 ? "default" : "outline"}
                            onClick={a.onClick}
                          >
                            {a.label}
                          </Button>
                        ))}
                      </div>
                      {/* Contextual calculators/frameworks */}
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {p.id === 2 && <span>SNAP scoring appears in Planning</span>}
                        {p.id === 4 && <span>MMR applies on approvals</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Add: Quality & Compliance Section */}
          <div id="compliance-section" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-4">
            <Card className="bg-white">
              <CardHeader className="flex items-start justify-between gap-4">
                <div>
                  <CardTitle>Quality & Compliance</CardTitle>
                  <CardDescription>Governance metrics, incidents, and audit trails.</CardDescription>
                </div>
                <div className="flex gap-2 flex-wrap">
                  <Button variant="outline" onClick={() => setReportOpen(true)} disabled={!selectedBusinessId}>
                    Report Incident
                  </Button>
                  <Button onClick={exportAuditCsv} variant="outline" disabled={!selectedBusinessId}>
                    Export Audit CSV
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
                  <Card className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>Incidents</CardDescription>
                      <CardTitle className="text-2xl">{incidents?.length ?? 0}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>Nonconformities</CardDescription>
                      <CardTitle className="text-2xl">{nonconformities?.length ?? 0}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>Risks</CardDescription>
                      <CardTitle className="text-2xl">{risks?.length ?? 0}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>SOPs</CardDescription>
                      <CardTitle className="text-2xl">{sops?.length ?? 0}</CardTitle>
                    </CardHeader>
                  </Card>
                  <Card className="bg-white">
                    <CardHeader className="pb-2">
                      <CardDescription>Compliance Checks</CardDescription>
                      <CardTitle className="text-2xl">{complianceChecks?.length ?? 0}</CardTitle>
                    </CardHeader>
                  </Card>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Recent Audit Logs */}
                  <Card className="bg-white">
                    <CardHeader className="flex items-center justify-between flex-row">
                      <div>
                        <CardTitle>Recent Audit Logs</CardTitle>
                        <CardDescription>Latest 5 entries</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="w-full overflow-x-auto">
                        <Table className="min-w-[560px]">
                          <TableHeader>
                            <TableRow>
                              <TableHead>Action</TableHead>
                              <TableHead>Actor</TableHead>
                              <TableHead>When</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(auditLogs || []).slice(-5).reverse().map((a: AuditLog) => (
                              <TableRow key={a._id}>
                                <TableCell className="max-w-[240px] truncate">{a.action}</TableCell>
                                <TableCell className="max-w-[160px] truncate">{a.actor || "—"}</TableCell>
                                <TableCell className="text-muted-foreground">
                                  {a.createdAt ? new Date(a.createdAt).toLocaleString() : "—"}
                                </TableCell>
                              </TableRow>
                            ))}
                            {((auditLogs || []).length === 0) && (
                              <TableRow>
                                <TableCell colSpan={3} className="text-muted-foreground">No audit logs.</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Recent Incidents */}
                  <Card className="bg-white">
                    <CardHeader className="flex items-center justify-between flex-row">
                      <div>
                        <CardTitle>Recent Incidents</CardTitle>
                        <CardDescription>Latest 5 incidents</CardDescription>
                      </div>
                    </CardHeader>
                    <CardContent>
                      <div className="w-full overflow-x-auto">
                        <Table className="min-w-[560px]">
                          <TableHeader>
                            <TableRow>
                              <TableHead>Title</TableHead>
                              <TableHead>Severity</TableHead>
                              <TableHead>Status</TableHead>
                              <TableHead>When</TableHead>
                            </TableRow>
                          </TableHeader>
                          <TableBody>
                            {(incidents || []).slice(-5).reverse().map((i: Incident) => (
                              <TableRow key={i._id}>
                                <TableCell className="max-w-[240px] truncate">{i.title}</TableCell>
                                <TableCell>
                                  <Badge variant={i.severity === "high" || i.severity === "critical" ? "destructive" : "outline"}>
                                    {i.severity}
                                  </Badge>
                                </TableCell>
                                <TableCell>
                                  <Badge variant="secondary">{i.status || "open"}</Badge>
                                </TableCell>
                                <TableCell className="text-muted-foreground">
                                  {i.createdAt ? new Date(i.createdAt).toLocaleString() : "—"}
                                </TableCell>
                              </TableRow>
                            ))}
                            {((incidents || []).length === 0) && (
                              <TableRow>
                                <TableCell colSpan={4} className="text-muted-foreground">No incidents.</TableCell>
                              </TableRow>
                            )}
                          </TableBody>
                        </Table>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Workflows Quick Access */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Play className="h-5 w-5" />
                Workflow Orchestration
              </CardTitle>
              <CardDescription>Quick access to automation tools</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex gap-2">
                <Button size="sm" variant="outline" onClick={() => navigate("/workflows")}>
                  All Workflows
                </Button>
                <Button size="sm" variant="outline" onClick={() => navigate("/workflows")}>
                  Templates
                </Button>
                <Button size="sm" variant="outline" onClick={() => navigate("/workflows")}>
                  Suggested
                </Button>
              </div>
              <div className="text-sm text-muted-foreground">
                Create automated workflows with triggers, approvals, and cross-agent collaboration
              </div>
            </CardContent>
          </Card>

          <div id="mmr-section" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-4">
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>MMR Calculator</CardTitle>
                <CardDescription>Set human review thresholds by content type. Stored per business.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Sensitive Content — Human Review {mmr.sensitive}%</Label>
                    <span className="text-xs text-muted-foreground">{mmrSuggestion("sensitive")}</span>
                  </div>
                  <Slider
                    value={[mmr.sensitive]}
                    onValueChange={(v: number[]) => setMmr((p) => ({ ...p, sensitive: v[0] ?? 0 }))}
                    min={0}
                    max={100}
                    step={5}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Drafts — Human Review {mmr.drafts}%</Label>
                    <span className="text-xs text-muted-foreground">{mmrSuggestion("drafts")}</span>
                  </div>
                  <Slider
                    value={[mmr.drafts]}
                    onValueChange={(v: number[]) => setMmr((p) => ({ ...p, drafts: v[0] ?? 0 }))}
                    min={0}
                    max={100}
                    step={5}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <Label>Default — Human Review {mmr.default}%</Label>
                    <span className="text-xs text-muted-foreground">{mmrSuggestion("default")}</span>
                  </div>
                  <Slider
                    value={[mmr.default]}
                    onValueChange={(v: number[]) => setMmr((p) => ({ ...p, default: v[0] ?? 0 }))}
                    min={0}
                    max={100}
                    step={5}
                  />
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div className="text-xs text-muted-foreground">
                    Tip: Use 100% for regulated or high-risk items; 20–40% for iterative content like drafts.
                  </div>
                  <div className="flex justify-end">
                    <Button variant="outline" onClick={() => setMmr({ sensitive: 100, drafts: 20, default: 30, notes: "" })}>
                      Reset to Recommended
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          <div id="tasks-section" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-4">
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>SNAP Prioritization — Daily Tasks</CardTitle>
                <CardDescription>Senses signals, normalizes priority, and helps you act. You can reprioritize.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex flex-col md:flex-row gap-2">
                  <Input
                    placeholder="Task (e.g., Follow-up top pipeline deals)"
                    value={newTaskTitle}
                    onChange={(e) => setNewTaskTitle(e.target.value)}
                    className="md:flex-1"
                  />
                  <div className="flex items-center gap-2">
                    <Label className="text-xs">Priority</Label>
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      value={newTaskPriority}
                      onChange={(e) => setNewTaskPriority(Number(e.target.value))}
                      className="w-24"
                    />
                  </div>
                  <Button onClick={addTask}>Add</Button>
                </div>
                <div className="w-full overflow-x-auto">
                  <Table className="min-w-[560px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Task</TableHead>
                        <TableHead className="text-center">Priority</TableHead>
                        <TableHead className="text-center">Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {tasks.map((t) => (
                        <TableRow key={t.id} className={t.status === "done" ? "opacity-60" : ""}>
                          <TableCell className="max-w-[320px] truncate">{t.title}</TableCell>
                          <TableCell className="text-center">{t.priority}</TableCell>
                          <TableCell className="text-center">
                            <Badge variant={t.status === "done" ? "outline" : "secondary"}>
                              {t.status === "done" ? "Done" : "To do"}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right space-x-2">
                            <Button size="sm" variant="outline" onClick={() => bumpTask(t.id, +10)}>↑</Button>
                            <Button size="sm" variant="outline" onClick={() => bumpTask(t.id, -10)}>↓</Button>
                            <Button size="sm" variant="outline" onClick={() => toggleTask(t.id)}>
                              {t.status === "done" ? "Undone" : "Done"}
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => removeTask(t.id)}>Remove</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {tasks.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-muted-foreground">
                            No tasks yet. Add your top 3 by impact to start the day.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>

          <div id="okrs-section" className="max-w-6xl mx-auto px-4 md:px-6 py-6 space-y-4">
            <Card className="bg-white">
              <CardHeader>
                <CardTitle>OKRs — Objectives & Key Results</CardTitle>
                <CardDescription>Set outcomes, let Pikar tie metrics later. Quick add an objective.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  <Input
                    placeholder='Objective (e.g., "Increase online sales 20%")'
                    value={newOkrTitle}
                    onChange={(e) => setNewOkrTitle(e.target.value)}
                    className="sm:col-span-2"
                  />
                  <Select value={newOkrTimeframe} onValueChange={(v) => setNewOkrTimeframe(v as Objective["timeframe"])}>
                    <SelectTrigger><SelectValue placeholder="Timeframe" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="This Month">This Month</SelectItem>
                      <SelectItem value="This Quarter">This Quarter</SelectItem>
                      <SelectItem value="This Year">This Year</SelectItem>
                      <SelectItem value="Q1">Q1</SelectItem>
                      <SelectItem value="Q2">Q2</SelectItem>
                      <SelectItem value="Q3">Q3</SelectItem>
                      <SelectItem value="Q4">Q4</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end">
                  <Button onClick={addOkr}>Add Objective</Button>
                </div>
                <div className="w-full overflow-x-auto">
                  <Table className="min-w-[560px]">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Objective</TableHead>
                        <TableHead>Timeframe</TableHead>
                        <TableHead>Progress</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {okrs.map((o) => (
                        <TableRow key={o.id}>
                          <TableCell className="max-w-[320px] truncate">{o.title}</TableCell>
                          <TableCell>{o.timeframe}</TableCell>
                          <TableCell>
                            <Badge variant="outline">{Math.round(o.progress ?? 0)}%</Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <Button size="sm" variant="outline" onClick={() => removeOkr(o.id)}>Remove</Button>
                          </TableCell>
                        </TableRow>
                      ))}
                      {okrs.length === 0 && (
                        <TableRow>
                          <TableCell colSpan={4} className="text-muted-foreground">
                            No objectives yet. Add an objective to begin tracking outcomes.
                          </TableCell>
                        </TableRow>
                      )}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </SidebarInset>
    </SidebarProvider>
  );
}