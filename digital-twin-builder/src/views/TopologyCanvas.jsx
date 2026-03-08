import React, { useCallback, useRef, useEffect, useMemo } from 'react';
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
import TransmissionLineNode from '../components/NetworkNodes/TransmissionLineNode';
import NetworkSwitchNode from '../components/NetworkNodes/NetworkSwitchNode';
import GPSClockNode from '../components/NetworkNodes/GPSClockNode';
import ScadaServerNode from '../components/NetworkNodes/ScadaServerNode';
import Sidebar from '../components/Sidebar';
import NodePropertyModal from '../components/ConfigModals/NodePropertyModal';
import AttackInterface from '../components/Panels/AttackInterface';
import ControlRoom from '../components/Panels/ControlRoom';

const nodeTypes = {
  bus: BusNode,
  breaker: BreakerNode,
  ied: IEDNode,
  ext_grid: ExternalGridNode,
  load: LoadNode,
  transmission_line: TransmissionLineNode,
  gps_clock: GPSClockNode
};

const TopologyCanvas = () => {
  const reactFlowWrapper = useRef(null);
  const { nodes, edges, onNodesChange, onEdgesChange, onConnect, addNode, openModal, isRunMode, setLiveTelemetry, liveTelemetry, activeView } = useGridStore();

  // Telemetry Stream Listener
  useEffect(() => {
    let eventSource;
    if (isRunMode) {
      console.log("Connecting to TRINETRA Telemetry Stream...");
      eventSource = new EventSource('http://localhost:8000/api/stream');
      
      eventSource.onmessage = (event) => {
        try {
          const telemetryData = JSON.parse(event.data);
          setLiveTelemetry(telemetryData);
        } catch (error) {
          console.error("Failed to parse telemetry:", error);
        }
      };

      eventSource.onerror = (error) => {
        console.error("SSE Connection Error:", error);
        eventSource.close();
      };
    } else {
      setLiveTelemetry(null);
    }

    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [isRunMode, setLiveTelemetry]);

  // Dynamically style physical edges based on live power flow
  const animatedEdges = useMemo(() => {
    if (!isRunMode || !liveTelemetry) return edges;
    
    return edges.map(edge => {
      // Cyber control links remain strictly dashed blue
      if (edge.style?.strokeDasharray) return edge;
      
      // Physical power lines react to the live physics voltage
      const isDead = liveTelemetry.voltage_pu < 0.1;
      
      return {
        ...edge,
        animated: !isDead, // Marching ants when power is flowing
        style: {
          ...edge.style,
          stroke: isDead ? '#ef4444' : '#22c55e', // Red if dead, Green if energized
          strokeWidth: 4,
          transition: 'stroke 0.3s ease'
        }
      };
    });
  }, [edges, isRunMode, liveTelemetry]);

  const onNodeDoubleClick = useCallback((event, node) => {
    openModal(node.id);
  }, [openModal]);

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

      // Determine the next numerical ID for this specific type
      const typeCount = nodes.filter((n) => n.type === type).length + 1;
      
      // Formatting the label (e.g., 'ext_grid' -> 'Ext Grid 1')
      const formattedType = type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase());

      const newNode = {
        id: `node_${Math.random().toString(36).substring(2, 9)}`,
        type,
        position,
        data: { label: `${formattedType} ${typeCount}` },
      };
      
      addNode(newNode);
    },
    [addNode, nodes]
  );
  const isValidConnection = useCallback((connection) => {
    const sourceNode = nodes.find(n => n.id === connection.source);
    const targetNode = nodes.find(n => n.id === connection.target);
    if (!sourceNode || !targetNode) return false;

    const source = sourceNode.type;
    const target = targetNode.type;

    // Helper to check if a connection is exactly between two given types (order independent)
    const isPair = (typeA, typeB) => 
      (source === typeA && target === typeB) || (source === typeB && target === typeA);

    // Rule 1: Cyber Layer (IED -> Breaker)
    if (isPair('ied', 'breaker')) return true;
    if (isPair('ied', 'network_switch')) return true;
    if (isPair('scada_server', 'network_switch')) return true;
    if (isPair('gps_clock', 'network_switch')) return true;
    if (isPair('network_switch', 'network_switch')) return true;

    // Rule 2: Physics Layer (Everything must connect to a Bus)
    // You cannot connect Ext Grid to Load directly, nor Line to Load directly.
    if (isPair('bus', 'ext_grid')) return true;
    if (isPair('bus', 'load')) return true;
    if (isPair('bus', 'transmission_line')) return true;
    if (isPair('bus', 'breaker')) return true;
    if (isPair('bus', 'bus')) return true;

    // Any other connection is invalid (e.g. ext_grid to load, transmission_line to load)
    return false;
  }, [nodes]);

  return (
    <div className="flex-grow h-full w-full flex flex-col">
      <Topbar />
      <NodePropertyModal />
      <div className="flex-grow w-full relative flex overflow-hidden">
        {activeView === 'topology' ? (
          <div className="flex-grow w-full relative" ref={reactFlowWrapper}>
            <ReactFlow
              nodes={nodes}
              edges={animatedEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              isValidConnection={isValidConnection}
              onDrop={onDrop}
              onDragOver={onDragOver}
              onNodeDoubleClick={!isRunMode ? onNodeDoubleClick : undefined}
              fitView
              deleteKeyCode={!isRunMode ? ['Backspace', 'Delete'] : null}
              nodesDraggable={!isRunMode}
              nodesConnectable={!isRunMode}
              elementsSelectable={!isRunMode}
              nodeTypes={nodeTypes}
            >
              <Background variant="dots" gap={16} size={1} color={isRunMode ? "#E2E8F0" : "#CBD5E1"} />
              <Controls />
              <MiniMap />
            </ReactFlow>
          </div>
        ) : (
          <ControlRoom />
        )}

        {/* Show Attack API Interface in Run Mode */}
        {isRunMode && <AttackInterface />}
      </div>
    </div>
  );
};


export default function TopologyCanvasWrapper() {
  const { isRunMode } = useGridStore();
  
  return (
    <ReactFlowProvider>
      <div className="flex h-screen w-full bg-slate-50">
        {/* Sidebar Palette - Hide when running simulation */}
        {!isRunMode && <Sidebar />}
        <TopologyCanvas />
      </div>
    </ReactFlowProvider>
  );
}
