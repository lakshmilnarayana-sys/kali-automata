import * as Blockly from 'blockly';

// ─── Hue palette matching K-* module brand colours ───────────────────────────
const HUE = {
  experiment:      45,   // amber
  hypothesis:     160,   // emerald
  probe:          150,   // green
  circuitBreaker: 200,   // slate
  vortex:         220,   // blue   — K-Vortex
  reaper:           0,   // red    — K-Reaper
  gravity:        270,   // purple — K-Gravity
  divide:         175,   // teal   — K-Divide
  kube:           195,   // cyan   — K-Kube
};

// Blockly's FieldDropdown type is Field<string> but appendField expects Field<string|undefined>.
// The variance mismatch is a known Blockly typings quirk — cast via unknown to suppress it.
function dd(options: [string, string][], name?: string): Blockly.Field {
  return new Blockly.FieldDropdown(options) as unknown as Blockly.Field;
}

export function registerBlocks(): void {

  // ── EXPERIMENT ROOT ──────────────────────────────────────────────────────
  Blockly.Blocks['kali_experiment'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.experiment);
      this.appendDummyInput().appendField('⚡  KALI EXPERIMENT');
      this.appendDummyInput()
        .appendField('   Title')
        .appendField(new Blockly.FieldTextInput('My Chaos Experiment'), 'TITLE');
      this.appendDummyInput()
        .appendField('   Description')
        .appendField(new Blockly.FieldTextInput(''), 'DESCRIPTION');
      this.appendDummyInput()
        .appendField('   Tags (comma-separated)')
        .appendField(new Blockly.FieldTextInput(''), 'TAGS');
      this.appendDummyInput()
        .appendField('   Blast Radius  ')
        .appendField(new Blockly.FieldNumber(50, 0, 99, 1), 'BLAST_RADIUS')
        .appendField('%  (max 99 — 100% is blocked)');
      this.appendStatementInput('HYPOTHESIS').setCheck('Hypothesis').appendField('🎯  Steady State');
      this.appendStatementInput('METHOD').setCheck('Fault').appendField('⚙️  Method');
      this.appendStatementInput('CIRCUIT_BREAKER').setCheck('CircuitBreaker').appendField('🔒  Circuit Breaker');
      this.setDeletable(false);
      this.setTooltip('Root experiment block. Blast Radius 100% is blocked by the safety engine.');
    },
  };

  // ── STEADY STATE HYPOTHESIS ──────────────────────────────────────────────
  Blockly.Blocks['kali_hypothesis'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.hypothesis);
      this.appendDummyInput().appendField('🎯  STEADY STATE HYPOTHESIS');
      this.appendDummyInput()
        .appendField('   Title')
        .appendField(new Blockly.FieldTextInput('System is healthy'), 'TITLE');
      this.appendStatementInput('PROBES').setCheck('Probe').appendField('   Probes');
      this.setPreviousStatement(true, 'Hypothesis');
      this.setNextStatement(false);
      this.setTooltip('Defines what "healthy" looks like. Checked before and after the experiment.');
    },
  };

  // ── CIRCUIT BREAKER ──────────────────────────────────────────────────────
  Blockly.Blocks['kali_circuit_breaker'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.circuitBreaker);
      this.appendDummyInput().appendField('🔒  CIRCUIT BREAKER');
      this.appendDummyInput()
        .appendField('   Enabled')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ENABLED');
      this.appendDummyInput()
        .appendField('   Check interval')
        .appendField(new Blockly.FieldNumber(10, 1, 300, 1), 'CHECK_INTERVAL')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Max failures before abort')
        .appendField(new Blockly.FieldNumber(3, 1, 20, 1), 'MAX_FAILURES');
      this.setPreviousStatement(true, 'CircuitBreaker');
      this.setNextStatement(false);
      this.setTooltip('Auto-aborts the experiment and triggers immediate rollback after N consecutive probe failures.');
    },
  };

  // ═══════════════════════════════════ PROBES ═══════════════════════════════

  Blockly.Blocks['probe_http'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.probe);
      this.appendDummyInput().appendField('🌐  HTTP PROBE');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('health-check'), 'NAME');
      this.appendDummyInput()
        .appendField('   URL')
        .appendField(new Blockly.FieldTextInput('http://localhost:8080/health'), 'URL');
      this.appendDummyInput()
        .appendField('   Method')
        .appendField(dd([['GET','GET'],['POST','POST'],['PUT','PUT'],['HEAD','HEAD']]), 'METHOD')
        .appendField('   Expected status')
        .appendField(new Blockly.FieldNumber(200, 100, 599, 1), 'EXPECTED_STATUS');
      this.appendDummyInput()
        .appendField('   Timeout')
        .appendField(new Blockly.FieldNumber(3, 0.5, 30, 0.5), 'TIMEOUT')
        .appendField('seconds');
      this.setPreviousStatement(true, 'Probe');
      this.setNextStatement(true, 'Probe');
      this.setTooltip('HTTP health-check probe. Passes when the response status matches.');
    },
  };

  Blockly.Blocks['probe_process'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.probe);
      this.appendDummyInput().appendField('⚙️  PROCESS PROBE');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('process-check'), 'NAME');
      this.appendDummyInput()
        .appendField('   Process name')
        .appendField(new Blockly.FieldTextInput('myapp'), 'PROCESS');
      this.setPreviousStatement(true, 'Probe');
      this.setNextStatement(true, 'Probe');
      this.setTooltip('Passes when the named process is running (uses pgrep).');
    },
  };

  Blockly.Blocks['probe_metric'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.probe);
      this.appendDummyInput().appendField('📊  METRIC PROBE');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('error-rate'), 'NAME');
      this.appendDummyInput()
        .appendField('   Prometheus URL')
        .appendField(new Blockly.FieldTextInput('http://localhost:9090/api/v1/query'), 'URL');
      this.appendDummyInput()
        .appendField('   Metric name')
        .appendField(new Blockly.FieldTextInput('http_error_rate'), 'METRIC');
      this.appendDummyInput()
        .appendField('   Operator')
        .appendField(dd([['<','<'],['<=','<='],['>=','>='],['==','=='],['!=','!=']]), 'OPERATOR')
        .appendField('   Threshold')
        .appendField(new Blockly.FieldNumber(0.01, 0), 'THRESHOLD');
      this.setPreviousStatement(true, 'Probe');
      this.setNextStatement(true, 'Probe');
      this.setTooltip('Queries a Prometheus-compatible endpoint and checks the metric value against a threshold.');
    },
  };

  // ═══════════════════════════ K-VORTEX  ·  Network ════════════════════════

  Blockly.Blocks['fault_network_latency'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.vortex);
      this.appendDummyInput().appendField('🌊  K-VORTEX · Network Latency');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('inject-latency'), 'NAME');
      this.appendDummyInput()
        .appendField('   Interface')
        .appendField(new Blockly.FieldTextInput('eth0'), 'INTERFACE')
        .appendField('   Delay')
        .appendField(new Blockly.FieldNumber(200, 0), 'DELAY_MS')
        .appendField('ms  ±')
        .appendField(new Blockly.FieldNumber(50, 0), 'JITTER_MS')
        .appendField('ms');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Adds artificial latency via tc netem. Rollback clears the rule immediately on abort.');
    },
  };

  Blockly.Blocks['fault_network_loss'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.vortex);
      this.appendDummyInput().appendField('🌊  K-VORTEX · Packet Loss');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('inject-packet-loss'), 'NAME');
      this.appendDummyInput()
        .appendField('   Interface')
        .appendField(new Blockly.FieldTextInput('eth0'), 'INTERFACE')
        .appendField('   Loss')
        .appendField(new Blockly.FieldNumber(10, 0, 100, 1), 'LOSS_PERCENT')
        .appendField('%');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Drops a percentage of packets via tc netem.');
    },
  };

  // ═══════════════════════════ K-REAPER  ·  Process ════════════════════════

  Blockly.Blocks['fault_process_kill'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.reaper);
      this.appendDummyInput().appendField('💀  K-REAPER · Kill Process');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('kill-service'), 'NAME');
      this.appendDummyInput()
        .appendField('   Process name')
        .appendField(new Blockly.FieldTextInput('myapp'), 'PROCESS');
      this.appendDummyInput()
        .appendField('   Signal')
        .appendField(dd([['SIGTERM','SIGTERM'],['SIGKILL','SIGKILL'],['SIGHUP','SIGHUP'],['SIGSTOP','SIGSTOP']]), 'SIGNAL');
      this.appendDummyInput()
        .appendField('   Restart command (rollback)')
        .appendField(new Blockly.FieldTextInput(''), 'RESTART_CMD');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Sends a signal to a process. Set restart command for automatic rollback.');
    },
  };

  // ═══════════════════════════ K-GRAVITY  ·  Resources ═════════════════════

  Blockly.Blocks['fault_cpu_stress'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.gravity);
      this.appendDummyInput().appendField('🏋  K-GRAVITY · CPU Stress');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('cpu-stress'), 'NAME');
      this.appendDummyInput()
        .appendField('   Workers')
        .appendField(new Blockly.FieldNumber(2, 1, 128, 1), 'WORKERS')
        .appendField('   Load')
        .appendField(new Blockly.FieldNumber(80, 1, 100, 1), 'LOAD_PERCENT')
        .appendField('%');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Burns CPU cores using stress-ng. Rollback kills stress-ng immediately.');
    },
  };

  Blockly.Blocks['fault_memory_stress'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.gravity);
      this.appendDummyInput().appendField('🏋  K-GRAVITY · Memory Stress');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('memory-stress'), 'NAME');
      this.appendDummyInput()
        .appendField('   Workers')
        .appendField(new Blockly.FieldNumber(1, 1, 32, 1), 'WORKERS')
        .appendField('   Memory')
        .appendField(new Blockly.FieldNumber(512, 64, 65536, 64), 'MEMORY_MB')
        .appendField('MB');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Allocates RAM using stress-ng --vm. Rollback kills stress-ng immediately.');
    },
  };

  // ═══════════════════════════ K-DIVIDE  ·  Partition / DNS ════════════════

  Blockly.Blocks['fault_network_partition'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.divide);
      this.appendDummyInput().appendField('✂️  K-DIVIDE · Network Partition');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('partition-downstream'), 'NAME');
      this.appendDummyInput()
        .appendField('   Target IPs / CIDRs (comma-separated)')
        .appendField(new Blockly.FieldTextInput('10.0.0.50, 10.0.0.51'), 'TARGETS');
      this.appendDummyInput()
        .appendField('   Direction')
        .appendField(dd([['Both','both'],['Inbound','inbound'],['Outbound','outbound']]), 'DIRECTION');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(60, 1), 'DURATION')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Blocks traffic to/from target IPs via iptables DROP rules.');
    },
  };

  Blockly.Blocks['fault_dns_fault'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.divide);
      this.appendDummyInput().appendField('✂️  K-DIVIDE · DNS Fault');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('dns-fault'), 'NAME');
      this.appendDummyInput()
        .appendField('   Mode')
        .appendField(dd([['Poison /etc/hosts','poison'],['Block port 53','block']]), 'MODE');
      this.appendDummyInput()
        .appendField('   Domains (comma-separated)')
        .appendField(new Blockly.FieldTextInput('payments.example.com'), 'DOMAINS');
      this.appendDummyInput()
        .appendField('   Blackhole IP (poison mode)')
        .appendField(new Blockly.FieldTextInput('192.0.2.1'), 'BLACKHOLE_IP');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(45, 1), 'DURATION')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Poisons DNS resolution or blocks port 53. Rollback restores /etc/hosts immediately.');
    },
  };

  // ═══════════════════════════ K-KUBE  ·  Kubernetes ═══════════════════════

  Blockly.Blocks['fault_kube_pod_delete'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.kube);
      this.appendDummyInput().appendField('☸️  K-KUBE · Pod Delete');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('delete-pods'), 'NAME');
      this.appendDummyInput()
        .appendField('   Namespace')
        .appendField(new Blockly.FieldTextInput('default'), 'NAMESPACE');
      this.appendDummyInput()
        .appendField('   Label selector  (e.g. app=my-api)')
        .appendField(new Blockly.FieldTextInput('app=my-api'), 'LABEL_SELECTOR');
      this.appendDummyInput()
        .appendField('   Grace period')
        .appendField(new Blockly.FieldNumber(0, 0), 'GRACE_PERIOD')
        .appendField('seconds   Duration')
        .appendField(new Blockly.FieldNumber(30, 1), 'DURATION')
        .appendField('seconds');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Deletes pods by label selector. The deployment controller recreates them automatically.');
    },
  };

  Blockly.Blocks['fault_kube_scale_down'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.kube);
      this.appendDummyInput().appendField('☸️  K-KUBE · Scale to Zero');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('scale-down'), 'NAME');
      this.appendDummyInput()
        .appendField('   Namespace')
        .appendField(new Blockly.FieldTextInput('default'), 'NAMESPACE')
        .appendField('   Deployment')
        .appendField(new Blockly.FieldTextInput('my-service'), 'DEPLOYMENT');
      this.appendDummyInput()
        .appendField('   Restore to')
        .appendField(new Blockly.FieldNumber(3, 1, 100, 1), 'REPLICAS')
        .appendField('replicas (rollback)   Duration')
        .appendField(new Blockly.FieldNumber(60, 1), 'DURATION')
        .appendField('seconds');
      this.appendDummyInput()
        .appendField('   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Scales a deployment to 0 replicas. Rollback restores to the specified replica count.');
    },
  };

  Blockly.Blocks['fault_kube_node_drain'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.kube);
      this.appendDummyInput().appendField('☸️  K-KUBE · Node Drain');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('drain-node'), 'NAME');
      this.appendDummyInput()
        .appendField('   Node name')
        .appendField(new Blockly.FieldTextInput('worker-node-1'), 'NODE');
      this.appendDummyInput()
        .appendField('   Ignore DaemonSets')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'IGNORE_DS')
        .appendField('   Delete emptyDir data')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'DELETE_DATA');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(60, 1), 'DURATION')
        .appendField('seconds   Auto-rollback (uncordon)')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Drains a Kubernetes node. Rollback runs kubectl uncordon immediately.');
    },
  };

  Blockly.Blocks['fault_kube_network_policy'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.kube);
      this.appendDummyInput().appendField('☸️  K-KUBE · Network Policy');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('isolate-pods'), 'NAME');
      this.appendDummyInput()
        .appendField('   Namespace')
        .appendField(new Blockly.FieldTextInput('default'), 'NAMESPACE')
        .appendField('   Policy name')
        .appendField(new Blockly.FieldTextInput('kali-deny-policy'), 'POLICY_NAME');
      this.appendDummyInput()
        .appendField('   Deny ingress')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'DENY_INGRESS')
        .appendField('   Deny egress')
        .appendField(new Blockly.FieldCheckbox('FALSE'), 'DENY_EGRESS');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(60, 1), 'DURATION')
        .appendField('seconds   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Applies a deny NetworkPolicy. Rollback deletes the policy immediately.');
    },
  };

  Blockly.Blocks['fault_kube_resource_limit'] = {
    init(this: Blockly.Block) {
      this.setColour(HUE.kube);
      this.appendDummyInput().appendField('☸️  K-KUBE · Resource Limits');
      this.appendDummyInput()
        .appendField('   Name')
        .appendField(new Blockly.FieldTextInput('throttle-resources'), 'NAME');
      this.appendDummyInput()
        .appendField('   Namespace')
        .appendField(new Blockly.FieldTextInput('default'), 'NAMESPACE')
        .appendField('   Deployment')
        .appendField(new Blockly.FieldTextInput('my-service'), 'DEPLOYMENT');
      this.appendDummyInput()
        .appendField('   CPU limit')
        .appendField(new Blockly.FieldTextInput('100m'), 'CPU_LIMIT')
        .appendField('   Memory limit')
        .appendField(new Blockly.FieldTextInput('128Mi'), 'MEMORY_LIMIT');
      this.appendDummyInput()
        .appendField('   Duration')
        .appendField(new Blockly.FieldNumber(60, 1), 'DURATION')
        .appendField('seconds   Auto-rollback')
        .appendField(new Blockly.FieldCheckbox('TRUE'), 'ADD_ROLLBACK');
      this.setPreviousStatement(true, 'Fault');
      this.setNextStatement(true, 'Fault');
      this.setTooltip('Patches a deployment with restrictive CPU/memory limits. Rollback removes them immediately.');
    },
  };
}

// ─── Toolbox configuration ────────────────────────────────────────────────────

export const toolboxConfig = {
  kind: 'categoryToolbox',
  contents: [
    {
      kind: 'category', name: '📋  Setup', colour: `${HUE.experiment}`,
      contents: [
        { kind: 'block', type: 'kali_experiment' },
        { kind: 'block', type: 'kali_hypothesis' },
        { kind: 'block', type: 'kali_circuit_breaker' },
      ],
    },
    {
      kind: 'category', name: '🔍  Probes', colour: `${HUE.probe}`,
      contents: [
        { kind: 'block', type: 'probe_http' },
        { kind: 'block', type: 'probe_process' },
        { kind: 'block', type: 'probe_metric' },
      ],
    },
    {
      kind: 'category', name: '🌊  K-Vortex · Network', colour: `${HUE.vortex}`,
      contents: [
        { kind: 'block', type: 'fault_network_latency' },
        { kind: 'block', type: 'fault_network_loss' },
      ],
    },
    {
      kind: 'category', name: '💀  K-Reaper · Process', colour: `${HUE.reaper}`,
      contents: [{ kind: 'block', type: 'fault_process_kill' }],
    },
    {
      kind: 'category', name: '🏋  K-Gravity · Resources', colour: `${HUE.gravity}`,
      contents: [
        { kind: 'block', type: 'fault_cpu_stress' },
        { kind: 'block', type: 'fault_memory_stress' },
      ],
    },
    {
      kind: 'category', name: '✂️  K-Divide · Partition', colour: `${HUE.divide}`,
      contents: [
        { kind: 'block', type: 'fault_network_partition' },
        { kind: 'block', type: 'fault_dns_fault' },
      ],
    },
    {
      kind: 'category', name: '☸️  K-Kube · Kubernetes', colour: `${HUE.kube}`,
      contents: [
        { kind: 'block', type: 'fault_kube_pod_delete' },
        { kind: 'block', type: 'fault_kube_scale_down' },
        { kind: 'block', type: 'fault_kube_node_drain' },
        { kind: 'block', type: 'fault_kube_network_policy' },
        { kind: 'block', type: 'fault_kube_resource_limit' },
      ],
    },
  ],
};

// ─── Starter workspace XML ────────────────────────────────────────────────────

export const STARTER_XML = `
<xml xmlns="https://developers.google.com/blockly/xml">
  <block type="kali_experiment" x="30" y="30">
    <field name="TITLE">API Latency Resilience Test</field>
    <field name="DESCRIPTION">Verify the API handles 500ms network latency gracefully</field>
    <field name="TAGS">k-vortex, network, api</field>
    <field name="BLAST_RADIUS">30</field>
    <statement name="HYPOTHESIS">
      <block type="kali_hypothesis">
        <field name="TITLE">API is healthy and responsive</field>
        <statement name="PROBES">
          <block type="probe_http">
            <field name="NAME">api-health</field>
            <field name="URL">http://localhost:8080/health</field>
            <field name="METHOD">GET</field>
            <field name="EXPECTED_STATUS">200</field>
            <field name="TIMEOUT">3</field>
          </block>
        </statement>
      </block>
    </statement>
    <statement name="METHOD">
      <block type="fault_network_latency">
        <field name="NAME">inject-500ms-latency</field>
        <field name="INTERFACE">eth0</field>
        <field name="DELAY_MS">500</field>
        <field name="JITTER_MS">100</field>
        <field name="DURATION">60</field>
        <field name="ADD_ROLLBACK">TRUE</field>
      </block>
    </statement>
    <statement name="CIRCUIT_BREAKER">
      <block type="kali_circuit_breaker">
        <field name="ENABLED">TRUE</field>
        <field name="CHECK_INTERVAL">10</field>
        <field name="MAX_FAILURES">3</field>
      </block>
    </statement>
  </block>
</xml>`;
