export default function Overview() {
  const capabilities = [
    {
      icon: '🔬',
      title: 'Multimodal Vision',
      description: 'Advanced vision analysis with text, images, video (MP4), and real-time simulator integration.',
    },
    {
      icon: '🤖',
      title: 'Multi-Agent Pipeline',
      description: '9 specialist agents handle decomposition, planning, safety, execution, and verification.',
    },
    {
      icon: '⚡',
      title: 'Speed Optimized',
      description: 'Real-time metrics tracking with sub-second decision loops powered by Gemma 4.',
    },
    {
      icon: '🔐',
      title: 'Safety First',
      description: 'Built-in hazard detection, safety veto system, and human-in-the-loop confirmation.',
    },
    {
      icon: '📊',
      title: 'Full Audit Trail',
      description: 'Complete lab notebook with verified actions, metrics, and replan tracking.',
    },
    {
      icon: '🌐',
      title: 'Seamless Integration',
      description: 'REST API, webhook bridge, MQTT hardware integration, and cloud-ready architecture.',
    },
  ]

  return (
    <section className="py-20 md:py-32 bg-white/5">
      <div className="container-max">
        <div className="text-center mb-16">
          <h2 className="section-title mb-6">What Makes VialPilot Special</h2>
          <p className="section-subtitle">
            Every component designed for reliability, speed, and enterprise-grade automation.
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {capabilities.map((cap, idx) => (
            <div
              key={idx}
              className="glass p-6 hover:border-accent/50 transition-all hover:shadow-lg hover:shadow-accent/10"
            >
              <div className="text-4xl mb-4">{cap.icon}</div>
              <h3 className="text-lg font-semibold mb-3 text-foreground">{cap.title}</h3>
              <p className="text-neutral text-sm leading-relaxed">{cap.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
