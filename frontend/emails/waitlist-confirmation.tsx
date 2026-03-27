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

interface WaitlistConfirmationEmailProps {
  firstName?: string | null;
}

export default function WaitlistConfirmationEmail({
  firstName,
}: WaitlistConfirmationEmailProps) {
  const displayName = firstName ?? 'there';

  return (
    <Html>
      <Head />
      <Preview>
        You&apos;re on the Pikar AI waitlist — founding member pricing locked in.
      </Preview>
      <Body style={body}>
        <Container style={container}>
          {/* Header */}
          <Section style={header}>
            <Text style={logo}>Pikar AI</Text>
          </Section>

          {/* Hero */}
          <Section style={heroSection}>
            <div style={badgeWrapper}>
              <span style={badge}>✓ You&apos;re on the list</span>
            </div>
            <Heading style={h1}>
              Hey {displayName}, you&apos;re in early!
            </Heading>
            <Text style={subtext}>
              You&apos;ve secured your spot on the Pikar AI waitlist — and with it,
              founding member pricing — <strong>20% off your first two months</strong>.
            </Text>
          </Section>

          {/* What you get */}
          <Section style={benefitsSection}>
            <Text style={benefitsTitle}>What comes next</Text>
            <table style={benefitsTable} cellPadding={0} cellSpacing={0}>
              <tbody>
                {[
                  {
                    icon: '⚡',
                    title: 'Early access invite',
                    desc: "You'll be among the first to get hands-on with the platform before public launch.",
                  },
                  {
                    icon: '💸',
                    title: '20% off — founding member pricing',
                    desc: '20% off for your first two months. First 500 signups only.',
                  },
                  {
                    icon: '🎯',
                    title: 'Priority onboarding',
                    desc: "Dedicated support to get your first AI agents running on day one.",
                  },
                  {
                    icon: '🛠️',
                    title: 'Shape the product',
                    desc: 'Direct feedback channel to our team — your use case influences what we build.',
                  },
                ].map(({ icon, title, desc }) => (
                  <tr key={title}>
                    <td style={benefitIcon}>{icon}</td>
                    <td style={benefitContent}>
                      <Text style={benefitTitle}>{title}</Text>
                      <Text style={benefitDesc}>{desc}</Text>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Section>

          {/* CTA */}
          <Section style={ctaSection}>
            <Button href="https://pikar.ai" style={ctaButton}>
              Visit Pikar AI
            </Button>
            <Text style={ctaNote}>
              Or share your spot with a friend who should know about this.
            </Text>
          </Section>

          <Hr style={divider} />

          {/* Footer */}
          <Section style={footer}>
            <Text style={footerText}>
              You&apos;re receiving this because you signed up at{' '}
              <Link href="https://pikar.ai" style={footerLink}>
                pikar.ai
              </Link>
              .
            </Text>
            <Text style={footerText}>
              To unsubscribe or exercise your data rights, email{' '}
              <Link href="mailto:privacy@pikar.ai" style={footerLink}>
                privacy@pikar.ai
              </Link>{' '}
              ·{' '}
              <Link href="https://pikar.ai/privacy" style={footerLink}>
                Privacy Policy
              </Link>
            </Text>
            <Text style={footerAddress}>Pikar AI · San Francisco, CA</Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

// ─── Styles ──────────────────────────────────────────────────────────────────

const body: React.CSSProperties = {
  backgroundColor: '#f6f8f8',
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
  margin: 0,
  padding: 0,
};

const container: React.CSSProperties = {
  backgroundColor: '#ffffff',
  margin: '40px auto',
  maxWidth: '560px',
  borderRadius: '12px',
  overflow: 'hidden',
  border: '1px solid #e2e8f0',
};

const header: React.CSSProperties = {
  backgroundColor: '#0a2e2e',
  padding: '24px 40px',
  textAlign: 'center',
};

const logo: React.CSSProperties = {
  color: '#ffffff',
  fontSize: '20px',
  fontWeight: 800,
  margin: 0,
  letterSpacing: '-0.5px',
};

const heroSection: React.CSSProperties = {
  padding: '40px 40px 24px',
  textAlign: 'center',
};

const badgeWrapper: React.CSSProperties = {
  marginBottom: '16px',
};

const badge: React.CSSProperties = {
  display: 'inline-block',
  backgroundColor: '#1a8a6e1a',
  color: '#1a8a6e',
  fontSize: '12px',
  fontWeight: 700,
  letterSpacing: '0.5px',
  padding: '4px 12px',
  borderRadius: '100px',
  border: '1px solid #1a8a6e33',
};

const h1: React.CSSProperties = {
  color: '#0d1b19',
  fontSize: '26px',
  fontWeight: 800,
  lineHeight: '1.2',
  margin: '0 0 12px',
};

const subtext: React.CSSProperties = {
  color: '#475569',
  fontSize: '15px',
  lineHeight: '1.6',
  margin: 0,
};

const benefitsSection: React.CSSProperties = {
  padding: '8px 40px 32px',
};

const benefitsTitle: React.CSSProperties = {
  color: '#94a3b8',
  fontSize: '11px',
  fontWeight: 700,
  letterSpacing: '1px',
  textTransform: 'uppercase',
  margin: '0 0 16px',
};

const benefitsTable: React.CSSProperties = {
  width: '100%',
  borderCollapse: 'separate',
  borderSpacing: '0 12px',
};

const benefitIcon: React.CSSProperties = {
  fontSize: '20px',
  paddingRight: '12px',
  verticalAlign: 'top',
  paddingTop: '2px',
  width: '32px',
};

const benefitContent: React.CSSProperties = {
  verticalAlign: 'top',
};

const benefitTitle: React.CSSProperties = {
  color: '#0d1b19',
  fontSize: '14px',
  fontWeight: 700,
  margin: '0 0 2px',
};

const benefitDesc: React.CSSProperties = {
  color: '#64748b',
  fontSize: '13px',
  lineHeight: '1.5',
  margin: 0,
};

const ctaSection: React.CSSProperties = {
  padding: '0 40px 40px',
  textAlign: 'center',
};

const ctaButton: React.CSSProperties = {
  backgroundColor: '#1a8a6e',
  borderRadius: '8px',
  color: '#ffffff',
  fontSize: '15px',
  fontWeight: 700,
  padding: '14px 32px',
  textDecoration: 'none',
  display: 'inline-block',
};

const ctaNote: React.CSSProperties = {
  color: '#94a3b8',
  fontSize: '13px',
  marginTop: '16px',
};

const divider: React.CSSProperties = {
  borderColor: '#e2e8f0',
  margin: '0 40px',
};

const footer: React.CSSProperties = {
  padding: '24px 40px 32px',
  textAlign: 'center',
};

const footerText: React.CSSProperties = {
  color: '#94a3b8',
  fontSize: '12px',
  lineHeight: '1.6',
  margin: '0 0 4px',
};

const footerLink: React.CSSProperties = {
  color: '#1a8a6e',
  textDecoration: 'underline',
};

const footerAddress: React.CSSProperties = {
  color: '#cbd5e1',
  fontSize: '11px',
  marginTop: '8px',
};
