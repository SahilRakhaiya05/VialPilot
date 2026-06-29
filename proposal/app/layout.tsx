import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'VialPilot - Professional Proposal',
  description: 'Professional proposal for VialPilot Autonomous Robotics Lab',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="bg-background text-foreground">{children}</body>
    </html>
  )
}
