# Milestone 2: Interactive Digital Twin Builder (React Flow & Zustand)

**Date:** March 6, 2026
**Status:** Completed

## ⚡ Summary of Accomplishments

In this milestone, we successfully built the interactive, drag-and-drop Topology Canvas for the TRINETRA system. We transformed a static landing page into a fully functional workspace where users can graphically design electrical and SCADA networks and configure their deeply-nested physics parameters.

### 1. Interactive Topology Canvas (`@xyflow/react`)
- Implemented a spanning, interactive grid canvas allowing users to map out their digital twin architectures.
- Added visual aesthetics including a `dots` variant background for alignment and snapping guides.
- Implemented Keyboard Shortcuts (`Backspace` and `Delete`) tied directly into the global state to allow rapid removal of components and wired edges.

### 2. Custom Hybrid Node Architecture
- Built 5 distinct, highly-styled custom React Flow nodes: External Grid, Bus, Breaker, Consumer Load, and SCADA IED.
- **Hybrid Interface:** We designed these nodes to show "critical micro-badges" directly on the canvas (like live Voltage or Port numbers) while hiding complex Pandapower equations behind a double-click interaction to keep the UI clean.

### 3. Drag-and-Drop Component Palette (Sidebar)
- Created a categorised Sidebar containingdraggable representations of all our Nodes.
- Utilized HTML5 `Drag and Drop (DnD)` APIs combined with React Flow's coordinate system to instantly spawn customized nodes exactly where the user drops them.

### 4. Global State Management (Zustand)
- Replaced cumbersome React `useState` prop-drilling with a centralized `useGridStore`.
- This store acts as the single source of truth for all `nodes`, `edges`, and `modals`.
- Built purely reactive update functions that instantly sync data changes (like changing a Load's MW rating) straight into the visual component on the canvas without full page reloads.

### 5. Double-Click Configuration Modals
- Created a dynamic Property Modal system that listens for `onNodeDoubleClick`.
- Rendered dynamic input form fields based strictly on the selected `node.type` (e.g. `ext_grid` asks for `vm_pu`, but `ied` asks for `Bind Port`).

---

## 🧠 Educational Deep-Dive: Concepts Learned

This section contains code snippets and conceptual breakdowns of the powerful React features we utilized in this phase.

### Concept 1: Global State with Zustand vs Context API

In traditional React, if your Sidebar, your Canvas, and your Modal all need to access the same `nodes` array, you have to use React Context or pass props down 5 levels deep ("Prop Drilling"). **Zustand** solves this elegantly.

```javascript
// src/store/useGridStore.js
import { create } from 'zustand'

const useGridStore = create((set, get) => ({
  nodes: [],
  isModalOpen: false,

  // Action: Open the modal
  openModal: (nodeId) => set({ isModalOpen: true, selectedNodeId: nodeId }),
}));
```

**Why this is powerful:** Any component anywhere in the app can instantly access or modify this state without wrapping the app in Context Providers.

```javascript
// How a component reads from the store
const { nodes, openModal } = useGridStore();
```

### Concept 2: Immutable Reactivity (The Reference Bug)

During building, we encountered a bug where modifying node properties in the modal updated the *data*, but the visual icon on screen didn't change its text. 

**The Bug:**
```javascript
// BAD: Mutating existing memory
node.data = { ...node.data, ...newData };
return node;
```
React (and React Flow) uses **Shallow Object Comparison**. If you mutate the inside of an object but return the exact same object reference, React thinks nothing changed and refuses to re-render to save performance.

**The Fix:**
```javascript
// GOOD: Returning a completely new memory reference
return {
  ...node,                     // Copy the old node properties over
  data: { ...node.data, ...newData } // Override the data with a new object
};
```
By spreading `...node` into a new curly-brace `{}` object, we create a new memory address. React sees the new address, realizes something changed, and instantly triggers a visual UI update!

### Concept 3: Custom React Flow Nodes

React Flow allows you to break out of boring default boxes and build fully custom React components with HTML/Tailwind that act as nodes. 

```javascript
// src/components/NetworkNodes/BreakerNode.jsx
import { Handle, Position } from '@xyflow/react';

const BreakerNode = ({ data }) => {
  return (
    <div className="bg-white border-2 border-emerald-500 p-4 rounded-md">
       <Handle type="target" position={Position.Top} /> {/* Input wire hole */}
       
       <p>{data.label}</p>
       
       <Handle type="source" position={Position.Bottom} /> {/* Output wire hole */}
    </div>
  )
}
```
**How it works:** You create a normal React component, design it with Tailwind, and inject `<Handle />` components where you want users to be able to plug wires in. You then pass a mapping object `const nodeTypes = { breaker: BreakerNode }` to the main `<ReactFlow>` wrapper container.

### Concept 4: The HTML5 Drag-and-Drop API

To drag components from the Sidebar onto the Canvas, we utilized the native browser event `dataTransfer`.

**1. The Sidebar (The Draggable Item):**
When the user starts dragging an icon, we pack a string ("ext_grid") into the invisible `dataTransfer` envelope.
```javascript
const onDragStart = (event, nodeType) => {
  event.dataTransfer.setData('application/reactflow', nodeType);
};
// <div draggable onDragStart={(e) => onDragStart(e, 'ext_grid')}>
```

**2. The Canvas (The Drop Zone):**
When the user lets go of the mouse over the Canvas, the Canvas reads the envelope, finds out it's an "ext_grid", calculates the exact X/Y mouse pixel coordinates, and injects a new node into the Zustand state.
```javascript
const onDrop = (event) => {
  const type = event.dataTransfer.getData('application/reactflow');
  
  // Calculate relative mouse position inside the canvas
  const position = { x: event.clientX, y: event.clientY };
  
  // Add to Zustand Store!
  addNode({ id: Math.random(), type, position, data: {} });
};
```

---

**Next Milestone:** Developing the JSON Compiler (`jsonBuilder.js`) to translate this visual graph structure into a purely mathematical JSON payload suitable for the FastAPI backend and Pandapower physics engine.
