export default function Services() {
  const services = [
    {
      number: '01',
      title: 'Vision Analysis',
      items: [
        'Real-time scene understanding',
        'Multi-frame video processing',
        'Hazard zone detection',
        'Object localization with bounding boxes',
      ],
    },
    {
      number: '02',
      title: 'Task Decomposition',
      items: [
        'Natural language instruction parsing',
        'Subtask generation and sequencing',
        'Dependency management',
        'Plan optimization',
      ],
    },
    {
      number: '03',
      title: 'Motion Planning & Execution',
      items: [
        'Inverse kinematics solving',
        'Collision avoidance',
        'Smooth trajectory interpolation',
        'Real-time simulator sync',
      ],
    },
    {
      number: '04',
      title: 'Verification & Replanning',
      items: [
        'Post-action visual verification',
        'One-shot replan capability',
        'Automatic error recovery',
        'Quality assurance checks',
      ],
    },
    {
      number: '05',
      title: 'Safety & Compliance',
      items: [
        'Automated hazard veto system',
        'Human-in-the-loop confirmation',
        'Full audit trail logging',
        'Compliance reporting',
      ],
    },
    {
      number: '06',
      title: 'Integration & Deployment',
      items: [
        'REST API with JSON mode',
        'MQTT hardware bridge',
        'Webhook integration',
        'Docker containerization',
      ],
    },
  ]

  return (
    <section className="py-20 md:py-32">
      <div className="container-max">
        <div className="text-center mb-16">
          <h2 className="section-title mb-6">Core Services & Capabilities</h2>
          <p className="section-subtitle">
            A complete solution covering every aspect of autonomous laboratory automation.
          </p>
        </div>

        <div className="grid md:grid-cols-2 gap-8 lg:gap-12">
          {services.map((service, idx) => (
            <div key={idx} className="glass p-8 border-l-4 border-accent hover:border-primary transition-colors">
              <div className="flex items-start gap-4 mb-6">
                <span className="text-3xl font-bold text-accent opacity-50">{service.number}</span>
                <h3 className="text-2xl font-semibold text-foreground mt-1">{service.title}</h3>
              </div>
              <ul className="space-y-3">
                {service.items.map((item, itemIdx) => (
                  <li key={itemIdx} className="flex items-start gap-3 text-neutral">
                    <span className="w-1 h-1 rounded-full bg-accent mt-2 flex-shrink-0"></span>
                    <span className="text-sm">{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
