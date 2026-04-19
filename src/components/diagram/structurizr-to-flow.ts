import ELK from 'elkjs/lib/elk.bundled.js';
import { Node, Edge } from '@xyflow/react';
import { StructurizrWorkspace } from '@/lib/protocol';

const elk = new ELK();

export async function getLayoutedElements(
  workspace: StructurizrWorkspace,
  viewKey: "c1" | "c2" | "c3" | "c4"
): Promise<{ nodes: Node[], edges: Edge[] }> {
  if (!workspace || !workspace.views) return { nodes: [], edges: [] };

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  // Extremely simplified stub for translating standard structurizr JSON into React Flow.
  // In a full implementation, we traverse workspace.views.systemContexts / containerViews / componentViews
  // based on the viewKey, and pull the references from workspace.model.

  // Elk Layout Root
  const graph = {
    id: "root",
    layoutOptions: {
      'elk.algorithm': 'layered',
      'elk.direction': 'DOWN',
      'elk.spacing.nodeNode': '40',
      'elk.layered.spacing.nodeNodeBetweenLayers': '50'
    },
    children: nodes.map(n => ({ id: n.id, width: 250, height: 100 })),
    edges: edges.map(e => ({ id: e.id, sources: [e.source], targets: [e.target] }))
  };

  try {
    const layout = await elk.layout(graph);
    
    const layoutedNodes = nodes.map(node => {
      const elkNode = layout.children?.find(c => c.id === node.id);
      return {
        ...node,
        position: { x: elkNode?.x || 0, y: elkNode?.y || 0 }
      };
    });

    return { nodes: layoutedNodes, edges };
  } catch (e) {
    console.error("Elk layout error", e);
    return { nodes, edges };
  }
}
