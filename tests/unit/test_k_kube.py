"""Unit tests for K-Kube Kubernetes fault injectors."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from kali.experiments.k_kube import (
    KKubeNetworkPolicyInjector,
    KKubeNodeDrainInjector,
    KKubePodDeleteInjector,
    KKubeResourceLimitInjector,
    KKubeScaleDownInjector,
)
from kali.experiments import INJECTOR_REGISTRY


# ── Registry ──────────────────────────────────────────────────────────────────

def test_registry_contains_k_kube_types():
    expected = {
        "kubernetes/pod-delete",
        "kubernetes/node-drain",
        "kubernetes/scale-down",
        "kubernetes/network-policy",
        "kubernetes/resource-limit",
    }
    assert expected.issubset(set(INJECTOR_REGISTRY.keys()))


# ── K-Kube: Pod Delete ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pod_delete_dry_run_label_selector():
    injector = KKubePodDeleteInjector()
    result = await injector.inject(
        {"namespace": "default", "label_selector": "app=my-api"}, 1, dry_run=True
    )
    assert result.success is True
    assert "[dry-run]" in result.output
    assert "delete" in result.output.lower()


@pytest.mark.asyncio
async def test_pod_delete_dry_run_pod_name():
    injector = KKubePodDeleteInjector()
    result = await injector.inject(
        {"namespace": "default", "pod_name": "my-pod-abc123"}, 1, dry_run=True
    )
    assert result.success is True
    assert "my-pod-abc123" in result.output


@pytest.mark.asyncio
async def test_pod_delete_fails_without_selector_or_name():
    injector = KKubePodDeleteInjector()
    result = await injector.inject({"namespace": "default"}, 1, dry_run=False)
    assert result.success is False
    assert "label_selector" in result.error or "pod_name" in result.error


@pytest.mark.asyncio
async def test_pod_delete_rollback_is_noop():
    injector = KKubePodDeleteInjector()
    result = await injector.rollback({}, dry_run=True)
    assert result.success is True
    assert "automatic" in result.output.lower()


@pytest.mark.asyncio
async def test_pod_delete_live_calls_kubectl():
    injector = KKubePodDeleteInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(0, "pod deleted", "")):
        result = await injector.inject(
            {"namespace": "prod", "label_selector": "app=svc"}, 0, dry_run=False
        )
    assert result.success is True
    assert "prod" in result.output


@pytest.mark.asyncio
async def test_pod_delete_live_fails_on_nonzero():
    injector = KKubePodDeleteInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(1, "", "not found")):
        result = await injector.inject(
            {"namespace": "default", "label_selector": "app=x"}, 0, dry_run=False
        )
    assert result.success is False
    assert "not found" in result.error


# ── K-Kube: Node Drain ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_node_drain_dry_run():
    injector = KKubeNodeDrainInjector()
    result = await injector.inject(
        {"node": "worker-1", "ignore_daemonsets": True}, 1, dry_run=True
    )
    assert result.success is True
    assert "worker-1" in result.output


@pytest.mark.asyncio
async def test_node_drain_fails_without_node():
    injector = KKubeNodeDrainInjector()
    result = await injector.inject({}, 1, dry_run=False)
    assert result.success is False
    assert "node" in result.error.lower()


@pytest.mark.asyncio
async def test_node_drain_rollback_uncordons_dry_run():
    injector = KKubeNodeDrainInjector()
    result = await injector.rollback({"node": "worker-1"}, dry_run=True)
    assert result.success is True
    assert "uncordon" in result.output.lower()


@pytest.mark.asyncio
async def test_node_drain_rollback_calls_kubectl():
    injector = KKubeNodeDrainInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(0, "node/worker-1 uncordoned", "")):
        result = await injector.rollback({"node": "worker-1"}, dry_run=False)
    assert result.success is True


# ── K-Kube: Scale Down ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_scale_down_dry_run():
    injector = KKubeScaleDownInjector()
    result = await injector.inject(
        {"namespace": "default", "deployment": "my-app"}, 1, dry_run=True
    )
    assert result.success is True
    assert "replicas=0" in result.output


@pytest.mark.asyncio
async def test_scale_down_fails_without_deployment():
    injector = KKubeScaleDownInjector()
    result = await injector.inject({"namespace": "default"}, 1, dry_run=False)
    assert result.success is False
    assert "deployment" in result.error.lower()


@pytest.mark.asyncio
async def test_scale_down_rollback_dry_run():
    injector = KKubeScaleDownInjector()
    result = await injector.rollback(
        {"namespace": "default", "deployment": "my-app", "replicas": 3}, dry_run=True
    )
    assert result.success is True
    assert "replicas=3" in result.output


@pytest.mark.asyncio
async def test_scale_down_live():
    injector = KKubeScaleDownInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(0, "scaled", "")):
        result = await injector.inject(
            {"namespace": "default", "deployment": "my-app"}, 0, dry_run=False
        )
    assert result.success is True


# ── K-Kube: Network Policy ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_network_policy_dry_run():
    injector = KKubeNetworkPolicyInjector()
    result = await injector.inject(
        {"namespace": "default", "policy_name": "kali-deny", "deny_ingress": True},
        1, dry_run=True,
    )
    assert result.success is True
    assert "kali-deny" in result.output


@pytest.mark.asyncio
async def test_network_policy_manifest_includes_policy_types():
    injector = KKubeNetworkPolicyInjector()
    import json
    manifest = injector._policy_manifest({
        "namespace": "staging",
        "policy_name": "deny-all",
        "deny_ingress": True,
        "deny_egress": True,
    })
    parsed = json.loads(manifest)
    assert "Ingress" in parsed["spec"]["policyTypes"]
    assert "Egress" in parsed["spec"]["policyTypes"]
    assert parsed["metadata"]["namespace"] == "staging"


@pytest.mark.asyncio
async def test_network_policy_rollback_dry_run():
    injector = KKubeNetworkPolicyInjector()
    result = await injector.rollback(
        {"namespace": "default", "policy_name": "kali-deny"}, dry_run=True
    )
    assert result.success is True
    assert "kali-deny" in result.output


@pytest.mark.asyncio
async def test_network_policy_live_calls_kubectl_apply():
    injector = KKubeNetworkPolicyInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(0, "networkpolicy/kali-deny-policy created", "")):
        result = await injector.inject(
            {"namespace": "default", "deny_ingress": True}, 0, dry_run=False
        )
    assert result.success is True


# ── K-Kube: Resource Limit ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_resource_limit_dry_run():
    injector = KKubeResourceLimitInjector()
    result = await injector.inject(
        {"namespace": "default", "deployment": "my-app", "cpu_limit": "100m", "memory_limit": "128Mi"},
        1, dry_run=True,
    )
    assert result.success is True
    assert "100m" in result.output
    assert "128Mi" in result.output


@pytest.mark.asyncio
async def test_resource_limit_fails_without_deployment():
    injector = KKubeResourceLimitInjector()
    result = await injector.inject({"namespace": "default"}, 1, dry_run=False)
    assert result.success is False
    assert "deployment" in result.error.lower()


@pytest.mark.asyncio
async def test_resource_limit_rollback_dry_run():
    injector = KKubeResourceLimitInjector()
    result = await injector.rollback(
        {"namespace": "default", "deployment": "my-app"}, dry_run=True
    )
    assert result.success is True
    assert "limit" in result.output.lower()


@pytest.mark.asyncio
async def test_resource_limit_live_calls_kubectl_patch():
    injector = KKubeResourceLimitInjector()
    with patch("kali.experiments.k_kube._kubectl", new_callable=AsyncMock, return_value=(0, "deployment patched", "")):
        result = await injector.inject(
            {"namespace": "default", "deployment": "my-app", "cpu_limit": "50m", "memory_limit": "64Mi"},
            0, dry_run=False,
        )
    assert result.success is True
