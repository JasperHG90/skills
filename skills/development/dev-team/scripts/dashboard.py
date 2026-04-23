# /// script
# requires-python = ">=3.10"
# dependencies = ["jinja2>=3.1"]
# ///
"""Dev-team dashboard CLI.

Every mutating subcommand: appends event → updates state.json → re-renders dashboard.html.
"""
from __future__ import annotations

import argparse
import copy
import fcntl
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1
PHASES = ["Requirements", "Planning", "Development", "Review", "Report"]
DEFAULT_DOD = {
    "code_complete": False,
    "tests_pass": False,
    "peer_review": False,
    "test_specialist": False,
    "qa_go": False,
}
STATUS_MAP = {
    "pending": "backlog",
    "in_progress": "in_progress",
    "completed": "done",
    "in_review": "in_review",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _resolve_dir(args: argparse.Namespace) -> Path:
    """Return the team artifact directory."""
    if getattr(args, "dir", None):
        return Path(args.dir)
    project = Path.cwd()
    af = project / ".dev-team-artifacts"
    sentinel = af / ".active-team"
    if sentinel.exists():
        slug = sentinel.read_text().strip()
        if slug:
            return af / slug
    sys.exit("Cannot resolve team directory. Pass --dir or set .active-team sentinel.")


def _extract_workstream(subject: str) -> str | None:
    m = re.match(r"\[(\w[\w-]*)\]", subject)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def empty_state(team_name: str = "", project_title: str = "") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "team_name": team_name,
        "project_title": project_title,
        "current_phase": 0,
        "last_updated": _now(),
        "agents": {},
        "tasks": {},
        "blockers": {},
        "rework": {},
        "timeline": [],
    }


def load_state(d: Path) -> dict:
    p = d / "state.json"
    if p.exists():
        return json.loads(p.read_text())
    return empty_state()


def save_state(d: Path, state: dict) -> None:
    state["last_updated"] = _now()
    (d / "state.json").write_text(json.dumps(state, indent=2) + "\n")


def append_event(d: Path, event: dict) -> None:
    event.setdefault("ts", _now())
    with open(d / "events.jsonl", "a") as f:
        f.write(json.dumps(event) + "\n")


def apply_event(state: dict, event: dict) -> dict:
    """Pure function: state + event → new state."""
    s = state  # mutate in place for speed; callers pass a copy when needed
    t = event["type"]
    data = event.get("data", {})

    if t == "meta.init":
        s["team_name"] = data.get("team_name", s.get("team_name", ""))
        s["project_title"] = data.get("project_title", s.get("project_title", ""))

    elif t == "phase.transition":
        s["current_phase"] = data["phase"]

    elif t == "agent.spawn":
        s["agents"][data["name"]] = {
            "role": data["role"],
            "status": "active",
            "certainty": None,
            "certainty_context": None,
        }

    elif t == "agent.status":
        if data["name"] in s["agents"]:
            s["agents"][data["name"]]["status"] = data["status"]

    elif t == "agent.certainty":
        if data["name"] in s["agents"]:
            s["agents"][data["name"]]["certainty"] = data["certainty"]
            s["agents"][data["name"]]["certainty_context"] = data.get("context")

    elif t == "task.create":
        s["tasks"][data["id"]] = {
            "subject": data["subject"],
            "workstream": data.get("workstream") or _extract_workstream(data["subject"]),
            "status": data.get("status", "backlog"),
            "owner": data.get("owner"),
            "certainty": None,
            "certainty_context": None,
            "dod": copy.deepcopy(DEFAULT_DOD),
        }

    elif t == "task.update":
        tid = data["id"]
        if tid in s["tasks"]:
            for k in ("status", "owner", "subject"):
                if k in data:
                    s["tasks"][tid][k] = data[k]
            if "subject" in data:
                s["tasks"][tid]["workstream"] = (
                    data.get("workstream") or _extract_workstream(data["subject"])
                )

    elif t == "task.dod":
        tid = data["id"]
        if tid in s["tasks"]:
            s["tasks"][tid]["dod"][data["gate"]] = data["value"]

    elif t == "task.certainty":
        tid = data["id"]
        if tid in s["tasks"]:
            s["tasks"][tid]["certainty"] = data["certainty"]
            s["tasks"][tid]["certainty_context"] = data.get("context")

    elif t == "tasks.synced":
        for task in data.get("tasks", []):
            tid = task["id"]
            status = STATUS_MAP.get(task.get("status", "pending"), task.get("status", "backlog"))
            ws = task.get("workstream") or _extract_workstream(task.get("subject", ""))
            if tid in s["tasks"]:
                s["tasks"][tid]["status"] = status
                s["tasks"][tid]["subject"] = task.get("subject", s["tasks"][tid]["subject"])
                s["tasks"][tid]["owner"] = task.get("owner", s["tasks"][tid]["owner"])
                s["tasks"][tid]["workstream"] = ws or s["tasks"][tid].get("workstream")
            else:
                s["tasks"][tid] = {
                    "subject": task.get("subject", ""),
                    "workstream": ws,
                    "status": status,
                    "owner": task.get("owner"),
                    "certainty": None,
                    "certainty_context": None,
                    "dod": copy.deepcopy(DEFAULT_DOD),
                }

    elif t == "blocker.add":
        s["blockers"][data["id"]] = {
            "task_id": data["task_id"],
            "reason": data["reason"],
            "resolved": False,
        }

    elif t == "blocker.resolve":
        if data["id"] in s["blockers"]:
            s["blockers"][data["id"]]["resolved"] = True

    elif t == "rework.add":
        s["rework"][data["id"]] = {
            "task_id": data["task_id"],
            "issue": data["issue"],
            "cycle": data["cycle"],
            "resolved": False,
        }

    elif t == "rework.resolve":
        if data["id"] in s["rework"]:
            s["rework"][data["id"]]["resolved"] = True

    elif t == "timeline.event":
        s["timeline"].append({"ts": event.get("ts", _now()), "message": data["message"]})

    return s


def rebuild_state(d: Path) -> dict:
    """Replay events.jsonl → state."""
    state = empty_state()
    p = d / "events.jsonl"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line:
                event = json.loads(line)
                apply_event(state, event)
    return state


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _certainty_color(n: int | None) -> str:
    if n is None:
        return ""
    if n < 80:
        return "cert-red"
    if n < 95:
        return "cert-yellow"
    return "cert-green"


def _gate_symbol(value: bool | None) -> tuple[str, str]:
    """Return (symbol, css_class)."""
    if value is True:
        return ("✓", "gate-pass")
    if value is False:
        return ("○", "gate-pending")
    return ("○", "gate-pending")


def _time_format(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%H:%M")
    except Exception:
        return iso_str


def render(d: Path, state: dict) -> None:
    from jinja2 import Environment, FileSystemLoader

    template_dir = Path(__file__).resolve().parent
    env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
    env.filters["certainty_color"] = _certainty_color
    env.globals["gate_symbol"] = _gate_symbol
    env.filters["time_format"] = _time_format

    tmpl = env.get_template("dashboard.html.j2")

    # Prepare grouped tasks by status
    columns = {"backlog": [], "in_progress": [], "in_review": [], "done": []}
    for tid, task in state.get("tasks", {}).items():
        col = task.get("status", "backlog")
        if col not in columns:
            col = "backlog"
        columns[col].append({"id": tid, **task})

    # Active blockers/rework
    active_blockers = {k: v for k, v in state.get("blockers", {}).items() if not v.get("resolved")}
    active_rework = {k: v for k, v in state.get("rework", {}).items() if not v.get("resolved")}

    # Active tasks (in_progress + in_review) for DoD table
    active_tasks = columns["in_progress"] + columns["in_review"]

    html = tmpl.render(
        state=state,
        columns=columns,
        active_tasks=active_tasks,
        active_blockers=active_blockers,
        active_rework=active_rework,
        phases=PHASES,
    )

    lock_path = d / ".lock"
    with open(lock_path, "w") as lock_f:
        fcntl.flock(lock_f, fcntl.LOCK_EX)
        try:
            (d / "dashboard.html").write_text(html)
        finally:
            fcntl.flock(lock_f, fcntl.LOCK_UN)


# ---------------------------------------------------------------------------
# Mutate helper: event → apply → append → save → render
# ---------------------------------------------------------------------------

def _mutate(d: Path, event: dict) -> None:
    state = load_state(d)
    apply_event(state, event)
    append_event(d, event)
    save_state(d, state)
    render(d, state)


# ---------------------------------------------------------------------------
# CLI subcommand handlers
# ---------------------------------------------------------------------------

def cmd_init(args: argparse.Namespace) -> None:
    af = Path.cwd() / ".dev-team-artifacts"
    d = af / args.team
    d.mkdir(parents=True, exist_ok=True)
    (af / ".active-team").write_text(args.team + "\n")

    state = empty_state(args.team, args.title)
    event = {"ts": _now(), "type": "meta.init", "data": {"team_name": args.team, "project_title": args.title}}
    append_event(d, event)
    apply_event(state, event)
    # Add initial timeline event
    init_timeline = {"ts": _now(), "type": "timeline.event", "data": {"message": f"Team '{args.team}' initialized"}}
    append_event(d, init_timeline)
    apply_event(state, init_timeline)
    save_state(d, state)
    render(d, state)
    print(f"Initialized dashboard at {d / 'dashboard.html'}")


def cmd_sync_tasks(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    tasks = json.loads(args.json)
    event = {"ts": _now(), "type": "tasks.synced", "data": {"tasks": tasks}}
    _mutate(d, event)
    print(f"Synced {len(tasks)} tasks")


def cmd_phase(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    phase = args.phase
    if not 0 <= phase <= 4:
        sys.exit("Phase must be 0-4")
    event = {"ts": _now(), "type": "phase.transition", "data": {"phase": phase}}
    _mutate(d, event)
    # Add timeline event
    tl = {"ts": _now(), "type": "timeline.event", "data": {"message": f"Entered Phase {phase}: {PHASES[phase]}"}}
    state = load_state(d)
    apply_event(state, tl)
    append_event(d, tl)
    save_state(d, state)
    render(d, state)
    print(f"Phase set to {phase} ({PHASES[phase]})")


def cmd_agent_spawn(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    event = {"ts": _now(), "type": "agent.spawn", "data": {"name": args.name, "role": args.role}}
    _mutate(d, event)
    print(f"Agent '{args.name}' spawned")


def cmd_agent_status(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    if args.status not in ("active", "idle", "down"):
        sys.exit("Status must be active, idle, or down")
    state = load_state(d)
    if args.name not in state.get("agents", {}):
        sys.exit(f"Agent '{args.name}' not found")
    event = {"ts": _now(), "type": "agent.status", "data": {"name": args.name, "status": args.status}}
    _mutate(d, event)
    print(f"Agent '{args.name}' status → {args.status}")


def cmd_agent_certainty(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    if not 0 <= args.certainty <= 100:
        sys.exit("Certainty must be 0-100")
    state = load_state(d)
    if args.name not in state.get("agents", {}):
        sys.exit(f"Agent '{args.name}' not found")
    data = {"name": args.name, "certainty": args.certainty}
    if args.context:
        data["context"] = args.context
    event = {"ts": _now(), "type": "agent.certainty", "data": data}
    _mutate(d, event)
    print(f"Agent '{args.name}' certainty → {args.certainty}%")


def cmd_task_dod(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    if args.id not in state.get("tasks", {}):
        sys.exit(f"Task '{args.id}' not found")
    valid_gates = list(DEFAULT_DOD.keys())
    if args.gate not in valid_gates:
        sys.exit(f"Gate must be one of: {', '.join(valid_gates)}")
    value = args.value.lower() in ("true", "1", "yes")
    event = {"ts": _now(), "type": "task.dod", "data": {"id": args.id, "gate": args.gate, "value": value}}
    _mutate(d, event)
    print(f"Task '{args.id}' DoD gate '{args.gate}' → {value}")


def cmd_task_certainty(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    if not 0 <= args.certainty <= 100:
        sys.exit("Certainty must be 0-100")
    state = load_state(d)
    if args.id not in state.get("tasks", {}):
        sys.exit(f"Task '{args.id}' not found")
    data = {"id": args.id, "certainty": args.certainty}
    if args.context:
        data["context"] = args.context
    event = {"ts": _now(), "type": "task.certainty", "data": data}
    _mutate(d, event)
    print(f"Task '{args.id}' certainty → {args.certainty}%")


def cmd_blocker_add(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    if args.task not in state.get("tasks", {}):
        sys.exit(f"Task '{args.task}' not found")
    event = {"ts": _now(), "type": "blocker.add", "data": {"id": args.id, "task_id": args.task, "reason": args.reason}}
    _mutate(d, event)
    print(f"Blocker '{args.id}' added")


def cmd_blocker_resolve(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    if args.id not in state.get("blockers", {}):
        sys.exit(f"Blocker '{args.id}' not found")
    event = {"ts": _now(), "type": "blocker.resolve", "data": {"id": args.id}}
    _mutate(d, event)
    print(f"Blocker '{args.id}' resolved")


def cmd_rework_add(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    if args.task not in state.get("tasks", {}):
        sys.exit(f"Task '{args.task}' not found")
    if not 1 <= args.cycle <= 3:
        sys.exit("Cycle must be 1-3")
    event = {"ts": _now(), "type": "rework.add", "data": {"id": args.id, "task_id": args.task, "issue": args.issue, "cycle": args.cycle}}
    _mutate(d, event)
    print(f"Rework '{args.id}' added (cycle {args.cycle})")


def cmd_rework_resolve(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    if args.id not in state.get("rework", {}):
        sys.exit(f"Rework '{args.id}' not found")
    event = {"ts": _now(), "type": "rework.resolve", "data": {"id": args.id}}
    _mutate(d, event)
    print(f"Rework '{args.id}' resolved")


def cmd_event(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    event = {"ts": _now(), "type": "timeline.event", "data": {"message": args.message}}
    _mutate(d, event)
    print("Timeline event added")


def cmd_render(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = load_state(d)
    render(d, state)
    print(f"Dashboard rendered at {d / 'dashboard.html'}")


def cmd_rebuild(args: argparse.Namespace) -> None:
    d = _resolve_dir(args)
    state = rebuild_state(d)
    save_state(d, state)
    render(d, state)
    print(f"State rebuilt from events.jsonl, dashboard rendered at {d / 'dashboard.html'}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(prog="dashboard", description="Dev-team dashboard CLI")
    parser.add_argument("--dir", help="Team artifact directory (overrides .active-team)")
    sub = parser.add_subparsers(dest="command", required=True)

    # init
    p = sub.add_parser("init", help="Initialize a new team dashboard")
    p.add_argument("--team", required=True, help="Team slug")
    p.add_argument("--title", required=True, help="Project title")

    # sync-tasks
    p = sub.add_parser("sync-tasks", help="Batch sync tasks from TaskList")
    p.add_argument("--json", required=True, help="JSON array of tasks")

    # phase
    p = sub.add_parser("phase", help="Transition to a new phase")
    p.add_argument("--phase", type=int, required=True, help="Phase number (0-4)")

    # agent-spawn
    p = sub.add_parser("agent-spawn", help="Register a new agent")
    p.add_argument("--name", required=True)
    p.add_argument("--role", required=True)

    # agent-status
    p = sub.add_parser("agent-status", help="Update agent status")
    p.add_argument("--name", required=True)
    p.add_argument("--status", required=True, help="active|idle|down")

    # agent-certainty
    p = sub.add_parser("agent-certainty", help="Update agent certainty")
    p.add_argument("--name", required=True)
    p.add_argument("--certainty", type=int, required=True, help="0-100")
    p.add_argument("--context", help="Optional context text")

    # task-dod
    p = sub.add_parser("task-dod", help="Flip a DoD gate on a task")
    p.add_argument("--id", required=True)
    p.add_argument("--gate", required=True, help="code_complete|tests_pass|peer_review|test_specialist|qa_go")
    p.add_argument("--value", required=True, help="true|false")

    # task-certainty
    p = sub.add_parser("task-certainty", help="Update task certainty")
    p.add_argument("--id", required=True)
    p.add_argument("--certainty", type=int, required=True, help="0-100")
    p.add_argument("--context", help="Optional context text")

    # blocker-add
    p = sub.add_parser("blocker-add", help="Add a blocker")
    p.add_argument("--id", required=True)
    p.add_argument("--task", required=True, help="Task ID")
    p.add_argument("--reason", required=True)

    # blocker-resolve
    p = sub.add_parser("blocker-resolve", help="Resolve a blocker")
    p.add_argument("--id", required=True)

    # rework-add
    p = sub.add_parser("rework-add", help="Add a rework item")
    p.add_argument("--id", required=True)
    p.add_argument("--task", required=True, help="Task ID")
    p.add_argument("--issue", required=True)
    p.add_argument("--cycle", type=int, required=True, help="1-3")

    # rework-resolve
    p = sub.add_parser("rework-resolve", help="Resolve a rework item")
    p.add_argument("--id", required=True)

    # event
    p = sub.add_parser("event", help="Add a timeline event")
    p.add_argument("--message", required=True)

    # render
    sub.add_parser("render", help="Re-render dashboard from state.json")

    # rebuild
    sub.add_parser("rebuild", help="Replay events.jsonl → state.json → dashboard.html")

    args = parser.parse_args()
    cmd = {
        "init": cmd_init,
        "sync-tasks": cmd_sync_tasks,
        "phase": cmd_phase,
        "agent-spawn": cmd_agent_spawn,
        "agent-status": cmd_agent_status,
        "agent-certainty": cmd_agent_certainty,
        "task-dod": cmd_task_dod,
        "task-certainty": cmd_task_certainty,
        "blocker-add": cmd_blocker_add,
        "blocker-resolve": cmd_blocker_resolve,
        "rework-add": cmd_rework_add,
        "rework-resolve": cmd_rework_resolve,
        "event": cmd_event,
        "render": cmd_render,
        "rebuild": cmd_rebuild,
    }
    cmd[args.command](args)


if __name__ == "__main__":
    main()
