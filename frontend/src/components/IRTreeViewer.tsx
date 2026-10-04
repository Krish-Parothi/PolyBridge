import React, { useState, useRef, useMemo } from 'react';
import { ZoomIn, ZoomOut, Maximize2, ChevronRight, ChevronDown, Layers } from 'lucide-react';

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
  attributes?: Record<string, any>;
  x: number;
  y: number;
  width: number;
  height: number;
  depth: number;
  collapsed: boolean;
  children: LayoutNode[];
}

export const IRTreeViewer: React.FC<IRTreeViewerProps> = ({ data }) => {
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 30, y: 30 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [collapsedNodes, setCollapsedNodes] = useState<Set<string>>(new Set());
  const containerRef = useRef<HTMLDivElement>(null);

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

  // Convert raw tree data into hierarchical layout coordinates
  const layout = useMemo(() => {
    if (!data) return null;

    let currentY = 20;
    const nodeHeight = 36;
    const levelIndent = 32;

    function buildLayout(node: TreeNode, depth: number, path: string): LayoutNode {
      const id = `${path}_${node.name}`;
      const isCollapsed = collapsedNodes.has(id);
      const y = currentY;
      currentY += nodeHeight + 10;

      const childrenLayout: LayoutNode[] = [];
      if (!isCollapsed && node.children && node.children.length > 0) {
        node.children.forEach((child, idx) => {
          childrenLayout.push(buildLayout(child, depth + 1, `${id}_${idx}`));
        });
      }

      return {
        id,
        name: node.name,
        attributes: node.attributes,
        x: depth * levelIndent + 20,
        y,
        width: Math.max(160, node.name.length * 8 + 50),
        height: nodeHeight,
        depth,
        collapsed: isCollapsed,
        children: childrenLayout,
      };
    }

    const root = buildLayout(data, 0, 'root');
    return { root, totalHeight: currentY + 40 };
  }, [data, collapsedNodes]);

  // Mouse drag pan handler
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

  // Determine node aesthetic color based on node name
  const getNodeColor = (name: string) => {
    if (name.startsWith('Program')) return { bg: '#312e81', border: '#6366f1', text: '#e0e7ff' };
    if (name.startsWith('Function')) return { bg: '#4c1d95', border: '#8b5cf6', text: '#ede9fe' };
    if (name.startsWith('If') || name.startsWith('While') || name.startsWith('For') || name.startsWith('Condition'))
      return { bg: '#78350f', border: '#f59e0b', text: '#fef3c7' };
    if (name.startsWith('BinaryOp') || name.startsWith('UnaryOp') || name.startsWith('Call'))
      return { bg: '#134e4a', border: '#14b8a6', text: '#ccfbf1' };
    if (name.startsWith('VarDecl') || name.startsWith('Assignment'))
      return { bg: '#064e3b', border: '#10b981', text: '#d1fae5' };
    if (name.startsWith('Literal')) return { bg: '#1e293b', border: '#475569', text: '#cbd5e1' };
    return { bg: '#1e1b4b', border: '#4338ca', text: '#c7d2fe' };
  };

  if (!data) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}>
        <Layers size={40} style={{ opacity: 0.4, marginBottom: 12 }} />
        <p style={{ fontSize: 13 }}>Click <strong>"Transpile"</strong> to generate and visualize the Universal IR tree.</p>
      </div>
    );
  }

  // Flatten layout nodes and connections
  const flatNodes: LayoutNode[] = [];
  const links: { x1: number; y1: number; x2: number; y2: number }[] = [];

  function traverse(node: LayoutNode) {
    flatNodes.push(node);
    for (const child of node.children) {
      links.push({
        x1: node.x + 16,
        y1: node.y + node.height,
        x2: child.x + 16,
        y2: child.y + child.height / 2,
      });
      traverse(child);
    }
  }

  if (layout) {
    traverse(layout.root);
  }

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        cursor: isDragging ? 'grabbing' : 'grab',
        background: '#0a0d14',
      }}
    >
      {/* Controls Overlay */}
      <div
        style={{
          position: 'absolute',
          top: 10,
          right: 10,
          display: 'flex',
          gap: 6,
          zIndex: 10,
          background: 'rgba(15, 20, 32, 0.85)',
          padding: '4px 6px',
          borderRadius: 8,
          border: '1px solid rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(8px)',
        }}
      >
        <button
          onClick={() => setZoom((z) => Math.min(2.0, z + 0.15))}
          title="Zoom In"
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 4 }}
        >
          <ZoomIn size={16} />
        </button>
        <button
          onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}
          title="Zoom Out"
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 4 }}
        >
          <ZoomOut size={16} />
        </button>
        <button
          onClick={() => { setZoom(1); setPan({ x: 30, y: 30 }); }}
          title="Reset View"
          style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: 4 }}
        >
          <Maximize2 size={16} />
        </button>
      </div>

      {/* SVG Canvas */}
      <svg
        style={{
          width: '100%',
          height: '100%',
        }}
      >
        <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
          {/* Connecting Links */}
          {links.map((link, idx) => (
            <path
              key={`link_${idx}`}
              d={`M ${link.x1} ${link.y1} V ${link.y2} H ${link.x2}`}
              fill="none"
              stroke="#243049"
              strokeWidth={1.5}
            />
          ))}

          {/* Nodes */}
          {flatNodes.map((n) => {
            const colors = getNodeColor(n.name);
            const hasChildren = (n.children && n.children.length > 0) || collapsedNodes.has(n.id);
            const typeAttr = n.attributes?.type;

            return (
              <g
                key={n.id}
                transform={`translate(${n.x}, ${n.y})`}
                onClick={(e) => hasChildren && toggleCollapse(n.id, e)}
                style={{ cursor: hasChildren ? 'pointer' : 'default' }}
              >
                <rect
                  width={n.width}
                  height={n.height}
                  rx={6}
                  fill={colors.bg}
                  stroke={colors.border}
                  strokeWidth={1.2}
                  style={{ filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.4))' }}
                />

                {/* Expand / Collapse Icon */}
                {hasChildren && (
                  <g transform="translate(6, 10)">
                    {n.collapsed ? (
                      <ChevronRight size={14} color={colors.text} />
                    ) : (
                      <ChevronDown size={14} color={colors.text} />
                    )}
                  </g>
                )}

                {/* Node Title */}
                <text
                  x={hasChildren ? 24 : 12}
                  y={18}
                  fill={colors.text}
                  fontSize={11}
                  fontFamily="'Fira Code', monospace"
                  fontWeight={500}
                >
                  {n.name}
                </text>

                {/* Type/Attribute Pill */}
                {typeAttr && (
                  <text
                    x={hasChildren ? 24 : 12}
                    y={30}
                    fill="#94a3b8"
                    fontSize={9}
                    fontFamily="'Inter', sans-serif"
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
  );
};
