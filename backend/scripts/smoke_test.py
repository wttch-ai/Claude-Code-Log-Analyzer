"""API 冒烟测试。用法：cd backend && .venv/Scripts/python -m scripts.smoke_test"""

import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8000"


def get(path: str):
    with urllib.request.urlopen(BASE + path, timeout=120) as r:
        return json.load(r)


def main() -> int:
    o = get("/api/overview")
    print("[overview] totals.tokens =", o["totals"]["tokens"])
    print("[overview] models =", [(m["model"], m["tokens"]["total"]) for m in o["models"]])
    print("[overview] cache_read_ratio =", o["cache_read_ratio"])
    print("[overview] compactions =", o["compactions"])

    a = get("/api/aggregate?dim=skill&granularity=day")
    print(f"[agg skill] series={len(a['series'])} dates={a['dates'][:3]} total={a['total_tokens']}")
    print("[agg skill] top =", [s["name"] for s in a["series"][:6]])

    a2 = get("/api/aggregate?dim=project&granularity=day")
    print(f"[agg project] series={len(a2['series'])} total={a2['total_tokens']}")

    pr = get("/api/projects?sort=tokens&order=desc&limit=5")
    print("[projects] total =", pr["total"])
    for it in pr["items"]:
        print("   ", it["id"], it["name"], "tokens=", it["tokens"]["total"], "price=", it["price"])

    if not pr["items"]:
        print("WARN: no projects")
        return 1
    pid = pr["items"][0]["id"]
    ss = get(f"/api/projects/{pid}/sessions")
    print(f"[sessions] project {pid} count={len(ss)}")
    if not ss:
        print("WARN: no sessions")
        return 1

    sid = ss[0]["session_id"]
    tl = get(f"/api/sessions/{sid}/timeline")
    print(f"[timeline] {sid} nodes={len(tl['nodes'])} summary.tokens={tl['summary']['tokens']}")
    sub_found = 0
    detail_checked = False
    for n in tl["nodes"]:
        if n.get("tool_uses"):
            for tu in n["tool_uses"]:
                if "subagent" in tu:
                    sub_found += 1
                    print(
                        f"   subagent: type={tu['subagent']['agent_type']} "
                        f"tokens={tu['subagent']['tokens']['total']} nodes={len(tu['subagent']['nodes'])}"
                    )
        if not detail_checked and n["type"] == "assistant" and n.get("row_uuid"):
            md = get(f"/api/messages/{n['row_uuid']}")
            print(
                f"[detail] model={md.get('model')} tokens={md.get('tokens')} "
                f"tool_calls={len(md.get('tool_calls') or [])} subagents={md.get('subagents')}"
            )
            detail_checked = True
    print(f"[timeline] subagent attached count = {sub_found}")

    p = get("/api/prices")
    print("[prices] count =", len(p), "first =", p[0] if p else None)
    m = get("/api/models")
    print("[models] =", m)

    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
