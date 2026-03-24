import Link from 'next/link';

const skills = [
  { icon: 'code', label: 'Python & Java' },
  { icon: 'cloud', label: 'AWS' },
  { icon: 'psychology', label: 'GenAI / LLMs' },
  { icon: 'hub', label: 'Microservices' },
  { icon: 'account_tree', label: 'Distributed Systems' },
  { icon: 'biotech', label: 'NLP & Computer Vision' },
];

const terminalLines = [
  { line: '01', segments: [{ text: 'class ', color: '#00daf3' }, { text: 'ShivomThakkar:', color: '#dae2fd' }] },
  { line: '02', segments: [{ text: '    def ', color: '#00daf3' }, { text: '__init__(self):', color: '#dae2fd' }] },
  { line: '03', segments: [{ text: '        self.role = ', color: '#dae2fd' }, { text: '"Lead Engineer"', color: '#00e5ff' }] },
  { line: '04', segments: [{ text: '        self.experience = ', color: '#dae2fd' }, { text: '"7 years"', color: '#00e5ff' }] },
  { line: '05', segments: [{ text: '        self.location = ', color: '#dae2fd' }, { text: '"Pune, India"', color: '#00e5ff' }] },
  { line: '06', segments: [{ text: '        self.stack = ', color: '#dae2fd' }, { text: '["Python", "Java", "AWS"]', color: '#00e5ff' }] },
  { line: '07', segments: [{ text: '    ', color: '#dae2fd' }] },
  { line: '08', segments: [{ text: '    # Optimise infrastructure cost', color: '#bac9cc', italic: true }] },
  { line: '09', segments: [{ text: '    async def ', color: '#00daf3' }, { text: 'optimise(self):', color: '#dae2fd' }] },
  { line: '10', segments: [{ text: '        ', color: '#dae2fd' }, { text: 'await ', color: '#00daf3' }, { text: 'infra.reduce_cost(', color: '#dae2fd' }, { text: '0.70', color: '#00e5ff' }, { text: ')', color: '#dae2fd' }] },
  { line: '11', segments: [{ text: '    ', color: '#dae2fd' }] },
  { line: '12', segments: [{ text: '    # Ship ML pipelines to production', color: '#bac9cc', italic: true }] },
  { line: '13', segments: [{ text: '    async def ', color: '#00daf3' }, { text: 'deploy_model(self, model):', color: '#dae2fd' }] },
  { line: '14', segments: [{ text: '        ', color: '#dae2fd' }, { text: 'await ', color: '#00daf3' }, { text: 'aws.lambda_deploy(model)', color: '#dae2fd' }] },
  { line: '15', segments: [{ text: '        ', color: '#dae2fd' }, { text: 'return ', color: '#00daf3' }, { text: 'self.', color: '#dae2fd' }, { text: 'accuracy', color: '#00e5ff' }] },
];

export default function Home() {
  const leadingSpaces = (segments: typeof terminalLines[0]['segments']) => {
    const first = segments[0]?.text ?? '';
    const m = first.match(/^( +)/);
    return m ? m[1].length : 0;
  };
  return (
    <>
      <main className="relative min-h-screen flex flex-col justify-center overflow-hidden pt-20 bg-[#0b1326]">
        {/* Background decorative elements */}
        <div aria-hidden="true" className="absolute inset-0 z-0 overflow-hidden pointer-events-none">
          <div
            className="absolute top-[10%] right-[-5%] w-[600px] h-[600px] rounded-full blur-[120px]"
            style={{ background: 'rgba(195, 245, 255, 0.05)' }}
          />
          <div
            className="absolute bottom-[-10%] left-[-5%] w-[500px] h-[500px] rounded-full blur-[100px]"
            style={{ background: 'rgba(0, 229, 255, 0.05)' }}
          />
          <div
            className="absolute inset-0 opacity-[0.03]"
            style={{
              backgroundImage: 'radial-gradient(circle at 2px 2px, #c3f5ff 1px, transparent 0)',
              backgroundSize: '40px 40px',
            }}
          />
        </div>

        <div className="max-w-7xl mx-auto px-8 w-full relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center py-24">
          {/* Left: Hero content */}
          <div className="lg:col-span-7 space-y-10 pl-0 lg:pl-20">
            <div className="inline-flex items-center gap-3 px-3 py-1 bg-[#222a3d] rounded-lg outline outline-1 outline-[#3b494c]/15">
              <span className="w-2 h-2 rounded-full bg-[#00e5ff] animate-pulse" />
              <span className="text-[0.75rem] font-medium tracking-[0.1rem] uppercase text-[#c3f5ff]">
                Lead Engineer · 7 Years
              </span>
            </div>

            <h1 className="text-5xl md:text-7xl font-bold tracking-tighter text-[#dae2fd] leading-[1.1]" style={{ fontFamily: 'Space Grotesk, sans-serif' }}>
              Architecting{' '}
              <span className="bg-gradient-to-r from-[#c3f5ff] to-[#00e5ff] bg-clip-text text-transparent">
                Scalable, Intelligent
              </span>{' '}
              Systems
            </h1>

            <p className="text-[#bac9cc] text-lg md:text-xl max-w-xl leading-relaxed">
              Lead Engineer with 7 years of experience building distributed backends, cloud-native platforms on AWS,
              and GenAI applications using LLMs. I&apos;ve reduced infrastructure costs by ~70%, automated workflows
              to boost productivity by ~87%, and shipped ML systems across fintech and healthcare.
            </p>

            {/* Skill tags */}
            <div className="flex flex-wrap gap-4 pt-4">
              {skills.map(({ icon, label }) => (
                <div
                  key={label}
                  className="flex items-center gap-2 px-4 py-2 bg-[#131b2e] rounded-lg outline outline-1 outline-[#3b494c]/10 hover:bg-[#222a3d] transition-colors"
                >
                  <span className="material-symbols-outlined text-[#c3f5ff]" style={{ fontSize: '1rem' }}>{icon}</span>
                  <span className="text-sm text-[#dae2fd]">{label}</span>
                </div>
              ))}
            </div>

            {/* CTA buttons */}
            <div className="flex flex-wrap gap-6 pt-6">
              <Link
                href="/blogs"
                className="px-8 py-4 bg-gradient-to-br from-[#c3f5ff] to-[#00e5ff] text-[#00363d] font-bold rounded-lg shadow-[0_10px_30px_-10px_rgba(0,218,243,0.3)] hover:-translate-y-0.5 transition-all duration-300"
              >
                Read My Blog
              </Link>
              <Link
                href="/talk"
                className="px-8 py-4 bg-transparent border border-[#849396]/20 text-[#dae2fd] font-bold rounded-lg hover:bg-[#222a3d] transition-all duration-300 flex items-center gap-2"
              >
                Talk to My Digital Twin!
                <span className="material-symbols-outlined" style={{ fontSize: '1rem' }}>arrow_forward</span>
              </Link>
            </div>
          </div>

          {/* Right: Terminal card */}
          <div className="lg:col-span-5 hidden lg:block pr-10">
            <div className="relative">
              <div className="bg-[#060e20] rounded-xl outline outline-1 outline-[#3b494c]/20 shadow-2xl overflow-hidden flex flex-col">
                {/* Terminal header */}
                <div className="bg-[#2d3449] px-4 py-3 flex items-center justify-between">
                  <div className="flex gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#ffb4ab]/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-[#b9c7df]/50" />
                    <div className="w-2.5 h-2.5 rounded-full bg-[#00e5ff]/50" />
                  </div>
                  <div className="text-[0.65rem] font-mono text-[#849396] uppercase tracking-widest">
                    digital_twin.py
                  </div>
                </div>

                {/* Terminal body */}
                <div className="p-6 font-mono text-sm space-y-3">
                  {terminalLines.map(({ line, segments }) => {
                    const indent = leadingSpaces(segments);
                    return (
                      <div key={line} className="flex gap-4">
                        <span className="text-[#849396]/40 select-none shrink-0">{line}</span>
                        <span style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word', display: 'block', paddingLeft: `${indent}ch`, textIndent: `-${indent}ch` }}>
                          {segments.map((seg, i) => (
                            <span key={i} style={{ color: seg.color, fontStyle: seg.italic ? 'italic' : undefined }}>
                              {seg.text}
                            </span>
                          ))}
                        </span>
                      </div>
                    );
                  })}

                  {/* Metric cards */}
                  <div className="pt-6 grid grid-cols-2 gap-3">
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">Cost Reduction</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">~70%</div>
                    </div>
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">Productivity Boost</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">~87%</div>
                    </div>
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">ML Accuracy</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">83%</div>
                    </div>
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">Claim Time</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">15→5 min</div>
                    </div>
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">Events / Day</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">Millions</div>
                    </div>
                    <div className="p-4 bg-[#222a3d] rounded-lg outline outline-1 outline-[#c3f5ff]/10">
                      <div className="text-[0.6rem] text-[#849396] uppercase tracking-tighter">Experience</div>
                      <div className="text-xl font-bold text-[#c3f5ff]">7 Years</div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Accent decorations */}
              <div className="absolute -top-6 -right-6 w-24 h-24 bg-[#c3f5ff]/10 rounded-xl -z-10 rotate-12" />
              <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-[#00e5ff]/10 rounded-full -z-10 blur-2xl" />
            </div>
          </div>
        </div>
      </main>

    </>
  );
}