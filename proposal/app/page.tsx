'use client'

import { useState } from 'react'
import Header from '@/components/Header'
import Hero from '@/components/Hero'
import Overview from '@/components/Overview'
import Services from '@/components/Services'
import Pricing from '@/components/Pricing'
import Timeline from '@/components/Timeline'
import CTA from '@/components/CTA'
import Footer from '@/components/Footer'

export default function Home() {
  const [activeSection, setActiveSection] = useState('overview')

  return (
    <div className="min-h-screen bg-background">
      <Header activeSection={activeSection} setActiveSection={setActiveSection} />
      <main>
        <Hero />
        <div id="overview">
          <Overview />
        </div>
        <div id="services">
          <Services />
        </div>
        <div id="pricing">
          <Pricing />
        </div>
        <div id="timeline">
          <Timeline />
        </div>
        <div id="cta">
          <CTA />
        </div>
      </main>
      <Footer />
    </div>
  )
}
