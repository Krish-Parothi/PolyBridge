import React, { useState } from 'react';
import { Clock, RotateCcw, Zap, ChevronRight } from 'lucide-react';
import type { HlsMetadata } from './CircuitSchematicViewer';

interface CycleTimingWaveformProps {
  metadata: HlsMetadata | null;
}

export const CycleTimingWaveform: React.FC<CycleTimingWaveformProps> = ({ metadata }) => {
  const [selectedCycle, setSelectedCycle] = useState<number>(1);

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
        <Clock size={36} style={{ color: 'var(--text-muted)', marginBottom: 12, opacity: 0.6 }} />
        <h3 style={{ margin: '0 0 6px 0', fontSize: 14, color: 'var(--text-secondary)' }}>
          No Cycle Timing Data Synthesized
        </h3>
        <p style={{ margin: 0, fontSize: 11.5, maxWidth: 320, lineHeight: 1.5 }}>
          Transpile to Verilog to generate cycle-accurate digital waveforms and hardware timing analysis.
        </p>
      </div>
    );
  }

  const { is_sequential, metrics, timing_steps = [] } = metadata;
  const steps = timing_steps.length > 0 ? timing_steps : [
    { cycle: 0, time_ns: 0, clk: 0, rst: 1, start: 0, state: 'IDLE', done: 0, result: '0' },
    { cycle: 1, time_ns: 10, clk: 1, rst: 0, start: 1, state: 'IDLE', done: 0, result: '0' },
    { cycle: 2, time_ns: 20, clk: 1, rst: 0, start: 0, state: 'EXEC', done: 0, result: '0' },
    { cycle: 3, time_ns: 30, clk: 1, rst: 0, start: 0, state: 'EXEC', done: 0, result: '0' },
    { cycle: 4, time_ns: 40, clk: 1, rst: 0, start: 0, state: 'DONE', done: 1, result: 'VALID' },
  ];

  const currentStep = steps[Math.min(selectedCycle, steps.length - 1)] || steps[0];

  const handleNextCycle = () => {
    setSelectedCycle((c) => (c + 1) % steps.length);
  };

  const handleReset = () => {
    setSelectedCycle(0);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#090d16',
        color: '#e2e8f0',
        overflow: 'hidden',
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* HUD Header Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 16px',
          background: '#0d131f',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#38bdf8' }}>
            <Clock size={14} />
            <span style={{ fontSize: 12, fontWeight: 700 }}>Cycle-Accurate Hardware Timing</span>
          </div>

          <div style={{ height: 14, width: 1, background: 'rgba(255,255,255,0.1)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontFamily: 'monospace' }}>
            <span style={{ color: '#94a3b8' }}>Latency:</span>
            <span style={{ color: '#34d399', fontWeight: 600 }}>{metrics.latency_cycles}</span>
            <span style={{ color: '#64748b' }}>({metrics.latency_ns})</span>
          </div>

          <div style={{ height: 14, width: 1, background: 'rgba(255,255,255,0.1)' }} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, fontFamily: 'monospace' }}>
            <span style={{ color: '#94a3b8' }}>Freq:</span>
            <span style={{ color: '#f59e0b', fontWeight: 600 }}>~{metrics.max_freq_mhz} MHz</span>
          </div>
        </div>

        {/* Stepper Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <button
            onClick={handleReset}
            title="Reset to Cycle 0"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              borderRadius: 4,
              border: '1px solid rgba(255, 255, 255, 0.12)',
              background: '#1e293b',
              color: '#94a3b8',
              fontSize: 10.5,
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={11} /> Reset
          </button>

          <button
            onClick={handleNextCycle}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '4px 10px',
              borderRadius: 4,
              border: 'none',
              background: '#0284c7',
              color: '#ffffff',
              fontSize: 11,
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 0 10px rgba(2, 132, 199, 0.3)',
            }}
          >
            <ChevronRight size={13} /> Next Cycle ({selectedCycle + 1}/{steps.length})
          </button>
        </div>
      </div>

      {/* Main Content: Waveform Tracks + Inspector Panel */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Left: Digital Timing Waveform Canvas */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: 16, overflowY: 'auto' }}>
          <div
            style={{
              background: '#0f172a',
              borderRadius: 8,
              border: '1px solid rgba(255, 255, 255, 0.08)',
              padding: '16px 20px',
              boxShadow: 'inset 0 0 20px rgba(0, 0, 0, 0.5)',
            }}
          >
            {/* Waveform Axis Header */}
            <div style={{ display: 'flex', marginBottom: 16, borderBottom: '1px solid rgba(255,255,255,0.08)', paddingBottom: 8 }}>
              <div style={{ width: 110, fontSize: 11, fontWeight: 700, color: '#64748b', fontFamily: 'monospace' }}>
                SIGNAL
              </div>
              <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', fontFamily: 'monospace', fontSize: 10, color: '#94a3b8' }}>
                {steps.map((st, idx) => (
                  <div
                    key={idx}
                    onClick={() => setSelectedCycle(idx)}
                    style={{
                      cursor: 'pointer',
                      textAlign: 'center',
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: selectedCycle === idx ? '#0284c7' : 'transparent',
                      color: selectedCycle === idx ? '#ffffff' : '#94a3b8',
                      fontWeight: selectedCycle === idx ? 700 : 500,
                    }}
                  >
                    C{st.cycle} ({st.time_ns}ns)
                  </div>
                ))}
              </div>
            </div>

            {/* Signal Waveform Tracks */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* 1. CLOCK (clk) */}
              <WaveformTrack
                name="clk"
                type="clock"
                color="#f59e0b"
                steps={steps}
                selectedCycle={selectedCycle}
                getValue={(s) => s.clk}
              />

              {/* 2. RESET (rst) */}
              {is_sequential && (
                <WaveformTrack
                  name="rst"
                  type="binary"
                  color="#ef4444"
                  steps={steps}
                  selectedCycle={selectedCycle}
                  getValue={(s) => s.rst}
                />
              )}

              {/* 3. START STROBE (start) */}
              {is_sequential && (
                <WaveformTrack
                  name="start"
                  type="binary"
                  color="#38bdf8"
                  steps={steps}
                  selectedCycle={selectedCycle}
                  getValue={(s) => s.start}
                />
              )}

              {/* 4. STATE MACHINE (state) */}
              {is_sequential && (
                <WaveformTrack
                  name="state [1:0]"
                  type="bus"
                  color="#a855f7"
                  steps={steps}
                  selectedCycle={selectedCycle}
                  getValue={(s) => s.state}
                />
              )}

              {/* 5. DONE STROBE (done) */}
              {is_sequential && (
                <WaveformTrack
                  name="done"
                  type="binary"
                  color="#10b981"
                  steps={steps}
                  selectedCycle={selectedCycle}
                  getValue={(s) => s.done}
                />
              )}

              {/* 6. RESULT DATA BUS (result[31:0]) */}
              <WaveformTrack
                name="result [31:0]"
                type="bus"
                color="#34d399"
                steps={steps}
                selectedCycle={selectedCycle}
                getValue={(s) => s.result}
              />
            </div>
          </div>
        </div>

        {/* Right: Real-time Signal State Inspector */}
        <div
          style={{
            width: 250,
            borderLeft: '1px solid rgba(255, 255, 255, 0.08)',
            background: '#0d131f',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 14,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8' }}>
              Cycle C{currentStep.cycle} State
            </span>
            <span style={{ fontSize: 10, fontFamily: 'monospace', color: '#94a3b8', background: '#1e293b', padding: '2px 6px', borderRadius: 4 }}>
              t = {currentStep.time_ns} ns
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 11, fontFamily: 'monospace' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
              <span style={{ color: '#94a3b8' }}>clk</span>
              <span style={{ color: '#f59e0b', fontWeight: 600 }}>{currentStep.clk}</span>
            </div>

            {is_sequential && (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
                  <span style={{ color: '#94a3b8' }}>rst</span>
                  <span style={{ color: currentStep.rst ? '#ef4444' : '#64748b', fontWeight: 600 }}>
                    {currentStep.rst}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
                  <span style={{ color: '#94a3b8' }}>start</span>
                  <span style={{ color: currentStep.start ? '#38bdf8' : '#64748b', fontWeight: 600 }}>
                    {currentStep.start}
                  </span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
                  <span style={{ color: '#94a3b8' }}>state</span>
                  <span style={{ color: '#a855f7', fontWeight: 600 }}>{currentStep.state}</span>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
                  <span style={{ color: '#94a3b8' }}>done</span>
                  <span style={{ color: currentStep.done ? '#10b981' : '#64748b', fontWeight: 600 }}>
                    {currentStep.done}
                  </span>
                </div>
              </>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 8px', background: '#111827', borderRadius: 4 }}>
              <span style={{ color: '#94a3b8' }}>result</span>
              <span style={{ color: '#34d399', fontWeight: 600 }}>{currentStep.result}</span>
            </div>
          </div>

          {/* Timing Note */}
          <div
            style={{
              marginTop: 'auto',
              padding: 10,
              borderRadius: 6,
              background: 'rgba(56, 189, 248, 0.08)',
              border: '1px solid rgba(56, 189, 248, 0.2)',
              fontSize: 10.5,
              color: '#94a3b8',
              lineHeight: 1.5,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#38bdf8', marginBottom: 4, fontWeight: 600 }}>
              <Zap size={11} /> Waveform Simulation
            </div>
            Digital signals reflect IEEE 1364-2001 synthesizable hardware behavior. Ready for testbench `$dumpfile` &amp; GTKWave verification.
          </div>
        </div>
      </div>
    </div>
  );
};

// Sub-component: Waveform Track
interface WaveformTrackProps {
  name: string;
  type: 'clock' | 'binary' | 'bus';
  color: string;
  steps: any[];
  selectedCycle: number;
  getValue: (step: any) => any;
}

const WaveformTrack: React.FC<WaveformTrackProps> = ({ name, type, color, steps, selectedCycle, getValue }) => {
  return (
    <div style={{ display: 'flex', alignItems: 'center' }}>
      <div style={{ width: 110, fontSize: 11, fontFamily: 'monospace', color: '#e2e8f0', fontWeight: 600 }}>
        {name}
      </div>

      <div style={{ flex: 1, display: 'flex', height: 26, background: 'rgba(0,0,0,0.25)', borderRadius: 4, position: 'relative' }}>
        {steps.map((st, idx) => {
          const val = getValue(st);
          const isHigh = val === 1 || val === true;
          const isSelected = selectedCycle === idx;

          return (
            <div
              key={idx}
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                borderRight: '1px dashed rgba(255,255,255,0.08)',
                background: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'transparent',
                position: 'relative',
              }}
            >
              {type === 'clock' ? (
                // Clock square pulse
                <svg width="100%" height="100%" viewBox="0 0 100 24" preserveAspectRatio="none">
                  <path d="M 0 20 L 50 20 L 50 4 L 100 4" stroke={color} strokeWidth="2" fill="none" />
                </svg>
              ) : type === 'binary' ? (
                // Binary High/Low
                <svg width="100%" height="100%" viewBox="0 0 100 24" preserveAspectRatio="none">
                  <path
                    d={isHigh ? 'M 0 4 L 100 4' : 'M 0 20 L 100 20'}
                    stroke={isHigh ? color : '#475569'}
                    strokeWidth="2"
                    fill="none"
                  />
                </svg>
              ) : (
                // Bus Hex / State Polygon
                <div
                  style={{
                    width: '90%',
                    height: 18,
                    background: 'rgba(255,255,255,0.06)',
                    border: `1px solid ${color}`,
                    borderRadius: 3,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: 9.5,
                    fontFamily: 'monospace',
                    color: color,
                    fontWeight: 700,
                  }}
                >
                  {String(val)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
