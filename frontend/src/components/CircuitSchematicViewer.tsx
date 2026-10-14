import React, { useState } from 'react';
import { Cpu, Zap, Activity, GitBranch, ShieldCheck, ArrowRight } from 'lucide-react';

export interface HlsPort {
  name: string;
  direction: 'input' | 'output';
  width: number;
  type: string;
}

export interface HlsMetrics {
  estimated_luts: number;
  estimated_ffs: number;
  clock_period_ns: number;
  max_freq_mhz: number;
  latency_cycles: string;
  latency_ns: string;
  throughput: string;
}

export interface HlsMetadata {
  module_name: string;
  is_sequential: boolean;
  architecture: string;
  ports: HlsPort[];
  registers: string[];
  operations: string[];
  fsm_states: string[];
  metrics: HlsMetrics;
  timing_steps?: any[];
}

interface CircuitSchematicViewerProps {
  metadata: HlsMetadata | null;
}

export const CircuitSchematicViewer: React.FC<CircuitSchematicViewerProps> = ({ metadata }) => {
  const [activeTab, setActiveTab] = useState<'schematic' | 'fsm' | 'specs'>('schematic');
  const [selectedElement, setSelectedElement] = useState<string | null>(null);

  if (!metadata) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 24,
          background: 'var(--bg-surface)',
          color: 'var(--text-muted)',
          textAlign: 'center',
        }}
      >
        <Cpu size={36} style={{ color: 'var(--text-muted)', marginBottom: 12, opacity: 0.6 }} />
        <h3 style={{ margin: '0 0 6px 0', fontSize: 14, color: 'var(--text-secondary)' }}>
          No Hardware RTL Synthesized Yet
        </h3>
        <p style={{ margin: 0, fontSize: 11.5, maxWidth: 320, lineHeight: 1.5 }}>
          Write your algorithm in the source editor and click <strong>Transpile</strong> with Verilog target to synthesize the hardware circuit diagram.
        </p>
      </div>
    );
  }

  const {
    module_name,
    is_sequential,
    ports,
    registers,
    operations,
    metrics,
  } = metadata;

  const inputPorts = ports.filter((p) => p.direction === 'input');
  const outputPorts = ports.filter((p) => p.direction === 'output');

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#0a0d14',
        color: '#e2e8f0',
        overflow: 'hidden',
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* Top Bar: Sub-tabs and architecture badge */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 14px',
          background: '#0d131f',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={() => setActiveTab('schematic')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '3px 10px',
              fontSize: 11,
              fontWeight: activeTab === 'schematic' ? 600 : 500,
              borderRadius: 4,
              border: 'none',
              background: activeTab === 'schematic' ? '#0284c7' : 'transparent',
              color: activeTab === 'schematic' ? '#ffffff' : '#94a3b8',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Cpu size={12} /> RTL Circuit Schematic
          </button>

          {is_sequential && (
            <button
              onClick={() => setActiveTab('fsm')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 5,
                padding: '3px 10px',
                fontSize: 11,
                fontWeight: activeTab === 'fsm' ? 600 : 500,
                borderRadius: 4,
                border: 'none',
                background: activeTab === 'fsm' ? '#0284c7' : 'transparent',
                color: activeTab === 'fsm' ? '#ffffff' : '#94a3b8',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <GitBranch size={12} /> FSM State Machine
            </button>
          )}

          <button
            onClick={() => setActiveTab('specs')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '3px 10px',
              fontSize: 11,
              fontWeight: activeTab === 'specs' ? 600 : 500,
              borderRadius: 4,
              border: 'none',
              background: activeTab === 'specs' ? '#0284c7' : 'transparent',
              color: activeTab === 'specs' ? '#ffffff' : '#94a3b8',
              cursor: 'pointer',
              transition: 'all 0.15s ease',
            }}
          >
            <Activity size={12} /> Hardware Specs
          </button>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11 }}>
          <span
            style={{
              padding: '2px 8px',
              borderRadius: 12,
              background: is_sequential ? 'rgba(56, 189, 248, 0.15)' : 'rgba(52, 211, 153, 0.15)',
              color: is_sequential ? '#38bdf8' : '#34d399',
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              border: `1px solid ${is_sequential ? 'rgba(56, 189, 248, 0.3)' : 'rgba(52, 211, 153, 0.3)'}`,
            }}
          >
            {is_sequential ? 'Clocked Sequential FSM' : 'Zero-Latency Combinational Logic'}
          </span>
        </div>
      </div>

      {/* Main Interactive Display Area */}
      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflowY: 'auto' }}>
        {activeTab === 'schematic' && (
          <div style={{ padding: 20, minWidth: 620, height: '100%', boxSizing: 'border-box' }}>
            {/* SVG Schematic Canvas */}
            <svg
              viewBox="0 0 740 380"
              style={{
                width: '100%',
                maxHeight: '100%',
                background: 'radial-gradient(circle at 50% 50%, #0f172a 0%, #090d16 100%)',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)',
                boxShadow: 'inset 0 0 30px rgba(0, 0, 0, 0.5)',
              }}
            >
              <defs>
                <linearGradient id="aluGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#1e293b" />
                  <stop offset="100%" stopColor="#0f172a" />
                </linearGradient>
                <linearGradient id="fsmGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#0c4a6e" />
                  <stop offset="100%" stopColor="#075985" />
                </linearGradient>
                <linearGradient id="wireGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#38bdf8" />
                  <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
                <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                  <feGaussianBlur stdDeviation="3" result="blur" />
                  <feComposite in="SourceGraphic" in2="blur" operator="over" />
                </filter>
              </defs>

              {/* Grid Background Pattern */}
              <pattern id="grid" width="20" height="20" patternUnits="userSpaceOnUse">
                <path d="M 20 0 L 0 0 0 20" fill="none" stroke="rgba(255, 255, 255, 0.03)" strokeWidth="1" />
              </pattern>
              <rect width="100%" height="100%" fill="url(#grid)" />

              {/* Module Boundary */}
              <rect
                x="40"
                y="30"
                width="660"
                height="320"
                rx="12"
                fill="none"
                stroke="rgba(56, 189, 248, 0.35)"
                strokeWidth="1.5"
                strokeDasharray="6 3"
              />
              <text x="56" y="52" fill="#38bdf8" fontSize="12" fontWeight="700" fontFamily="monospace">
                module {module_name} (IEEE 1364-2001 Synthesizable RTL)
              </text>

              {/* ================= LEFT: INPUT PORTS ================= */}
              {inputPorts.map((port, idx) => {
                const y = 80 + idx * 40;
                const isClock = port.name === 'clk';
                const isReset = port.name === 'rst';
                const isControl = port.name === 'start';
                const color = isClock ? '#f59e0b' : isReset ? '#ef4444' : isControl ? '#10b981' : '#38bdf8';

                return (
                  <g
                    key={port.name}
                    cursor="pointer"
                    onClick={() => setSelectedElement(`Input Port: ${port.name} (${port.width}-bit ${port.type})`)}
                  >
                    {/* Input Pin Pad */}
                    <rect x="15" y={y - 12} width="55" height="24" rx="4" fill="#1e293b" stroke={color} strokeWidth="1.5" />
                    <text x="42" y={y + 4} fill={color} fontSize="11" fontWeight="600" textAnchor="middle" fontFamily="monospace">
                      {port.name}
                    </text>
                    {/* Wire to internal block */}
                    <path
                      d={`M 70 ${y} L 180 ${y}`}
                      stroke={color}
                      strokeWidth={port.width > 1 ? 2.5 : 1.5}
                      fill="none"
                    />
                    {/* Bit width slash tag */}
                    {port.width > 1 && (
                      <g>
                        <line x1="100" y1={y - 5} x2="108" y2={y + 5} stroke={color} strokeWidth="1.5" />
                        <text x="112" y={y - 4} fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          {port.width}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}

              {/* ================= CENTER: LOGIC & CONTROL BLOCKS ================= */}
              {is_sequential ? (
                // Sequential FSM & Datapath
                <g>
                  {/* FSM Controller Block */}
                  <g
                    cursor="pointer"
                    onClick={() => setSelectedElement('FSM Controller: 3-State Moore machine managing IDLE, EXEC, and DONE transitions.')}
                  >
                    <rect x="180" y="70" width="160" height="110" rx="8" fill="url(#fsmGrad)" stroke="#38bdf8" strokeWidth="2" filter="url(#glow)" />
                    <text x="260" y="98" fill="#ffffff" fontSize="13" fontWeight="700" textAnchor="middle">
                      FSM Controller
                    </text>
                    <text x="260" y="118" fill="#bae6fd" fontSize="10.5" textAnchor="middle" fontFamily="monospace">
                      3 States: IDLE, EXEC, DONE
                    </text>
                    <text x="260" y="136" fill="#7dd3fc" fontSize="9.5" textAnchor="middle">
                      always @(posedge clk)
                    </text>
                    <text x="260" y="156" fill="#38bdf8" fontSize="9" textAnchor="middle" fontWeight="600">
                      Handshake: start → done
                    </text>
                  </g>

                  {/* Datapath ALU / Arithmetic Unit */}
                  <g
                    cursor="pointer"
                    onClick={() => setSelectedElement(`32-bit Arithmetic Core: Executes operations: ${operations.join(', ')}`)}
                  >
                    <polygon
                      points="390,80 490,110 490,170 390,200 390,155 410,140 390,125"
                      fill="url(#aluGrad)"
                      stroke="#06b6d4"
                      strokeWidth="2"
                    />
                    <text x="440" y="145" fill="#38bdf8" fontSize="13" fontWeight="800" textAnchor="middle" fontFamily="monospace">
                      ALU Core
                    </text>
                    <text x="440" y="162" fill="#94a3b8" fontSize="9.5" textAnchor="middle" fontFamily="monospace">
                      {operations.slice(0, 3).join(' ')}
                    </text>
                  </g>

                  {/* Internal D-Flip-Flop Register Array */}
                  <g
                    cursor="pointer"
                    onClick={() => setSelectedElement(`Internal State Registers: [${registers.join(', ')}] latched on clock rising edge.`)}
                  >
                    <rect x="250" y="225" width="220" height="85" rx="6" fill="#1e293b" stroke="#64748b" strokeWidth="1.5" />
                    <text x="360" y="248" fill="#e2e8f0" fontSize="12" fontWeight="700" textAnchor="middle">
                      Sequential Register Bank
                    </text>
                    <text x="360" y="270" fill="#94a3b8" fontSize="10" textAnchor="middle" fontFamily="monospace">
                      {registers.slice(0, 3).join('  ')}
                    </text>
                    <text x="360" y="292" fill="#34d399" fontSize="9" textAnchor="middle">
                      Clocked Synchronous Storage (D-FF)
                    </text>
                  </g>

                  {/* Connecting Wires: FSM to ALU */}
                  <path d="M 340 125 L 390 125" stroke="#38bdf8" strokeWidth="2" fill="none" />
                  {/* ALU to Output */}
                  <path d="M 490 140 L 590 140" stroke="#06b6d4" strokeWidth="3" fill="none" />
                  {/* FSM Done wire to Output */}
                  <path d="M 340 160 L 590 160 L 590 220" stroke="#10b981" strokeWidth="2" fill="none" />
                  {/* Feedback loop from ALU to Registers */}
                  <path d="M 470 170 L 470 225" stroke="#a855f7" strokeWidth="2" strokeDasharray="4 2" fill="none" />
                </g>
              ) : (
                // Pure Combinational ALU / Logic Array
                <g>
                  {/* Combinational Logic Block */}
                  <g
                    cursor="pointer"
                    onClick={() => setSelectedElement(`Combinational Hardware Matrix: Instant zero-latency propagation. Ops: ${operations.join(', ')}`)}
                  >
                    <polygon
                      points="240,70 480,120 480,240 240,290 240,200 270,180 240,160"
                      fill="url(#aluGrad)"
                      stroke="#34d399"
                      strokeWidth="2.5"
                      filter="url(#glow)"
                    />
                    <text x="360" y="165" fill="#34d399" fontSize="16" fontWeight="800" textAnchor="middle" fontFamily="monospace">
                      COMBINATIONAL ALU
                    </text>
                    <text x="360" y="190" fill="#a7f3d0" fontSize="11" textAnchor="middle" fontFamily="monospace">
                      Operations: {operations.join(', ') || 'Math/Bitwise'}
                    </text>
                    <text x="360" y="212" fill="#6ee7b7" fontSize="10" textAnchor="middle">
                      Zero-Clock Latency (Gate Propagation ~3.2ns)
                    </text>
                  </g>

                  {/* Input wires straight into ALU */}
                  <path d="M 180 80 L 250 110" stroke="#38bdf8" strokeWidth="2.5" fill="none" />
                  <path d="M 180 120 L 250 140" stroke="#38bdf8" strokeWidth="2.5" fill="none" />
                  {inputPorts.length > 2 && (
                    <path d="M 180 160 L 250 170" stroke="#38bdf8" strokeWidth="2.5" fill="none" />
                  )}

                  {/* Output wire from ALU to Pad */}
                  <path d="M 480 180 L 600 180" stroke="#34d399" strokeWidth="3" fill="none" />
                </g>
              )}

              {/* ================= RIGHT: OUTPUT PORTS ================= */}
              {outputPorts.map((port) => {
                const y = is_sequential ? (port.name === 'done' ? 220 : 140) : 180;
                const isDone = port.name === 'done';
                const color = isDone ? '#10b981' : '#34d399';

                return (
                  <g
                    key={port.name}
                    cursor="pointer"
                    onClick={() => setSelectedElement(`Output Port: ${port.name} (${port.width}-bit ${port.type})`)}
                  >
                    {/* Output Pad */}
                    <rect x="600" y={y - 14} width="70" height="28" rx="4" fill="#1e293b" stroke={color} strokeWidth="1.5" />
                    <text x="635" y={y + 4} fill={color} fontSize="11" fontWeight="600" textAnchor="middle" fontFamily="monospace">
                      {port.name}
                    </text>
                    {/* Bit width slash tag */}
                    {port.width > 1 && (
                      <g>
                        <line x1="530" y1={y - 5} x2="538" y2={y + 5} stroke={color} strokeWidth="1.5" />
                        <text x="542" y={y - 4} fill="#94a3b8" fontSize="9" fontFamily="monospace">
                          {port.width}
                        </text>
                      </g>
                    )}
                  </g>
                );
              })}
            </svg>

            {/* Inspector Footnote */}
            <div
              style={{
                marginTop: 12,
                padding: '8px 12px',
                borderRadius: 6,
                background: '#111827',
                border: '1px solid rgba(255, 255, 255, 0.08)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 11,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#38bdf8' }}>
                <Zap size={13} />
                <span>
                  <strong>Interactive RTL Inspector:</strong> {selectedElement || 'Click any gate, wire, or port in the circuit diagram above to inspect details.'}
                </span>
              </div>
              <span style={{ color: '#64748b', fontFamily: 'monospace' }}>
                Target: IEEE 1364-2001
              </span>
            </div>
          </div>
        )}

        {/* FSM State Machine Tab */}
        {activeTab === 'fsm' && is_sequential && (
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h4 style={{ margin: 0, fontSize: 13, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
              <GitBranch size={14} /> Finite State Machine (FSM) State Transition Graph
            </h4>

            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 24,
                padding: '30px 20px',
                background: '#0d131f',
                borderRadius: 8,
                border: '1px solid rgba(255, 255, 255, 0.08)',
              }}
            >
              {/* State 0: IDLE */}
              <div
                style={{
                  width: 130,
                  height: 130,
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, #1e293b 0%, #0f172a 100%)',
                  border: '2px solid #38bdf8',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 20px rgba(56, 189, 248, 0.2)',
                  textAlign: 'center',
                }}
              >
                <span style={{ fontSize: 10, color: '#94a3b8', fontFamily: 'monospace' }}>State 2'b00</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>STATE_IDLE</span>
                <span style={{ fontSize: 9.5, color: '#38bdf8', marginTop: 4 }}>Wait for start==1</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 10, color: '#34d399', fontFamily: 'monospace' }}>start == 1</span>
                <ArrowRight size={22} style={{ color: '#38bdf8' }} />
              </div>

              {/* State 1: EXEC */}
              <div
                style={{
                  width: 140,
                  height: 140,
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, #0c4a6e 0%, #082f49 100%)',
                  border: '2px solid #06b6d4',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 24px rgba(6, 182, 212, 0.3)',
                  textAlign: 'center',
                }}
              >
                <span style={{ fontSize: 10, color: '#bae6fd', fontFamily: 'monospace' }}>State 2'b01</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>STATE_EXEC</span>
                <span style={{ fontSize: 9.5, color: '#34d399', marginTop: 4 }}>Loop Iteration</span>
                <span style={{ fontSize: 8.5, color: '#7dd3fc' }}>Loop back if cond</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                <span style={{ fontSize: 10, color: '#f59e0b', fontFamily: 'monospace' }}>Loop exit</span>
                <ArrowRight size={22} style={{ color: '#10b981' }} />
              </div>

              {/* State 2: DONE */}
              <div
                style={{
                  width: 130,
                  height: 130,
                  borderRadius: '50%',
                  background: 'radial-gradient(circle, #064e3b 0%, #022c22 100%)',
                  border: '2px solid #10b981',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  justifyContent: 'center',
                  boxShadow: '0 0 20px rgba(16, 185, 129, 0.2)',
                  textAlign: 'center',
                }}
              >
                <span style={{ fontSize: 10, color: '#a7f3d0', fontFamily: 'monospace' }}>State 2'b10</span>
                <span style={{ fontSize: 13, fontWeight: 700, color: '#ffffff' }}>STATE_DONE</span>
                <span style={{ fontSize: 9.5, color: '#34d399', marginTop: 4 }}>done &lt;= 1'b1</span>
                <span style={{ fontSize: 8.5, color: '#6ee7b7' }}>Latch result</span>
              </div>
            </div>

            <div style={{ fontSize: 11.5, color: '#94a3b8', lineHeight: 1.6, padding: '0 8px' }}>
              <strong>FSM Protocol:</strong> When <code>start</code> pulses high, internal registers capture inputs and move from <code>STATE_IDLE</code> into <code>STATE_EXEC</code>. The arithmetic datapath runs one clock step per iteration. Upon termination condition, the FSM enters <code>STATE_DONE</code>, setting <code>done = 1</code> and latching the stable 32-bit output on <code>result</code>.
            </div>
          </div>
        )}

        {/* Hardware Specs & Metrics Tab */}
        {activeTab === 'specs' && (
          <div style={{ padding: 24, display: 'flex', flexDirection: 'column', gap: 16 }}>
            <h4 style={{ margin: 0, fontSize: 13, color: '#38bdf8', display: 'flex', alignItems: 'center', gap: 6 }}>
              <ShieldCheck size={14} /> Hardware Synthesis Resource &amp; Performance Estimate
            </h4>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 12,
              }}
            >
              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <span style={{ fontSize: 10.5, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Estimated Logic Gates (LUTs)</span>
                <span style={{ fontSize: 20, fontWeight: 700, color: '#38bdf8', fontFamily: 'monospace' }}>
                  {metrics.estimated_luts} LUTs
                </span>
                <span style={{ fontSize: 10, color: '#64748b', display: 'block', marginTop: 4 }}>Xilinx 7-Series / Artix-7</span>
              </div>

              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <span style={{ fontSize: 10.5, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Flip-Flops / Registers</span>
                <span style={{ fontSize: 20, fontWeight: 700, color: '#34d399', fontFamily: 'monospace' }}>
                  {metrics.estimated_ffs} FFs
                </span>
                <span style={{ fontSize: 10, color: '#64748b', display: 'block', marginTop: 4 }}>Clock-Synchronous D-FFs</span>
              </div>

              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <span style={{ fontSize: 10.5, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Target Clock Frequency</span>
                <span style={{ fontSize: 20, fontWeight: 700, color: '#f59e0b', fontFamily: 'monospace' }}>
                  ~{metrics.max_freq_mhz} MHz
                </span>
                <span style={{ fontSize: 10, color: '#64748b', display: 'block', marginTop: 4 }}>T_clk = {metrics.clock_period_ns} ns</span>
              </div>

              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <span style={{ fontSize: 10.5, color: '#94a3b8', display: 'block', marginBottom: 4 }}>Execution Latency</span>
                <span style={{ fontSize: 18, fontWeight: 700, color: '#a855f7', fontFamily: 'monospace' }}>
                  {metrics.latency_cycles}
                </span>
                <span style={{ fontSize: 10, color: '#64748b', display: 'block', marginTop: 4 }}>Delay: {metrics.latency_ns}</span>
              </div>
            </div>

            {/* Ports and Registers Breakdown */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 8 }}>
              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <h5 style={{ margin: '0 0 10px 0', fontSize: 12, color: '#e2e8f0' }}>I/O Pin Mapping</h5>
                <ul style={{ margin: 0, paddingLeft: 16, fontSize: 11, color: '#94a3b8', lineHeight: 1.7, fontFamily: 'monospace' }}>
                  {ports.map((p) => (
                    <li key={p.name}>
                      <span style={{ color: p.direction === 'input' ? '#38bdf8' : '#34d399' }}>
                        {p.direction.toUpperCase()}
                      </span>{' '}
                      [{p.width - 1}:0] <strong>{p.name}</strong> ({p.type})
                    </li>
                  ))}
                </ul>
              </div>

              <div style={{ background: '#0d131f', padding: 14, borderRadius: 8, border: '1px solid rgba(255,255,255,0.08)' }}>
                <h5 style={{ margin: '0 0 10px 0', fontSize: 12, color: '#e2e8f0' }}>Synthesized Operations</h5>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {operations.map((op) => (
                    <span
                      key={op}
                      style={{
                        padding: '3px 8px',
                        borderRadius: 4,
                        background: 'rgba(56, 189, 248, 0.1)',
                        border: '1px solid rgba(56, 189, 248, 0.25)',
                        color: '#38bdf8',
                        fontSize: 11,
                        fontFamily: 'monospace',
                      }}
                    >
                      {op}
                    </span>
                  ))}
                </div>

                <h5 style={{ margin: '14px 0 8px 0', fontSize: 12, color: '#e2e8f0' }}>Target FPGA Compatibility</h5>
                <p style={{ margin: 0, fontSize: 11, color: '#94a3b8', lineHeight: 1.5 }}>
                  Compatible with Xilinx Vivado, Intel Quartus Prime, Lattice Diamond, and Open-Source Yosys/NextPNR synthesis toolchains.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
