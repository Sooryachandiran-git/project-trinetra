import { create } from 'zustand'
import {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react'

const useGridStore = create((set, get) => ({
  nodes: [],
  edges: [],
  onNodesChange: (changes) => {
    set({
      nodes: applyNodeChanges(changes, get().nodes),
    });
  },
  onEdgesChange: (changes) => {
    set({
      edges: applyEdgeChanges(changes, get().edges),
    });
  },
  onConnect: (connection) => {
    set({
      edges: addEdge(connection, get().edges),
    });
  },
  addNode: (node) => {
    set({
      nodes: [...get().nodes, node],
    });
  },
  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((node) => {
        if (node.id === nodeId) {
          node.data = { ...node.data, ...data };
        }
        return node;
      })
    });
  },
  saveGrid: () => {
    const state = get();
    console.log('Grid saved:', { nodes: state.nodes, edges: state.edges });
    // Future integration: send to FastAPI backend
  },
  loadGrid: (gridData) => {
    set({
      nodes: gridData.nodes || [],
      edges: gridData.edges || [],
    });
  }
}));

export default useGridStore;
