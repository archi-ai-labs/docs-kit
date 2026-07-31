#!/usr/bin/env python3
"""Report what a repository is built with. READ-ONLY — it writes nothing, creates
nothing, and makes no network call.

Usage:  docs_detect.py [repo_root]      (default: .)

Output is one fact per line, sorted, in a fixed grammar so a skill can read it
without guessing:

    manifest: go.mod
    lang: go 1.22
    dep: github.com/jackc/pgx/v5
    dep-count: 24
    service: postgres image postgres:16
    frontend: no
    DETECT OK

It reports only what a file actually declares. A version is printed when the
manifest states one and omitted otherwise — never inferred from a lockfile or a
CI config, because a guess here becomes a line in `tech_stack:` that nobody can
trace back to anything.

`frontend:` is informational. It must never change what gets scaffolded: the
docs tree is 15 folders for every repo, and making it conditional would leave
every backend repo printing a layout NOTE forever.

Python 3.9 stdlib only (`tomllib` is 3.11+, so TOML is line-parsed, not parsed).
"""
import json
import os
import re
import sys

DEP_CAP = 15   # per manifest; the true total always follows as dep-count:

UI_FRAMEWORKS = ("@angular/core", "next", "nuxt", "preact", "react", "solid-js",
                 "svelte", "vue")


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return ""


def load_json(path):
    try:
        return json.loads(read(path))
    except ValueError:
        return {}


def go_mod(text):
    ver, deps = "", []
    m = re.search(r"^go\s+(\d+\.\d+(?:\.\d+)?)\s*$", text, re.M)
    if m:
        ver = m.group(1)
    # A require line carrying "// indirect" is a transitive dependency; only what
    # this module asks for directly says anything about what it is built with.
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("require ") and "(" not in line:
            line = line[len("require "):].strip()
        elif line.startswith(("module ", "go ", "require", ")", "//")) or not line:
            continue
        if "// indirect" in line:
            continue
        parts = line.split()
        if len(parts) >= 2 and "/" in parts[0] or (parts and parts[0].startswith("golang.org")):
            deps.append(parts[0])
    return ("go", ver), deps


def package_json(path):
    data = load_json(path)
    ver = ""
    eng = data.get("engines")
    if isinstance(eng, dict) and isinstance(eng.get("node"), str):
        ver = eng["node"]
    deps = [k for k in data.get("dependencies", {}) if isinstance(k, str)]
    return ("node", ver), deps


def requirements_txt(text):
    deps = []
    for line in text.split("\n"):
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        deps.append(re.split(r"[=<>!~\[;\s]", line, 1)[0])
    return ("python", ""), [d for d in deps if d]


def pyproject(text):
    ver = ""
    m = re.search(r'requires-python\s*=\s*"([^"]+)"', text)
    if m:
        ver = m.group(1)
    deps = []
    m = re.search(r"^dependencies\s*=\s*\[(.*?)\]", text, re.S | re.M)
    if m:
        for item in re.findall(r'["\']([^"\']+)["\']', m.group(1)):
            deps.append(re.split(r"[=<>!~\[;\s]", item, 1)[0])
    for name in re.findall(r"^([A-Za-z0-9_.\-]+)\s*=\s*[\"^~]",
                           _section(text, "tool.poetry.dependencies"), re.M):
        if name.lower() != "python":
            deps.append(name)
    return ("python", ver), [d for d in deps if d]


def cargo_toml(text):
    ver = ""
    m = re.search(r'rust-version\s*=\s*"([^"]+)"', text)
    if m:
        ver = m.group(1)
    deps = re.findall(r"^([A-Za-z0-9_.\-]+)\s*=", _section(text, "dependencies"), re.M)
    return ("rust", ver), deps


def _section(text, name):
    """The body of a `[name]` TOML table, up to the next table header."""
    m = re.search(r"^\[%s\]\s*$" % re.escape(name), text, re.M)
    if not m:
        return ""
    rest = text[m.end():]
    nxt = re.search(r"^\[", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def pom_xml(text):
    ver = ""
    m = (re.search(r"<java\.version>([^<]+)</java\.version>", text)
         or re.search(r"<maven\.compiler\.source>([^<]+)</maven\.compiler\.source>", text))
    if m:
        ver = m.group(1)
    deps = re.findall(r"<dependency>.*?<artifactId>([^<]+)</artifactId>", text, re.S)
    return ("java", ver), deps


def build_gradle(text):
    ver = ""
    m = re.search(r"sourceCompatibility\s*=?\s*['\"]?([\w.]+)", text)
    if m:
        ver = m.group(1)
    deps = []
    for coord in re.findall(r"""(?:implementation|api)\s*\(?\s*['"]([^'"]+)['"]""", text):
        parts = coord.split(":")
        deps.append(parts[1] if len(parts) >= 2 else coord)
    return ("java", ver), deps


def gemfile(text):
    ver = ""
    m = re.search(r"""^ruby\s+['"]([^'"]+)['"]""", text, re.M)
    if m:
        ver = m.group(1)
    return ("ruby", ver), re.findall(r"""^\s*gem\s+['"]([^'"]+)['"]""", text, re.M)


def composer_json(path):
    data = load_json(path)
    req = data.get("require", {})
    req = req if isinstance(req, dict) else {}
    ver = req.get("php", "") if isinstance(req.get("php"), str) else ""
    return ("php", ver), [k for k in req if k != "php"]


def csproj(text):
    ver = ""
    m = re.search(r"<TargetFramework[s]?>([^<;]+)", text)
    if m:
        ver = m.group(1)
    return ("dotnet", ver), re.findall(r'<PackageReference\s+Include="([^"]+)"', text)


# filename → reader. A reader takes the file's text (or its path, when it needs
# real JSON) and returns ((language, version), [direct dependency, ...]).
TEXT_READERS = {
    "go.mod": go_mod,
    "requirements.txt": requirements_txt,
    "pyproject.toml": pyproject,
    "Cargo.toml": cargo_toml,
    "pom.xml": pom_xml,
    "build.gradle": build_gradle,
    "build.gradle.kts": build_gradle,
    "Gemfile": gemfile,
}
PATH_READERS = {
    "package.json": package_json,
    "composer.json": composer_json,
}


SKIP_DIRS = ("node_modules", "vendor", "target", "dist", "build", "venv",
             "__pycache__", "testdata", "fixtures")
MAX_DEPTH = 2   # a monorepo keeps its manifests at apps/<name>/, services/<name>/


def manifests(root):
    """Every manifest down to MAX_DEPTH, sorted so two runs print the same lines."""
    found, dirs = [], [""]
    for depth in range(MAX_DEPTH):
        nxt = []
        for d in [x for x in dirs if x.count(os.sep) + (1 if x else 0) == depth]:
            base = os.path.join(root, d) if d else root
            try:
                names = sorted(os.listdir(base))
            except OSError:
                continue
            for name in names:
                if name.startswith(".") or name in SKIP_DIRS:
                    continue
                if os.path.isdir(os.path.join(base, name)):
                    nxt.append(os.path.join(d, name) if d else name)
        dirs.extend(nxt)
    for d in dirs:
        base = os.path.join(root, d) if d else root
        try:
            names = sorted(os.listdir(base))
        except OSError:
            continue
        for name in names:
            path = os.path.join(base, name)
            if not os.path.isfile(path):
                continue
            if name in TEXT_READERS or name in PATH_READERS or name.endswith(".csproj"):
                found.append((os.path.join(d, name) if d else name, path))
    return sorted(found)


def compose_services(root):
    """Service name and image from a docker-compose file. This is where a real
    `PostgreSQL 16` comes from — a language manifest never says it. Line-based on
    purpose: the alternative is a YAML dependency, and the shape read here is the
    one every compose file uses."""
    out = []
    for name in ("docker-compose.yml", "docker-compose.yaml", "compose.yml",
                 "compose.yaml"):
        path = os.path.join(root, name)
        if not os.path.isfile(path):
            continue
        lines = read(path).split("\n")
        i, n = 0, len(lines)
        while i < n and not re.match(r"^services:\s*$", lines[i]):
            i += 1
        i += 1
        svc, child_indent = None, None
        while i < n:
            line = lines[i]
            i += 1
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            indent = len(line) - len(line.lstrip())
            if indent == 0:
                break                      # back to a top-level key
            if child_indent is None:
                child_indent = indent
            if indent == child_indent and line.rstrip().endswith(":"):
                svc = line.strip().rstrip(":")
                continue
            m = re.match(r"^\s*image:\s*[\"']?([^\"'\s]+)", line)
            if m and svc:
                out.append((svc, m.group(1)))
    return sorted(set(out))


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    lines, ui = [], False
    for rel, path in manifests(root):
        name = os.path.basename(path)
        if name in PATH_READERS:
            (lang, ver), deps = PATH_READERS[name](path)
        elif name.endswith(".csproj") and name not in TEXT_READERS:
            (lang, ver), deps = csproj(read(path))
        else:
            (lang, ver), deps = TEXT_READERS[name](read(path))
        lines.append("manifest: %s" % rel)
        lines.append("lang: %s%s" % (lang, (" " + ver) if ver else ""))
        deps = sorted(set(d for d in deps if d))
        if name == "package.json" and any(d in UI_FRAMEWORKS for d in deps):
            ui = True
        for dep in deps[:DEP_CAP]:
            lines.append("dep: %s" % dep)
        # Always print the true total. A cap that is not stated reads as
        # "that was all of them", which is a different claim.
        lines.append("dep-count: %d" % len(deps))
    for svc, image in compose_services(root):
        lines.append("service: %s image %s" % (svc, image))
    if lines:
        lines.append("frontend: %s" % ("yes" if ui else "no"))
    # An unrecognised repo is not an error — it is a repo whose stack this script
    # cannot state, which is exactly what printing nothing says.
    print("\n".join(lines + ["DETECT OK"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
