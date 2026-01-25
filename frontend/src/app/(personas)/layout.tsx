// frontend/src/app/(personas)/layout.tsx
export default function PersonaLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <section>{children}</section>;
}