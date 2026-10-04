import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import {
  Code2,
  Play,
  Zap,
  ArrowRightLeft,
  Copy,
  Check,
  Sparkles,
  Layers,
  Terminal,
  Cpu,
  AlertTriangle,
} from 'lucide-react';
import { IRTreeViewer } from './components/IRTreeViewer';
import type { TreeNode } from './components/IRTreeViewer';
import { VerificationDiff } from './components/VerificationDiff';
import type { VerificationResult } from './components/VerificationDiff';

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
  const [sourceLang, setSourceLang] = useState<string>('python');
  const [targetLang, setTargetLang] = useState<string>('java');
  const [sourceCode, setSourceCode] = useState<string>(DEFAULT_PYTHON_CODE);
  const [targetCode, setTargetCode] = useState<string>('');
  const [irTree, setIrTree] = useState<TreeNode | null>(null);

  const [isTranspiling, setIsTranspiling] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [diagnostics, setDiagnostics] = useState<Array<{ line: number; column: number; severity: string; message: string }>>([]);
  const [verificationResult, setVerificationResult] = useState<VerificationResult | null>(null);

  const [examples, setExamples] = useState<PresetExample[]>([]);
  const [copiedTarget, setCopiedTarget] = useState(false);
  const [activeBottomTab, setActiveBottomTab] = useState<'verification' | 'diagnostics'>('verification');

  // Load preset examples from backend
  useEffect(() => {
    fetch(`${API_BASE}/api/examples`)
      .then((res) => res.json())
      .then((data) => setExamples(data))
      .catch((err) => console.warn('Could not load preset examples:', err));
  }, []);

  // Handle Transpile action
  const handleTranspile = async () => {
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
        setDiagnostics(data.diagnostics || []);
      } else {
        setTargetCode('');
        setDiagnostics(data.diagnostics || [
          { line: 1, column: 1, severity: 'error', message: data.error || 'Transpilation failed' },
        ]);
        setActiveBottomTab('diagnostics');
      }
    } catch (err: any) {
      setDiagnostics([
        { line: 1, column: 1, severity: 'error', message: `Backend connection error: ${err.message}` },
      ]);
      setActiveBottomTab('diagnostics');
    } finally {
      setIsTranspiling(false);
    }
  };

  // Handle Run & Verify Equivalence
  const handleVerify = async () => {
    // If target code is empty, transpile first
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
        } else {
          setDiagnostics(data.diagnostics || [
            { line: 1, column: 1, severity: 'error', message: data.error || 'Transpilation failed' },
          ]);
          setIsTranspiling(false);
          return;
        }
      } catch (e: any) {
        setIsTranspiling(false);
        return;
      }
      setIsTranspiling(false);
    }

    setIsVerifying(true);
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
    } finally {
      setIsVerifying(false);
    }
  };

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
    }
  };

  // Load Preset
  const handleSelectExample = (exId: string) => {
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

  const handleCopyTarget = () => {
    navigator.clipboard.writeText(targetCode);
    setCopiedTarget(true);
    setTimeout(() => setCopiedTarget(false), 2000);
  };

  // Language display mapping for Monaco
  const getMonacoLang = (lang: string) => {
    if (lang === 'python') return 'python';
    if (lang === 'javascript') return 'javascript';
    if (lang === 'java') return 'java';
    if (lang === 'go') return 'go';
    return 'plaintext';
  };

  const sourceLineCount = sourceCode.split('\n').length;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', background: '#07090e', color: '#f8fafc' }}>
      {/* Top Navbar */}
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 20px',
          background: '#0d111a',
          borderBottom: '1px solid rgba(255, 255, 255, 0.08)',
          zIndex: 20,
        }}
      >
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 34,
              height: 34,
              borderRadius: 8,
              background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 0 15px rgba(99, 102, 241, 0.5)',
            }}
          >
            <Cpu size={20} color="#fff" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <h1 style={{ fontSize: 17, fontWeight: 700, letterSpacing: '-0.3px', margin: 0, color: '#f8fafc' }}>
                POLYBRIDGE
              </h1>
              <span className="badge badge-info" style={{ fontSize: 10 }}>v1.0 COMPILER</span>
            </div>
            <p style={{ fontSize: 11, color: '#64748b', margin: 0 }}>
              Scoped Multi-Language Transpiler & Behavioral Verification
            </p>
          </div>
        </div>

        {/* Algorithm Presets Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#94a3b8' }}>
            <Sparkles size={14} color="#f59e0b" />
            <span>Preset Algorithm:</span>
          </div>
          <select
            onChange={(e) => handleSelectExample(e.target.value)}
            defaultValue=""
            style={{
              background: '#161e31',
              color: '#f8fafc',
              border: '1px solid rgba(255, 255, 255, 0.12)',
              borderRadius: 6,
              padding: '6px 12px',
              fontSize: 12,
              fontFamily: "'Inter', sans-serif",
              cursor: 'pointer',
              outline: 'none',
            }}
          >
            <option value="" disabled>Select an Algorithm...</option>
            {examples.map((ex) => (
              <option key={ex.id} value={ex.id}>
                {ex.title} ({ex.category})
              </option>
            ))}
          </select>
        </div>

        {/* Action Buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={handleTranspile}
            disabled={isTranspiling}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '7px 16px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(99, 102, 241, 0.3)',
              transition: 'all 0.2s',
            }}
          >
            <Zap size={14} />
            {isTranspiling ? 'Transpiling...' : 'Transpile (IR)'}
          </button>

          <button
            onClick={handleVerify}
            disabled={isVerifying}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
              color: '#fff',
              border: 'none',
              borderRadius: 6,
              padding: '7px 16px',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 2px 10px rgba(16, 185, 129, 0.3)',
              transition: 'all 0.2s',
            }}
          >
            <Play size={14} />
            {isVerifying ? 'Verifying Sandbox...' : 'Run & Verify'}
          </button>
        </div>
      </header>

      {/* Main Workspace: 3-Panel Split View */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0, overflow: 'hidden' }}>
        {/* Panel 1: Source Editor */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            background: '#0d111a',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 12px',
              background: '#0f1422',
              borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code2 size={15} color="#38bdf8" />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>SOURCE CODE</span>
              <select
                value={sourceLang}
                onChange={(e) => setSourceLang(e.target.value)}
                style={{
                  background: '#161e31',
                  color: '#38bdf8',
                  border: '1px solid rgba(56, 189, 248, 0.2)',
                  borderRadius: 4,
                  padding: '2px 8px',
                  fontSize: 11,
                  fontWeight: 600,
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
                className={`badge ${sourceLineCount > 300 ? 'badge-error' : 'badge-info'}`}
                style={{ fontSize: 10 }}
              >
                {sourceLineCount} / 300 lines
              </span>
              <button
                onClick={handleSwap}
                title="Swap source & target languages"
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  cursor: 'pointer',
                  padding: 2,
                }}
              >
                <ArrowRightLeft size={14} />
              </button>
            </div>
          </div>

          {/* Monaco Editor */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <Editor
              height="100%"
              language={getMonacoLang(sourceLang)}
              theme="vs-dark"
              value={sourceCode}
              onChange={(val) => setSourceCode(val || '')}
              options={{
                fontSize: 13,
                fontFamily: "'Fira Code', monospace",
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                padding: { top: 10 },
              }}
            />
          </div>
        </div>

        {/* Panel 2: Universal IR Tree Visualizer */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid rgba(255, 255, 255, 0.08)',
            background: '#090d14',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 12px',
              background: '#0f1422',
              borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Layers size={15} color="#818cf8" />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>UNIVERSAL IR TREE</span>
              <span className="badge badge-info" style={{ fontSize: 10 }}>LANGUAGE-AGNOSTIC</span>
            </div>
            {irTree && (
              <span style={{ fontSize: 11, color: '#64748b' }}>
                Interactive AST nodes
              </span>
            )}
          </div>

          {/* Tree Viewer */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <IRTreeViewer data={irTree} />
          </div>
        </div>

        {/* Panel 3: Target Code Output */}
        <div
          style={{
            flex: '1 1 33.33%',
            display: 'flex',
            flexDirection: 'column',
            background: '#0d111a',
          }}
        >
          {/* Header */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '6px 12px',
              background: '#0f1422',
              borderBottom: '1px solid rgba(255, 255, 255, 0.06)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Code2 size={15} color="#a855f7" />
              <span style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>TRANSLATED CODE</span>
              <select
                value={targetLang}
                onChange={(e) => setTargetLang(e.target.value)}
                style={{
                  background: '#161e31',
                  color: '#a855f7',
                  border: '1px solid rgba(168, 85, 247, 0.2)',
                  borderRadius: 4,
                  padding: '2px 8px',
                  fontSize: 11,
                  fontWeight: 600,
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
              <button
                onClick={handleCopyTarget}
                disabled={!targetCode}
                title="Copy Target Code"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 4,
                  background: 'none',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: 4,
                  padding: '3px 8px',
                  color: copiedTarget ? '#34d399' : '#94a3b8',
                  fontSize: 11,
                  cursor: targetCode ? 'pointer' : 'default',
                  opacity: targetCode ? 1 : 0.5,
                }}
              >
                {copiedTarget ? <Check size={12} /> : <Copy size={12} />}
                {copiedTarget ? 'Copied' : 'Copy'}
              </button>
            </div>
          </div>

          {/* Target Monaco Editor */}
          <div style={{ flex: 1, minHeight: 0 }}>
            <Editor
              height="100%"
              language={getMonacoLang(targetLang)}
              theme="vs-dark"
              value={targetCode}
              onChange={(val) => setTargetCode(val || '')}
              options={{
                fontSize: 13,
                fontFamily: "'Fira Code', monospace",
                minimap: { enabled: false },
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
                padding: { top: 10 },
              }}
            />
          </div>
        </div>
      </div>

      {/* Bottom Panel: Behavioral Equivalence Console & Unified Diff */}
      <div
        style={{
          height: 220,
          display: 'flex',
          flexDirection: 'column',
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          background: '#0a0d14',
          zIndex: 10,
        }}
      >
        {/* Bottom Tabs */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '4px 16px',
            background: '#0d111a',
            borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
          }}
        >
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              onClick={() => setActiveBottomTab('verification')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 12px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                border: 'none',
                background: activeBottomTab === 'verification' ? '#161e31' : 'none',
                color: activeBottomTab === 'verification' ? '#38bdf8' : '#64748b',
                cursor: 'pointer',
              }}
            >
              <Terminal size={13} />
              Execution & Behavioral Verification
            </button>
            <button
              onClick={() => setActiveBottomTab('diagnostics')}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 12px',
                borderRadius: 4,
                fontSize: 11,
                fontWeight: 600,
                border: 'none',
                background: activeBottomTab === 'diagnostics' ? '#161e31' : 'none',
                color: activeBottomTab === 'diagnostics' ? '#f43f5e' : '#64748b',
                cursor: 'pointer',
              }}
            >
              <AlertTriangle size={13} />
              Scope Diagnostics ({diagnostics.filter((d) => d.severity === 'error').length})
            </button>
          </div>

          <div style={{ fontSize: 11, color: '#64748b' }}>
            Isolated Subprocess Execution Sandbox • Output Normalization Active
          </div>
        </div>

        {/* Console / Diff Content */}
        <div style={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
          <VerificationDiff
            result={verificationResult}
            isLoading={isVerifying}
            diagnostics={diagnostics}
            sourceLang={sourceLang}
            targetLang={targetLang}
          />
        </div>
      </div>
    </div>
  );
};

export default App;
