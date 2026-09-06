"""Operator commands. No install or provider connection is performed implicitly."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from . import __version__
from .config import load_settings


def output(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sherlock", description="Local Agent Sherlock MCP service and operator tools.")
    p.add_argument("--version", action="version", version=__version__)
    p.add_argument("--data-dir", help="Private data directory; defaults to OS application data.")
    p.add_argument("--profile", help="Organization profile; default, or demo for the demo command.")
    p.add_argument("--config", help="Operator-owned JSON connector and save-policy configuration.")
    sub = p.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup", help="Install Sherlock's runtime and skills, configure your agent, and check local recall.")
    setup.add_argument("--host", choices=("claude-code", "codex", "manual"))
    setup.add_argument("--scope", choices=("user", "project"), default="user")
    setup.add_argument("--project", type=Path, help="Existing project folder for project-scoped setup.")
    setup.add_argument("--install-dir", type=Path, help="Private folder for managed software and settings backups.")
    setup.add_argument("--host-config", type=Path, help="Explicit agent configuration path for a custom host installation.")
    setup.add_argument("--skills-dir", type=Path, help="Explicit agent skill folder for a custom host installation.")
    setup.add_argument("--dry-run", action="store_true", help="Preview paths and conflicts without writing setup files.")
    setup.add_argument("--yes", action="store_true", help="Install the selected setup without another terminal prompt.")
    setup.add_argument("--json", action="store_true", help="Print a machine-readable preview or result.")
    for command in ("doctor", "serve", "export", "changes"):
        sub.add_parser(command)
    sub.add_parser("demo").add_argument("--full", action="store_true", help="Include complete fictional evidence and findings in the JSON output.")
    sub.add_parser("backup").add_argument("destination")
    restore = sub.add_parser("restore")
    restore.add_argument("source")
    restore.add_argument("--confirm", required=True, help="Exact destination profile name.")
    sub.add_parser("review").add_argument("proposal_id")
    sub.add_parser("connector-inspect").add_argument("connection_id")
    template = sub.add_parser("connector-template", help="Prepare an experimental Composio HubSpot mapping from locally reviewed discovery.")
    template.add_argument("connection_id")
    template.add_argument("--inspection", required=True, help="Saved connector-inspect JSON output; treated as untrusted schema data.")
    template.add_argument("--properties", required=True, help="Comma-separated explicit company fields to read and permit in proposals.")
    template.add_argument("--account-id-path", required=True, help="Verified dotted account ID path from the provider response.")
    template.add_argument("--output", required=True, help="New private JSON config path; never overwrite an existing config.")
    rel = sub.add_parser("relationship-import", help="Atomically import a portable JSON batch into this profile; no provider calls.")
    rel.add_argument("source", help="Private JSON file with schema_version=1 and a relationships array (maximum 100).")
    for name in ("relationship-list", "relationship-evaluate", "relationship-queue"):
        rel = sub.add_parser(name)
        rel.add_argument("--limit", type=int, default=100)
        rel.add_argument("--after-id")
        if name == "relationship-queue":
            rel.add_argument("--state", default="ready", help="Review state or all.")
    rel = sub.add_parser("relationship-get")
    rel.add_argument("relationship_id")
    rel.add_argument("--history", action="store_true")
    rel = sub.add_parser("relationship-feedback")
    rel.add_argument("review_id")
    rel.add_argument("action")
    rel.add_argument("--expected-revision", type=int, required=True)
    rel.add_argument("--note", default="")
    rel.add_argument("--until")
    rel.add_argument("--clear-hold", action="append", dest="clear_holds", help="Explicit person hold to clear with reopen; repeat to name multiple holds.")
    delete = sub.add_parser("delete-case")
    delete.add_argument("case_id")
    delete.add_argument("--confirm", required=True, help="Repeat exact case ID; backups are not deleted.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "setup":
            from .setup import run_setup
            return run_setup(args)
        if args.command == "demo" and args.config:
            raise ValueError("Demo does not load a provider configuration.")
        settings = load_settings(args.data_dir,
                                 args.profile or ("demo" if args.command == "demo" else None),
                                 args.config, ignore_config=args.command == "demo")
        if args.command == "serve":
            from .operations import service_lock
            from .server import build_server
            with service_lock(settings):
                build_server(settings).run(transport="stdio")
            return 0
        if args.command == "connector-inspect":
            from .connectors import ConnectorGateway
            output(asyncio.run(ConnectorGateway(settings.config).inspect_tools(args.connection_id)))
            return 0
        if args.command == "connector-template":
            from .connectors import composio_hubspot_connection_config
            inspected = json.loads(Path(args.inspection).expanduser().read_text(encoding="utf-8"))
            connection = settings.config.get("connections", {}).get(args.connection_id)
            if not connection or inspected.get("connection_id") != args.connection_id:
                raise ValueError("Select the same configured connection used for this inspection.")
            draft = composio_hubspot_connection_config(
                inspected, connection_id=args.connection_id, account_id=connection["account_id"],
                transport=connection["transport"], properties=[p.strip() for p in args.properties.split(",") if p.strip()],
                account_id_path=args.account_id_path,
            )
            draft["profile"] = settings.profile
            destination = Path(args.output).expanduser()
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(draft, stream, indent=2)
            output({"draft_config": str(destination), "review_required": True,
                    "provider_calls": 0, "autosave_enabled": False,
                    "note": "Review native tools, account binding, properties, and exact mappings before using this config."})
            return 0
        if args.command == "backup":
            from .operations import backup
            output(backup(settings, args.destination))
            return 0
        if args.command == "restore":
            from .operations import restore
            output(restore(settings, args.source, args.confirm))
            return 0
        if args.command in ("review", "changes"):
            from .connectors import ConnectorGateway
            from .changes import ChangeManager
            manager = ChangeManager(settings.changes_database, ConnectorGateway(settings.config),
                                    policy=settings.config.get("policy"))
            if args.command == "changes":
                output(manager.list_pending())
                return 0
            proposal = manager.get(args.proposal_id)
            output(proposal)
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                raise ValueError("Review requires an interactive operator terminal. MCP agents cannot authorize proposals.")
            answer = input("Review the exact account, record, fields, and evidence above. Type approve or reject: ").strip()
            if answer == "approve":
                output(manager.authorize(args.proposal_id, proposal["payload_hash"]))
            elif answer == "reject":
                output(manager.reject(args.proposal_id))
            else:
                output({"state": "unchanged", "reason": "No approval or rejection recorded."})
            return 0
        from .storage import Store
        if args.command.startswith("relationship-"):
            from .operations import service_lock
            from .relationships import Relationships
            # Host calls should use the running MCP service. Standalone CLI
            # operations acquire the same profile lock before opening storage.
            with service_lock(settings), Store(settings.database, profile=settings.profile) as store:
                relationships = Relationships(store, settings.config.get("relationship_policy"))
                if args.command == "relationship-import":
                    source = Path(args.source).expanduser()
                    if source.stat().st_size > 2_000_000:
                        raise ValueError("Relationship import exceeds the 2 MB batch limit.")
                    payload = json.loads(source.read_text(encoding="utf-8"))
                    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
                        raise ValueError("Use portable relationship schema_version 1.")
                    result = relationships.import_records(payload.get("relationships"))
                elif args.command == "relationship-list":
                    result = relationships.list(limit=args.limit, after_id=args.after_id)
                elif args.command == "relationship-get":
                    result = relationships.get(args.relationship_id, include_history=args.history)
                elif args.command == "relationship-evaluate":
                    result = relationships.evaluate_all(limit=args.limit, after_id=args.after_id)
                elif args.command == "relationship-queue":
                    result = relationships.queue(state=None if args.state == "all" else args.state, limit=args.limit, after_id=args.after_id)
                else:
                    result = relationships.feedback(args.review_id, args.action, expected_revision=args.expected_revision, note=args.note, until=args.until, clear_holds=args.clear_holds)
                output(result)
            return 0
        with Store(settings.database, profile=settings.profile) as store:
            if args.command == "doctor":
                output({"version": __version__, "profile": settings.profile,
                        "local_storage": "ready", "database": str(settings.database),
                        "reasoning": "existing_host_agent", "transport": "stdio",
                        "connections": {name: "configured_not_verified" for name in settings.config.get("connections", {})},
                        "provider_calls": 0})
            elif args.command == "demo":
                from .demo import run_demo
                from .connectors import ConnectorGateway, fixture_connection_config
                result = run_demo(store)
                config = fixture_connection_config(settings.profile_dir / "fixture-crm.sqlite3")
                config["profile"] = settings.profile
                config_file = settings.profile_dir / "demo-config.json"
                config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
                config_file.chmod(0o600)
                gateway = ConnectorGateway(config)
                record = asyncio.run(gateway.read_record("fictional-demo", "company-001"))
                result["fictional_crm_record"] = record
                result["demo_config"] = str(config_file)
                result["demo_connection_id"] = "fictional-demo"
                if args.full:
                    output(result)
                else:
                    output({
                        "fictional": True, "network_calls": 0, "profile": settings.profile,
                        "cases": [{"id": c["id"], "subject": c["subject"], "type": c["case_type"]} for c in result["cases"]],
                        "medical_clients": result["medical_clients"],
                        "findings_recorded": sum(len(c["findings"]) for c in result["cases"]),
                        "fictional_crm_record": record, "demo_config": str(config_file),
                        "demo_connection_id": "fictional-demo",
                        "next": "Connect your agent to Sherlock using the demo profile/config, then ask about recorded medical clients. No real provider is connected.",
                    })
            elif args.command == "export":
                output(store.export_profile())
            elif args.command == "delete-case":
                if args.confirm != args.case_id:
                    raise ValueError("Confirmation does not match the case ID.")
                output({"deleted": store.delete_case(args.case_id), "backups_affected": False})
        return 0
    except (ValueError, OSError) as exc:
        print("Sherlock: " + str(exc), file=sys.stderr)
        return 2
    except Exception:
        # Providers may include credentials in exception text; never echo raw failures.
        print("Sherlock: operation failed. Inspect the saved status before retrying any CRM change.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
