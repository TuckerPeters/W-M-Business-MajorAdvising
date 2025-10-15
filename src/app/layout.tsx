import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'W&M Business Advising Platform',
  description: 'Pre-major and major advising platform for William & Mary Business School',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
