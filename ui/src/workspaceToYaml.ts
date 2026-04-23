import * as Blockly from 'blockly';
import yaml from 'js-yaml';

// ─── helpers ──────────────────────────────────────────────────────────────────

function stmtBlocks(block: Blockly.Block, input: string): Blockly.Block[] {
  const out: Blockly.Block[] = [];
  let cur: Blockly.Block | null = block.getInputTargetBlock(input);
  while (cur) {
    if (!cur.isInsertionMarker()) out.push(cur);
    cur = cur.getNextBlock();
  }
  return out;
}

function str(b: Blockly.Block, f: string): string {
  return (b.getFieldValue(f) ?? '').toString().trim();
}

function num(b: Blockly.Block, f: string): number {
  return parseFloat(b.getFieldValue(f) ?? '0');
}

function bool(b: Blockly.Block, f: string): boolean {
  return b.getFieldValue(f) === 'TRUE';
}

function csvList(raw: string): string[] {
  return raw.split(',').map(s => s.trim()).filter(Boolean);
}

// ─── probe builders ───────────────────────────────────────────────────────────

function buildProbe(b: Blockly.Block): Record<string, unknown> | null {
  switch (b.type) {
    case 'probe_http':
      return {
        name: str(b, 'NAME'),
        type: 'http',
        provider: {
          url: str(b, 'URL'),
          method: str(b, 'METHOD'),
          expected_status: num(b, 'EXPECTED_STATUS'),
          timeout: num(b, 'TIMEOUT'),
        },
      };
    case 'probe_process':
      return {
        name: str(b, 'NAME'),
        type: 'process',
        provider: { process: str(b, 'PROCESS') },
      };
    case 'probe_metric':
      return {
        name: str(b, 'NAME'),
        type: 'metric',
        provider: {
          url: str(b, 'URL'),
          metric: str(b, 'METRIC'),
          operator: str(b, 'OPERATOR'),
          threshold: num(b, 'THRESHOLD'),
        },
      };
    default:
      return null;
  }
}

// ─── action builders ──────────────────────────────────────────────────────────

function buildAction(b: Blockly.Block): Record<string, unknown> | null {
  switch (b.type) {
    case 'fault_network_latency':
      return {
        name: str(b, 'NAME'),
        type: 'network/latency',
        duration: num(b, 'DURATION'),
        provider: {
          interface: str(b, 'INTERFACE'),
          delay_ms: num(b, 'DELAY_MS'),
          jitter_ms: num(b, 'JITTER_MS'),
        },
      };
    case 'fault_network_loss':
      return {
        name: str(b, 'NAME'),
        type: 'network/loss',
        duration: num(b, 'DURATION'),
        provider: {
          interface: str(b, 'INTERFACE'),
          loss_percent: num(b, 'LOSS_PERCENT'),
        },
      };
    case 'fault_process_kill':
      return {
        name: str(b, 'NAME'),
        type: 'process/kill',
        duration: num(b, 'DURATION'),
        provider: {
          process: str(b, 'PROCESS') || undefined,
          signal: str(b, 'SIGNAL'),
          restart_cmd: str(b, 'RESTART_CMD') || undefined,
        },
      };
    case 'fault_cpu_stress':
      return {
        name: str(b, 'NAME'),
        type: 'cpu/stress',
        duration: num(b, 'DURATION'),
        provider: {
          workers: num(b, 'WORKERS'),
          load_percent: num(b, 'LOAD_PERCENT'),
        },
      };
    case 'fault_memory_stress':
      return {
        name: str(b, 'NAME'),
        type: 'memory/stress',
        duration: num(b, 'DURATION'),
        provider: {
          workers: num(b, 'WORKERS'),
          memory_mb: num(b, 'MEMORY_MB'),
        },
      };
    case 'fault_network_partition':
      return {
        name: str(b, 'NAME'),
        type: 'network/partition',
        duration: num(b, 'DURATION'),
        provider: {
          targets: csvList(str(b, 'TARGETS')),
          direction: str(b, 'DIRECTION'),
        },
      };
    case 'fault_dns_fault':
      return {
        name: str(b, 'NAME'),
        type: 'network/dns-fault',
        duration: num(b, 'DURATION'),
        provider: {
          mode: str(b, 'MODE'),
          domains: csvList(str(b, 'DOMAINS')),
          blackhole_ip: str(b, 'BLACKHOLE_IP') || undefined,
        },
      };
    default:
      return null;
  }
}

// ─── rollback builders ────────────────────────────────────────────────────────

function buildRollback(b: Blockly.Block): Record<string, unknown> | null {
  if (!bool(b, 'ADD_ROLLBACK')) return null;
  const name = `rollback-${str(b, 'NAME')}`;
  switch (b.type) {
    case 'fault_network_latency':
    case 'fault_network_loss':
      return {
        name,
        type: b.type === 'fault_network_latency' ? 'network/latency' : 'network/loss',
        provider: { interface: str(b, 'INTERFACE') },
      };
    case 'fault_network_partition':
      return {
        name,
        type: 'network/partition',
        provider: { targets: csvList(str(b, 'TARGETS')), direction: str(b, 'DIRECTION') },
      };
    case 'fault_dns_fault':
      return {
        name,
        type: 'network/dns-fault',
        provider: { mode: str(b, 'MODE'), domains: csvList(str(b, 'DOMAINS')) },
      };
    default:
      return null;
  }
}

// ─── main export ──────────────────────────────────────────────────────────────

export interface WorkspaceAnalysis {
  yaml: string;
  blastRadius: number;
  blastBlocked: boolean;
  faultCount: number;
  hasHypothesis: boolean;
  hasCircuitBreaker: boolean;
}

export function analyseWorkspace(workspace: Blockly.WorkspaceSvg): WorkspaceAnalysis {
  const topBlocks = workspace.getTopBlocks(true);
  const exp = topBlocks.find(b => b.type === 'kali_experiment');

  if (!exp) {
    return {
      yaml: '# Drag a "⚡ KALI EXPERIMENT" block from the Setup toolbox to begin.',
      blastRadius: 0,
      blastBlocked: false,
      faultCount: 0,
      hasHypothesis: false,
      hasCircuitBreaker: false,
    };
  }

  const blastRadius = num(exp, 'BLAST_RADIUS');
  const blastBlocked = blastRadius >= 100;

  const hypothesisBlocks = stmtBlocks(exp, 'HYPOTHESIS');
  const hBlock = hypothesisBlocks[0];
  const probes = hBlock
    ? stmtBlocks(hBlock, 'PROBES').map(buildProbe).filter(Boolean)
    : [];

  const methodBlocks = stmtBlocks(exp, 'METHOD');
  const method = methodBlocks.map(buildAction).filter(Boolean);
  const rollbacks = methodBlocks.map(buildRollback).filter(Boolean);

  const cbBlocks = stmtBlocks(exp, 'CIRCUIT_BREAKER');
  const cb = cbBlocks[0];

  const tags = str(exp, 'TAGS');

  const config: Record<string, unknown> = {
    version: '1.0.0',
    title: str(exp, 'TITLE') || 'My Chaos Experiment',
    ...(str(exp, 'DESCRIPTION') ? { description: str(exp, 'DESCRIPTION') } : {}),
    tags: tags ? csvList(tags) : [],
    blast_radius: blastRadius,
    steady_state_hypothesis: {
      title: hBlock?.getFieldValue('TITLE') ?? 'System is healthy',
      probes,
    },
    method,
    rollbacks,
    circuit_breaker: cb
      ? {
          enabled: bool(cb, 'ENABLED'),
          check_interval: num(cb, 'CHECK_INTERVAL'),
          max_failures: num(cb, 'MAX_FAILURES'),
        }
      : { enabled: true, check_interval: 10, max_failures: 3 },
  };

  let yamlStr: string;
  try {
    yamlStr = yaml.dump(config, { indent: 2, lineWidth: 100, noRefs: true });
  } catch {
    yamlStr = '# YAML generation error — check block values';
  }

  return {
    yaml: yamlStr,
    blastRadius,
    blastBlocked,
    faultCount: methodBlocks.length,
    hasHypothesis: probes.length > 0,
    hasCircuitBreaker: cb != null,
  };
}
