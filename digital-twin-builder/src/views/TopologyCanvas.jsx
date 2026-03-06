import React, { useCallback, useRef } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  ReactFlowProvider,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import useGridStore from '../store/useGridStore';
import Topbar from '../components/Topbar';
import BusNode from '../components/NetworkNodes/BusNode';
import BreakerNode from '../components/NetworkNodes/BreakerNode';
import IEDNode from '../components/NetworkNodes/IEDNode';
import ExternalGridNode from '../components/NetworkNodes/ExternalGridNode';
import LoadNode from '../components/NetworkNodes/LoadNode';
import Sidebar from '../components/Sidebar';

const nodeTypes = {
  bus: BusNode,
  breaker: BreakerNode,
  ied: IEDNode,
  ext_grid: ExternalGridNode,
  load: LoadNode,
};

const TopologyCanvas = () => {
  const reactFlowWrapper = useRef(null);
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode } = useGridStore();

  const onDragOver = useCallback((event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = 'move';
  }, []);

  const onDrop = useCallback(
    (event) => {
      event.preventDefault();
      const type = event.dataTransfer.getData('application/reactflow');
      if (typeof type === 'undefined' || !type) {
        return;
      }
      const position = {
        x: event.clientX - reactFlowWrapper.current.getBoundingClientRect().left,
        y: event.clientY - reactFlowWrapper.current.getBoundingClientRect().top,
      };
      const newNode = {
        id: `node_${Math.random().toString(36).substring(2, 9)}`,
        type,
        position,
        data: { label: `${type} node` },
      };
      addNode(newNode);
    },
    [addNode]
  );

  return (
    <div className="flex-grow h-full w-full flex flex-col">
      <Topbar />
      <div className="flex-grow w-full relative" ref={reactFlowWrapper}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          fitView
          deleteKeyCode={['Backspace', 'Delete']}
          nodeTypes={nodeTypes}
        >
          <Background variant="dots" gap={16} size={1} color="#CBD5E1" />
          <Controls />
          <MiniMap />
        </ReactFlow>
      </div>
    </div>
  );
};


export default function TopologyCanvasWrapper() {
  return (
    <ReactFlowProvider>
      <div className="flex h-screen w-full bg-slate-50">
        {/* Sidebar Palette */}
        <Sidebar />
        <TopologyCanvas />
      </div>
    </ReactFlowProvider>
  );
}
