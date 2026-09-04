"""Tests for agent.py CLI commands."""

import argparse

from agent import (
    cmd_incidents,
    cmd_metrics,
    cmd_run_cycle,
    cmd_status,
    cmd_trigger_scenario,
)


def test_cmd_status():
    args = argparse.Namespace(config="config/aegisos.yaml")
    cmd_status(args)


def test_cmd_incidents():
    args = argparse.Namespace(limit=5)
    cmd_incidents(args)


def test_cmd_metrics():
    args = argparse.Namespace()
    cmd_metrics(args)


def test_cmd_trigger_scenario():
    args = argparse.Namespace(config="config/aegisos.yaml", type="service_failure")
    cmd_trigger_scenario(args)


def test_cmd_run_cycle():
    args = argparse.Namespace(config="config/aegisos.yaml")
    cmd_run_cycle(args)
