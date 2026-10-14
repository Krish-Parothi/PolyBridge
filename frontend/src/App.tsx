import React, { useState, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';
import {
  Code2,
  Play,
  ArrowRightLeft,
  Copy,
  Check,
  Layers,
  Terminal,
  AlertTriangle,
  Sun,
  Moon,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Cpu,
  Clock,
} from 'lucide-react';
import { IRTreeViewer } from './components/IRTreeViewer';
import type { TreeNode } from './components/IRTreeViewer';
import { VerificationDiff } from './components/VerificationDiff';
import type { VerificationResult } from './components/VerificationDiff';
import { CircuitSchematicViewer } from './components/CircuitSchematicViewer';
import type { HlsMetadata } from './components/CircuitSchematicViewer';
import { CycleTimingWaveform } from './components/CycleTimingWaveform';

const API_BASE = 'http://localhost:8000';

interface PresetExample {
  id: string;
  title: string;
  category: string;
  description: string;
  language: string;
  code: string;
}

const DEFAULT_PYTHON_CODE = `def bubble_sort(arr):
    n = len(arr)
    for i in range(n):
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                temp = arr[j]
                arr[j] = arr[j + 1]
                arr[j + 1] = temp
    return arr

a = [64, 34, 25, 12, 22, 11, 90]
res = bubble_sort(a)
print(res)
`;

export const App: React.FC = () => {
  // Theme state: light by default
  const [theme, setTheme] = useState<'light' | 'dark'>('light');

  // Compiler state
  const [sourceLang, setSourceLang] = useState<string>('python');
  const [targetLang, setTargetLang] = useState<string>('java');
  const [sourceCode, setSourceCode] = useState<string>(DEFAULT_PYTHON_CODE);
  const [targetCode, setTargetCode] = useState<string>('');
  const [irTree, setIrTree] = useState<TreeNode | null>(null);
  const [hlsMetadata, setHlsMetadata] = useState<HlsMetadata | null>(null);
  const [targetViewMode, setTargetViewMode] = useState<'code' | 'schematic' | 'waveform'>('code');

  const [isTranspiling, setIsTranspiling] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [diagnostics, setDiagnostics] = useState<
    Array<{ line: number; column: number; severity: string; message: string }>
  >([]);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  const [examples, setExamples] = useState<PresetExample[]>([]);
  const [selectedExampleId, setSelectedExampleId] = useState<string>('');
  const [copiedTarget, setCopiedTarget] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'verification' | 'diagnostics'>('verification');
  const [isConsoleOpen, setIsConsoleOpen] = useState(true);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  // Synchronize theme with HTML document attribute
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  // Load preset examples and check health
  useEffect(() => {
    fetch(`${API_BASE}/api/examples`)
      .then((res) => res.json())
      .then((data) => {
        setExamples(data);
        setIsBackendOnline(true);
      })
      .catch((err) => {
        console.warn('Could not load preset examples:', err);
        setIsBackendOnline(false);
      });

    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then(() => setIsBackendOnline(true))
      .catch(() => setIsBackendOnline(false));
  }, []);

  // Handle Language selection changes - clear previous target code to prevent cross-language execution mismatch
  const handleSourceLangChange = (newLang: string) => {
    setSourceLang(newLang);
    setTargetCode('');
    setIrTree(null);
    setVerificationResult(null);
    setDiagnostics([]);
  };

  const handleTargetLangChange = (newLang: string) => {
    setTargetLang(newLang);
    setTargetCode('');
    setIrTree(null);
    setVerificationResult(null);
    setHlsMetadata(null);
    setTargetViewMode('code');
    setDiagnostics([]);
  };

  // Handle Transpile action
  const handleTranspile = useCallback(async () => {
    setIsTranspiling(true);
    setDiagnostics([]);
    setVerificationResult(null);

    try {
      const res = await fetch(`${API_BASE}/api/transpile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_code: sourceCode,
          source_lang: sourceLang,
          target_lang: targetLang,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setTargetCode(data.target_code);
        setIrTree(data.ir_tree);
        setHlsMetadata(data.hls_metadata || null);
        setDiagnostics(data.diagnostics || []);
      } else {
        setTargetCode('');
        setHlsMetadata(null);
        setDiagnostics(
          data.diagnostics || [
            { line: 1, column: 1, severity: 'error', message: data.error || 'Transpilation failed' },
          ]
        );
        setActiveBottomTab('diagnostics');
        setIsConsoleOpen(true);
      }
    } catch (err: any) {
      setDiagnostics([
        { line: 1, column: 1, severity: 'error', message: `Backend connection error: ${err.message}` },
      ]);
      setActiveBottomTab('diagnostics');
      setIsConsoleOpen(true);
    } finally {
      setIsTranspiling(false);
    }
  }, [sourceCode, sourceLang, targetLang]);

  // Handle Run & Verify Equivalence
  const handleVerify = useCallback(async () => {
    let currentTarget = targetCode;
    if (!currentTarget) {
      setIsTranspiling(true);
      try {
        const transpileRes = await fetch(`${API_BASE}/api/transpile`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            source_code: sourceCode,
            source_lang: sourceLang,
            target_lang: targetLang,
          }),
        });
        const data = await transpileRes.json();
        if (data.success) {
          currentTarget = data.target_code;
          setTargetCode(data.target_code);
          setIrTree(data.ir_tree);
          setHlsMetadata(data.hls_metadata || null);
        } else {
          setDiagnostics(
            data.diagnostics || [
              { line: 1, column: 1, severity: 'error', message: data.error || 'Transpilation failed' },
            ]
          );
          setIsTranspiling(false);
          setActiveBottomTab('diagnostics');
          setIsConsoleOpen(true);
          return;
        }
      } catch {
        setIsTranspiling(false);
        return;
      }
      setIsTranspiling(false);
    }

    setIsVerifying(true);
    setIsConsoleOpen(true);
    try {
      const res = await fetch(`${API_BASE}/api/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_code: sourceCode,
          source_lang: sourceLang,
          target_code: currentTarget,
          target_lang: targetLang,
          stdin_data: '',
        }),
      });

      const data = await res.json();
      setVerificationResult(data);
      setActiveBottomTab('verification');
    } catch (err: any) {
      setDiagnostics([
        { line: 1, column: 1, severity: 'error', message: `Sandbox verification failed: ${err.message}` },
      ]);
      setActiveBottomTab('diagnostics');
    } finally {
      setIsVerifying(false);
    }
  }, [sourceCode, sourceLang, targetCode, targetLang]);

  // Keyboard shortcut listener: Ctrl+Enter (Transpile), Ctrl+Shift+Enter (Verify)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        if (e.shiftKey) {
          handleVerify();
        } else {
          handleTranspile();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleTranspile, handleVerify]);

  // Swap Languages
  const handleSwap = () => {
    const tempLang = sourceLang;
    setSourceLang(targetLang);
    setTargetLang(tempLang);
    if (targetCode) {
      setSourceCode(targetCode);
      setTargetCode('');
      setIrTree(null);
      setVerificationResult(null);
      setHlsMetadata(null);
    }
  };

  // Auto-Fix / Unwrap Class to Procedural Code
  const handleAutoFixProcedural = () => {
    const lines = sourceCode.split('\n');
    const newLines: string[] = [];
    let insideClass = false;

    for (const line of lines) {
      const trimmed = line.trim();
      if (
        trimmed.startsWith('class ') ||
        trimmed.startsWith('public class ') ||
        trimmed.startsWith('export class ')
      ) {
        insideClass = true;
        continue;
      }
      if (insideClass) {
        let cleaned = line;
        if (cleaned.startsWith('    ')) {
          cleaned = cleaned.substring(4);
        } else if (cleaned.startsWith('\t')) {
          cleaned = cleaned.substring(1);
        }
        cleaned = cleaned.replace(/def\s+([a-zA-Z0-9_]+)\(self,\s*/, 'def $1(');
        cleaned = cleaned.replace(/def\s+([a-zA-Z0-9_]+)\(self\)/, 'def $1()');
        cleaned = cleaned.replace(/self\./g, '');
        newLines.push(cleaned);
      } else {
        newLines.push(line);
      }
    }

    setSourceCode(newLines.join('\n'));
    setDiagnostics([]);
  };

  // Load Preset Example
  const handleSelectExample = (exId: string) => {
    setSelectedExampleId(exId);
    const ex = examples.find((e) => e.id === exId);
    if (ex) {
      setSourceCode(ex.code);
      setSourceLang(ex.language);
      setTargetCode('');
      setIrTree(null);
      setVerificationResult(null);
      setDiagnostics([]);
    }
  };

  const handleResetDefault = () => {
    setSourceCode(DEFAULT_PYTHON_CODE);
    setSourceLang('python');
    setTargetLang('java');
    setTargetCode('');
    setIrTree(null);
    setVerificationResult(null);
    setDiagnostics([]);
    setSelectedExampleId('');
  };

  const handleCopyTarget = () => {
    if (!targetCode) return;
    navigator.clipboard.writeText(targetCode);
    setCopiedTarget(true);
    setTimeout(() => setCopiedTarget(false), 2000);
  };

  const getMonacoLang = (lang: string) => {
    if (lang === 'python') return 'python';
    if (lang === 'javascript') return 'javascript';
    if (lang === 'java') return 'java';
    if (lang === 'go') return 'go';
    if (lang === 'cpp') return 'cpp';
    if (lang === 'verilog') return 'systemverilog';
    return 'plaintext';
  };

  const sourceLineCount = sourceCode.split('\n').length;
  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        background: 'var(--bg-app)',
        color: 'var(--text-primary)',
        fontFamily: 'var(--font-sans)',
      }}
    >
      {/* 1. Header Toolbar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 46,
          padding: '0 16px',
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-default)',
          zIndex: 30,
          flexShrink: 0,
        }}
      >
        {/* Brand / Title */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontWeight: 700,
                fontSize: 14,
                letterSpacing: '-0.3px',
                color: 'var(--text-primary)',
              }}
            >
              PolyBridge
            </span>
            <span
              style={{
                fontSize: 11,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-muted)',
                padding: '1px 5px',
                borderRadius: 'var(--radius-xs)',
                border: '1px solid var(--border-subtle)',
                background: 'var(--bg-subtle)',
              }}
            >
              v1.0.0
            </span>
          </div>

          <div
            style={{
              width: 1,
              height: 16,
              background: 'var(--border-default)',
              margin: '0 2px',
            }}
          />

          <span
            style={{
              fontSize: 11.5,
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-sans)',
            }}
          >
            Universal IR Compiler Workbench
          </span>
        </div>

        {/* Center: Algorithm Presets Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <label
            htmlFor="preset-select"
            style={{
              fontSize: 11.5,
              fontWeight: 500,
              color: 'var(--text-secondary)',
            }}
          >
            Preset:
          </label>
          <select
            id="preset-select"
            value={selectedExampleId}
            onChange={(e) => handleSelectExample(e.target.value)}
            style={{
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 8px',
              fontSize: 11.5,
              fontFamily: 'var(--font-sans)',
              cursor: 'pointer',
              outline: 'none',
              minWidth: 200,
            }}
          >
            <option value="">Select Algorithm Benchmark...</option>
            {examples.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} [{ex.category}] ({ex.language})
              </option>
            ))}
          </select>

          <button
            onClick={handleResetDefault}
            title="Reset to default code"
            style={{
              background: 'transparent',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 7px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            <RotateCcw size={12} />
          </button>
        </div>

        {/* Right Actions: Transpile, Run & Verify, Theme Toggle, Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {/* Transpile Action */}
          <button
            onClick={handleTranspile}
            disabled={isTranspiling}
            title="Parse into Intermediate Representation AST (Ctrl+Enter)"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--bg-surface)',
              color: 'var(--accent-text)',
              border: '1px solid var(--accent-border)',
              borderRadius: 'var(--radius-sm)',
              padding: '5px 12px',
              fontSize: 11.5,
              fontWeight: 600,
              fontFamily: 'var(--font-mono)',
              cursor: isTranspiling ? 'not-allowed' : 'pointer',
              opacity: isTranspiling ? 0.7 : 1,
              transition: 'all 0.15s ease',
            }}
          >
            <Layers size={13} />
            {isTranspiling ? 'Transpiling...' : 'Transpile (IR)'}
          </button>

          {/* Run & Verify Action (Primary) */}
          <button
            onClick={handleVerify}
            disabled={isVerifying}
            title="Execute source and target in sandbox to verify behavioral equivalence (Ctrl+Shift+Enter)"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'var(--accent)',
              color: '#ffffff',
              border: '1px solid var(--accent)',
              borderRadius: 'var(--radius-sm)',
              padding: '5px 14px',
              fontSize: 11.5,
              fontWeight: 600,
              fontFamily: 'var(--font-sans)',
              cursor: isVerifying ? 'not-allowed' : 'pointer',
              opacity: isVerifying ? 0.8 : 1,
              boxShadow: 'var(--shadow-sm)',
              transition: 'background 0.15s ease',
            }}
          >
            <Play size={12} fill="#ffffff" />
            {isVerifying ? 'Verifying...' : 'Run & Verify'}
          </button>

          <div
            style={{
              width: 1,
              height: 16,
              background: 'var(--border-default)',
              margin: '0 2px',
            }}
          />

          {/* Theme Toggle */}
          <button
            onClick={() => setTheme((t) => (t === 'light' ? 'dark' : 'light'))}
            title={`Switch to ${theme === 'light' ? 'Dark IDE' : 'Light Workbench'} Theme`}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 7px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
            }}
          >
            {theme === 'light' ? <Moon size={13} /> : <Sun size={13} />}
          </button>

          {/* Backend Status indicator */}
          <div
            title={`Backend Service: ${isBackendOnline ? 'Online (Port 8000)' : 'Offline'}`}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 5,
              padding: '3px 7px',
              borderRadius: 'var(--radius-xs)',
              background: 'var(--bg-subtle)',
              border: '1px solid var(--border-default)',
              fontSize: 10.5,
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
            }}
          >
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: '50%',
                background: isBackendOnline ? 'var(--color-success)' : 'var(--color-error)',
                display: 'inline-block',
              }}
            />
            {isBackendOnline ? '8000' : 'Offline'}
          </div>
        </div>
      </header>

      {/* 2. Main 3-Panel Compiler Workspace */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Panel 1: Source Code Editor */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid var(--border-default)',
            background: 'var(--bg-surface)',
            minWidth: 0,
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: 34,
              padding: '0 12px',
              background: 'var(--bg-subtle)',
              borderBottom: '1px solid var(--border-default)',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code2 size={13} style={{ color: 'var(--accent-text)' }} />
              <span
                style={{
                  fontSize: 11.5,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--text-primary)',
                }}
              >
                Source Code
              </span>

              <select
                value={sourceLang}
                onChange={(e) => handleSourceLangChange(e.target.value)}
                style={{
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '2px 6px',
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 500,
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="python">Python 3</option>
                <option value="javascript">JavaScript (ES6)</option>
                <option value="java">Java 17</option>
                <option value="go">Go 1.21</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span
                style={{
                  fontSize: 10.5,
                  fontFamily: 'var(--font-mono)',
                  color: sourceLineCount > 300 ? 'var(--color-error)' : 'var(--text-muted)',
                }}
              >
                {sourceLineCount}/300 lines
              </span>
              <button
                onClick={handleSwap}
                title="Swap source &amp; target languages"
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--text-secondary)',
                  cursor: 'pointer',
                  padding: 2,
                  display: 'flex',
                  alignItems: 'center',
                }}
              >
                <ArrowRightLeft size={12} />
              </button>
            </div>
          </div>

          {/* Monaco Editor */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <Editor
              height="100%"
              language={getMonacoLang(sourceLang)}
              theme={monacoTheme}
              value={sourceCode}
              onChange={(val) => setSourceCode(val || '')}
              options={{
                fontSize: 12.5,
                fontFamily: "'JetBrains Mono', 'IBM Plex Mono', 'Iosevka', monospace",
                lineHeight: 19,
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                padding: { top: 8, bottom: 8 },
                renderLineHighlight: 'all',
              }}
            />
          </div>
        </div>

        {/* Panel 2: Universal Intermediate Representation (IR) Explorer */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid var(--border-default)',
            background: 'var(--bg-surface)',
            minWidth: 0,
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: 34,
              padding: '0 12px',
              background: 'var(--bg-subtle)',
              borderBottom: '1px solid var(--border-default)',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Layers size={13} style={{ color: 'var(--text-secondary)' }} />
              <span
                style={{
                  fontSize: 11.5,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--text-primary)',
                }}
              >
                Universal IR AST
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                  background: 'var(--bg-surface)',
                  padding: '1px 5px',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                Language-Agnostic
              </span>
            </div>

            {irTree && (
              <span
                style={{
                  fontSize: 10.5,
                  fontFamily: 'var(--font-mono)',
                  color: 'var(--text-muted)',
                }}
              >
                CST → IR Verified
              </span>
            )}
          </div>

          {/* IR Tree Viewer Component */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <IRTreeViewer data={irTree} />
          </div>
        </div>

        {/* Panel 3: Translated Target Code Output */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            background: 'var(--bg-surface)',
            minWidth: 0,
          }}
        >
          {/* Panel Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: 34,
              padding: '0 12px',
              background: 'var(--bg-subtle)',
              borderBottom: '1px solid var(--border-default)',
              flexShrink: 0,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code2 size={13} style={{ color: 'var(--text-secondary)' }} />
              <span
                style={{
                  fontSize: 11.5,
                  fontWeight: 600,
                  fontFamily: 'var(--font-sans)',
                  color: 'var(--text-primary)',
                }}
              >
                Translated Output
              </span>

              <select
                value={targetLang}
                onChange={(e) => handleTargetLangChange(e.target.value)}
                style={{
                  background: 'var(--bg-surface)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '2px 6px',
                  fontSize: 11,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 500,
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="python">Python 3</option>
                <option value="javascript">JavaScript (ES6)</option>
                <option value="java">Java 17</option>
                <option value="go">Go 1.21</option>
                <option value="cpp">C++ 20</option>
                <option value="verilog">Verilog 2001 (HDL)</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              {targetLang === 'verilog' && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-xs)',
                    padding: 2,
                    gap: 2,
                  }}
                >
                  <button
                    onClick={() => setTargetViewMode('code')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '2px 7px',
                      fontSize: 10.5,
                      fontFamily: 'var(--font-mono)',
                      fontWeight: targetViewMode === 'code' ? 600 : 500,
                      borderRadius: 2,
                      border: 'none',
                      background: targetViewMode === 'code' ? 'var(--accent)' : 'transparent',
                      color: targetViewMode === 'code' ? '#ffffff' : 'var(--text-secondary)',
                      cursor: 'pointer',
                    }}
                  >
                    <Code2 size={11} /> Code
                  </button>

                  <button
                    onClick={() => setTargetViewMode('schematic')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '2px 7px',
                      fontSize: 10.5,
                      fontFamily: 'var(--font-mono)',
                      fontWeight: targetViewMode === 'schematic' ? 600 : 500,
                      borderRadius: 2,
                      border: 'none',
                      background: targetViewMode === 'schematic' ? '#0284c7' : 'transparent',
                      color: targetViewMode === 'schematic' ? '#ffffff' : 'var(--text-secondary)',
                      cursor: 'pointer',
                    }}
                  >
                    <Cpu size={11} /> RTL Circuit
                  </button>

                  <button
                    onClick={() => setTargetViewMode('waveform')}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 4,
                      padding: '2px 7px',
                      fontSize: 10.5,
                      fontFamily: 'var(--font-mono)',
                      fontWeight: targetViewMode === 'waveform' ? 600 : 500,
                      borderRadius: 2,
                      border: 'none',
                      background: targetViewMode === 'waveform' ? '#0284c7' : 'transparent',
                      color: targetViewMode === 'waveform' ? '#ffffff' : 'var(--text-secondary)',
                      cursor: 'pointer',
                    }}
                  >
                    <Clock size={11} /> Waveform
                  </button>
                </div>
              )}

              <button
                onClick={handleCopyTarget}
                disabled={!targetCode}
                title="Copy generated code to clipboard"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-xs)',
                  padding: '2px 7px',
                  color: copiedTarget ? 'var(--color-success)' : 'var(--text-secondary)',
                  fontSize: 10.5,
                  fontFamily: 'var(--font-mono)',
                  cursor: targetCode ? 'pointer' : 'default',
                  opacity: targetCode ? 1 : 0.5,
                }}
              >
                {copiedTarget ? <Check size={11} /> : <Copy size={11} />}
                {copiedTarget ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Target Content Area: Monaco Editor OR RTL Circuit Schematic OR Cycle Timing Waveform */}
          <div style={{ flex: 1, minHeight: 0 }}>
            {targetLang === 'verilog' && targetViewMode === 'schematic' ? (
              <CircuitSchematicViewer metadata={hlsMetadata} />
            ) : targetLang === 'verilog' && targetViewMode === 'waveform' ? (
              <CycleTimingWaveform metadata={hlsMetadata} />
            ) : (
              <Editor
                height="100%"
                language={getMonacoLang(targetLang)}
                theme={monacoTheme}
                value={targetCode}
                onChange={(val) => setTargetCode(val || '')}
                options={{
                  fontSize: 12.5,
                  fontFamily: "'JetBrains Mono', 'IBM Plex Mono', 'Iosevka', monospace",
                  lineHeight: 19,
                  minimap: { enabled: false },
                  lineNumbers: 'on',
                  scrollBeyondLastLine: false,
                  automaticLayout: true,
                  tabSize: 4,
                  padding: { top: 8, bottom: 8 },
                  renderLineHighlight: 'all',
                }}
              />
            )}
          </div>
        </div>
      </div>

      {/* 3. Lower Execution Console & Behavioral Verification Panel */}
      <div
        style={{
          height: isConsoleOpen ? 230 : 34,
          display: 'flex',
          flexDirection: 'column',
          borderTop: '1px solid var(--border-default)',
          background: 'var(--bg-surface)',
          zIndex: 10,
          transition: 'height 0.2s ease',
          flexShrink: 0,
        }}
      >
        {/* Bottom Tab Bar */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            height: 34,
            padding: '0 12px',
            background: 'var(--bg-subtle)',
            borderBottom: isConsoleOpen ? '1px solid var(--border-default)' : 'none',
            flexShrink: 0,
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <button
              onClick={() => {
                setActiveBottomTab('verification');
                setIsConsoleOpen(true);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 'var(--radius-xs)',
                fontSize: 11,
                fontFamily: 'var(--font-sans)',
                fontWeight: activeBottomTab === 'verification' ? 600 : 500,
                border: 'none',
                background:
                  activeBottomTab === 'verification' && isConsoleOpen
                    ? 'var(--bg-surface)'
                    : 'transparent',
                color:
                  activeBottomTab === 'verification' && isConsoleOpen
                    ? 'var(--text-primary)'
                    : 'var(--text-secondary)',
                boxShadow:
                  activeBottomTab === 'verification' && isConsoleOpen
                    ? 'var(--shadow-sm)'
                    : 'none',
                cursor: 'pointer',
              }}
            >
              <Terminal size={12} />
              Behavioral Verification
              {verificationResult && (
                <span
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: '50%',
                    background: verificationResult.match
                      ? 'var(--color-success)'
                      : 'var(--color-error)',
                    display: 'inline-block',
                  }}
                />
              )}
            </button>

            <button
              onClick={() => {
                setActiveBottomTab('diagnostics');
                setIsConsoleOpen(true);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 'var(--radius-xs)',
                fontSize: 11,
                fontFamily: 'var(--font-sans)',
                fontWeight: activeBottomTab === 'diagnostics' ? 600 : 500,
                border: 'none',
                background:
                  activeBottomTab === 'diagnostics' && isConsoleOpen
                    ? 'var(--bg-surface)'
                    : 'transparent',
                color:
                  activeBottomTab === 'diagnostics' && isConsoleOpen
                    ? 'var(--text-primary)'
                    : 'var(--text-secondary)',
                boxShadow:
                  activeBottomTab === 'diagnostics' && isConsoleOpen
                    ? 'var(--shadow-sm)'
                    : 'none',
                cursor: 'pointer',
              }}
            >
              <AlertTriangle size={12} />
              Diagnostics ({diagnostics.filter((d) => d.severity === 'error').length})
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span
              style={{
                fontSize: 10.5,
                fontFamily: 'var(--font-mono)',
                color: 'var(--text-muted)',
              }}
            >
              Subprocess Sandbox • AST Output Normalization Active
            </span>

            {/* Collapse / Expand Toggle */}
            <button
              onClick={() => setIsConsoleOpen(!isConsoleOpen)}
              title={isConsoleOpen ? 'Collapse Console' : 'Expand Console'}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-secondary)',
                cursor: 'pointer',
                padding: 2,
                display: 'flex',
                alignItems: 'center',
              }}
            >
              {isConsoleOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
            </button>
          </div>
        </div>

        {/* Verification Diff / Diagnostic Body */}
        {isConsoleOpen && (
          <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
            <VerificationDiff
              result={verificationResult}
              isLoading={isVerifying}
              diagnostics={activeBottomTab === 'diagnostics' ? diagnostics : []}
              sourceLang={sourceLang}
              targetLang={targetLang}
              onAutoFixProcedural={handleAutoFixProcedural}
            />
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
