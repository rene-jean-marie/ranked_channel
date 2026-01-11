from __future__ import annotations

import argparse
import json
import asyncio

from ranked_channel.engine.session_runner import SessionEngine
from ranked_channel.store.sqlite import Store


def main():
    p = argparse.ArgumentParser(prog="ranked-channel")
    sub = p.add_subparsers(dest="cmd", required=True)

    run = sub.add_parser("run", help="Build a ranked session playlist")
    run.add_argument("--seed-url", required=True)
    run.add_argument("--n", type=int, default=30)
    run.add_argument("--profile", default="discovery")
    run.add_argument("--out", default="session.json")

    args = p.parse_args()

    if args.cmd == "run":
        store = Store()
        engine = SessionEngine(store=store)
        session = asyncio.run(engine.build_session(args.seed_url, args.n, args.profile))
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(session, f, indent=2)
        print(f"Wrote {args.out} (session_id={session['session_id']})")


if __name__ == "__main__":
    main()
