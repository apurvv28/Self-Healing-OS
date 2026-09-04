"""Tests for ResourceMonitor module."""

from monitor.resource_monitor import ResourceMonitor


def test_collect_system_metrics():
    monitor = ResourceMonitor(disk_paths=["/"])
    metrics = monitor.collect_system_metrics()

    assert "timestamp" in metrics
    assert "cpu" in metrics
    assert "total_percent" in metrics["cpu"]
    assert "memory" in metrics
    assert "used_percent" in metrics["memory"]
    assert "disk" in metrics
    assert "load_avg" in metrics


def test_collect_top_processes():
    monitor = ResourceMonitor()
    procs = monitor.collect_top_processes(limit=5, sort_by="cpu")

    assert isinstance(procs, list)
    if procs:
        p = procs[0]
        assert "pid" in p
        assert "name" in p
        assert "cpu_percent" in p


def test_normalize_resource_evidence():
    monitor = ResourceMonitor()
    metrics = monitor.collect_system_metrics()
    evidence_list = monitor.normalize_resource_evidence(metrics)

    assert isinstance(evidence_list, list)
    assert len(evidence_list) >= 2
    metric_names = [e["metric_name"] for e in evidence_list]
    assert "cpu_utilization" in metric_names
    assert "memory_utilization" in metric_names
