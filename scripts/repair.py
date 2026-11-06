#!/usr/bin/env python3
"""Applying the fixes of an audit in the code of the site: on a branch of its own, one commit per task, tested on this machine.

  python3 repair.py plan   AUDIT REPO                   what Claude can do, what needs the person, what is off the code
  python3 repair.py start  AUDIT REPO                   refuses a folder with work in progress, then creates the branch
  python3 repair.py verify AUDIT --url LOCAL --baseline  reads the local site before any change
  python3 repair.py place  AUDIT REPO CODE              puts a ready file where it belongs, merged with what is there
  python3 repair.py commit AUDIT REPO CODE [--note T]   one commit for one task, after looking for secrets; --open Q keeps a question unanswered
  python3 repair.py skip   AUDIT CODE --why TEXT        a task that could not be done, and why
  python3 repair.py verify AUDIT --url LOCAL            reads the local site again and flags what got worse (exit code 3); --accept C --why T records a false alarm
  python3 repair.py finish AUDIT REPO                   writes what was done and what stays to do, next to the audit

AUDIT is quick.json or audit.json, REPO the folder of the site's code. Nothing here pushes or publishes: it has no such command.
What a person decides stays with them: reading the branch, merging it, putting it online. quick.py check then confirms on the live site."""
import argparse, datetime, json, os, re, subprocess, sys, urllib.parse
import fixes
from common import ASSETS, PLACEABLE, answers_form, date_label, repair_kind, report_lang, task_questions, translator, waiting_tasks
from quick import FAIL_ONLY, GRID, auto_scores, build_tasks, enrich_tasks, read_site, score_rows

# what a local copy can answer: its pages, links and files. Https, headers, compression and speed belong to the host
LOCAL = ("A3", "A4", "B4", "B5", "D1", "D2", "F1", "F2")
SECRET = re.compile(r"ghp_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
                    r"|(?i:password|passwd|secret|api[_-]?key|auth[_-]?token)[\"']?\s*[:=]\s*[\"'][^\"'\s]{8,}")
NEVER = re.compile(r"(^|/)\.env(\.(?!example$)[^/]*)?$|(^|/)node_modules/|(^|/)\.next/")
LOCK = re.compile(r"(^|/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$")


def load(path):
    """(data, tasks by code, language). The same tasks and codes as the report."""
    data = json.load(open(path, encoding="utf-8"))
    S = data["site"]
    lang = report_lang(S)
    if "measures" in data:
        QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]
        rows, _ = score_rows(data, QL)
        tasks, _, errs = build_tasks(data, rows, QL, limit=None)
        if errs:
            sys.exit("inconsistent audit:\n- " + "\n- ".join(errs))
        folder = os.path.dirname(os.path.abspath(path))
        made = fixes.write_fixes(data["measures"]["crawl"], S["url"], S.get("brand", S["domain"]), lang, folder)
        stack = enrich_tasks(tasks, data, made, lang)
        for t in tasks:
            t["criterion"] = t.get("criterion") or (t["key"] if t["key"] in GRID else None)
    else:
        stack = S.get("stack") or {}
        tasks = [{**t, "code": c, "key": c, "lane": c[0]} for c, t in data["tasks"].items()]
    T = translator(lang)
    for t in tasks:
        t["kind"] = repair_kind(t)
        t["questions"] = task_questions(t, lang, T)
    return data, {t["code"]: t for t in tasks}, lang, stack


def save(path, data):
    json.dump(data, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"git {args[0]} failed: {(r.stderr or r.stdout).strip()}")
    return r.stdout.strip()


def require_repo(repo):
    if not os.path.isdir(repo):
        sys.exit(f"{repo} is not a folder")
    if git(repo, "rev-parse", "--is-inside-work-tree", check=False) != "true":
        sys.exit(f"{repo} is not a git repository: without git the changes could be neither read nor undone. Nothing was changed.")


def project(repo):
    """What the folder says about itself: framework, where public files go, how to build and run it."""
    pkg = {}
    if os.path.isfile(os.path.join(repo, "package.json")):
        pkg = json.load(open(os.path.join(repo, "package.json"), encoding="utf-8"))
    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
    framework = next((n for n, d in (("next", "next"), ("nuxt", "nuxt"), ("astro", "astro"), ("gatsby", "gatsby"), ("sveltekit", "@sveltejs/kit"), ("vite", "vite")) if d in deps), None)
    if not framework and any(os.path.isfile(os.path.join(repo, f)) for f in ("hugo.toml", "hugo.yaml", "config.toml")):
        framework = "hugo"
    exists = lambda d: os.path.isdir(os.path.join(repo, d))
    if framework in ("gatsby", "hugo", "sveltekit"):
        publish = "static" if exists("static") else None
    elif framework:
        publish = "public" if exists("public") else None
    elif os.path.isfile(os.path.join(repo, "index.html")):
        publish = "."
    else:
        publish = None
    mgr = next((m for f, m in (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("package-lock.json", "npm")) if os.path.isfile(os.path.join(repo, f))), "npm")
    scripts = pkg.get("scripts", {})
    run = next((f"{mgr} run {s}" for s in ("start", "preview") if s in scripts), None) if pkg else "python3 -m http.server 8000"
    return {"framework": framework, "publish": publish, "build": f"{mgr} run build" if "build" in scripts else None, "run": run}


def current_repair(data, repo=None):
    R = data.get("repair")
    if not R or not R.get("branch"):
        sys.exit("run repair.py start first")
    if repo:
        require_repo(repo)
        here = git(repo, "branch", "--show-current")
        if here != R["branch"]:
            sys.exit(f"this folder is on {here or 'no branch'}, not on {R['branch']}: nothing was changed")
    return R


def cmd_plan(a):
    data, tasks, lang, stack = load(a.audit)
    require_repo(a.repo)
    P = project(a.repo)
    state = (data.get("repair") or {}).get("tasks", {})
    if stack.get("framework") and P["framework"] and stack["framework"] != P["framework"]:
        print(f"WARNING: the audit saw {stack['framework']} online, this folder is {P['framework']}. Check it is the code of this site.")
    print(f"framework: {P['framework'] or 'none detected'} · public files: {P['publish'] or 'unknown'} · build: {P['build'] or 'none'} · run: {P['run'] or 'unknown'}")
    dirty = git(a.repo, "status", "--porcelain")
    if dirty:
        print(f"WARNING: {len(dirty.splitlines())} uncommitted changes in this folder. start will refuse until they are committed or put aside.")
    for kind, head in (("file", "ready file, Claude places it"), ("code", "Claude changes the code"), ("facts", "needs the person's own facts first"), ("outside", "off the code: host, other sites, admin")):
        # llms.txt repeats the titles of the pages: it goes after the tasks that change them
        rows = sorted((t for t in tasks.values() if t["kind"] == kind), key=lambda t: os.path.basename(t.get("file") or "") == "llms.txt")
        if rows:
            print(f"\n{head}:")
            for t in rows:
                entry = state.get(t["code"]) or {}
                if entry.get("status") == "applied":
                    print(f"  {t['code']:<4} already on the branch: {', '.join(entry['commits'])}")
                    for q in entry.get("open", []):
                        print(f"       ? {q}")
                    continue
                print(f"  {t['code']:<4} P{t.get('prio', 2)} {t['name']}\n       {t.get('what', '')}\n       {t.get('check', '')}")
                for k in ("where", "how", "snippet"):
                    if t.get(k):
                        print(f"       {k}: {t[k]}")
                for q in t["questions"]:
                    print(f"       ? {q}")


def cmd_start(a):
    data, _, _, _ = load(a.audit)
    require_repo(a.repo)
    if git(a.repo, "status", "--porcelain"):
        sys.exit("this folder has uncommitted work. Commit it or put it aside first: fixes must not mix with it. Nothing was changed.")
    base = git(a.repo, "branch", "--show-current")
    if not base:
        sys.exit("this folder is not on a branch. Nothing was changed.")
    today = datetime.date.today().isoformat()
    branch = a.branch or f"audit-fixes/{data['site']['date']}"
    if git(a.repo, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}", check=False):
        sys.exit(f"the branch {branch} already exists. Continue on it, or name another with --branch. Nothing was changed.")
    git(a.repo, "switch", "-c", branch)
    # a second round keeps the record of the first
    data["repair"] = {"date": today, "branch": branch, "base": base, "base_commit": git(a.repo, "rev-parse", "--short", "HEAD"), "tasks": (data.get("repair") or {}).get("tasks", {})}
    save(a.audit, data)
    print(f"on {branch}, from {base}. Nothing is pushed or published by this script.")


def merge_headers(old, new):
    """Adds to the /* block of a _headers file only the headers it does not have. Someone's own lines stay as they are."""
    wanted = [l for l in new.splitlines() if l.startswith("  ")]
    lines = old.rstrip("\n").split("\n")
    if "/*" not in [l.strip() for l in lines]:
        return old.rstrip("\n") + "\n\n/*\n" + "\n".join(wanted) + "\n"
    at = [l.strip() for l in lines].index("/*") + 1
    end = at
    while end < len(lines) and lines[end].startswith((" ", "\t")):
        end += 1
    names = {l.split(":")[0].strip().lower() for l in lines[at:end]}
    # a report-only policy is not added next to a real one
    if "content-security-policy" in names:
        names.add("content-security-policy-report-only")
    add = [l for l in wanted if l.split(":")[0].strip().lower() not in names]
    return "\n".join(lines[:end] + add + lines[end:]) + "\n"


def merge_vercel(old, new):
    body, add = json.loads(old), json.loads(new)["headers"][0]
    rules = body.setdefault("headers", [])
    if not rules or not any(r.get("source") == add["source"] for r in rules):
        rules.append(add)
    else:
        rule = next(r for r in rules if r.get("source") == add["source"])
        have = {h["key"].lower() for h in rule["headers"]}
        rule["headers"] += [h for h in add["headers"] if h["key"].lower() not in have]
    return json.dumps(body, indent=2) + "\n"


def cmd_place(a):
    data, tasks, lang, _ = load(a.audit)
    current_repair(data, a.repo)
    t = tasks.get(a.code)
    if not t:
        sys.exit(f"unknown task: {a.code}. Known: {', '.join(tasks)}")
    name = os.path.basename(t.get("file") or "")
    if name not in PLACEABLE:
        sys.exit(f"{a.code} has no file that can be placed in the code: {name or 'no file'}")
    content = t.get("file_content")
    if content is None:
        with open(os.path.join(os.path.dirname(os.path.abspath(a.audit)), t["file"]), encoding="utf-8") as f:
            content = f.read()
    marks = [v for L in ("en", "fr") for k, v in fixes.load_recipes(L)["_files"].items() if k.startswith("todo_")]
    left = [m for m in marks if m in content]
    if left:
        sys.exit(f"{name} still has something to complete: {left[0]}. Ask the person, change the file, and try again.")
    P = project(a.repo)
    folder = "." if name == "vercel.json" else P["publish"]
    if not folder:
        sys.exit(f"cannot tell where public files go in this project: place {name} by hand, then commit")
    target = os.path.join(a.repo, folder, name)
    if os.path.exists(target):
        old = open(target, encoding="utf-8").read()
        if name == "llms.txt":
            sys.exit(f"{os.path.join(folder, name)} already exists: read it and change it by hand. Nothing was changed.")
        content = merge_headers(old, content) if name == "_headers" else merge_vercel(old, content)
        if content == old:
            sys.exit(f"{os.path.join(folder, name)} already has all of this. Nothing was changed.")
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"written: {os.path.normpath(os.path.join(folder, name))}. Read it, then: repair.py commit {a.audit} {a.repo} {a.code}")


def cmd_commit(a):
    data, tasks, _, _ = load(a.audit)
    R = current_repair(data, a.repo)
    t = tasks.get(a.code)
    if not t:
        sys.exit(f"unknown task: {a.code}. Known: {', '.join(tasks)}")
    if t["kind"] == "outside":
        sys.exit(f"{a.code} is settled off the code ({t['name']}): nothing to commit for it")
    if t["kind"] == "facts" and not a.facts_given:
        sys.exit(f"{a.code} needs facts only the person has ({t['name']}). Ask them, then use --facts-given. Nothing was committed.")
    git(a.repo, "add", "-A")
    names = git(a.repo, "diff", "--cached", "--name-only").splitlines()

    def refuse(why):
        git(a.repo, "reset", "-q")
        sys.exit(why + " Nothing was committed; the changes are still in the folder.")
    if not names:
        refuse(f"no change to commit for {a.code}.")
    bad = [n for n in names if NEVER.search(n)]
    if bad:
        refuse(f"these must not go in a commit: {', '.join(bad)}.")
    added = "\n".join(l[1:] for n in names if not LOCK.search(n) for l in git(a.repo, "diff", "--cached", "--", n).splitlines() if l.startswith("+") and not l.startswith("+++"))
    hit = SECRET.search(added)
    if hit:
        refuse(f"this looks like a secret, in the changes: {hit.group(0)[:12]}…")
    git(a.repo, "commit", "-q", "-m", f"audit-seo-geo {a.code}: {t['name']}", *(["-m", a.note] if a.note else []))
    sha = git(a.repo, "rev-parse", "--short", "HEAD")
    entry = R["tasks"].get(a.code) or {"status": "applied", "commits": [], "files": []}
    entry["status"] = "applied"
    entry["commits"].append(sha)
    entry["files"] = sorted(set(entry["files"]) | set(names))
    if a.note:
        entry["note"] = a.note
    entry["open"] = a.open or []
    R["tasks"][a.code] = entry
    save(a.audit, data)
    print(f"{sha} {a.code}: {len(names)} file(s): {', '.join(names)}")
    if any(LOCK.search(n) for n in names):
        print("NOTE: a lockfile changed: say which dependency was added and why.")


def cmd_skip(a):
    data, tasks, _, _ = load(a.audit)
    R = current_repair(data)
    if a.code not in tasks:
        sys.exit(f"unknown task: {a.code}. Known: {', '.join(tasks)}")
    R["tasks"][a.code] = {"status": "blocked", "note": a.why}
    save(a.audit, data)


def local_scores(url, prod, delay, max_pages, E):
    crawl = read_site(url, delay, max_pages, map_host=prod)
    if not crawl["pages_ok"]:
        sys.exit(f"no page could be read at {url}. Is the site running?")
    gone = {"status": "unavailable", "reason": "local"}
    now = auto_scores({"crawl": crawl, "psi": gone, "observatory": gone, "wikidata": gone}, None, E)
    return crawl, {c: {"score": now[c][0] if c in now else "2", "evidence": now[c][1] if c in now else ""} for c in LOCAL if c in now or c in FAIL_ONLY}


def cmd_verify(a):
    data, tasks, lang, _ = load(a.audit)
    R = current_repair(data)
    if a.accept and not a.why:
        sys.exit("--accept needs --why: say how you checked that this is a false alarm")
    u = urllib.parse.urlparse(a.url)
    if u.hostname not in ("localhost", "127.0.0.1", "::1") and not (u.hostname or "").endswith(".localhost"):
        sys.exit(f"{a.url} is not on this machine. For the live site, use quick.py check.")
    S = data["site"]
    live = urllib.parse.urlparse(S["url"])
    start = f"{u.scheme}://{u.netloc}{live.path}"
    QL = json.load(open(os.path.join(ASSETS, "quick.json"), encoding="utf-8"))[lang]
    # here nothing limits the reading: every page of the sitemap, so that none hides what a fix broke
    crawl, now = local_scores(start, live.netloc, a.delay, a.max or 300, QL["ev"])
    print(f"{crawl['pages_ok']} pages read, {crawl['errors']} errors, {crawl['no_canonical']} without canonical, {crawl['no_hreflang']} without hreflang, {crawl['repeated_titles']} titles with a repeated name")
    if a.baseline:
        R["local_before"] = {"date": datetime.date.today().isoformat(), "scores": {c: v["score"] for c, v in now.items()}}
        save(a.audit, data)
        # a machine against a machine: a score judged by hand in the audit would look like a difference. A full audit has only those
        audit = {c: v[0] for c, v in auto_scores(data["measures"], None, QL["ev"]).items()} if "measures" in data else {}
        differ = [f"{c} {audit[c]} online, {v['score']} here" for c, v in now.items() if audit.get(c) not in (None, "NV", v["score"])]
        print("baseline stored: " + ", ".join(f"{c} {v['score']}" for c, v in now.items()))
        if differ:
            print("WARNING: this code and the live site differ: " + "; ".join(differ) + ". The live site may run another version, or its host may behave differently: only a recheck online settles those.")
        return
    before = (R.get("local_before") or {}).get("scores")
    if not before:
        sys.exit("no baseline: run verify --baseline before changing anything, on the code as it was")
    results, worse = {}, []
    for c, v in now.items():
        old = before.get(c)
        results[c] = {"old": old, "new": v["score"], "evidence": v["evidence"]}
        accepted = c in (a.accept or [])
        if old is not None and int(v["score"]) < int(old) and not accepted:
            worse.append(c)
        mark = "WORSE" if c in worse else "accepted" if accepted else "better" if old is not None and int(v["score"]) > int(old) else "same"
        print(f"{c:<3} {old} -> {v['score']} {mark:<6} {v['evidence'] or 'no problem found'}")
        if c in worse and c == "A4":
            print("    pages:", ", ".join(crawl.get("js_urls", [])))
    R["local"] = {"date": datetime.date.today().isoformat(), "results": results, "worse": worse, "accepted": {c: a.why for c in a.accept or []}}
    save(a.audit, data)
    only_online = [t["code"] for c, t in tasks.items() if R["tasks"].get(c, {}).get("status") == "applied" and t.get("criterion") not in LOCAL]
    if only_online:
        print("in the code, but only the live site can confirm:", ", ".join(only_online))
    if worse:
        print("WORSE than before the fixes:", ", ".join(worse))
        sys.exit(3)


def cmd_finish(a):
    data, tasks, lang, _ = load(a.audit)
    R = current_repair(data, a.repo)
    T = translator(lang)
    head = [f"# {T('repair_md_title', domain=data['site']['domain'])}", "", T("repair_md_where", branch=R["branch"], base=R["base"], date=date_label(R["date"], lang)), ""]
    done = [(c, e) for c, e in R["tasks"].items() if e["status"] == "applied"]
    if done:
        head += [f"## {T('repair_md_done')}", ""]
        for c, e in done:
            head.append(f"- **{c}** {tasks[c]['name']} · `{', '.join(e['commits'])}` · {', '.join('`' + f + '`' for f in e['files'])}" + (f"\n  {e['note']}" if e.get("note") else ""))
        head.append("")
    L = R.get("local")
    if L:
        head += [f"## {T('repair_md_local')}", ""]
        head += [f"- {c}: {v['old']} → {v['new']}" + (f" · {T('repair_md_worse')}" if c in L["worse"] else "") + (f" · {T('repair_md_accepted')}{L['accepted'][c]}" if c in L.get("accepted", {}) else "") for c, v in L["results"].items() if v["old"] != v["new"]] or [T("repair_md_nochange")]
        head += ["", T("repair_md_local_note"), ""]
    open_kinds = (("blocked", "repair_md_blocked"), ("facts", "repair_md_facts"), ("outside", "repair_md_outside"), ("code", "repair_md_left"), ("file", "repair_md_left"))
    seen = set()
    for kind, key in open_kinds:
        rows = []
        for c, t in tasks.items():
            e = R["tasks"].get(c)
            if (e and e["status"] == "applied") or c in seen:
                continue
            if kind == "blocked" and e:
                rows.append(f"- **{c}** {t['name']}: {e.get('note', '')}")
            elif kind != "blocked" and not e and t["kind"] == kind:
                rows.append(f"- **{c}** {t['name']}")
                rows += [f"  - {q}" for q in t["questions"]]
            else:
                continue
            seen.add(c)
        if rows:
            head += [f"## {T(key)}", "", *rows, ""]
    waiting = waiting_tasks(tasks.values(), R["tasks"])
    if waiting:
        head += [f"## {T('repair_answers_title', n=len(waiting))}", "", T("repair_answers_note"), "", "```text", answers_form(waiting, T, os.path.dirname(os.path.abspath(a.audit)), os.path.abspath(a.repo)).rstrip(), "```", ""]
    head += [f"## {T('repair_md_next')}", "", T("repair_md_read"), "", "```bash", f'git -C "{a.repo}" diff {R["base"]}...{R["branch"]}', "```", "",
             T("repair_md_online"), "", "```bash", f'git -C "{a.repo}" switch {R["base"]}', f'git -C "{a.repo}" merge {R["branch"]}', f'git -C "{a.repo}" push', "```", "", T("repair_md_recheck"), "", T("repair_md_undo"), "", "```bash", f'git -C "{a.repo}" switch {R["base"]}', f'git -C "{a.repo}" branch -D {R["branch"]}', "```", ""]
    out = a.out or os.path.join(os.path.dirname(os.path.abspath(a.audit)), T("repair_md_file"))
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(head))
    print(out)
    print(git(a.repo, "diff", "--stat", f"{R['base']}...{R['branch']}") or "no change on the branch")


def main():
    ap = argparse.ArgumentParser(description="Apply an audit's fixes in the site's code, on a branch, with nothing sent anywhere")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan"); p.add_argument("audit"); p.add_argument("repo"); p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("start"); p.add_argument("audit"); p.add_argument("repo"); p.add_argument("--branch"); p.set_defaults(fn=cmd_start)
    p = sub.add_parser("place"); p.add_argument("audit"); p.add_argument("repo"); p.add_argument("code"); p.set_defaults(fn=cmd_place)
    p = sub.add_parser("commit"); p.add_argument("audit"); p.add_argument("repo"); p.add_argument("code"); p.add_argument("--note"); p.add_argument("--facts-given", action="store_true"); p.add_argument("--open", action="append", help="a question still unanswered: it stays in the form"); p.set_defaults(fn=cmd_commit)
    p = sub.add_parser("skip"); p.add_argument("audit"); p.add_argument("code"); p.add_argument("--why", required=True); p.set_defaults(fn=cmd_skip)
    p = sub.add_parser("verify"); p.add_argument("audit"); p.add_argument("--url", required=True); p.add_argument("--baseline", action="store_true"); p.add_argument("--accept", action="append", help="a criterion you checked by hand: a false alarm"); p.add_argument("--why"); p.add_argument("--delay", type=float, default=0.2); p.add_argument("--max", type=int); p.set_defaults(fn=cmd_verify)
    p = sub.add_parser("finish"); p.add_argument("audit"); p.add_argument("repo"); p.add_argument("--out"); p.set_defaults(fn=cmd_finish)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
