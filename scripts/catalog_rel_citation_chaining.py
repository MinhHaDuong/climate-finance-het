"""Resumable REL citation collection and immutable multi-output delivery."""

import argparse

import requests
from _rel_chaining import (
    ChainError,
    Store,
    export_delivery,
    harvest,
    init_seeds,
    resolve_seed_aliases,
    restore_cached_metadata,
    retry_title_identities,
)
from utils import get_logger

log = get_logger("rel_citation_chaining")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seeds", "harvest", "export", "aliases", "restore-cache", "identities"])
    parser.add_argument("--output-dir", required=True, help="multi-output round checkpoint")
    parser.add_argument("--pool")
    parser.add_argument("--view")
    parser.add_argument("--sentinel", action="append", default=[])
    parser.add_argument("--frontier", help="exact retained frontier with frozen full-round closure and pool/view hashes")
    parser.add_argument("--budget-usd", type=float, default=20)
    parser.add_argument("--delivery")
    parser.add_argument("--budget-ledger", help="shared cumulative ledger across every round and screening route")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    store = Store(args.output_dir, args.budget_ledger)
    try:
        if args.action == "seeds":
            init_seeds(store, args.pool, args.view, args.sentinel, args.budget_usd, frontier_path=args.frontier)
        elif args.action == "harvest":
            harvest(store)
        elif args.action == "export":
            export_delivery(store, args.delivery)
        elif args.action == "aliases":
            resolve_seed_aliases(store)
        elif args.action == "restore-cache":
            restore_cached_metadata(store, args.cache_dir)
        else:
            retry_title_identities(store)
    except (ChainError, requests.RequestException) as exc:
        log.error("checkpoint preserved: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
