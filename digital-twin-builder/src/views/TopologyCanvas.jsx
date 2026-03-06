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
        {/* Placeholder for Sidebar Component (To be implemented next) */}
        <div className="w-64 bg-white border-r border-slate-200 p-6 flex flex-col shadow-sm z-10">
            <h2 className="font-semibold text-slate-800 mb-6 text-lg tracking-tight">Component Palette</h2>
            <div 
                className="p-4 bg-white border border-slate-200 shadow-sm rounded-xl text-slate-700 cursor-grab mb-3 hover:border-blue-400 hover:shadow-md transition-all flex items-center justify-center font-medium"
                onDragStart={(event) => {
                    event.dataTransfer.setData('application/reactflow', 'default');
                    event.dataTransfer.effectAllowed = 'move';
                }}
                draggable
            >
                Generic Node
            </div>
            
            <a 
                href="#"
                className="w-full mt-auto px-4 py-3 bg-slate-100 text-slate-700 font-medium rounded-xl hover:bg-slate-200 transition-colors text-center border border-slate-300"
            >
                Back to Home
            </a>
        </div>
        <TopologyCanvas />
      </div>
    </ReactFlowProvider>
  );
}
