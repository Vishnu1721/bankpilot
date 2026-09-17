"""Evaluator-facing CLI for discovery and deterministic capability replay."""

import argparse
import json
from pathlib import Path

from src.agent.budget import DiscoveryBudget
from src.agent.discovery import DiscoveryAgent
from src.capability.replay import ReplayEngine
from src.capability.results import ReplayStatus
from src.handoff.manager import HumanHandoffManager
from src.safety.policy import SafetyPolicy
from src.surface.browser import BrowserSurface


def key_value(value):
    if "=" not in value:
        raise argparse.ArgumentTypeError("Expected NAME=VALUE.")
    name, raw_value = value.split("=", 1)
    if not name.strip() or not raw_value:
        raise argparse.ArgumentTypeError("Expected a non-empty NAME=VALUE.")
    return name.strip(), raw_value


def build_parser():
    parser = argparse.ArgumentParser(
        description="Discover and deterministically replay BankPilot capabilities."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    discover = commands.add_parser(
        "discover", help="Run bounded LLM discovery and save an artifact."
    )
    discover.add_argument("--goal", required=True, help="Trusted user goal.")
    discover.add_argument("--target", required=True, help="Allowlisted starting URL.")
    discover.add_argument(
        "--artifact",
        default="artifacts/discovered_capability.json",
        help="Output capability JSON path.",
    )
    _add_parameters(discover, "Runtime parameter used during discovery.")
    discover.add_argument("--max-steps", type=int, default=10)
    discover.add_argument("--timeout-seconds", type=float, default=120.0)
    discover.add_argument("--headless", action="store_true")
    discover.add_argument(
        "--enable-handoff",
        action="store_true",
        help="Allow same-session terminal-guided human intervention.",
    )
    discover.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing artifact after successful discovery.",
    )
    discover.add_argument(
        "--log-path",
        default="evidence/discovery_log.jsonl",
        help="Structured discovery JSONL output.",
    )

    replay = commands.add_parser(
        "replay", help="Replay a saved artifact without invoking the LLM."
    )
    replay.add_argument("--artifact", required=True, help="Capability JSON path.")
    _add_parameters(replay, "Capability invocation parameter.")
    replay.add_argument("--headless", action="store_true")
    replay.add_argument(
        "--enable-handoff",
        action="store_true",
        help="Allow same-session terminal-guided human intervention.",
    )
    replay.add_argument(
        "--log-path",
        default="evidence/replay_log.jsonl",
        help="Structured replay JSONL output.",
    )
    return parser


def _add_parameters(parser, help_text):
    parser.add_argument(
        "--parameter",
        "--param",
        action="append",
        default=[],
        type=key_value,
        metavar="NAME=VALUE",
        help=f"{help_text} Repeat as needed.",
    )


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.headless and args.enable_handoff:
        raise SystemExit("--enable-handoff requires a visible browser.")
    if args.command == "discover":
        return run_discovery(args)
    return run_replay(args)


def run_discovery(args):
    if args.max_steps < 1 or args.timeout_seconds <= 0:
        raise SystemExit("--max-steps and --timeout-seconds must be positive.")

    artifact_path = Path(args.artifact)
    if artifact_path.exists() and not args.overwrite:
        raise SystemExit(
            f"Artifact already exists: {artifact_path}. Use --overwrite to replace it."
        )

    parameters = dict(args.parameter)
    safety = SafetyPolicy()
    safety.check_url(args.target)

    surface = BrowserSurface(headless=args.headless).start()
    try:
        surface.navigate(args.target)
        handoff = HumanHandoffManager(surface) if args.enable_handoff else None
        agent = DiscoveryAgent(
            surface,
            safety_policy=safety,
            budget=DiscoveryBudget(
                max_steps=args.max_steps,
                max_llm_calls=args.max_steps,
                max_elapsed_seconds=args.timeout_seconds,
            ),
            handoff_manager=handoff,
            log_path=args.log_path,
        )
        result = agent.run(
            goal=args.goal,
            artifact_path=str(artifact_path),
            parameters=parameters,
        )
        completed = artifact_path.is_file() and not (
            isinstance(result, dict) and result.get("status") in {
                "escalated", "human_intervention_completed"
            }
        )
        print(json.dumps({"artifact": str(artifact_path) if completed else None,
                          "result": result}, indent=2))
        return 0 if completed else 1
    finally:
        surface.close()


def run_replay(args):
    artifact_path = Path(args.artifact)
    if not artifact_path.is_file():
        raise SystemExit(f"Artifact does not exist: {artifact_path}")

    surface = BrowserSurface(headless=args.headless).start()
    try:
        handoff = HumanHandoffManager(surface) if args.enable_handoff else None
        engine = ReplayEngine(
            surface,
            handoff_manager=handoff,
            log_path=args.log_path,
        )
        capability = engine.load_capability(artifact_path)
        result = engine.run(capability, dict(args.parameter))
        print(json.dumps(result.model_dump(mode="json"), indent=2))
        return 1 if result.status == ReplayStatus.FAILURE else 0
    finally:
        surface.close()


if __name__ == "__main__":
    raise SystemExit(main())
