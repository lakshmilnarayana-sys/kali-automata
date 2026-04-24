import { useEffect, useRef, useCallback } from 'react';
import * as Blockly from 'blockly';
import { registerBlocks, toolboxConfig, STARTER_XML } from '../blocks';
import { analyseWorkspace, WorkspaceAnalysis } from '../workspaceToYaml';

registerBlocks();

interface Props {
  onAnalysis: (a: WorkspaceAnalysis) => void;
}

export function BlocklyWorkspace({ onAnalysis }: Props) {
  const divRef = useRef<HTMLDivElement>(null);
  const wsRef  = useRef<Blockly.WorkspaceSvg | null>(null);

  const reanalyse = useCallback((ws: Blockly.WorkspaceSvg) => {
    onAnalysis(analyseWorkspace(ws));
  }, [onAnalysis]);

  useEffect(() => {
    if (!divRef.current || wsRef.current) return;

    const ws = Blockly.inject(divRef.current, {
      toolbox: toolboxConfig,
      // Dark theme applied via CSS overrides in index.css
      grid: { spacing: 24, length: 4, colour: '#13161e', snap: true },
      zoom: { controls: true, wheel: true, startScale: 0.85, maxScale: 2, minScale: 0.3 },
      trashcan: true,
      move: { scrollbars: true, drag: true, wheel: false },
    });

    wsRef.current = ws;

    // Load starter experiment
    try {
      Blockly.Xml.domToWorkspace(Blockly.utils.xml.textToDom(STARTER_XML), ws);
    } catch (e) {
      console.warn('Could not load starter XML', e);
    }

    reanalyse(ws);

    const listener = (e: Blockly.Events.Abstract) => {
      const relevant = [
        Blockly.Events.BLOCK_CHANGE,
        Blockly.Events.BLOCK_CREATE,
        Blockly.Events.BLOCK_DELETE,
        Blockly.Events.BLOCK_MOVE,
      ];
      if (relevant.includes(e.type as string)) reanalyse(ws);
    };

    ws.addChangeListener(listener);

    const handleResize = () => Blockly.svgResize(ws);
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      ws.removeChangeListener(listener);
      ws.dispose();
      wsRef.current = null;
    };
  }, [reanalyse]);

  return <div ref={divRef} className="w-full h-full" />;
}
