"""K-Kube — Kubernetes fault injection (pod delete, node drain, scale-down, network policy, resource limits)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict

from kali.experiments.base import FaultInjector
from kali.models.experiment import ActionResult


async def _kubectl(
    *args: str,
    stdin: str | None = None,
) -> tuple[int, str, str]:
    """Run a kubectl command; returns (returncode, stdout, stderr)."""
    proc = await asyncio.create_subprocess_exec(
        "kubectl", *args,
        stdin=asyncio.subprocess.PIPE if stdin else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin.encode() if stdin else None)
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


# ── K-Kube: Pod Delete ────────────────────────────────────────────────────────

class KKubePodDeleteInjector(FaultInjector):
    """K-Kube: deletes pods matching a label selector, triggering restart via the deployment controller."""

    name = "kubernetes/pod-delete"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        namespace = provider.get("namespace", "default")
        selector = provider.get("label_selector", "")
        pod_name = provider.get("pod_name", "")
        grace = provider.get("grace_period_seconds", 0)

        if not selector and not pod_name:
            return ActionResult(
                action_name=self.name, success=False,
                error="Provider must specify 'label_selector' or 'pod_name'",
                started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
            )

        if pod_name:
            cmd = ["delete", "pod", pod_name, "-n", namespace, f"--grace-period={grace}"]
            target = pod_name
        else:
            cmd = ["delete", "pods", "-l", selector, "-n", namespace, f"--grace-period={grace}"]
            target = f"selector={selector}"

        started = datetime.utcnow()
        if not dry_run:
            rc, stdout, stderr = await _kubectl(*cmd)
            if rc != 0:
                return ActionResult(
                    action_name=self.name, success=False, error=stderr,
                    started_at=started, ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
            return ActionResult(
                action_name=self.name, success=True,
                output=f"K-Kube: deleted pods ({target}) in {namespace}\n{stdout}",
                started_at=started, ended_at=datetime.utcnow(),
            )
        return ActionResult(
            action_name=self.name, success=True,
            output=f"[dry-run] kubectl {' '.join(cmd)}",
            started_at=started, ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        started = datetime.utcnow()
        return ActionResult(
            action_name=f"{self.name}/rollback", success=True,
            output="K-Kube pod-delete: rollback is automatic — deployment controller recreates pods",
            started_at=started, ended_at=datetime.utcnow(),
        )


# ── K-Kube: Node Drain ────────────────────────────────────────────────────────

class KKubeNodeDrainInjector(FaultInjector):
    """K-Kube: drains a Kubernetes node (evicts all pods) then uncordons on rollback."""

    name = "kubernetes/node-drain"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        node = provider.get("node")
        if not node:
            return ActionResult(
                action_name=self.name, success=False, error="Provider must specify 'node'",
                started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
            )

        ignore_ds = "--ignore-daemonsets" if provider.get("ignore_daemonsets", True) else ""
        delete_data = "--delete-emptydir-data" if provider.get("delete_emptydir_data", True) else ""
        cmd = ["drain", node, "--force", ignore_ds, delete_data]
        cmd = [c for c in cmd if c]  # strip empty

        started = datetime.utcnow()
        if not dry_run:
            rc, stdout, stderr = await _kubectl(*cmd)
            if rc != 0:
                return ActionResult(
                    action_name=self.name, success=False, error=stderr,
                    started_at=started, ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name, success=True,
            output=f"[dry-run] kubectl {' '.join(cmd)}" if dry_run else f"K-Kube: drained node {node}",
            started_at=started, ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        node = provider.get("node", "")
        started = datetime.utcnow()
        if not dry_run and node:
            rc, stdout, stderr = await _kubectl("uncordon", node)
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=rc == 0,
                output=f"K-Kube: uncordoned {node}" if rc == 0 else None,
                error=stderr if rc != 0 else None,
                started_at=started, ended_at=datetime.utcnow(),
            )
        return ActionResult(
            action_name=f"{self.name}/rollback", success=True,
            output=f"[dry-run] kubectl uncordon {node}",
            started_at=started, ended_at=datetime.utcnow(),
        )


# ── K-Kube: Scale Down ───────────────────────────────────────────────────────

class KKubeScaleDownInjector(FaultInjector):
    """K-Kube: scales a deployment to 0 replicas; rollback restores the original count."""

    name = "kubernetes/scale-down"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        namespace = provider.get("namespace", "default")
        deployment = provider.get("deployment")
        if not deployment:
            return ActionResult(
                action_name=self.name, success=False, error="Provider must specify 'deployment'",
                started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
            )

        cmd = ["scale", "deployment", deployment, "--replicas=0", "-n", namespace]
        started = datetime.utcnow()
        if not dry_run:
            rc, stdout, stderr = await _kubectl(*cmd)
            if rc != 0:
                return ActionResult(
                    action_name=self.name, success=False, error=stderr,
                    started_at=started, ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name, success=True,
            output=f"[dry-run] kubectl {' '.join(cmd)}" if dry_run else f"K-Kube: scaled {deployment} to 0 in {namespace}",
            started_at=started, ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        namespace = provider.get("namespace", "default")
        deployment = provider.get("deployment", "")
        replicas = provider.get("replicas", 1)
        cmd = ["scale", "deployment", deployment, f"--replicas={replicas}", "-n", namespace]
        started = datetime.utcnow()
        if not dry_run and deployment:
            rc, _, stderr = await _kubectl(*cmd)
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=rc == 0,
                output=f"K-Kube: restored {deployment} to {replicas} replica(s)" if rc == 0 else None,
                error=stderr if rc != 0 else None,
                started_at=started, ended_at=datetime.utcnow(),
            )
        return ActionResult(
            action_name=f"{self.name}/rollback", success=True,
            output=f"[dry-run] kubectl {' '.join(cmd)}",
            started_at=started, ended_at=datetime.utcnow(),
        )


# ── K-Kube: Network Policy ───────────────────────────────────────────────────

class KKubeNetworkPolicyInjector(FaultInjector):
    """K-Kube: applies a deny-all NetworkPolicy to isolate pods; rollback deletes it."""

    name = "kubernetes/network-policy"

    def _policy_manifest(self, provider: Dict[str, Any]) -> str:
        namespace = provider.get("namespace", "default")
        selector = provider.get("pod_selector", {})
        deny_ingress = provider.get("deny_ingress", True)
        deny_egress = provider.get("deny_egress", False)
        policy_name = provider.get("policy_name", "kali-deny-policy")

        policy_types = []
        if deny_ingress:
            policy_types.append("Ingress")
        if deny_egress:
            policy_types.append("Egress")

        manifest = {
            "apiVersion": "networking.k8s.io/v1",
            "kind": "NetworkPolicy",
            "metadata": {"name": policy_name, "namespace": namespace},
            "spec": {
                "podSelector": {"matchLabels": selector} if selector else {},
                "policyTypes": policy_types,
            },
        }
        return json.dumps(manifest)

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        policy_name = provider.get("policy_name", "kali-deny-policy")
        namespace = provider.get("namespace", "default")
        manifest = self._policy_manifest(provider)

        started = datetime.utcnow()
        if not dry_run:
            rc, stdout, stderr = await _kubectl("apply", "-f", "-", stdin=manifest)
            if rc != 0:
                return ActionResult(
                    action_name=self.name, success=False, error=stderr,
                    started_at=started, ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name, success=True,
            output=(
                f"[dry-run] would apply NetworkPolicy '{policy_name}' in {namespace}"
                if dry_run
                else f"K-Kube: applied NetworkPolicy '{policy_name}' in {namespace}"
            ),
            started_at=started, ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        policy_name = provider.get("policy_name", "kali-deny-policy")
        namespace = provider.get("namespace", "default")
        started = datetime.utcnow()
        if not dry_run:
            rc, _, stderr = await _kubectl(
                "delete", "networkpolicy", policy_name, "-n", namespace, "--ignore-not-found"
            )
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=rc == 0,
                output=f"K-Kube: deleted NetworkPolicy '{policy_name}'" if rc == 0 else None,
                error=stderr if rc != 0 else None,
                started_at=started, ended_at=datetime.utcnow(),
            )
        return ActionResult(
            action_name=f"{self.name}/rollback", success=True,
            output=f"[dry-run] kubectl delete networkpolicy {policy_name} -n {namespace}",
            started_at=started, ended_at=datetime.utcnow(),
        )


# ── K-Kube: Resource Limit ───────────────────────────────────────────────────

class KKubeResourceLimitInjector(FaultInjector):
    """K-Kube: applies restrictive CPU/memory limits to a deployment's containers."""

    name = "kubernetes/resource-limit"

    async def inject(self, provider: Dict[str, Any], duration: int, dry_run: bool = False) -> ActionResult:
        namespace = provider.get("namespace", "default")
        deployment = provider.get("deployment")
        container = provider.get("container", "")
        cpu_limit = provider.get("cpu_limit", "100m")
        memory_limit = provider.get("memory_limit", "128Mi")

        if not deployment:
            return ActionResult(
                action_name=self.name, success=False, error="Provider must specify 'deployment'",
                started_at=datetime.utcnow(), ended_at=datetime.utcnow(),
            )

        patch: Dict[str, Any] = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {
                                "name": container or deployment,
                                "resources": {
                                    "limits": {"cpu": cpu_limit, "memory": memory_limit}
                                },
                            }
                        ]
                    }
                }
            }
        }

        started = datetime.utcnow()
        if not dry_run:
            rc, _, stderr = await _kubectl(
                "patch", "deployment", deployment, "-n", namespace,
                "--patch", json.dumps(patch),
            )
            if rc != 0:
                return ActionResult(
                    action_name=self.name, success=False, error=stderr,
                    started_at=started, ended_at=datetime.utcnow(),
                )
            await asyncio.sleep(duration)
        return ActionResult(
            action_name=self.name, success=True,
            output=(
                f"[dry-run] would patch {deployment}: cpu={cpu_limit}, memory={memory_limit}"
                if dry_run
                else f"K-Kube: applied limits to {deployment} (cpu={cpu_limit}, mem={memory_limit})"
            ),
            started_at=started, ended_at=datetime.utcnow(),
        )

    async def rollback(self, provider: Dict[str, Any], dry_run: bool = False) -> ActionResult:
        namespace = provider.get("namespace", "default")
        deployment = provider.get("deployment", "")
        container = provider.get("container", "") or deployment
        patch = {
            "spec": {
                "template": {
                    "spec": {
                        "containers": [{"name": container, "resources": {"limits": None}}]
                    }
                }
            }
        }
        started = datetime.utcnow()
        if not dry_run and deployment:
            rc, _, stderr = await _kubectl(
                "patch", "deployment", deployment, "-n", namespace,
                "--patch", json.dumps(patch),
            )
            return ActionResult(
                action_name=f"{self.name}/rollback",
                success=rc == 0,
                output=f"K-Kube: removed resource limits from {deployment}" if rc == 0 else None,
                error=stderr if rc != 0 else None,
                started_at=started, ended_at=datetime.utcnow(),
            )
        return ActionResult(
            action_name=f"{self.name}/rollback", success=True,
            output=f"[dry-run] would remove limits from {deployment}",
            started_at=started, ended_at=datetime.utcnow(),
        )
