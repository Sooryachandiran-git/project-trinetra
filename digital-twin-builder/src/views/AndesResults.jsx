import React, { useState } from 'react';
import useGridStore from '../store/useGridStore';
import { Zap } from 'lucide-react';

const DataTable = ({ title, data }) => {
  if (!data || data.length === 0) return null;

  const columns = Object.keys(data[0]);

  return (
    <div className="mb-8 bg-white p-4 rounded-xl shadow-sm border border-slate-200">
      <h3 className="text-lg font-bold text-slate-800 mb-4">{title}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left text-slate-600">
          <thead className="text-xs text-slate-700 uppercase bg-slate-50">
            <tr>
              {columns.map((col, idx) => (
                <th key={idx} className="px-4 py-3 font-semibold border-b border-slate-200">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                {columns.map((col, colIndex) => {
                  let val = row[col];
                  if (typeof val === 'number') val = Number(val).toFixed(4);
                  if (val === null) val = 'NaN';
                  
                  // Highlight problematic values
                  let cellClass = "px-4 py-2 font-mono";
                  if (col === 'v' && (val < 0.95 || val > 1.05)) {
                    cellClass += " text-red-600 font-bold";
                  }

                  return (
                    <td key={colIndex} className={cellClass}>
                      {val}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const AndesResults = () => {
  const { andesResults } = useGridStore();
  const [activeTab, setActiveTab] = useState('res_bus');

  if (!andesResults) {
    return (
      <div className="flex-grow flex items-center justify-center bg-slate-50">
        <div className="text-slate-400 font-medium">No results available. Please run an ANDES solve first.</div>
      </div>
    );
  }

  const tabs = [
    { id: 'res_bus', label: 'Buses' },
    { id: 'res_line', label: 'Lines' },
    { id: 'res_load', label: 'PQ Injections' },
    { id: 'res_ext_grid', label: 'Slack Buses' }
  ].filter(tab => andesResults[tab.id] && andesResults[tab.id].length > 0);

  return (
    <div className="flex-grow flex flex-col h-full overflow-hidden bg-slate-50">
      <div className="p-6 bg-white border-b border-slate-200 shadow-sm flex-shrink-0">
        <h2 className="text-2xl font-bold text-slate-800 flex items-center mb-2">
          <Zap className="mr-3 text-purple-600" size={28} />
          ANDES Power Flow Results
        </h2>
        <p className="text-slate-500 text-sm">
          Review the solved physics dataframes from the ANDES DAE engine. Values are typically in Per-Unit (p.u.).
        </p>
      </div>

      <div className="flex border-b border-slate-200 bg-white px-6">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 font-semibold text-sm transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'border-purple-500 text-purple-600'
                : 'border-transparent text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-grow p-6 overflow-y-auto">
        <DataTable title={`Results: ${activeTab}`} data={andesResults[activeTab]} />
      </div>
    </div>
  );
};

export default AndesResults;
