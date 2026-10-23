import React from 'react';
import {
  CheckCircle2,
  XCircle,
  Clock,
  AlertTriangle,
  Terminal,
  Wrench,
  Cpu,
} from 'lucide-react';

export interface VerificationResult {
  match: boolean;
  status?: string;
  source_result: {
    stdout: string;
    stderr: string;
    exit_code: number;
    duration_ms: number;
    error?: string | null;
    status?: string;
  };
  target_result: {
    stdout: string;
    stderr: string;
    exit_code: number;
    duration_ms: number;
    error?: string | null;
    status?: string;
  };
  diff: string[];
  normalized_source: string;
  normalized_target: string;
}

interface VerificationDiffProps {
  result: VerificationResult | null;
  isLoading: boolean;
  diagnostics: Array<{ line: number; column: number; severity: string; message: string }>;
  sourceLang: string;
  targetLang: string;
  onAutoFixProcedural?: () => void;
}

export const VerificationDiff: React.FC<VerificationDiffProps> = ({
  result,
  isLoading,
  diagnostics,
  sourceLang,
  targetLang,
  onAutoFixProcedural,
}) => {
  if (isLoading) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 10,
          color: 'var(--text-secondary)',
          background: 'var(--bg-surface)',
        }}
      >
        <div
          style={{
            width: 22,
            height: 22,
            border: '2px solid var(--border-default)',
            borderTopColor: 'var(--accent)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }}
        />
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
        <div
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: 'var(--text-secondary)',
          }}
        >
          Spawning sandboxed runtimes ({sourceLang} &amp; {targetLang}) and comparing normalized stdout...
        </div>
      </div>
    );
  }

  // Display Scope Violations if present
  const errors = diagnostics.filter((d) => d.severity === 'error');
  const hasClassError = errors.some((e) => e.message.toLowerCase().includes('class'));

  if (errors.length > 0) {
    return (
      <div
        style={{
          padding: '12px 16px',
          overflowY: 'auto',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
          background: 'var(--bg-surface)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--color-error)' }}>
            <AlertTriangle size={15} />
            <span style={{ fontSize: 12, fontWeight: 600, fontFamily: 'var(--font-sans)' }}>
              Compiler Scope Diagnostics ({errors.length} error{errors.length > 1 ? 's' : ''})
            </span>
          </div>
          {hasClassError && onAutoFixProcedural && (
            <button
              onClick={onAutoFixProcedural}
              style={{
                background: 'var(--bg-subtle)',
                color: 'var(--accent-text)',
                border: '1px solid var(--accent-border)',
                borderRadius: 'var(--radius-sm)',
                padding: '4px 10px',
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transition: 'background 0.15s ease',
              }}
            >
              <Wrench size={12} />
              Unwrap to Procedural
            </button>
          )}
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {errors.map((err, i) => (
            <div
              key={i}
              style={{
                padding: '6px 10px',
                borderRadius: 'var(--radius-xs)',
                background: 'var(--color-error-bg)',
                border: '1px solid var(--color-error-border)',
                fontSize: 11.5,
                color: 'var(--color-error)',
                fontFamily: 'var(--font-mono)',
                display: 'flex',
                alignItems: 'baseline',
                gap: 8,
              }}
            >
              <span style={{ fontWeight: 600, opacity: 0.85, whiteSpace: 'nowrap' }}>
                [{err.line}:{err.column}]
              </span>
              <span>{err.message}</span>
            </div>
          ))}
        </div>

        {hasClassError && (
          <div
            style={{
              padding: '8px 12px',
              borderRadius: 'var(--radius-sm)',
              background: 'var(--bg-subtle)',
              border: '1px solid var(--border-default)',
              fontSize: 11.5,
              color: 'var(--text-secondary)',
              lineHeight: 1.5,
            }}
          >
            <strong>Scope Constraint:</strong> PolyBridge focuses on educational, transparent procedural algorithms (loops, functions, arrays, math). Standard LeetCode wrapper classes are unwrapped into procedural functions by default.
          </div>
        )}
      </div>
    );
  }

  if (!result) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          fontSize: 12,
          background: 'var(--bg-surface)',
          padding: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
          <Terminal size={15} style={{ opacity: 0.6 }} />
          <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
            $ polybridge verify --source={sourceLang} --target={targetLang}
          </span>
        </div>
        <p style={{ margin: 0, fontSize: 11, color: 'var(--text-muted)' }}>
          Click <strong>Run &amp; Verify</strong> to execute source and target ASTs with identical input and test behavioral equivalence.
        </p>
      </div>
    );
  }

  // Status Classification
  const status = result?.status;
  const isTargetRuntimeMissing =
    status === 'runtime_unavailable' ||
    result?.target_result?.error === 'Go compiler not found' ||
    result?.target_result?.stderr?.includes('Go compiler') ||
    result?.target_result?.error?.includes('compiler not found');
  const isTargetCompilationError = status === 'target_compile_error' || status === 'target_compilation_failure';
  const isSourceCompilationError = status === 'parse_error' || status === 'source_compilation_failure';
  const isTargetRuntimeError = status === 'target_runtime_error' || status === 'target_runtime_failure';
  const isSourceRuntimeError = status === 'source_runtime_error' || status === 'source_runtime_failure';
  const isTimeout = status === 'timeout';
  const isVerificationNotRun = status === 'verification_not_run';

  const isHlsVerified = false;
  const isWarning = isTargetRuntimeMissing || isTimeout;
  const isSuccess = result?.match === true;

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: 'var(--bg-surface)',
      }}
    >
      {/* Verification Status Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 14px',
          background: isWarning
            ? 'var(--color-warning-bg)'
            : isHlsVerified
            ? 'rgba(6, 182, 212, 0.12)'
            : isSuccess
            ? 'var(--color-success-bg)'
            : 'var(--color-error-bg)',
          borderBottom: isWarning
            ? '1px solid var(--color-warning-border)'
            : isHlsVerified
            ? '1px solid rgba(6, 182, 212, 0.3)'
            : isSuccess
            ? '1px solid var(--color-success-border)'
            : '1px solid var(--color-error-border)',
          flexShrink: 0,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {isTargetRuntimeMissing ? (
            <>
              <AlertTriangle size={15} style={{ color: 'var(--color-warning)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-warning)',
                }}
              >
                COMPILER RUNTIME UNAVAILABLE ({targetLang.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Transpilation succeeded, but execution engine requires local runtime installation.
              </span>
            </>
          ) : isTimeout ? (
            <>
              <AlertTriangle size={15} style={{ color: 'var(--color-warning)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-warning)',
                }}
              >
                EXECUTION TIMED OUT
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Program execution exceeded safety time limit.
              </span>
            </>
          ) : isTargetCompilationError ? (
            <>
              <XCircle size={15} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-error)',
                }}
              >
                TARGET COMPILATION FAILURE ({targetLang.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Emitted code failed target compilation. Inspect compiler diagnostic in stderr below.
              </span>
            </>
          ) : isSourceCompilationError ? (
            <>
              <XCircle size={15} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-error)',
                }}
              >
                SOURCE COMPILATION / SYNTAX ERROR ({sourceLang.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Source program failed parse or compilation check.
              </span>
            </>
          ) : isTargetRuntimeError ? (
            <>
              <XCircle size={15} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-error)',
                }}
              >
                TARGET RUNTIME ERROR ({targetLang.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Target executable exited with an unhandled runtime error.
              </span>
            </>
          ) : isSourceRuntimeError ? (
            <>
              <XCircle size={15} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-error)',
                }}
              >
                SOURCE RUNTIME ERROR ({sourceLang.toUpperCase()})
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Source program crashed with an unhandled runtime error.
              </span>
            </>
          ) : isVerificationNotRun ? (
            <>
              <AlertTriangle size={15} style={{ color: 'var(--color-warning)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-warning)',
                }}
              >
                BEHAVIORAL VERIFICATION NOT RUN
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — HDL compilation/simulation is reported separately from software stdout equivalence.
              </span>
            </>
          ) : isHlsVerified ? (
            <>
              <Cpu size={15} style={{ color: '#06b6d4' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: '#06b6d4',
                }}
              >
                HLS SYNTHESIZABLE RTL VERIFIED (STRUCTURAL SUCCESS)
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Hardware RTL &amp; testbench generated. Local hardware simulation requires Icarus Verilog or EDA Playground.
              </span>
            </>
          ) : isSuccess ? (
            <>
              <CheckCircle2 size={15} style={{ color: 'var(--color-success)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-success)',
                }}
              >
                BEHAVIORAL EQUIVALENCE VERIFIED
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Normalized stdout outputs are strictly identical.
              </span>
            </>
          ) : (
            <>
              <XCircle size={15} style={{ color: 'var(--color-error)' }} />
              <span
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--color-error)',
                }}
              >
                BEHAVIORAL DIVERGENCE DETECTED
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                — Discrepancy observed between runtime outputs. Inspect unified diff below.
              </span>
            </>
          )}
        </div>

        {/* Runtime Performance Metrics */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 14,
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            color: 'var(--text-secondary)',
          }}
        >
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Clock size={11} /> {sourceLang}: {result?.source_result.duration_ms} ms
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <Clock size={11} /> {targetLang}: {result?.target_result.duration_ms} ms
          </span>
        </div>
      </div>

      {/* Side-by-side terminal outputs */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Source Output Pane */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid var(--border-default)',
            background: 'var(--term-bg)',
          }}
        >
          <div
            style={{
              padding: '4px 12px',
              fontSize: 10.5,
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              background: 'var(--term-header-bg)',
              color: 'var(--term-text-muted)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <span>{sourceLang.toUpperCase()} STDOUT</span>
            <span
              style={{
                color:
                  result.source_result.exit_code === 0 ? 'var(--color-success)' : 'var(--color-error)',
              }}
            >
              exit {result.source_result.exit_code}
            </span>
          </div>
          <pre
            style={{
              flex: 1,
              padding: '8px 12px',
              margin: 0,
              fontSize: 11.5,
              fontFamily: 'var(--font-mono)',
              color: result.source_result.stderr ? '#fca5a5' : 'var(--term-text)',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.45,
            }}
          >
            {result.source_result.stdout || result.source_result.stderr || '(No output produced)'}
          </pre>
        </div>

        {/* Target Output Pane */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--term-bg)',
          }}
        >
          <div
            style={{
              padding: '4px 12px',
              fontSize: 10.5,
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              background: 'var(--term-header-bg)',
              color: 'var(--term-text-muted)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
            }}
          >
            <span>{targetLang.toUpperCase()} STDOUT</span>
            <span
              style={{
                color:
                  result.target_result.exit_code === 0 ? 'var(--color-success)' : 'var(--color-error)',
              }}
            >
              exit {result.target_result.exit_code}
            </span>
          </div>
          <pre
            style={{
              flex: 1,
              padding: '8px 12px',
              margin: 0,
              fontSize: 11.5,
              fontFamily: 'var(--font-mono)',
              color: result.target_result.stderr ? '#fca5a5' : 'var(--term-text)',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.45,
            }}
          >
            {result.target_result.stdout || result.target_result.stderr || '(No output produced)'}
          </pre>
        </div>
      </div>

      {/* HLS Verification Footer Information */}
      {isHlsVerified && (
        <div
          style={{
            background: 'rgba(6, 182, 212, 0.05)',
            borderTop: '1px solid rgba(6, 182, 212, 0.2)',
            padding: '7px 14px',
            fontSize: 11,
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={14} style={{ color: '#06b6d4', flexShrink: 0 }} />
            <span>
              <strong>HLS Hardware Mode:</strong> Verilog RTL &amp; testbench ready for FPGA synthesis or simulation on <a href="https://www.edaplayground.com" target="_blank" rel="noreferrer" style={{ color: '#06b6d4', textDecoration: 'underline' }}>edaplayground.com</a>.
            </span>
          </div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10.5, color: '#06b6d4' }}>
            Local Simulation: winget install Icarus.Verilog
          </span>
        </div>
      )}

      {/* Unified Output Diff on Mismatch */}
      {!result.match && !isHlsVerified && result.diff.length > 0 && (
        <div
          style={{
            maxHeight: 110,
            overflowY: 'auto',
            background: 'var(--bg-subtle)',
            borderTop: '1px solid var(--color-error-border)',
            padding: '6px 12px',
            flexShrink: 0,
          }}
        >
          <div
            style={{
              fontSize: 10.5,
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              color: 'var(--color-error)',
              marginBottom: 4,
            }}
          >
            Unified Output Diff:
          </div>
          {result.diff.map((line, idx) => {
            const isAdd = line.startsWith('+');
            const isSub = line.startsWith('-');
            return (
              <div
                key={idx}
                style={{
                  fontFamily: 'var(--font-mono)',
                  fontSize: 11,
                  lineHeight: 1.4,
                  color: isAdd
                    ? 'var(--color-success)'
                    : isSub
                    ? 'var(--color-error)'
                    : 'var(--text-secondary)',
                  background: isAdd
                    ? 'rgba(26, 127, 55, 0.08)'
                    : isSub
                    ? 'rgba(207, 34, 46, 0.08)'
                    : 'transparent',
                  padding: '1px 4px',
                  borderRadius: 2,
                }}
              >
                {line}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
