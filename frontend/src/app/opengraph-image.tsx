import { ImageResponse } from 'next/og';

export const runtime = 'edge';
export const alt = 'Pikar AI – Your AI-Powered Executive Team';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  return new ImageResponse(
    (
      <div
        style={{
          background: 'linear-gradient(135deg, #0a2e2e 0%, #0d3d3a 50%, #061a1a 100%)',
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '60px',
          fontFamily: 'sans-serif',
          position: 'relative',
        }}
      >
        {/* Grid pattern overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.12,
            backgroundImage:
              'linear-gradient(rgba(86,171,145,1) 1px, transparent 1px), linear-gradient(90deg, rgba(86,171,145,1) 1px, transparent 1px)',
            backgroundSize: '60px 60px',
          }}
        />
        {/* Ambient glow */}
        <div
          style={{
            position: 'absolute',
            top: '-5%',
            left: '15%',
            width: '500px',
            height: '500px',
            background: 'rgba(26,138,110,0.18)',
            borderRadius: '50%',
            filter: 'blur(80px)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            bottom: '-10%',
            right: '10%',
            width: '350px',
            height: '350px',
            background: 'rgba(100,60,180,0.12)',
            borderRadius: '50%',
            filter: 'blur(70px)',
          }}
        />

        {/* Brand row */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '18px',
            marginBottom: '40px',
          }}
        >
          <div
            style={{
              width: '60px',
              height: '60px',
              borderRadius: '16px',
              background: 'linear-gradient(135deg, #1a8a6e, #0d6b4f)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '32px',
              boxShadow: '0 8px 32px rgba(26,138,110,0.4)',
            }}
          >
            ⚡
          </div>
          <span
            style={{
              color: 'white',
              fontSize: '36px',
              fontWeight: 800,
              letterSpacing: '-1px',
            }}
          >
            Pikar AI
          </span>
        </div>

        {/* Headline */}
        <div
          style={{
            fontSize: '72px',
            fontWeight: 900,
            color: 'white',
            textAlign: 'center',
            lineHeight: 1.05,
            marginBottom: '24px',
            maxWidth: '950px',
            letterSpacing: '-2.5px',
          }}
        >
          Your AI-Powered{' '}
          <span style={{ color: '#56ab91' }}>Executive Team</span>
        </div>

        {/* Subheadline */}
        <div
          style={{
            fontSize: '26px',
            color: 'rgba(255,255,255,0.55)',
            textAlign: 'center',
            maxWidth: '700px',
            lineHeight: 1.4,
            marginBottom: '48px',
          }}
        >
          10 AI agents for finance, marketing, sales, HR & operations — 24/7
        </div>

        {/* Waitlist badge */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '14px 30px',
            borderRadius: '100px',
            background: 'rgba(26,138,110,0.25)',
            border: '1.5px solid rgba(86,171,145,0.5)',
            color: '#56ab91',
            fontSize: '20px',
            fontWeight: 700,
            letterSpacing: '-0.3px',
          }}
        >
          🚀 Join the Waitlist · Limited Early Access
        </div>

        {/* Stat pills row */}
        <div
          style={{
            display: 'flex',
            gap: '16px',
            marginTop: '36px',
          }}
        >
          {['10 AI Agents', '24/7 Autonomous', 'Human-in-Loop'].map((label) => (
            <div
              key={label}
              style={{
                padding: '8px 20px',
                borderRadius: '100px',
                background: 'rgba(255,255,255,0.07)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: 'rgba(255,255,255,0.6)',
                fontSize: '16px',
                fontWeight: 600,
              }}
            >
              {label}
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size }
  );
}
