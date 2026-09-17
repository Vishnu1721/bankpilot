"""Parameterized live-browser assertion runner; no model API key required."""

import argparse
import json

from main import key_value

from src.capability.replay import ReplayEngine
from src.surface.browser import BrowserSurface


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--artifact', required=True)
    parser.add_argument('--param', action='append', type=key_value, default=[])
    parser.add_argument('--expect-status', required=True,
                        choices=['success', 'business_outcome', 'failure'])
    parser.add_argument('--expect-code')
    parser.add_argument('--expect-output', action='append', type=key_value, default=[])
    parser.add_argument('--log-path', default='tmp/reviewer_replay.jsonl')
    return parser


def verify_result(result, args):
    assert result.status.value == args.expect_status, result
    assert result.code == args.expect_code, result
    assert result.outputs == dict(args.expect_output), result


def main(argv=None):
    args = build_parser().parse_args(argv)
    surface = BrowserSurface(headless=True).start()
    try:
        engine = ReplayEngine(
            surface,
            log_path=args.log_path,
        )
        capability = engine.load_capability(args.artifact)
        result = engine.run(capability, dict(args.param))
        verify_result(result, args)
        print(json.dumps(result.model_dump(mode='json'), indent=2))
        print("HEADLESS REPLAY PASS")
    finally:
        surface.close()


if __name__ == "__main__":
    main()
