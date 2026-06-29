export default function CTA() {
  return (
    <section className="py-20 md:py-32 bg-gradient-to-br from-primary/20 via-transparent to-accent/20">
      <div className="container-max">
        <div className="max-w-3xl mx-auto text-center glass p-12 md:p-16">
          <h2 className="text-3xl md:text-4xl font-bold text-foreground mb-6">
            Ready to Transform Your Laboratory?
          </h2>

          <p className="text-lg text-neutral mb-8">
            Join leading institutions using VialPilot to increase efficiency by 300% and reduce errors to nearly zero.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center mb-12">
            <button className="btn-primary">
              Schedule a Demo Today
            </button>
            <button className="btn-secondary">
              Download Proposal PDF
            </button>
          </div>

          <div className="grid sm:grid-cols-3 gap-6 pt-8 border-t border-white/10">
            <div>
              <div className="text-2xl font-bold text-accent mb-2">99%</div>
              <p className="text-sm text-neutral">Accuracy Rate</p>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent mb-2">300%</div>
              <p className="text-sm text-neutral">Efficiency Gain</p>
            </div>
            <div>
              <div className="text-2xl font-bold text-accent mb-2">24/7</div>
              <p className="text-sm text-neutral">Support & Monitoring</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
