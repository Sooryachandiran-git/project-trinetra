import React from 'react'
import { Zap } from 'lucide-react'

function LandingPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-slate-900 tracking-tight mb-4">
          Project TRINETRA
        </h1>
        <p className="text-lg text-slate-600 max-w-2xl mx-auto">
          Physics-Aware Digital Twin & Virtual Cyber Range for SCADA Security.
          Select your plant system to continue.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8 max-w-6xl w-full">
        <div className="group relative flex flex-col items-center justify-center p-12 bg-white rounded-3xl shadow-sm border border-slate-200 hover:shadow-xl hover:border-blue-200 transition-all duration-300 cursor-pointer">
          <div className="w-20 h-20 mb-8 rounded-2xl bg-blue-50 flex items-center justify-center text-blue-600 group-hover:scale-110 transition-transform duration-300">
            <Zap size={40} strokeWidth={1.5} />
          </div>
          <h2 className="text-2xl font-semibold text-slate-800 mb-3">Electrical SCADA</h2>
          <p className="text-center text-slate-500 text-sm leading-relaxed">
            Design and simulate power grid topologies with Pandapower and OpenPLC.
          </p>
          <div className="mt-8 px-6 py-2 bg-slate-900 text-white text-sm font-medium rounded-full shadow-lg group-hover:bg-blue-600 transition-colors">
            Open Workspace
          </div>
        </div>

        {/* Placeholder for future plant types */}
        <div className="flex flex-col items-center justify-center p-12 bg-slate-50 rounded-3xl border border-dashed border-slate-300 opacity-60">
          <div className="w-16 h-16 mb-6 rounded-full bg-slate-200 flex items-center justify-center text-slate-400">
            <span className="text-2xl font-bold">+</span>
          </div>
          <p className="text-slate-400 font-medium">Coming Soon</p>
        </div>
      </div>

      <footer className="mt-20 text-slate-400 text-xs font-medium uppercase tracking-[0.2em]">
        Research-Grade Security Testing Environment
      </footer>
    </div>
  )
}

export default LandingPage
