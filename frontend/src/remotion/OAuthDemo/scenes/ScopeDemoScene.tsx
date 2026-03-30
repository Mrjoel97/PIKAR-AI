import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';
import { COLORS, FONTS, TOTAL_SECTIONS } from '../constants';

/**
 * Reusable scene for demonstrating a single OAuth scope.
 * Each scope gets its own instance with different content.
 */

interface MockChatMessage {
  role: 'user' | 'agent';
  text: string;
}

interface ScopeDemoProps {
  sectionNumber: number;
  title: string;
  scopeName: string;
  scopeFullName: string;
  classification: 'basic' | 'sensitive' | 'restricted';
  icon: string;
  description: string;
  chatMessages: MockChatMessage[];
  codeSnippet: string;
  features: string[];
}

const ChatBubble: React.FC<{
  message: MockChatMessage;
  delay: number;
}> = ({ message, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = interpolate(frame, [delay, delay + fps * 0.3], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const y = interpolate(frame, [delay, delay + fps * 0.3], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const isAgent = message.role === 'agent';

  return (
    <div
      style={{
        opacity,
        transform: `translateY(${y}px)`,
        display: 'flex',
        justifyContent: isAgent ? 'flex-start' : 'flex-end',
        marginBottom: 12,
      }}
    >
      <div
        style={{
          maxWidth: '80%',
          padding: '12px 18px',
          borderRadius: 16,
          borderBottomLeftRadius: isAgent ? 4 : 16,
          borderBottomRightRadius: isAgent ? 16 : 4,
          background: isAgent
            ? 'rgba(43,168,143,0.15)'
            : 'rgba(255,255,255,0.08)',
          border: `1px solid ${isAgent ? 'rgba(43,168,143,0.25)' : 'rgba(255,255,255,0.08)'}`,
          fontFamily: FONTS.body,
          fontSize: 16,
          lineHeight: 1.5,
          color: COLORS.textPrimary,
        }}
      >
        {isAgent && (
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 11,
              color: COLORS.accent,
              marginBottom: 4,
              letterSpacing: 1,
            }}
          >
            PIKAR AI AGENT
          </div>
        )}
        {message.text}
      </div>
    </div>
  );
};

export const ScopeDemoScene: React.FC<ScopeDemoProps> = ({
  sectionNumber,
  title,
  scopeName,
  scopeFullName,
  classification,
  icon,
  description,
  chatMessages,
  codeSnippet,
  features,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, fps * 0.4], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const classColors = {
    basic: { bg: COLORS.scopeBasicBg, text: '#166534', border: COLORS.scopeBasic },
    sensitive: { bg: COLORS.scopeSensitiveBg, text: '#92400e', border: COLORS.scopeSensitive },
    restricted: { bg: COLORS.scopeRestrictedBg, text: '#991b1b', border: COLORS.scopeRestricted },
  };
  const cls = classColors[classification];

  const codeOpacity = interpolate(frame, [fps * 4, fps * 5], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const featuresOpacity = interpolate(frame, [fps * 5, fps * 6], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `linear-gradient(160deg, ${COLORS.bgDark} 0%, #0d3333 100%)`,
        padding: 80,
        display: 'flex',
        gap: 60,
      }}
    >
      {/* Left side: title + chat */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Section badge */}
        <div
          style={{
            opacity: headerOpacity,
            fontFamily: FONTS.mono,
            fontSize: 14,
            color: COLORS.accent,
            letterSpacing: 3,
            textTransform: 'uppercase',
            marginBottom: 12,
          }}
        >
          Section {sectionNumber} of {TOTAL_SECTIONS}
        </div>

        {/* Title row */}
        <div style={{ opacity: headerOpacity, display: 'flex', alignItems: 'center', gap: 16, marginBottom: 12 }}>
          <span style={{ fontSize: 44 }}>{icon}</span>
          <div
            style={{
              fontFamily: FONTS.display,
              fontSize: 40,
              fontWeight: 700,
              color: COLORS.textPrimary,
            }}
          >
            {title}
          </div>
        </div>

        {/* Scope badge */}
        <div
          style={{
            opacity: headerOpacity,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 32,
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 14,
              color: COLORS.textMuted,
              background: 'rgba(255,255,255,0.06)',
              padding: '6px 14px',
              borderRadius: 8,
            }}
          >
            {scopeFullName}
          </div>
          <div
            style={{
              padding: '4px 12px',
              borderRadius: 6,
              background: cls.bg,
              fontFamily: FONTS.mono,
              fontSize: 11,
              fontWeight: 700,
              color: cls.text,
              letterSpacing: 1,
              textTransform: 'uppercase',
            }}
          >
            {classification}
          </div>
        </div>

        {/* Description */}
        <div
          style={{
            opacity: headerOpacity,
            fontFamily: FONTS.body,
            fontSize: 18,
            color: COLORS.textSecondary,
            marginBottom: 32,
            lineHeight: 1.5,
          }}
        >
          {description}
        </div>

        {/* Mock chat */}
        <div
          style={{
            flex: 1,
            background: 'rgba(0,0,0,0.2)',
            borderRadius: 16,
            padding: 20,
            border: '1px solid rgba(255,255,255,0.06)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 12,
              color: COLORS.textMuted,
              marginBottom: 16,
              letterSpacing: 1,
            }}
          >
            LIVE DEMO
          </div>
          {chatMessages.map((msg, i) => (
            <ChatBubble key={i} message={msg} delay={fps * 1.5 + i * fps * 0.8} />
          ))}
        </div>
      </div>

      {/* Right side: code + features */}
      <div style={{ flex: 0.8, display: 'flex', flexDirection: 'column', justifyContent: 'center', gap: 32 }}>
        {/* Code snippet */}
        <div
          style={{
            opacity: codeOpacity,
            background: '#0d1117',
            borderRadius: 16,
            padding: 28,
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 11,
              color: COLORS.textMuted,
              marginBottom: 16,
              letterSpacing: 1,
            }}
          >
            IMPLEMENTATION
          </div>
          <pre
            style={{
              fontFamily: FONTS.mono,
              fontSize: 14,
              color: '#e2e8f0',
              lineHeight: 1.6,
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            {codeSnippet}
          </pre>
        </div>

        {/* Features list */}
        <div style={{ opacity: featuresOpacity }}>
          <div
            style={{
              fontFamily: FONTS.mono,
              fontSize: 12,
              color: COLORS.textMuted,
              marginBottom: 12,
              letterSpacing: 1,
            }}
          >
            APP FUNCTIONALITY
          </div>
          {features.map((feature, i) => (
            <div
              key={i}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                marginBottom: 10,
                fontFamily: FONTS.body,
                fontSize: 16,
                color: COLORS.textSecondary,
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: 3,
                  background: COLORS.accent,
                  flexShrink: 0,
                }}
              />
              {feature}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// --- Pre-configured scope scenes ---

export const GmailReadonlyScene: React.FC = () => (
  <ScopeDemoScene
    sectionNumber={3}
    title="Gmail Read Access"
    scopeName="gmail.readonly"
    scopeFullName="googleapis.com/auth/gmail.readonly"
    classification="restricted"
    icon="📨"
    description="Allows Pikar AI agents to read the user's Gmail inbox for automated briefings, email triage, and intelligent classification."
    chatMessages={[
      { role: 'user', text: 'Check my inbox and triage unread emails by priority' },
      {
        role: 'agent',
        text: '📬 Found 12 unread emails. Here\'s your triage:\n\n🔴 High: Contract renewal from Acme Corp\n🟡 Medium: Q1 report from finance team\n🟢 Low: 8 newsletters and notifications',
      },
    ]}
    codeSnippet={`# Gmail inbox reader tool
reader = GmailReader(credentials)
messages = reader.list_messages(
    query="is:unread",
    max_results=20
)

# Parse and classify each message
for msg in messages:
    parsed = reader.get_message(msg["id"])
    # AI agent classifies priority`}
    features={[
      'Morning briefing — summarizes overnight emails',
      'Inbox triage — classifies by priority (high/medium/low)',
      'Email search — finds specific conversations',
      'Thread analysis — understands email context',
    ]}
  />
);

export const GmailModifyScene: React.FC = () => (
  <ScopeDemoScene
    sectionNumber={4}
    title="Gmail Label Management"
    scopeName="gmail.modify"
    scopeFullName="googleapis.com/auth/gmail.modify"
    classification="restricted"
    icon="📂"
    description="Allows Pikar AI agents to archive emails and manage labels after triage. No content is ever deleted — only labels are modified."
    chatMessages={[
      { role: 'user', text: 'Archive the low-priority emails from my triage' },
      {
        role: 'agent',
        text: '✅ Archived 8 low-priority emails:\n• 5 newsletters → removed from INBOX\n• 3 notifications → marked as read\n\nYour inbox now has 4 actionable items.',
      },
    ]}
    codeSnippet={`# Archive email (remove INBOX label)
def archive_email(message_id):
    reader.modify_message(
        message_id,
        remove_labels=["INBOX", "UNREAD"]
    )

# Mark as read only
def mark_read(message_id):
    reader.modify_message(
        message_id,
        remove_labels=["UNREAD"]
    )`}
    features={[
      'Archive processed emails after triage',
      'Mark emails as read when reviewed by agent',
      'Label management — organize by category',
      'Never deletes email content — labels only',
    ]}
  />
);

export const GmailSendScene: React.FC = () => (
  <ScopeDemoScene
    sectionNumber={5}
    title="Gmail Send Access"
    scopeName="gmail.send"
    scopeFullName="googleapis.com/auth/gmail.send"
    classification="restricted"
    icon="📤"
    description="Allows Pikar AI agents to send emails on the user's behalf. Every send requires explicit user approval through our confirmation workflow."
    chatMessages={[
      { role: 'user', text: 'Send a follow-up email to the Acme team about the contract' },
      {
        role: 'agent',
        text: '📝 Draft ready for your approval:\n\nTo: contracts@acme.com\nSubject: Re: Contract Renewal\n\n"Hi team, following up on our contract discussion..."\n\n⚠️ Send this email? [Approve] [Edit] [Cancel]',
      },
      { role: 'user', text: 'Approve' },
      { role: 'agent', text: '✅ Email sent successfully. Message ID: 18d4f...' },
    ]}
    codeSnippet={`# Send email with approval gate
def send_email(to, subject, body):
    service = GmailService(credentials)
    result = service.send_email(
        to=to,
        subject=subject,
        body=body,
        body_html=formatted_html
    )
    return result  # {status, message_id}`}
    features={[
      'AI-drafted emails with user approval required',
      'Supports plain text and HTML formatting',
      'CC/BCC and attachment support',
      'Approval workflow prevents unauthorized sends',
    ]}
  />
);

export const CalendarScene: React.FC = () => (
  <ScopeDemoScene
    sectionNumber={6}
    title="Google Calendar Access"
    scopeName="calendar"
    scopeFullName="googleapis.com/auth/calendar"
    classification="sensitive"
    icon="📅"
    description="Allows Pikar AI agents to read and create calendar events for scheduling, availability checking, and meeting coordination."
    chatMessages={[
      { role: 'user', text: "What's on my calendar this week?" },
      {
        role: 'agent',
        text: '📅 This week\'s schedule:\n\nMon 10am — Team standup\nTue 2pm — Client demo (Acme)\nWed 11am — 1:1 with Sarah\nThu 3pm — Sprint planning\n\nYou have 4 hours open on Friday.',
      },
      { role: 'user', text: 'Schedule a review meeting Friday at 10am' },
      { role: 'agent', text: '✅ Created: "Review Meeting" — Fri 10:00-11:00 AM\nCalendar link added.' },
    ]}
    codeSnippet={`# List upcoming events
service = GoogleCalendarService(creds)
events = service.list_upcoming_events(
    max_results=10,
    calendar_id="primary"
)

# Create new event
service.create_event(
    title="Review Meeting",
    start=datetime(2026, 3, 28, 10, 0),
    end=datetime(2026, 3, 28, 11, 0)
)`}
    features={[
      'View upcoming events and daily schedule',
      'Create meetings with title, time, and attendees',
      'Check availability for scheduling',
      'Morning briefing includes today\'s agenda',
    ]}
  />
);
