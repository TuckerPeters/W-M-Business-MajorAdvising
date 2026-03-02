import type { Metadata } from 'next';
import DebugOverlay from '@/components/debug/DebugOverlay';
import './globals.css';

export const metadata: Metadata = {
  title: 'W&M Business Advising Platform',
  description: 'Pre-major and major advising platform for William & Mary Business School',
  icons: {
    icon: '/buisness_emblem.png',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>
        {children}
        <DebugOverlay />
      </body>
    </html>
  );
}
