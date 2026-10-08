"""Resumable REL citation collection and immutable multi-output delivery."""

import argparse

import requests
from _rel_chaining import (
    ChainError,
    Store,
    export_delivery,
    harvest,
    init_seeds,
    migrate_labels,
    resolve_seed_aliases,
    restore_cached_metadata,
    retry_title_identities,
)
from utils import get_logger

log = get_logger("rel_citation_chaining")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["seeds", "harvest", "export", "rekey", "aliases", "restore-cache", "identities"])
    parser.add_argument("--output-dir", required=True, help="multi-output round checkpoint")
    parser.add_argument("--pool")
    parser.add_argument("--view")
    parser.add_argument("--sentinel", action="append", default=[])
    parser.add_argument("--budget-usd", type=float, default=20)
    parser.add_argument("--delivery")
    parser.add_argument("--budget-ledger", help="shared cumulative ledger across every round and screening route")
    parser.add_argument("--old-pool")
    parser.add_argument("--table")
    parser.add_argument("--dimensions-table")
    parser.add_argument("--cache-dir")
    args = parser.parse_args()
    store = Store(args.output_dir, args.budget_ledger)
    try:
        if args.action == "seeds":
            init_seeds(store, args.pool, args.view, args.sentinel, args.budget_usd)
        elif args.action == "harvest":
            harvest(store)
        elif args.action == "export":
            export_delivery(store, args.delivery)
        elif args.action == "aliases":
            resolve_seed_aliases(store)
        elif args.action == "restore-cache":
            restore_cached_metadata(store, args.cache_dir)
        elif args.action == "identities":
            retry_title_identities(store)
        else:
            migrate_labels(store, args.old_pool, args.pool, args.table, args.dimensions_table)
    except (ChainError, requests.RequestException) as exc:
        log.error("checkpoint preserved: %s", exc)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
