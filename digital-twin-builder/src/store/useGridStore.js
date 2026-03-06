import { create } from 'zustand'
import {
  addEdge,
  applyNodeChanges,
  applyEdgeChanges,
} from '@xyflow/react'

const useGridStore = create((set, get) => ({
  nodes: [],
  edges: [],
  isModalOpen: false,
  selectedNodeId: null,

  openModal: (nodeId) => set({ isModalOpen: true, selectedNodeId: nodeId }),
  closeModal: () => set({ isModalOpen: false, selectedNodeId: null }),

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
  onNodesDelete: (deleted) => {
    set({
      nodes: get().nodes.filter((node) => !deleted.map((d) => d.id).includes(node.id)),
    });
  },
  onEdgesDelete: (deleted) => {
    set({
      edges: get().edges.filter((edge) => !deleted.map((d) => d.id).includes(edge.id)),
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
          // React Flow requires a new object reference to trigger a re-render
          return {
            ...node,
            data: { ...node.data, ...data },
          };
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
