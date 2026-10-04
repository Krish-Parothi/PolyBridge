import React from 'react';
import { CheckCircle2, XCircle, Clock, AlertTriangle, Terminal } from 'lucide-react';

export interface VerificationResult {
  match: boolean;
  source_result: {
    stdout: string;
    stderr: string;
    exit_code: number;
    duration_ms: number;
    error?: string | null;
  };
  target_result: {
    stdout: string;
    stderr: string;
    exit_code: number;
    duration_ms: number;
    error?: string | null;
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
}

export const VerificationDiff: React.FC<VerificationDiffProps> = ({
  result,
  isLoading,
  diagnostics,
  sourceLang,
  targetLang,
}) => {
  if (isLoading) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, color: '#94a3b8' }}>
        <div style={{
          width: 20,
          height: 20,
          border: '2px solid rgba(99, 102, 241, 0.3)',
          borderTopColor: '#6366f1',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite'
        }} />
        <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
        <span style={{ fontSize: 13, fontFamily: "'Inter', sans-serif" }}>
          Executing both programs in isolated sandbox & comparing outputs...
        </span>
      </div>
    );
  }

  // Display Scope Violations if present
  const errors = diagnostics.filter((d) => d.severity === 'error');
  if (errors.length > 0) {
    return (
      <div style={{ padding: '12px 16px', overflowY: 'auto', height: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8, color: '#f43f5e' }}>
          <AlertTriangle size={18} />
          <strong style={{ fontSize: 13 }}>Diagnostic Scope Violations Detected</strong>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {errors.map((err, i) => (
            <div
              key={i}
              style={{
                padding: '8px 12px',
                borderRadius: 6,
                background: 'rgba(244, 63, 94, 0.1)',
                border: '1px solid rgba(244, 63, 94, 0.3)',
                fontSize: 12,
                color: '#fecdd3',
                fontFamily: "'Fira Code', monospace",
              }}
            >
              [Line {err.line}:{err.column}] {err.message}
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#64748b', fontSize: 13 }}>
        <Terminal size={18} style={{ marginRight: 8, opacity: 0.6 }} />
        Click <strong>"Run & Verify"</strong> to execute source and target code with identical inputs and verify output equivalence.
      </div>
    );
  }

  // Display Missing Runtime Warning
  const targetError = result?.target_result?.error;
  const isTargetRuntimeMissing = targetError === 'Go compiler not found' || result?.target_result?.stderr?.includes('Go compiler');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {isTargetRuntimeMissing ? (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            background: 'rgba(245, 158, 11, 0.1)',
            borderBottom: '1px solid rgba(245, 158, 11, 0.25)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <AlertTriangle size={18} color="#f59e0b" />
            <span style={{ fontSize: 13, fontWeight: 600, color: '#fbbf24' }}>
              TRANSPILATION SUCCEEDED — {targetLang.toUpperCase()} RUNTIME NOT INSTALLED
            </span>
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8' }}>
            Run in terminal: <code style={{ color: '#38bdf8' }}>winget install GoLang.Go</code>
          </div>
        </div>
      ) : (
        /* Status Bar */
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 16px',
            background: result?.match ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            borderBottom: result?.match ? '1px solid rgba(16, 185, 129, 0.25)' : '1px solid rgba(244, 63, 94, 0.25)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            {result?.match ? (
              <>
                <CheckCircle2 size={18} color="#10b981" />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#34d399' }}>
                  BEHAVIORAL EQUIVALENCE VERIFIED (STDOUT MATCH)
                </span>
              </>
            ) : (
              <>
                <XCircle size={18} color="#f43f5e" />
                <span style={{ fontSize: 13, fontWeight: 600, color: '#fb7185' }}>
                  OUTPUT MISMATCH DETECTED
                </span>
              </>
            )}
          </div>

          <div style={{ display: 'flex', gap: 16, fontSize: 11, color: '#94a3b8' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={12} /> {sourceLang}: {result?.source_result.duration_ms} ms
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Clock size={12} /> {targetLang}: {result?.target_result.duration_ms} ms
            </span>
          </div>
        </div>
      )}

      {/* Side-by-side terminal outputs */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Source Output */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            background: '#090d15',
          }}
        >
          <div
            style={{
              padding: '4px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: '#0e1422',
              color: '#38bdf8',
              display: 'flex',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
            }}
          >
            <span>{sourceLang.toUpperCase()} OUTPUT (STDOUT)</span>
            <span style={{ color: result.source_result.exit_code === 0 ? '#10b981' : '#f43f5e' }}>
              exit: {result.source_result.exit_code}
            </span>
          </div>
          <pre
            style={{
              flex: 1,
              padding: '10px 14px',
              margin: 0,
              fontSize: 12,
              fontFamily: "'Fira Code', monospace",
              color: result.source_result.stderr ? '#fca5a5' : '#e2e8f0',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {result.source_result.stdout || result.source_result.stderr || '(No standard output)'}
          </pre>
        </div>

        {/* Target Output */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            background: '#090d15',
          }}
        >
          <div
            style={{
              padding: '4px 12px',
              fontSize: 11,
              fontWeight: 600,
              background: '#0e1422',
              color: '#a855f7',
              display: 'flex',
              justifyContent: 'space-between',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
            }}
          >
            <span>{targetLang.toUpperCase()} OUTPUT (STDOUT)</span>
            <span style={{ color: result.target_result.exit_code === 0 ? '#10b981' : '#f43f5e' }}>
              exit: {result.target_result.exit_code}
            </span>
          </div>
          <pre
            style={{
              flex: 1,
              padding: '10px 14px',
              margin: 0,
              fontSize: 12,
              fontFamily: "'Fira Code', monospace",
              color: result.target_result.stderr ? '#fca5a5' : '#e2e8f0',
              overflowY: 'auto',
              whiteSpace: 'pre-wrap',
            }}
          >
            {result.target_result.stdout || result.target_result.stderr || '(No standard output)'}
          </pre>
        </div>
      </div>

      {/* Diff View if mismatch */}
      {!result.match && result.diff.length > 0 && (
        <div
          style={{
            maxHeight: 120,
            overflowY: 'auto',
            background: '#160b11',
            borderTop: '1px solid rgba(244, 63, 94, 0.3)',
            padding: '6px 12px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: '#fb7185', marginBottom: 4 }}>
            UNIFIED OUTPUT DIFF:
          </div>
          {result.diff.map((line, idx) => {
            let color = '#94a3b8';
            if (line.startsWith('+')) color = '#34d399';
            if (line.startsWith('-')) color = '#fb7185';
            return (
              <div
                key={idx}
                style={{
                  fontFamily: "'Fira Code', monospace",
                  fontSize: 11,
                  color,
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
