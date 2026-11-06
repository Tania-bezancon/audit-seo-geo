#!/usr/bin/env python3
"""Applying fixes for real on a copy of the test site: what must work, and above all what must be refused.

  python3 tests/repair_test.py OUT_DIR"""
import json, os, shutil, socket, subprocess, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
sys.path.insert(0, SCRIPTS)
import repair as R
from common import HOSTED, repair_block, repair_kind, translator

out = os.path.abspath(sys.argv[1])
repo, audit_dir = os.path.join(out, "repair-site"), os.path.join(out, "repair-audit")
audit = os.path.join(audit_dir, "quick.json")
err = []


def run(*args, script="repair.py"):
    return subprocess.run([sys.executable, os.path.join(SCRIPTS, script), *args], capture_output=True, text=True, cwd=ROOT)


def git(*args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, check=True).stdout.strip()


def expect(label, r, code=0, says=""):
    if r.returncode != code or says not in r.stdout + r.stderr:
        err.append(f"{label}: exit {r.returncode}, {(r.stdout + r.stderr).strip()[:200]}")


def refused(label, *args, says=""):
    """Refused, and nothing moved."""
    head = git("rev-parse", "HEAD")
    r = run(*args)
    if r.returncode == 0 or says not in r.stdout + r.stderr:
        err.append(f"{label} must be refused: exit {r.returncode}, {(r.stdout + r.stderr).strip()[:200]}")
    if git("rev-parse", "HEAD") != head:
        err.append(f"{label}: a commit was made")


shutil.rmtree(repo, ignore_errors=True)
shutil.rmtree(audit_dir, ignore_errors=True)
shutil.copytree(os.path.join(ROOT, "tests", "fixture-site"), repo)
with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
server = subprocess.Popen([sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", repo], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1)
url = f"http://127.0.0.1:{port}"
try:
    expect("measure", run("measure", url + "/", audit_dir, "--offline", "--delay", "0", "--brand", "Fixture", "--lang", "en", script="quick.py"))
    data = json.load(open(audit, encoding="utf-8"))
    data["task_overrides"] = {"X9": {"lane": "C", "prio": 1, "name": "Add the legal notice", "what": "Add it", "check": "Verified when it is linked"}}
    json.dump(data, open(audit, "w", encoding="utf-8"), ensure_ascii=False)
    refused_plain = run("plan", audit, audit_dir)
    if refused_plain.returncode == 0 or "not a git repository" not in refused_plain.stdout + refused_plain.stderr:
        err.append("a folder without git must be refused")
    subprocess.run(["git", "init", "-q", "-b", "main", repo], check=True)
    git("config", "user.name", "Selftest"); git("config", "user.email", "selftest@example.invalid")
    git("add", "-A"); git("commit", "-q", "-m", "the site as it was")
    base = git("rev-parse", "HEAD")
    tasks = R.load(audit)[1]
    by_kind = lambda k: [c for c, t in tasks.items() if t["kind"] == k]
    llms = next(c for c, t in tasks.items() if os.path.basename(t.get("file") or "") == "llms.txt")
    code_task = by_kind("code")[0]

    expect("plan", run("plan", audit, repo), says="Claude changes the code")
    refused("commit before start", "commit", audit, repo, code_task, says="start first")
    open(os.path.join(repo, "work.txt"), "w").write("someone's work")
    refused("start with work in progress", "start", audit, repo, says="uncommitted work")
    os.remove(os.path.join(repo, "work.txt"))
    expect("start", run("start", audit, repo), says="audit-fixes/")
    branch = json.load(open(audit, encoding="utf-8"))["repair"]["branch"]
    expect("baseline", run("verify", audit, "--url", url, "--baseline", "--delay", "0"), says="baseline stored")
    if "differ" in run("verify", audit, "--url", url, "--baseline", "--delay", "0").stdout:
        err.append("the same code as the audit must not be flagged as different")
    refused("a site that is not on this machine", "verify", audit, "--url", "https://www.example.com", says="not on this machine")

    # a ready file: placed, read once, never overwritten
    expect("place", run("place", audit, repo, llms), says="llms.txt")
    if not os.path.isfile(os.path.join(repo, "llms.txt")):
        err.append("llms.txt is not in the folder")
    refused("place over an uncommitted copy", "place", audit, repo, llms, says="already exists")
    expect("commit", run("commit", audit, repo, llms))
    if git("log", "-1", "--format=%s") != f"audit-seo-geo {llms}: {tasks[llms]['name']}":
        err.append("the commit does not name its task")
    refused("a commit with no change", "commit", audit, repo, code_task, says="no change")
    refused("an unknown task", "commit", audit, repo, "ZZ9", says="unknown task")

    # what must never go in a commit
    secret = os.path.join(repo, "config.js")
    open(secret, "w").write('const key = "sk-' + "a" * 30 + '";\n')
    refused("a secret", "commit", audit, repo, code_task, says="secret")
    if not os.path.isfile(secret) or git("diff", "--cached", "--name-only"):
        err.append("after a refusal the changes must stay in the folder, unstaged")
    open(secret, "w").write('const password = "correct-horse-battery";\n')
    refused("a password", "commit", audit, repo, code_task, says="secret")
    os.remove(secret)
    env = os.path.join(repo, ".env")
    open(env, "w").write("A=1\n")
    refused("an .env file", "commit", audit, repo, code_task, says=".env")
    os.remove(env)

    # what Claude must not do alone
    open(os.path.join(repo, "note.txt"), "w").write("x\n")
    refused("facts nobody gave", "commit", audit, repo, by_kind("facts")[0], says="facts only the person has")
    refused("what is off the code", "commit", audit, repo, by_kind("outside")[0], says="off the code")
    os.remove(os.path.join(repo, "note.txt"))
    git("switch", "-q", "main")
    open(os.path.join(repo, "note.txt"), "w").write("x\n")
    refused("a commit on the main branch", "commit", audit, repo, code_task, says=f"not on {branch}")
    os.remove(os.path.join(repo, "note.txt"))
    git("switch", "-q", branch)

    # a partial answer: what was answered goes in, what was not stays in the form
    facts = by_kind("facts")[0]
    open(os.path.join(repo, "legal.html"), "w").write("<h1>Legal</h1>Testeur\n")
    expect("a partial answer", run("commit", audit, repo, facts, "--facts-given", "--open", "Which address?"))
    done_ = {c: e for c, e in json.load(open(audit, encoding="utf-8"))["repair"]["tasks"].items()}
    left = R.waiting_tasks(R.load(audit)[1].values(), done_)
    if not any(t["code"] == facts and t["questions"] == ["Which address?"] for t in left):
        err.append(f"an open question must stay in the form: {left}")
    if "already on the branch" not in run("plan", audit, repo).stdout:
        err.append("the plan must say what is already on the branch")

    # a real fix, then a real regression
    about = os.path.join(repo, "about.html")
    page = open(about, encoding="utf-8").read()
    fixed = page.replace("<title>Fixture site</title></head>", '<title>About</title><meta name="viewport" content="width=device-width"></head>')
    if fixed == page:
        err.append("the fixture changed: this test no longer fixes anything")
    open(about, "w", encoding="utf-8").write(fixed)
    expect("a fix", run("commit", audit, repo, code_task, "--note", "Read me"))
    if "Read me" not in git("log", "-1", "--format=%B"):
        err.append("the note must be in the commit")
    r = run("verify", audit, "--url", url, "--delay", "0")
    expect("verify", r)
    if "better" not in r.stdout:
        err.append(f"verify must see the fixes: {r.stdout[:300]}")
    index = os.path.join(repo, "index.html")
    home = open(index, encoding="utf-8").read()
    open(index, "w", encoding="utf-8").write(home.replace("</head>", '<script src="http://example.invalid/x.js"></script></head>'))
    r = run("verify", audit, "--url", url, "--delay", "0")
    if r.returncode != 3 or "WORSE" not in r.stdout:
        err.append(f"what was good before the fixes and broken after must give exit code 3: {r.returncode}, {r.stdout[:200]}")
    refused("accepting without a reason", "verify", audit, "--url", url, "--delay", "0", "--accept", "B4", says="--why")
    expect("a false alarm checked by hand", run("verify", audit, "--url", url, "--delay", "0", "--accept", "B4", "--why", "Read by hand"))
    open(index, "w", encoding="utf-8").write(home)
    expect("verify again", run("verify", audit, "--url", url, "--delay", "0"))

    # what was promised stays true
    if git("rev-parse", "main") != base:
        err.append("the main branch moved")
    if git("remote"):
        err.append("a remote appeared")
    if git("branch", "--show-current") != branch:
        err.append("not on the branch")
    code = open(os.path.join(SCRIPTS, "repair.py"), encoding="utf-8").read()
    if any(w in code for w in ('"push"', "'push'", '"merge"', "netlify deploy", "vercel deploy")):
        err.append("repair.py must have no way of sending anything")

    # the summary and the report
    other = by_kind("facts")[1] if len(by_kind("facts")) > 1 else by_kind("outside")[0]
    run("skip", audit, other, "--why", "Waiting for the legal name")
    expect("finish", run("finish", audit, repo))
    md = open(os.path.join(audit_dir, "Fixes applied.md"), encoding="utf-8").read()
    for piece in (branch, tasks[llms]["name"], "Read me", "Nothing has been pushed", "Waiting for the legal name", "branch -D", "Here are my answers"):
        if piece not in md:
            err.append(f"the summary lacks: {piece}")
    expect("report", run("build", audit, os.path.join(audit_dir, "after"), script="quick.py"))
    html = next(open(os.path.join(audit_dir, "after", f), encoding="utf-8").read() for f in os.listdir(os.path.join(audit_dir, "after")) if f.endswith(".html"))
    todo = next(open(os.path.join(audit_dir, "after", f), encoding="utf-8-sig").read() for f in os.listdir(os.path.join(audit_dir, "after")) if f.endswith(".md"))
    table = next(open(os.path.join(audit_dir, "after", f), encoding="utf-8-sig").read() for f in os.listdir(os.path.join(audit_dir, "after")) if f.endswith(".csv"))
    if "In the code, not online yet" not in todo or "In the code, not online yet" not in table:
        err.append("the Markdown and CSV to-do must follow the fixes")
    for piece in ("In the code, not online yet", "on the branch " + branch, "Could not be done", "Fixes waiting for your answers"):
        if piece not in html:
            err.append(f"the report lacks: {piece}")
    if "Claude can apply" in html:
        err.append("once applied, the report must stop offering")
    before = json.load(open(audit, encoding="utf-8"))
    before.pop("repair")
    json.dump(before, open(os.path.join(audit_dir, "fresh.json"), "w", encoding="utf-8"))
    expect("fresh report", run("build", os.path.join(audit_dir, "fresh.json"), os.path.join(audit_dir, "fresh"), script="quick.py"))
    html = next(open(os.path.join(audit_dir, "fresh", f), encoding="utf-8").read() for f in os.listdir(os.path.join(audit_dir, "fresh")) if f.endswith(".html"))
    if "Claude can apply" not in html or "Fix my site with this audit" not in html:
        err.append("the report must offer the fixes it can apply")

    # a local copy lists the live addresses in its sitemap: they must be read here, never online
    open(os.path.join(repo, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: https://live.invalid/sitemap.xml\n")
    open(os.path.join(repo, "sitemap.xml"), "w").write("<urlset><url><loc>https://live.invalid/about.html</loc></url></urlset>")
    crawl_dir = os.path.join(audit_dir, "mapped")
    expect("crawl", run(url + "/", crawl_dir, "--delay", "0", "--max", "5", "--map-host", "live.invalid", script="crawl.py"))
    read = [json.loads(l)["url"] for l in open(os.path.join(crawl_dir, "crawl.jsonl"), encoding="utf-8")]
    if any("live.invalid" in u for u in read) or url + "/about.html" not in read:
        err.append(f"--map-host: read {read}")
finally:
    server.terminate()

# merging with what is already there
own = "/assets/*\n  Cache-Control: max-age=60\n\n/*\n  X-Frame-Options: DENY\n  Content-Security-Policy: default-src 'self'\n"
new = "# draft\n/*\n  X-Frame-Options: SAMEORIGIN\n  Referrer-Policy: no-referrer\n  Content-Security-Policy-Report-Only: default-src 'none'\n"
merged = R.merge_headers(own, new)
if "DENY" not in merged or "SAMEORIGIN" in merged or "Referrer-Policy: no-referrer" not in merged or "Report-Only" in merged or "Cache-Control: max-age=60" not in merged:
    err.append(f"_headers: {merged}")
if "/*\n  X-Frame-Options: SAMEORIGIN" not in R.merge_headers("/x\n  A: b\n", new):
    err.append("_headers: a missing /* block must be added")
if R.merge_headers(merged, new) != merged:
    err.append("_headers: merging twice must change nothing")
add = json.dumps({"headers": [{"source": "/(.*)", "headers": [{"key": "A", "value": "new"}, {"key": "B", "value": "2"}]}]})
body = json.loads(R.merge_vercel(json.dumps({"cleanUrls": True, "headers": [{"source": "/(.*)", "headers": [{"key": "a", "value": "mine"}]}]}), add))
if not body["cleanUrls"] or body["headers"][0]["headers"] != [{"key": "a", "value": "mine"}, {"key": "B", "value": "2"}]:
    err.append(f"vercel.json: {body}")

# who does what
for t, kind in (({"key": "D1"}, "code"), ({"key": "D4"}, "facts"), ({"key": "C3"}, "outside"), ({"key": "C2", "file": "fixes/_headers"}, "file"), ({"key": "C2", "file": "fixes/security-headers.txt"}, "outside"),
                ({"key": "F2"}, "code"), ({"key": "X1", "lane": "C"}, "facts"), ({"key": "X2", "lane": "F"}, "code"), ({"key": "D4", "repair": "code"}, "code"), ({"criterion": "F1", "key": "F7"}, "code")):
    if repair_kind(t) != kind:
        err.append(f"repair_kind({t}) = {repair_kind(t)}, expected {kind}")
T = translator("fr")
if repair_block(["code"], None, {"framework": HOSTED[0]}, T, str) or repair_block(["facts"], None, {}, T, str):
    err.append("no offer on a hosted platform, or with nothing to apply")
if "Claude peut appliquer 1 de ces 2" not in repair_block(["code", "facts"], None, {}, T, str):
    err.append("the offer counts wrongly")

print("\n".join("repair: " + e for e in err) if err else "repair checked: refusals, branch, commits, local verification, regression, summary, report")
sys.exit(1 if err else 0)
