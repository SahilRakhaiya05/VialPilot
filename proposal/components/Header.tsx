import { useState } from 'react'
import Link from 'next/link'

interface HeaderProps {
  activeSection: string
  setActiveSection: (section: string) => void
}

export default function Header({ activeSection, setActiveSection }: HeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const navItems = [
    { label: 'Overview', href: '#overview' },
    { label: 'Services', href: '#services' },
    { label: 'Pricing', href: '#pricing' },
    { label: 'Timeline', href: '#timeline' },
  ]

  const handleNavClick = (href: string) => {
    const section = href.replace('#', '')
    setActiveSection(section)
    setMobileMenuOpen(false)
  }

  return (
    <header className="sticky top-0 z-50 backdrop-blur-xl bg-background/80 border-b border-white/10">
      <div className="container-max py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
              <span className="text-white font-bold text-sm">VP</span>
            </div>
            <span className="font-bold text-lg text-foreground">VialPilot</span>
          </div>

          <nav className="hidden md:flex items-center gap-8">
            {navItems.map((item) => (
              <button
                key={item.href}
                onClick={() => handleNavClick(item.href)}
                className={`text-sm font-medium transition-colors ${
                  activeSection === item.href.replace('#', '')
                    ? 'text-accent'
                    : 'text-neutral hover:text-foreground'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          <div className="hidden md:flex items-center gap-4">
            <button className="btn-secondary">Get Demo</button>
            <button className="btn-primary">Schedule Call</button>
          </div>

          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden text-foreground"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {mobileMenuOpen && (
          <div className="md:hidden mt-4 pt-4 border-t border-white/10 flex flex-col gap-3">
            {navItems.map((item) => (
              <button
                key={item.href}
                onClick={() => handleNavClick(item.href)}
                className="text-left py-2 text-sm font-medium text-neutral hover:text-foreground transition-colors"
              >
                {item.label}
              </button>
            ))}
            <div className="flex gap-2 mt-2">
              <button className="btn-secondary flex-1 text-sm">Get Demo</button>
              <button className="btn-primary flex-1 text-sm">Schedule Call</button>
            </div>
          </div>
        )}
      </div>
    </header>
  )
}
