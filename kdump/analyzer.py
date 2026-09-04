"""Kernel crash dump analyzer for AegisOS."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CrashAnalyzer:
    """Parses vmcore and dmesg kernel crash dumps to extract panic causes and suspect modules."""

    PANIC_PATTERNS = [
        re.compile(r"Kernel panic - not syncing: (.*)", re.IGNORECASE),
        re.compile(r"BUG: unable to handle kernel (.*)", re.IGNORECASE),
        re.compile(r"SysRq : (Trigger a Crash.*)", re.IGNORECASE),
        re.compile(r"general protection fault: (.*)", re.IGNORECASE),
        re.compile(r"Machine Check Exception: (.*)", re.IGNORECASE),
    ]

    MODULE_PATTERN = re.compile(r"\[([a-zA-Z0-9_\-]+)\]")
    RIP_PATTERN = re.compile(r"RIP:\s*0010:\[<([0-9a-fA-F]+)>\]\s*([a-zA-Z0-9_]+)?")

    def parse_crash_log(self, dmesg_content: str) -> dict[str, Any]:
        """Parse raw dmesg crash log text into a structured KernelCrashReport."""
        lines = dmesg_content.splitlines()

        panic_type = "Unknown Kernel Panic"
        suspect_module = "kernel_core"
        faulting_function = "unknown"
        instruction_pointer = "0x0"
        call_trace: list[str] = []

        in_trace = False

        for line in lines:
            line_str = line.strip()

            # 1. Match Panic Message
            for pattern in self.PANIC_PATTERNS:
                match = pattern.search(line_str)
                if match:
                    panic_type = match.group(1).strip()
                    break

            # 2. Extract Instruction Pointer & Function
            rip_match = self.RIP_PATTERN.search(line_str)
            if rip_match:
                instruction_pointer = rip_match.group(1)
                if rip_match.group(2):
                    faulting_function = rip_match.group(2)

            # 3. Extract Suspect Module (from bracketed tags like [my_test_driver])
            if "[" in line_str and "]" in line_str:
                for mod_match in self.MODULE_PATTERN.finditer(line_str):
                    mod_candidate = mod_match.group(1)
                    if mod_candidate not in ("kernel", "dmesg", "syslog", "end trace", "CRITICAL", "WARNING"):
                        # Avoid hex numbers in brackets
                        if not re.match(r"^0x[0-9a-fA-F]+$", mod_candidate) and not mod_candidate.isdigit():
                            suspect_module = mod_candidate

            # 4. Extract Call Trace
            if "Call Trace:" in line_str:
                in_trace = True
                continue
            if in_trace:
                if not line_str or line_str.startswith("---[ end trace"):
                    in_trace = False
                else:
                    call_trace.append(line_str)

        if suspect_module == "kernel_core" and faulting_function != "unknown":
            suspect_module = faulting_function

        summary = f"Kernel Panic: '{panic_type}' in module '{suspect_module}'"

        return {
            "panic_type": panic_type,
            "suspect_module": suspect_module,
            "faulting_function": faulting_function,
            "instruction_pointer": instruction_pointer,
            "call_trace": call_trace[:10],
            "summary": summary,
            "raw_excerpt": "\n".join(lines[-15:]) if len(lines) > 15 else dmesg_content,
        }

    def parse_vmcore_file(self, file_path: str | Path) -> dict[str, Any]:
        """Parse a vmcore-dmesg text file or crash report from disk."""
        path = Path(file_path)
        if not path.exists():
            logger.warning("Crash dump file %s not found.", path)
            return {
                "panic_type": "Missing Crash Dump",
                "suspect_module": "unknown",
                "instruction_pointer": "0x0",
                "call_trace": [],
                "summary": f"Crash dump file {path} not found.",
                "raw_excerpt": "",
            }

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            return self.parse_crash_log(content)
        except Exception as exc:
            logger.error("Failed to read crash dump file %s: %s", path, exc)
            return {
                "panic_type": "Read Error",
                "suspect_module": "unknown",
                "instruction_pointer": "0x0",
                "call_trace": [],
                "summary": f"Failed to read crash dump file {path}: {exc}",
                "raw_excerpt": "",
            }
