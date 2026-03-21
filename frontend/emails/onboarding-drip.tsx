import {
  Body,
  Button,
  Container,
  Head,
  Heading,
  Hr,
  Html,
  Link,
  Preview,
  Section,
  Text,
} from '@react-email/components';

type Persona = 'solopreneur' | 'startup' | 'sme' | 'enterprise';
type DripKey = 'welcome' | 'tips' | 'checkin';

interface OnboardingDripEmailProps {
  firstName?: string | null;
  persona?: Persona;
  dripKey?: DripKey;
  dashboardUrl?: string;
}

// ─── Persona-specific content ───────────────────────────────────────────────

const PERSONA_LABELS: Record<Persona, string> = {
  solopreneur: 'Solopreneur',
  startup: 'Startup',
  sme: 'SME',
  enterprise: 'Enterprise',
};

const WELCOME_CONTENT: Record<Persona, { headline: string; intro: string; actions: { icon: string; title: string; desc: string }[] }> = {
  solopreneur: {
    headline: 'Your AI team is ready. Here\'s your first move.',
    intro: 'Pikar AI is now configured for lean, solo execution. No corporate overhead — just actionable AI that saves you time and grows revenue.',
    actions: [
      { icon: '💰', title: 'Map Your Revenue Strategy', desc: 'Identify your best income opportunities and build a growth plan' },
      { icon: '🧠', title: 'Brain Dump Everything', desc: 'Get all your ideas organized so you can focus on what matters' },
      { icon: '📋', title: 'Plan Your Week', desc: 'Create a focused 7-day action plan that moves the needle' },
    ],
  },
  startup: {
    headline: 'Your growth engine is live. Start experimenting.',
    intro: 'Pikar AI is tuned for rapid validation, team alignment, and growth. Every interaction is designed to help you find product-market fit faster.',
    actions: [
      { icon: '🚀', title: 'Design a Growth Experiment', desc: 'Test a hypothesis quickly to learn what drives growth' },
      { icon: '🎯', title: 'Review Your Pitch', desc: 'Sharpen your value proposition for investors and customers' },
      { icon: '📊', title: 'Check Your Burn Rate', desc: 'Understand your runway and make smart spending decisions' },
    ],
  },
  sme: {
    headline: 'Your operations command center is ready.',
    intro: 'Pikar AI is configured for multi-department coordination, process optimization, and operational reporting. Your AI team understands SME complexity.',
    actions: [
      { icon: '🏥', title: 'Department Health Check', desc: 'See how each team is performing at a glance' },
      { icon: '⚙️', title: 'Audit Your Processes', desc: 'Find bottlenecks and optimization opportunities' },
      { icon: '🛡️', title: 'Compliance Review', desc: 'Make sure nothing is falling through the cracks' },
    ],
  },
  enterprise: {
    headline: 'Your executive AI suite is configured.',
    intro: 'Pikar AI is set up for governance-aware execution, portfolio visibility, and stakeholder coordination. Built for the complexity of large organizations.',
    actions: [
      { icon: '📋', title: 'Stakeholder Briefing', desc: 'Prepare a strategic update for leadership' },
      { icon: '⚠️', title: 'Risk Assessment', desc: 'Identify and prioritize organizational risks' },
      { icon: '📈', title: 'Portfolio Review', desc: 'Evaluate your initiative portfolio health' },
    ],
  },
};

const TIPS_CONTENT: Record<Persona, { headline: string; intro: string; tips: { icon: string; title: string; desc: string }[] }> = {
  solopreneur: {
    headline: '3 ways to save 10+ hours this week',
    intro: 'You\'ve been set up for 3 days now. Here are the highest-leverage features solo operators love:',
    tips: [
      { icon: '⚡', title: 'Automate your weekly report', desc: 'Ask your AI to generate a business health snapshot every Monday. One prompt, zero spreadsheets.' },
      { icon: '✍️', title: 'Repurpose your content', desc: 'Turn one blog post into 5 social posts, an email, and a LinkedIn article — automatically.' },
      { icon: '💰', title: 'Pipeline in 60 seconds', desc: 'Say "show me my pipeline" and get instant visibility on deals, follow-ups, and revenue.' },
    ],
  },
  startup: {
    headline: 'Your first growth experiment framework',
    intro: 'Day 3 is the perfect time to run your first structured experiment. Here\'s how your AI accelerates the cycle:',
    tips: [
      { icon: '🧪', title: 'Hypothesis → Test → Learn', desc: 'Ask your AI to help you structure a growth hypothesis with a clear success metric and timeline.' },
      { icon: '📈', title: 'Track what matters', desc: 'Set up your North Star metric and supporting indicators. Your AI keeps them front and center.' },
      { icon: '🔄', title: 'Iterate faster', desc: 'After each experiment, your AI summarizes learnings and suggests the next test to run.' },
    ],
  },
  sme: {
    headline: 'Streamline your department operations',
    intro: 'After 3 days, your AI has context on your business. Here are features that transform how departments work together:',
    tips: [
      { icon: '📊', title: 'Automated KPI dashboards', desc: 'Ask for a department scorecard and get real-time performance visibility across teams.' },
      { icon: '📝', title: 'SOP generation', desc: 'Describe any process and your AI creates a documented, shareable standard operating procedure.' },
      { icon: '🤝', title: 'Cross-department workflows', desc: 'Set up automated handoffs between teams — no more things falling through the cracks.' },
    ],
  },
  enterprise: {
    headline: 'Governance that doesn\'t slow you down',
    intro: 'Your AI suite is designed to add visibility and control without adding bureaucracy. Here\'s what to try next:',
    tips: [
      { icon: '✅', title: 'Approval workflows', desc: 'Set up multi-level approvals that route automatically based on risk, budget, and stakeholder impact.' },
      { icon: '📋', title: 'Executive briefings', desc: 'Generate board-ready summaries of any initiative, complete with risk analysis and dependency maps.' },
      { icon: '🔍', title: 'Audit trails', desc: 'Every AI decision and recommendation is logged with full context for compliance review.' },
    ],
  },
};

const CHECKIN_CONTENT: Record<Persona, { headline: string; intro: string; prompts: { icon: string; title: string; desc: string }[] }> = {
  solopreneur: {
    headline: 'How\'s your first week going?',
    intro: 'You\'ve had a full week with your AI team. Here are some questions to help you get even more out of it:',
    prompts: [
      { icon: '📊', title: 'Review your week', desc: '"What did I accomplish this week and what should I focus on next?"' },
      { icon: '🎯', title: 'Adjust your priorities', desc: '"Based on this week, what\'s the single most impactful thing I should do next?"' },
      { icon: '💡', title: 'Unlock a new capability', desc: '"What features haven\'t I tried yet that would save me the most time?"' },
    ],
  },
  startup: {
    headline: 'Week 1 recap — what did you learn?',
    intro: 'Great startups learn fast. Let your AI help you synthesize your first week of insights:',
    prompts: [
      { icon: '🔬', title: 'Experiment readout', desc: '"Summarize what we learned this week and what experiments we should run next."' },
      { icon: '📈', title: 'Growth check', desc: '"How are our key metrics trending? What\'s our biggest growth lever right now?"' },
      { icon: '👥', title: 'Team alignment', desc: '"Help me write a quick team update covering this week\'s wins and next week\'s focus."' },
    ],
  },
  sme: {
    headline: 'Your operations scorecard after 7 days',
    intro: 'A week of data means your AI can now surface patterns. Try these to unlock operational insights:',
    prompts: [
      { icon: '📊', title: 'Department scorecard', desc: '"Generate a weekly operations report covering all departments."' },
      { icon: '⚠️', title: 'Risk check', desc: '"What operational risks should I be paying attention to this week?"' },
      { icon: '📋', title: 'Process improvements', desc: '"Based on this week, what processes should we optimize first?"' },
    ],
  },
  enterprise: {
    headline: 'Your executive dashboard is warming up',
    intro: 'After a week of context, your AI suite is ready for strategic-level analysis. Try these power features:',
    prompts: [
      { icon: '📋', title: 'Strategic review', desc: '"Prepare an executive summary of all active initiatives with risk status."' },
      { icon: '🔗', title: 'Dependency analysis', desc: '"Map the dependencies across our top initiatives and flag any blockers."' },
      { icon: '📊', title: 'Portfolio health', desc: '"How is our initiative portfolio performing against strategic objectives?"' },
    ],
  },
};

// ─── Email subjects (exported for the cron route) ───────────────────────────

export const DRIP_SUBJECTS: Record<DripKey, (persona: Persona) => string> = {
  welcome: (persona) => {
    const map: Record<Persona, string> = {
      solopreneur: 'Your AI team is ready — here\'s your first move 🚀',
      startup: 'Your growth engine is live — start experimenting 🧪',
      sme: 'Your operations command center is ready ⚙️',
      enterprise: 'Your executive AI suite is configured 📋',
    };
    return map[persona];
  },
  tips: (persona) => {
    const map: Record<Persona, string> = {
      solopreneur: '3 ways to save 10+ hours this week ⚡',
      startup: 'Your first growth experiment framework 📈',
      sme: 'Streamline your department operations 📊',
      enterprise: 'Governance that doesn\'t slow you down ✅',
    };
    return map[persona];
  },
  checkin: (persona) => {
    const map: Record<Persona, string> = {
      solopreneur: 'How\'s your first week going? 📊',
      startup: 'Week 1 recap — what did you learn? 🔬',
      sme: 'Your operations scorecard after 7 days 📋',
      enterprise: 'Your executive dashboard is warming up 📊',
    };
    return map[persona];
  },
};

// ─── Component ──────────────────────────────────────────────────────────────

export default function OnboardingDripEmail({
  firstName,
  persona = 'startup',
  dripKey = 'welcome',
  dashboardUrl = 'https://pikar-ai.com/dashboard/command-center',
}: OnboardingDripEmailProps) {
  const displayName = firstName ?? 'there';
  const personaLabel = PERSONA_LABELS[persona];

  // Select content based on drip stage
  const renderContent = () => {
    if (dripKey === 'welcome') {
      const c = WELCOME_CONTENT[persona];
      return (
        <>
          <Section style={heroSection}>
            <div style={badgeWrapper}>
              <span style={badge}>🎉 Onboarding Complete — {personaLabel} Mode</span>
            </div>
            <Heading style={h1}>Hey {displayName}, {c.headline.toLowerCase()}</Heading>
            <Text style={subtext}>{c.intro}</Text>
          </Section>

          <Section style={cardSection}>
            <Text style={sectionLabel}>YOUR FIRST ACTIONS</Text>
            {c.actions.map((action, i) => (
              <div key={i} style={actionCard}>
                <div style={actionIcon}>{action.icon}</div>
                <div>
                  <Text style={actionTitle}>{action.title}</Text>
                  <Text style={actionDesc}>{action.desc}</Text>
                </div>
              </div>
            ))}
          </Section>
        </>
      );
    }

    if (dripKey === 'tips') {
      const c = TIPS_CONTENT[persona];
      return (
        <>
          <Section style={heroSection}>
            <div style={badgeWrapper}>
              <span style={badge}>💡 Day 3 — Pro Tips</span>
            </div>
            <Heading style={h1}>{c.headline}</Heading>
            <Text style={subtext}>{c.intro}</Text>
          </Section>

          <Section style={cardSection}>
            <Text style={sectionLabel}>TIPS FOR YOUR {personaLabel.toUpperCase()} WORKSPACE</Text>
            {c.tips.map((tip, i) => (
              <div key={i} style={actionCard}>
                <div style={actionIcon}>{tip.icon}</div>
                <div>
                  <Text style={actionTitle}>{tip.title}</Text>
                  <Text style={actionDesc}>{tip.desc}</Text>
                </div>
              </div>
            ))}
          </Section>
        </>
      );
    }

    // checkin
    const c = CHECKIN_CONTENT[persona];
    return (
      <>
        <Section style={heroSection}>
          <div style={badgeWrapper}>
            <span style={badge}>📊 Day 7 — Check-in</span>
          </div>
          <Heading style={h1}>{c.headline}</Heading>
          <Text style={subtext}>{c.intro}</Text>
        </Section>

        <Section style={cardSection}>
          <Text style={sectionLabel}>TRY THESE PROMPTS</Text>
          {c.prompts.map((prompt, i) => (
            <div key={i} style={actionCard}>
              <div style={actionIcon}>{prompt.icon}</div>
              <div>
                <Text style={actionTitle}>{prompt.title}</Text>
                <Text style={{ ...actionDesc, fontStyle: 'italic' }}>{prompt.desc}</Text>
              </div>
            </div>
          ))}
        </Section>
      </>
    );
  };

  const previewText = DRIP_SUBJECTS[dripKey](persona);

  return (
    <Html>
      <Head />
      <Preview>{previewText}</Preview>
      <Body style={body}>
        <Container style={container}>
          {/* Header */}
          <Section style={header}>
            <Text style={logo}>Pikar AI</Text>
          </Section>

          {renderContent()}

          {/* CTA */}
          <Section style={{ textAlign: 'center' as const, padding: '10px 0 30px' }}>
            <Button style={ctaButton} href={dashboardUrl}>
              Open Your Dashboard
            </Button>
          </Section>

          <Hr style={divider} />

          {/* Footer */}
          <Section style={footer}>
            <Text style={footerText}>
              You&apos;re receiving this because you completed onboarding on Pikar AI.
            </Text>
            <Text style={footerText}>
              <Link href="https://pikar-ai.com/privacy" style={footerLink}>Privacy Policy</Link>
              {' · '}
              <Link href="mailto:hello@pikar-ai.com" style={footerLink}>Contact Us</Link>
            </Text>
            <Text style={{ ...footerText, marginTop: '12px', color: '#9ca3af' }}>
              Pikar AI · San Francisco, CA
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

// ─── Styles ─────────────────────────────────────────────────────────────────

const body: React.CSSProperties = {
  backgroundColor: '#f6f8f8',
  fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  margin: 0,
  padding: 0,
};

const container: React.CSSProperties = {
  maxWidth: '580px',
  margin: '0 auto',
  backgroundColor: '#ffffff',
  borderRadius: '16px',
  overflow: 'hidden',
  marginTop: '40px',
  marginBottom: '40px',
  border: '1px solid #e5e7eb',
};

const header: React.CSSProperties = {
  backgroundColor: '#0a2e2e',
  padding: '24px 32px',
  textAlign: 'center' as const,
};

const logo: React.CSSProperties = {
  color: '#56ab91',
  fontSize: '22px',
  fontWeight: 800,
  letterSpacing: '-0.5px',
  margin: 0,
};

const heroSection: React.CSSProperties = {
  padding: '32px 32px 16px',
  textAlign: 'center' as const,
};

const badgeWrapper: React.CSSProperties = {
  textAlign: 'center' as const,
  marginBottom: '16px',
};

const badge: React.CSSProperties = {
  display: 'inline-block',
  backgroundColor: '#ecfdf5',
  color: '#065f46',
  fontSize: '12px',
  fontWeight: 700,
  padding: '6px 14px',
  borderRadius: '9999px',
  border: '1px solid #a7f3d0',
};

const h1: React.CSSProperties = {
  fontSize: '24px',
  fontWeight: 800,
  color: '#0f172a',
  lineHeight: '1.3',
  margin: '0 0 12px',
};

const subtext: React.CSSProperties = {
  fontSize: '15px',
  color: '#64748b',
  lineHeight: '1.6',
  margin: '0 0 8px',
};

const cardSection: React.CSSProperties = {
  padding: '8px 32px 24px',
};

const sectionLabel: React.CSSProperties = {
  fontSize: '11px',
  fontWeight: 700,
  color: '#94a3b8',
  letterSpacing: '1.5px',
  margin: '0 0 16px',
};

const actionCard: React.CSSProperties = {
  display: 'flex',
  gap: '14px',
  padding: '16px',
  backgroundColor: '#f8fafc',
  borderRadius: '12px',
  border: '1px solid #e2e8f0',
  marginBottom: '10px',
};

const actionIcon: React.CSSProperties = {
  fontSize: '24px',
  lineHeight: '1',
  flexShrink: 0,
  paddingTop: '2px',
};

const actionTitle: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: 700,
  color: '#0f172a',
  margin: '0 0 2px',
};

const actionDesc: React.CSSProperties = {
  fontSize: '13px',
  color: '#64748b',
  lineHeight: '1.5',
  margin: 0,
};

const ctaButton: React.CSSProperties = {
  display: 'inline-block',
  backgroundColor: '#1a8a6e',
  color: '#ffffff',
  fontSize: '14px',
  fontWeight: 700,
  padding: '14px 32px',
  borderRadius: '12px',
  textDecoration: 'none',
};

const divider: React.CSSProperties = {
  borderColor: '#e2e8f0',
  margin: '0 32px',
};

const footer: React.CSSProperties = {
  padding: '24px 32px',
  textAlign: 'center' as const,
};

const footerText: React.CSSProperties = {
  fontSize: '12px',
  color: '#94a3b8',
  lineHeight: '1.6',
  margin: '0 0 4px',
};

const footerLink: React.CSSProperties = {
  color: '#1a8a6e',
  textDecoration: 'none',
};
