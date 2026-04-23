import { useCallback, useState } from 'react';

interface Props {
  yaml: string;
  blastBlocked: boolean;
}

function tokenizeYaml(raw: string): string {
  return raw
    .split('\n')
    .map(line => {
      // comment
      if (/^\s*#/.test(line)) return `<span class="yaml-comment">${esc(line)}</span>`;
      // list item dash
      line = line.replace(/^(\s*)(- )/, (_m, sp, dash) => `${esc(sp)}<span class="yaml-dash">${esc(dash)}</span>`);
      // key: value
      line = line.replace(/^(\s*)([^:\n]+?)(:)(\s|$)/, (_m, sp, key, colon, after) =>
        `${esc(sp)}<span class="yaml-key">${esc(key)}</span>${esc(colon)}${after}`
      );
      // string values
      line = line.replace(/: (["'].*?["'])/, (_m, val) => `: <span class="yaml-str">${esc(val)}</span>`);
      // bare string values (after key:)
      line = line.replace(/: ([a-zA-Z][^\n#]*)$/, (_m, val) => `: <span class="yaml-str">${esc(val)}</span>`);
      // numbers
      line = line.replace(/: (\d+\.?\d*)/, (_m, val) => `: <span class="yaml-num">${val}</span>`);
      // booleans
      line = line.replace(/: (true|false)/, (_m, val) => `: <span class="yaml-bool">${val}</span>`);
      return line;
    })
    .join('\n');
}

function esc(s: string): string {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

export function YamlPreview({ yaml, blastBlocked }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = useCallback(async () => {
    await navigator.clipboard.writeText(yaml);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }, [yaml]);

  const download = useCallback(() => {
    const blob = new Blob([yaml], { type: 'text/yaml' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'experiment.yaml';
    a.click();
    URL.revokeObjectURL(url);
  }, [yaml]);

  const lineCount = yaml.split('\n').length;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Panel header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-800 bg-[#0f1117] shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-gray-500 uppercase tracking-widest">experiment.yaml</span>
          <span className="text-[10px] text-gray-700">{lineCount} lines</span>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={copy}
            className="text-[11px] px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-300 transition-colors"
          >
            {copied ? '✓ Copied' : 'Copy'}
          </button>
          <button
            onClick={download}
            disabled={blastBlocked}
            className="text-[11px] px-2.5 py-1 rounded bg-blue-900/60 hover:bg-blue-800/60 text-blue-300 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Download
          </button>
        </div>
      </div>

      {/* Blast radius warning banner */}
      {blastBlocked && (
        <div className="px-4 py-2 bg-red-950/60 border-b border-red-800 text-red-400 text-xs flex items-center gap-2 shrink-0">
          <span className="text-base">🛑</span>
          <span>
            <strong>Blast radius = 100% — execution blocked.</strong>{' '}
            Reduce to ≤ 99% in the experiment block to enable.
          </span>
        </div>
      )}

      {/* YAML code */}
      <div className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed">
        <pre
          className="text-gray-300 whitespace-pre-wrap break-words"
          dangerouslySetInnerHTML={{ __html: tokenizeYaml(yaml) }}
        />
      </div>

      {/* CLI footer */}
      <div className="shrink-0 border-t border-gray-800 px-4 py-3 bg-[#0f1117]">
        <div className="text-[10px] text-gray-600 mb-1 uppercase tracking-widest">Run with</div>
        <div className="flex items-center gap-2">
          <code className="text-[11px] text-emerald-400 font-mono flex-1 truncate">
            kali run experiment.yaml {blastBlocked ? '' : '--dry-run'}
          </code>
          {!blastBlocked && (
            <span className="text-[10px] bg-emerald-900/40 border border-emerald-700 text-emerald-400 rounded px-1.5 py-0.5">
              safe to run
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
