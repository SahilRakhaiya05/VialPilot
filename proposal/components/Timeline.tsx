export default function Timeline() {
  const phases = [
    {
      phase: 'Phase 1',
      title: 'Discovery & Planning',
      duration: 'Weeks 1-2',
      items: [
        'Requirements gathering',
        'Lab environment assessment',
        'Integration planning',
        'Custom configuration',
      ],
    },
    {
      phase: 'Phase 2',
      title: 'Setup & Training',
      duration: 'Weeks 3-4',
      items: [
        'Hardware installation',
        'Software deployment',
        'Team training',
        'Safety protocols',
      ],
    },
    {
      phase: 'Phase 3',
      title: 'Pilot & Validation',
      duration: 'Weeks 5-8',
      items: [
        'Initial operations',
        'Performance benchmarking',
        'Issue resolution',
        'Optimization',
      ],
    },
    {
      phase: 'Phase 4',
      title: 'Production Launch',
      duration: 'Ongoing',
      items: [
        'Full deployment',
        'Continuous monitoring',
        'Performance optimization',
        '24/7 support',
      ],
    },
  ]

  return (
    <section className="py-20 md:py-32">
      <div className="container-max">
        <div className="text-center mb-16">
          <h2 className="section-title mb-6">Implementation Timeline</h2>
          <p className="section-subtitle">
            Rapid deployment with comprehensive support every step of the way.
          </p>
        </div>

        <div className="relative">
          {/* Timeline line */}
          <div className="hidden lg:block absolute top-1/2 left-0 right-0 h-1 bg-gradient-to-r from-accent via-primary to-accent transform -translate-y-1/2"></div>

          <div className="grid lg:grid-cols-4 gap-8 relative z-10">
            {phases.map((phaseItem, idx) => (
              <div key={idx} className="relative">
                {/* Timeline dot */}
                <div className="hidden lg:flex absolute -top-4 left-1/2 transform -translate-x-1/2 w-8 h-8 rounded-full bg-accent border-4 border-background items-center justify-center">
                  <div className="w-2 h-2 rounded-full bg-background"></div>
                </div>

                <div className="glass p-6 lg:mt-12">
                  <div className="flex gap-3 mb-4">
                    <span className="px-3 py-1 rounded-full bg-accent/20 text-accent text-xs font-semibold">
                      {phaseItem.phase}
                    </span>
                    <span className="px-3 py-1 rounded-full bg-white/10 text-neutral text-xs font-medium">
                      {phaseItem.duration}
                    </span>
                  </div>

                  <h3 className="text-lg font-bold text-foreground mb-4">{phaseItem.title}</h3>

                  <ul className="space-y-2">
                    {phaseItem.items.map((item, itemIdx) => (
                      <li key={itemIdx} className="flex items-start gap-2 text-neutral text-sm">
                        <span className="w-1.5 h-1.5 rounded-full bg-accent mt-1 flex-shrink-0"></span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
