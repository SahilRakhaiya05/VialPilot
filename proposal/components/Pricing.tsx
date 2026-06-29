'use client'

import { useState } from 'react'

export default function Pricing() {
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly')

  const plans = [
    {
      name: 'Starter',
      price: billingCycle === 'monthly' ? '$5,000' : '$50,000',
      period: billingCycle === 'monthly' ? '/month' : '/year',
      description: 'Perfect for pilots and small operations',
      features: [
        '1 robotic arm',
        'Basic vision analysis',
        'Up to 100 operations/month',
        'Email support',
        'Standard audit trail',
        'Community access',
      ],
      highlighted: false,
    },
    {
      name: 'Professional',
      price: billingCycle === 'monthly' ? '$15,000' : '$150,000',
      period: billingCycle === 'monthly' ? '/month' : '/year',
      description: 'For growing enterprises',
      features: [
        '3 robotic arms',
        'Advanced multimodal vision',
        'Unlimited operations',
        'Priority support (24/7)',
        'Full audit trail + compliance reports',
        'API access',
        'Custom integrations',
        'Hazard zone configuration',
      ],
      highlighted: true,
    },
    {
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'For large-scale deployments',
      features: [
        'Unlimited robotic arms',
        'White-label solution',
        'Dedicated support team',
        'Custom agent development',
        'On-premises deployment option',
        'Advanced analytics dashboard',
        'SLA guarantees',
        'Full source code access',
      ],
      highlighted: false,
    },
  ]

  return (
    <section className="py-20 md:py-32 bg-white/5">
      <div className="container-max">
        <div className="text-center mb-16">
          <h2 className="section-title mb-6">Transparent Pricing</h2>
          <p className="section-subtitle mb-8">
            Flexible plans designed to scale with your laboratory operations.
          </p>

          <div className="flex justify-center gap-4 mb-12">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                billingCycle === 'monthly'
                  ? 'bg-accent text-background'
                  : 'bg-white/5 text-foreground hover:bg-white/10'
              }`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingCycle('annual')}
              className={`px-6 py-2 rounded-lg font-medium transition-colors ${
                billingCycle === 'annual'
                  ? 'bg-accent text-background'
                  : 'bg-white/5 text-foreground hover:bg-white/10'
              }`}
            >
              Annual <span className="text-xs ml-1 opacity-75">(Save 15%)</span>
            </button>
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, idx) => (
            <div
              key={idx}
              className={`glass p-8 flex flex-col transition-all ${
                plan.highlighted
                  ? 'ring-2 ring-accent md:scale-105 shadow-2xl shadow-accent/20'
                  : ''
              }`}
            >
              {plan.highlighted && (
                <div className="mb-4">
                  <span className="inline-block px-3 py-1 rounded-full bg-accent/20 text-accent text-xs font-semibold">
                    Most Popular
                  </span>
                </div>
              )}

              <h3 className="text-2xl font-bold text-foreground mb-2">{plan.name}</h3>
              <p className="text-neutral text-sm mb-6">{plan.description}</p>

              <div className="mb-8">
                <span className="text-4xl font-bold text-accent">{plan.price}</span>
                {plan.period && <span className="text-neutral text-sm ml-2">{plan.period}</span>}
              </div>

              <button
                className={`mb-8 py-3 px-4 rounded-lg font-semibold transition-colors ${
                  plan.highlighted
                    ? 'bg-accent text-background hover:bg-primary'
                    : 'bg-white/5 text-foreground hover:bg-white/10 border border-white/10'
                }`}
              >
                Get Started
              </button>

              <div className="space-y-4 flex-1">
                {plan.features.map((feature, featureIdx) => (
                  <div key={featureIdx} className="flex items-start gap-3">
                    <svg className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-neutral text-sm">{feature}</span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
