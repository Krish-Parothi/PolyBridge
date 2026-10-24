import React from 'react';
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Braces,
  CheckCircle2,
  Code2,
  Cpu,
  GitBranch,
  Layers3,
  ShieldCheck,
  Terminal,
} from 'lucide-react';
import './LandingPage.css';

interface LandingPageProps {
  onLaunchWorkbench: () => void;
}

const languageList = [
  { label: 'Python 3', tone: 'peach' },
  { label: 'JavaScript ES6', tone: 'yellow' },
  { label: 'Java 17', tone: 'blue' },
  { label: 'Go 1.21', tone: 'mint' },
  { label: 'C++20', tone: 'lavender' },
  { label: 'Arduino C++', tone: 'coral' },
  { label: 'Verilog 2001', tone: 'ink' },
];

const pipeline = [
  { number: '01', title: 'Parse', text: 'Tree-sitter frontends turn source into a stable syntax tree.', icon: Code2 },
  { number: '02', title: 'Normalize', text: 'One language-neutral IR makes the translation path inspectable.', icon: Layers3 },
  { number: '03', title: 'Emit', text: 'Deterministic backends generate readable target code.', icon: Braces },
  { number: '04', title: 'Verify', text: 'Real subprocesses compare behavior, not screenshots.', icon: ShieldCheck },
];

export const LandingPage: React.FC<LandingPageProps> = ({ onLaunchWorkbench }) => {
  return (
    <div className="landing-shell">
      <div className="landing-grid" aria-hidden="true" />

      <header className="landing-nav">
        <button className="landing-brand" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          <span className="landing-brand-mark"><span /><span /><span /></span>
          <span>
            <strong>PolyBridge</strong>
            <small>compiler workbench</small>
          </span>
        </button>

        <nav className="landing-nav-links" aria-label="Landing page navigation">
          <a href="#method">Method</a>
          <a href="#languages">Languages</a>
          <a href="#verification">Verification</a>
          <button className="landing-nav-button" onClick={onLaunchWorkbench}>
            Open workbench <ArrowUpRight size={15} />
          </button>
        </nav>
      </header>

      <main>
        <section className="landing-hero">
          <div className="landing-hero-copy">
            <div className="landing-eyebrow">
              <span className="eyebrow-dot" />
              <span>Universal IR / deterministic translation</span>
              <span className="eyebrow-rule" />
              <span>v1.0</span>
            </div>

            <h1>Move code<br /><em>without losing the plot.</em></h1>
            <p className="landing-lede">
              PolyBridge is a transparent compiler workbench for translating, inspecting,
              and verifying programs across seven languages through one shared intermediate representation.
            </p>

            <div className="landing-hero-actions">
              <button className="landing-primary-button" onClick={onLaunchWorkbench}>
                Start translating <ArrowRight size={17} />
              </button>
              <a className="landing-text-button" href="#method">
                See the pipeline <span>↓</span>
              </a>
            </div>

            <div className="landing-proof-row">
              <span><CheckCircle2 size={14} /> 49/49 sample pairs verified</span>
              <span><Activity size={14} /> actual compile + run checks</span>
            </div>
          </div>

          <div className="landing-console-card" aria-label="PolyBridge compiler pipeline preview">
            <div className="console-topbar">
              <div className="console-lights"><i /><i /><i /></div>
              <span>polybridge / trace</span>
              <span className="console-live"><span /> LIVE</span>
            </div>

            <div className="console-body">
              <div className="console-source-label"><span>source</span><span>python</span></div>
              <pre className="console-code"><code>{`def total(values):
    result = 0
    for value in values:
        result += value
    return result`}</code></pre>

              <div className="console-bridge-line">
                <span className="bridge-node">parse</span>
                <span className="bridge-dash" />
                <span className="bridge-node bridge-node-accent">universal IR</span>
                <span className="bridge-dash" />
                <span className="bridge-node">emit</span>
              </div>

              <div className="console-ir-preview">
                <div><span className="ir-key">ForRange</span><span className="ir-muted"> iterator: value</span></div>
                <div><span className="ir-key">Assignment</span><span className="ir-muted"> result += value</span></div>
                <div><span className="ir-key">Return</span><span className="ir-muted"> result : int</span></div>
              </div>

              <div className="console-output-row">
                <div><span className="output-kicker">target</span><strong>Go 1.21</strong></div>
                <div className="output-status"><span /> compiled / executed</div>
              </div>
            </div>

            <div className="console-footer">
              <span><Terminal size={13} /> stdout</span>
              <strong>42</strong>
              <span className="footer-check"><CheckCircle2 size={13} /> match</span>
            </div>
          </div>
        </section>

        <section className="landing-stats" aria-label="PolyBridge capabilities">
          <div><strong>7</strong><span>source languages</span></div>
          <div><strong>1</strong><span>shared IR</span></div>
          <div><strong>49</strong><span>sample paths checked</span></div>
          <div><strong>0</strong><span>black-box steps</span></div>
        </section>

        <section className="landing-section landing-method" id="method">
          <div className="section-intro">
            <span className="section-kicker">01 / the method</span>
            <h2>Every translation<br /><em>leaves a trail.</em></h2>
            <p>
              No opaque rewrite happens between the editor and the output. You can inspect the tree,
              follow the IR, read the generated code, and run both sides with the same inputs.
            </p>
          </div>

          <div className="pipeline-list">
            {pipeline.map(({ number, title, text, icon: Icon }) => (
              <div className="pipeline-item" key={number}>
                <span className="pipeline-number">{number}</span>
                <span className="pipeline-icon"><Icon size={17} /></span>
                <div><h3>{title}</h3><p>{text}</p></div>
                <ArrowUpRight className="pipeline-arrow" size={16} />
              </div>
            ))}
          </div>
        </section>

        <section className="landing-section landing-languages" id="languages">
          <div className="section-intro section-intro-wide">
            <span className="section-kicker">02 / the bridge</span>
            <h2>One workbench.<br /><em>Many dialects.</em></h2>
            <p>Use the same algorithm as a Rosetta stone, then inspect how each backend expresses it.</p>
          </div>

          <div className="language-board">
            <div className="language-board-head"><span>supported frontends &amp; emitters</span><span>source ↔ target</span></div>
            <div className="language-chip-grid">
              {languageList.map((language) => (
                <div className={`language-chip language-chip-${language.tone}`} key={language.label}>
                  <span className="language-chip-mark" />
                  <strong>{language.label}</strong>
                  <ArrowUpRight size={14} />
                </div>
              ))}
            </div>
            <div className="language-board-note"><GitBranch size={15} /> Translate through the hub, not through 42 hand-written pairings.</div>
          </div>
        </section>

        <section className="landing-section landing-verification" id="verification">
          <div className="verification-card">
            <div className="verification-card-top">
              <span className="section-kicker">03 / the proof</span>
              <span className="verification-stamp"><ShieldCheck size={14} /> execution-based</span>
            </div>
            <div className="verification-card-grid">
              <div>
                <h2>Looks right<br /><em>is not enough.</em></h2>
                <p>PolyBridge compiles and runs the source and target separately, compares exit codes and output, and shows the discrepancy when behavior diverges.</p>
                <button className="landing-inline-button" onClick={onLaunchWorkbench}>Try the workbench <ArrowRight size={15} /></button>
              </div>
              <div className="verification-diagram">
                <div className="verify-track"><span className="verify-dot verify-dot-source" /><span>source program</span><strong>→</strong><span className="verify-box">run</span></div>
                <div className="verify-track"><span className="verify-dot verify-dot-target" /><span>translated program</span><strong>→</strong><span className="verify-box">run</span></div>
                <div className="verify-compare"><span>same input</span><span className="compare-line" /><span className="compare-badge"><CheckCircle2 size={13} /> compare</span></div>
              </div>
            </div>
          </div>
        </section>

        <section className="landing-closing">
          <div className="closing-mark"><Cpu size={19} /></div>
          <p className="section-kicker">Make the compiler visible</p>
          <h2>Bring an algorithm.<br /><em>Leave with evidence.</em></h2>
          <button className="landing-primary-button" onClick={onLaunchWorkbench}>Open PolyBridge <ArrowUpRight size={17} /></button>
        </section>
      </main>

      <footer className="landing-footer">
        <span>PolyBridge / Universal IR Compiler Workbench</span>
        <span>built for readable translation and honest verification</span>
      </footer>
    </div>
  );
};
