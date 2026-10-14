import React, { useState, useRef, useMemo } from 'react';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  ChevronRight,
  ChevronDown,
  Layers,
  Search,
  Code,
  ListTree,
  X,
  FileCode2,
} from 'lucide-react';

export interface TreeNode {
  name: string;
  attributes?: Record<string, any>;
  children?: TreeNode[];
}

interface IRTreeViewerProps {
  data: TreeNode | null;
}

interface LayoutNode {
  id: string;
  name: string;
  category: string;
  attributes?: Record<string, any>;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
  collapsed: boolean;
  children: LayoutNode[];
  rawNode: TreeNode;
}

// Semantic node categorization for subtle, compiler-grade styling
function getNodeCategory(name: string): {
  category: string;
  bgLight: string;
  borderLight: string;
  textLight: string;
  bgDark: string;
  borderDark: string;
  textDark: string;
} {
  if (name.startsWith('Program') || name.startsWith('Function')) {
    return {
      category: 'Structure',
      bgLight: '#f0f4f9',
      borderLight: '#a8c7fa',
      textLight: '#0b57d0',
      bgDark: '#0c2340',
      borderDark: '#1f6feb',
      textDark: '#79c0ff',
    };
  }
  if (
    name.startsWith('If') ||
    name.startsWith('While') ||
    name.startsWith('For') ||
    name.startsWith('Condition') ||
    name.startsWith('Return')
  ) {
    return {
      category: 'Control Flow',
      bgLight: '#fff8eb',
      borderLight: '#fed7aa',
      textLight: '#b45309',
      bgDark: '#2b1d0c',
      borderDark: '#9e6a03',
      textDark: '#e3b341',
    };
  }
  if (
    name.startsWith('BinaryOp') ||
    name.startsWith('UnaryOp') ||
    name.startsWith('Call') ||
    name.startsWith('Index')
  ) {
    return {
      category: 'Operation',
      bgLight: '#f0fdfa',
      borderLight: '#99f6e4',
      textLight: '#0f766e',
      bgDark: '#082f2c',
      borderDark: '#14b8a6',
      textDark: '#5eead4',
    };
  }
  if (name.startsWith('VarDecl') || name.startsWith('Assign') || name.startsWith('Param')) {
    return {
      category: 'Declaration',
      bgLight: '#f0fdf4',
      borderLight: '#bbf7d0',
      textLight: '#15803d',
      bgDark: '#0e2a18',
      borderDark: '#238636',
      textDark: '#7ee787',
    };
  }
  if (name.startsWith('Literal') || name.startsWith('Id')) {
    return {
      category: 'Operand',
      bgLight: '#f6f8fa',
      borderLight: '#d0d7de',
      textLight: '#24292f',
      bgDark: '#161b22',
      borderDark: '#30363d',
      textDark: '#c9d1d9',
    };
  }
  return {
    category: 'Node',
    bgLight: '#f8f9fa',
    borderLight: '#d0d7de',
    textLight: '#1f2328',
    bgDark: '#161b22',
    borderDark: '#30363d',
    textDark: '#e6edf3',
  };
}

export const IRTreeViewer: React.FC<IRTreeViewerProps> = ({ data }) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 28, y: 28 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<LayoutNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [viewMode, setViewMode] = useState<'tree' | 'outline' | 'json'>('tree');

  const containerRef = useRef<HTMLDivElement>(null);

  // Toggle node collapse
  const toggleCollapse = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    setCollapsedNodes((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  // Collapse / Expand all handlers
  const handleExpandAll = () => setCollapsedNodes(new Set());

  const handleCollapseAll = () => {
    if (!data) return;
    const allIds = new Set<string>();
    function collect(node: TreeNode, path: string) {
      const id = `${path}_${node.name}`;
      if (node.children && node.children.length > 0) {
        allIds.add(id);
        node.children.forEach((c, i) => collect(c, `${id}_${i}`));
      }
    }
    collect(data, 'root');
    setCollapsedNodes(allIds);
  };

  // Layout calculation
  const layout = useMemo(() => {
    if (!data) return null;

    let currentY = 24;
    const nodeHeight = 34;
    const levelIndent = 28;
    let totalNodes = 0;
    let maxDepth = 0;

    function buildLayout(node: TreeNode, depth: number, path: string): LayoutNode {
      totalNodes++;
      if (depth > maxDepth) maxDepth = depth;

      const id = `${path}_${node.name}`;
      const isCollapsed = collapsedNodes.has(id);
      const y = currentY;
      currentY += nodeHeight + 8;

      const childrenLayout: LayoutNode[] = [];
      if (!isCollapsed && node.children && node.children.length > 0) {
        node.children.forEach((child, idx) => {
          childrenLayout.push(buildLayout(child, depth + 1, `${id}_${idx}`));
        });
      }

      // Compact width calculation
      const nameLen = node.name.length;
      const typeStr = node.attributes?.type ? String(node.attributes.type) : '';
      const estimatedWidth = Math.max(160, Math.min(320, nameLen * 7.5 + (typeStr ? typeStr.length * 6 + 40 : 36)));

      const styleInfo = getNodeCategory(node.name);

      return {
        id,
        name: node.name,
        category: styleInfo.category,
        attributes: node.attributes,
        x: depth * levelIndent + 20,
        y,
        width: estimatedWidth,
        height: nodeHeight,
        depth,
        collapsed: isCollapsed,
        children: childrenLayout,
        rawNode: node,
      };
    }

    const root = buildLayout(data, 0, 'root');
    return { root, totalHeight: currentY + 40, totalNodes, maxDepth };
  }, [data, collapsedNodes]);

  // Mouse pan handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y,
    });
  };

  const handleMouseUp = () => setIsDragging(false);

  // Flatten nodes and links
  const { flatNodes, links } = useMemo(() => {
    if (!layout) return { flatNodes: [], links: [] };

    const nodes: LayoutNode[] = [];
    const conns: { x1: number; y1: number; x2: number; y2: number }[] = [];

    function traverse(node: LayoutNode) {
      nodes.push(node);
      for (const child of node.children) {
        conns.push({
          x1: node.x + 14,
          y1: node.y + node.height,
          x2: child.x + 14,
          y2: child.y + child.height / 2,
        });
        traverse(child);
      }
    }

    traverse(layout.root);
    return { flatNodes: nodes, links: conns };
  }, [layout]);

  if (!data) {
    return (
      <div
        style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--text-muted)',
          padding: 24,
          textAlign: 'center',
          background: 'var(--bg-surface)',
        }}
      >
        <div
          style={{
            width: 44,
            height: 44,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-default)',
            background: 'var(--bg-subtle)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginBottom: 12,
          }}
        >
          <Layers size={22} style={{ color: 'var(--text-secondary)' }} />
        </div>
        <div
          style={{
            fontFamily: 'var(--font-sans)',
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: 4,
          }}
        >
          No IR Tree Available
        </div>
        <p
          style={{
            fontSize: 12,
            maxWidth: 280,
            lineHeight: 1.5,
            color: 'var(--text-secondary)',
            margin: 0,
          }}
        >
          Execute <strong>Transpile</strong> to parse source code into the language-agnostic Intermediate Representation AST.
        </p>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        background: 'var(--bg-surface)',
      }}
    >
      {/* Sub-toolbar: Search, View Mode, Zoom & Hierarchy stats */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '6px 12px',
          background: 'var(--bg-subtle)',
          borderBottom: '1px solid var(--border-default)',
          gap: 8,
          fontSize: 11,
          flexShrink: 0,
        }}
      >
        {/* Left: View Mode Switcher */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 2, background: 'var(--bg-surface)', padding: 2, borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-default)' }}>
          <button
            onClick={() => setViewMode('tree')}
            title="Interactive Tree Layout"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 500,
              border: 'none',
              borderRadius: 'var(--radius-xs)',
              background: viewMode === 'tree' ? 'var(--accent-subtle)' : 'transparent',
              color: viewMode === 'tree' ? 'var(--accent-text)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <ListTree size={12} />
            Tree
          </button>
          <button
            onClick={() => setViewMode('outline')}
            title="Hierarchical Outline List"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 500,
              border: 'none',
              borderRadius: 'var(--radius-xs)',
              background: viewMode === 'outline' ? 'var(--accent-subtle)' : 'transparent',
              color: viewMode === 'outline' ? 'var(--accent-text)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <Code size={12} />
            Outline
          </button>
          <button
            onClick={() => setViewMode('json')}
            title="Raw Structured IR JSON"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              padding: '3px 8px',
              fontSize: 11,
              fontWeight: 500,
              border: 'none',
              borderRadius: 'var(--radius-xs)',
              background: viewMode === 'json' ? 'var(--accent-subtle)' : 'transparent',
              color: viewMode === 'json' ? 'var(--accent-text)' : 'var(--text-secondary)',
              cursor: 'pointer',
            }}
          >
            <FileCode2 size={12} />
            Dump
          </button>
        </div>

        {/* Center: Search Filter */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-sm)',
            padding: '2px 8px',
            flex: '0 1 200px',
          }}
        >
          <Search size={12} style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Filter AST nodes..."
            style={{
              border: 'none',
              outline: 'none',
              background: 'transparent',
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-primary)',
              width: '100%',
            }}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', color: 'var(--text-muted)' }}
            >
              <X size={11} />
            </button>
          )}
        </div>

        {/* Right: Expand/Collapse & Zoom controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {viewMode === 'tree' && (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <button
                  onClick={handleExpandAll}
                  title="Expand All Nodes"
                  style={{
                    padding: '3px 6px',
                    fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-xs)',
                    cursor: 'pointer',
                  }}
                >
                  Expand
                </button>
                <button
                  onClick={handleCollapseAll}
                  title="Collapse All Nodes"
                  style={{
                    padding: '3px 6px',
                    fontSize: 10,
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-secondary)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border-default)',
                    borderRadius: 'var(--radius-xs)',
                    cursor: 'pointer',
                  }}
                >
                  Collapse
                </button>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border-default)',
                  borderRadius: 'var(--radius-sm)',
                  overflow: 'hidden',
                }}
              >
                <button
                  onClick={() => setZoom((z) => Math.min(2.0, +(z + 0.15).toFixed(2)))}
                  title="Zoom In"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '3px 6px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <ZoomIn size={13} />
                </button>
                <button
                  onClick={() => setZoom((z) => Math.max(0.4, +(z - 0.15).toFixed(2)))}
                  title="Zoom Out"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '3px 6px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <ZoomOut size={13} />
                </button>
                <button
                  onClick={() => {
                    setZoom(1);
                    setPan({ x: 28, y: 28 });
                  }}
                  title="Reset Zoom & Pan"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--text-secondary)',
                    cursor: 'pointer',
                    padding: '3px 6px',
                    display: 'flex',
                    alignItems: 'center',
                  }}
                >
                  <Maximize2 size={13} />
                </button>
              </div>
            </>
          )}

          {/* Node Count Metric */}
          <span
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: 'var(--text-muted)',
              whiteSpace: 'nowrap',
            }}
          >
            {layout?.totalNodes} nodes • depth {layout?.maxDepth}
          </span>
        </div>
      </div>

      {/* Main View Area */}
      <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
        {/* 1. Tree View (SVG Interactive Canvas) */}
        {viewMode === 'tree' && (
          <div
            ref={containerRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
            style={{
              width: '100%',
              height: '100%',
              overflow: 'hidden',
              cursor: isDragging ? 'grabbing' : 'grab',
              background: 'var(--bg-surface)',
              position: 'relative',
            }}
          >
            <svg
              style={{
                width: '100%',
                height: '100%',
                display: 'block',
              }}
            >
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Connecting Links */}
                {links.map((link, idx) => (
                  <path
                    key={`link_${idx}`}
                    d={`M ${link.x1} ${link.y1} V ${link.y2} H ${link.x2}`}
                    fill="none"
                    stroke="var(--border-default)"
                    strokeWidth={1.2}
                  />
                ))}

                {/* Nodes */}
                {flatNodes.map((n) => {
                  const styleInfo = getNodeCategory(n.name);
                  const hasChildren = (n.children && n.children.length > 0) || collapsedNodes.has(n.id);
                  const typeAttr = n.attributes?.type;
                  const isSelected = selectedNode?.id === n.id;
                  const isMatch = searchQuery
                    ? n.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                      (typeAttr && String(typeAttr).toLowerCase().includes(searchQuery.toLowerCase()))
                    : false;

                  return (
                    <g
                      key={n.id}
                      transform={`translate(${n.x}, ${n.y})`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(n);
                      }}
                      style={{ cursor: 'pointer' }}
                    >
                      {/* Node Card Box */}
                      <rect
                        width={n.width}
                        height={n.height}
                        rx={3}
                        fill={styleInfo.bgLight}
                        stroke={
                          isSelected
                            ? 'var(--accent)'
                            : isMatch
                            ? 'var(--color-warning)'
                            : styleInfo.borderLight
                        }
                        strokeWidth={isSelected ? 2 : isMatch ? 1.8 : 1}
                        style={{
                          transition: 'all 0.15s ease',
                          filter: isSelected
                            ? 'drop-shadow(0 2px 6px rgba(9, 105, 218, 0.2))'
                            : 'none',
                        }}
                      />

                      {/* Expand / Collapse Indicator */}
                      {hasChildren ? (
                        <g
                          transform="translate(6, 9)"
                          onClick={(e) => toggleCollapse(n.id, e)}
                          style={{ cursor: 'pointer' }}
                        >
                          <rect
                            x={-2}
                            y={-2}
                            width={16}
                            height={16}
                            rx={2}
                            fill="transparent"
                          />
                          {n.collapsed ? (
                            <ChevronRight size={13} color={styleInfo.textLight} />
                          ) : (
                            <ChevronDown size={13} color={styleInfo.textLight} />
                          )}
                        </g>
                      ) : (
                        <circle
                          cx={11}
                          cy={17}
                          r={2}
                          fill={styleInfo.textLight}
                          opacity={0.5}
                        />
                      )}

                      {/* Node Label */}
                      <text
                        x={hasChildren ? 22 : 18}
                        y={typeAttr ? 15 : 21}
                        fill={styleInfo.textLight}
                        fontSize={11}
                        fontFamily="var(--font-ir)"
                        fontWeight={500}
                        pointerEvents="none"
                      >
                        {n.name}
                      </text>

                      {/* Inferred Type Annotation */}
                      {typeAttr && (
                        <text
                          x={hasChildren ? 22 : 18}
                          y={27}
                          fill="var(--text-secondary)"
                          fontSize={9.5}
                          fontFamily="var(--font-mono)"
                          pointerEvents="none"
                        >
                          type: {String(typeAttr)}
                        </text>
                      )}
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>
        )}

        {/* 2. Hierarchical Outline View */}
        {viewMode === 'outline' && (
          <div
            style={{
              height: '100%',
              overflowY: 'auto',
              padding: '12px 16px',
              fontFamily: 'var(--font-mono)',
              fontSize: 11.5,
              background: 'var(--bg-surface)',
            }}
          >
            {flatNodes.map((n) => {
              const isSelected = selectedNode?.id === n.id;
              const hasChildren = (n.children && n.children.length > 0) || collapsedNodes.has(n.id);
              const typeAttr = n.attributes?.type;

              return (
                <div
                  key={n.id}
                  onClick={() => setSelectedNode(n)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                    padding: '3px 8px',
                    marginLeft: n.depth * 18,
                    borderRadius: 'var(--radius-xs)',
                    background: isSelected ? 'var(--accent-subtle)' : 'transparent',
                    border: isSelected ? '1px solid var(--accent-border)' : '1px solid transparent',
                    cursor: 'pointer',
                    lineHeight: 1.4,
                  }}
                >
                  {hasChildren ? (
                    <span
                      onClick={(e) => toggleCollapse(n.id, e)}
                      style={{ cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                    >
                      {n.collapsed ? <ChevronRight size={12} /> : <ChevronDown size={12} />}
                    </span>
                  ) : (
                    <span style={{ width: 12, display: 'inline-block' }} />
                  )}
                  <span style={{ fontWeight: 500, color: 'var(--text-primary)' }}>{n.name}</span>
                  {typeAttr && (
                    <span
                      style={{
                        fontSize: 10,
                        color: 'var(--text-muted)',
                        padding: '1px 4px',
                        borderRadius: 2,
                        background: 'var(--bg-subtle)',
                        border: '1px solid var(--border-subtle)',
                      }}
                    >
                      {String(typeAttr)}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* 3. Raw Structured IR Dump */}
        {viewMode === 'json' && (
          <pre
            style={{
              margin: 0,
              padding: 16,
              height: '100%',
              overflowY: 'auto',
              fontSize: 11.5,
              fontFamily: 'var(--font-mono)',
              background: 'var(--bg-surface)',
              color: 'var(--text-primary)',
              lineHeight: 1.5,
            }}
          >
            {JSON.stringify(data, null, 2)}
          </pre>
        )}

        {/* Selected Node Inspector Drawer */}
        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              bottom: 12,
              right: 12,
              width: 280,
              maxHeight: 240,
              overflowY: 'auto',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-md)',
              boxShadow: 'var(--shadow-md)',
              padding: 12,
              zIndex: 20,
              fontSize: 11,
              fontFamily: 'var(--font-sans)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                borderBottom: '1px solid var(--border-subtle)',
                paddingBottom: 6,
                marginBottom: 8,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span
                  style={{
                    padding: '2px 5px',
                    borderRadius: 'var(--radius-xs)',
                    fontSize: 9.5,
                    fontFamily: 'var(--font-mono)',
                    fontWeight: 600,
                    background: 'var(--accent-subtle)',
                    color: 'var(--accent-text)',
                  }}
                >
                  {selectedNode.category.toUpperCase()}
                </span>
                <strong style={{ fontSize: 12, color: 'var(--text-primary)' }}>AST Inspector</strong>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'var(--text-muted)',
                  cursor: 'pointer',
                  padding: 2,
                }}
              >
                <X size={13} />
              </button>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Node: </span>
                <span style={{ fontFamily: 'var(--font-ir)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {selectedNode.name}
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>AST Depth: </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  Level {selectedNode.depth}
                </span>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Sub-nodes: </span>
                <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-secondary)' }}>
                  {selectedNode.children.length} direct children
                </span>
              </div>

              {selectedNode.attributes && Object.keys(selectedNode.attributes).length > 0 && (
                <div style={{ marginTop: 4 }}>
                  <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>Attributes:</div>
                  <div
                    style={{
                      background: 'var(--bg-subtle)',
                      borderRadius: 'var(--radius-xs)',
                      padding: '4px 8px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10.5,
                      color: 'var(--text-secondary)',
                      lineHeight: 1.4,
                    }}
                  >
                    {Object.entries(selectedNode.attributes).map(([k, v]) => (
                      <div key={k}>
                        <span style={{ color: 'var(--accent-text)' }}>{k}</span>: {String(v)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
