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

interface TeamInviteEmailProps {
  inviterName: string;
  workspaceName: string;
  role: string;
  acceptUrl: string;
}

export default function TeamInviteEmail({
  inviterName,
  workspaceName,
  role,
  acceptUrl,
}: TeamInviteEmailProps) {
  return (
    <Html>
      <Head />
      <Preview>
        {inviterName} invited you to join {workspaceName} on Pikar AI
      </Preview>
      <Body style={body}>
        <Container style={container}>
          <Section style={header}>
            <Text style={logo}>Pikar AI</Text>
          </Section>

          <Section style={heroSection}>
            <div style={badgeWrapper}>
              <span style={badge}>Workspace invitation</span>
            </div>
            <Heading style={heading}>You&apos;ve been invited</Heading>
            <Text style={paragraph}>
              <strong>{inviterName}</strong> invited you to join{' '}
              <strong>{workspaceName}</strong> on Pikar AI as a <strong>{role}</strong>.
            </Text>
          </Section>

          <Section style={ctaSection}>
            <Button href={acceptUrl} style={ctaButton}>
              Accept Invitation
            </Button>
            <Text style={note}>
              This invitation expires in 7 days. If you didn&apos;t expect this,
              you can safely ignore it.
            </Text>
          </Section>

          <Hr style={divider} />

          <Section style={footer}>
            <Text style={footerText}>
              Need help getting started? Visit{' '}
              <Link href="https://pikar.ai" style={footerLink}>
                pikar.ai
              </Link>{' '}
              for more information.
            </Text>
          </Section>
        </Container>
      </Body>
    </Html>
  );
}

const body = {
  backgroundColor: '#f8fafc',
  fontFamily:
    '-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
  margin: 0,
  padding: '32px 16px',
};

const container = {
  backgroundColor: '#ffffff',
  border: '1px solid #e2e8f0',
  borderRadius: '24px',
  margin: '0 auto',
  maxWidth: '560px',
  overflow: 'hidden',
};

const header = {
  background:
    'linear-gradient(135deg, #4338ca 0%, #4f46e5 55%, #6366f1 100%)',
  padding: '24px 32px',
};

const logo = {
  color: '#ffffff',
  fontSize: '22px',
  fontWeight: 700,
  letterSpacing: '-0.02em',
  margin: 0,
};

const heroSection = {
  padding: '32px',
};

const badgeWrapper = {
  marginBottom: '16px',
};

const badge = {
  backgroundColor: '#eef2ff',
  borderRadius: '999px',
  color: '#4338ca',
  display: 'inline-block',
  fontSize: '12px',
  fontWeight: 700,
  padding: '6px 12px',
};

const heading = {
  color: '#0f172a',
  fontSize: '30px',
  fontWeight: 700,
  letterSpacing: '-0.02em',
  lineHeight: '1.2',
  margin: '0 0 16px',
};

const paragraph = {
  color: '#334155',
  fontSize: '16px',
  lineHeight: '1.7',
  margin: 0,
};

const ctaSection = {
  padding: '0 32px 32px',
};

const ctaButton = {
  backgroundColor: '#4f46e5',
  borderRadius: '14px',
  color: '#ffffff',
  display: 'inline-block',
  fontSize: '15px',
  fontWeight: 700,
  padding: '14px 24px',
  textDecoration: 'none',
};

const note = {
  color: '#64748b',
  fontSize: '13px',
  lineHeight: '1.6',
  margin: '16px 0 0',
};

const divider = {
  borderColor: '#e2e8f0',
  margin: 0,
};

const footer = {
  padding: '20px 32px 28px',
};

const footerText = {
  color: '#64748b',
  fontSize: '12px',
  lineHeight: '1.6',
  margin: 0,
};

const footerLink = {
  color: '#4338ca',
  textDecoration: 'underline',
};
