import Link from 'next/link'

export default function Hero() {
  return (
    <section className="relative py-20 md:py-32 overflow-hidden">
      <div className="absolute inset-0 opacity-30">
        <div className="absolute inset-0 bg-gradient-to-br from-primary/20 via-transparent to-accent/20"></div>
      </div>

      <div className="container-max relative z-10">
        <div className="max-w-4xl">
          <div className="inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-full border border-white/10 bg-white/5">
            <span className="w-2 h-2 rounded-full bg-accent"></span>
            <span className="text-sm font-medium text-accent">Autonomous Robotics Lab</span>
          </div>

          <h1 className="section-title mb-6">
            The Future of Laboratory Automation is Here
          </h1>

          <p className="section-subtitle mb-8">
            VialPilot combines advanced vision, intelligent agents, and precise robotics to transform how laboratories operate. Reduce errors by 99%, increase efficiency by 300%, and scale operations instantly.
          </p>

          <div className="flex flex-col sm:flex-row gap-4">
            <button className="btn-primary">
              View Full Proposal
            </button>
            <button className="btn-secondary">
              Watch Demo Video
            </button>
          </div>

          <div className="mt-16 grid grid-cols-3 gap-8">
            {[
              { label: '9 Agents', value: 'AI-powered' },
              { label: '99% Accuracy', value: 'Vision verified' },
              { label: '24/7 Operation', value: 'Zero downtime' },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="text-2xl md:text-3xl font-bold text-accent mb-1">{stat.label}</div>
                <div className="text-sm text-neutral">{stat.value}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
