import { useState, useCallback } from 'react';
import { BlocklyWorkspace } from './components/BlocklyWorkspace';
import { YamlPreview } from './components/YamlPreview';
import { Header } from './components/Header';
import { WorkspaceAnalysis } from './workspaceToYaml';

const DEFAULT_ANALYSIS: WorkspaceAnalysis = {
  yaml: '# Drag a "⚡ KALI EXPERIMENT" block to get started.',
  blastRadius: 0,
  blastBlocked: false,
  faultCount: 0,
  hasHypothesis: false,
  hasCircuitBreaker: false,
};

export default function App() {
  const [analysis, setAnalysis] = useState<WorkspaceAnalysis>(DEFAULT_ANALYSIS);

  const handleAnalysis = useCallback((a: WorkspaceAnalysis) => {
    setAnalysis(a);
  }, []);

  return (
    <div className="flex flex-col h-screen bg-[#0a0c10] text-gray-100 overflow-hidden">
      <Header
        blastRadius={analysis.blastRadius}
        blastBlocked={analysis.blastBlocked}
        faultCount={analysis.faultCount}
        hasHypothesis={analysis.hasHypothesis}
        hasCircuitBreaker={analysis.hasCircuitBreaker}
      />

      <main className="flex flex-1 overflow-hidden">
        {/* Blockly canvas */}
        <div className="flex-1 overflow-hidden relative">
          <BlocklyWorkspace onAnalysis={handleAnalysis} />
          {/* Module legend overlay */}
          <div className="absolute bottom-3 right-3 flex flex-col gap-1 pointer-events-none">
            {[
              { colour: 'bg-blue-500',   label: 'K-Vortex · Network'  },
              { colour: 'bg-red-500',    label: 'K-Reaper · Process'  },
              { colour: 'bg-purple-500', label: 'K-Gravity · Resources'},
              { colour: 'bg-teal-400',   label: 'K-Divide · Partition' },
            ].map(({ colour, label }) => (
              <div key={label} className="flex items-center gap-1.5 bg-[#0a0c10]/70 rounded px-2 py-0.5">
                <span className={`w-2 h-2 rounded-full ${colour}`} />
                <span className="text-[10px] text-gray-400">{label}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right panel — YAML + controls */}
        <div className="w-[400px] xl:w-[440px] flex flex-col border-l border-gray-800 bg-[#0a0c10] overflow-hidden">
          <YamlPreview yaml={analysis.yaml} blastBlocked={analysis.blastBlocked} />
        </div>
      </main>
    </div>
  );
}
