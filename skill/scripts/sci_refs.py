#!/usr/bin/env python3
"""Offline-safe BibTeX/LaTeX audit and explicit DOI evidence-gated citation edits.

Python 3.10+ standard library only. Network is used solely by search/import/verify.
"""
from __future__ import annotations
import argparse
import datetime as dt
import difflib
import html
import json
import os
import re
import shutil
import sys
import tempfile
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

USER_AGENT = "sci-literature-codex/1.0 (research bibliography verification; contact via CROSSREF_MAILTO when set)"
DOI_RE = re.compile(r"^10\.\d{4,9}/\S+$", re.I)
ENTRY_RE = re.compile(r"@([a-zA-Z]+)\s*\{\s*([^,\s{}]+)\s*,", re.M)
FIELD_RE = re.compile(r"([a-zA-Z][\w-]*)\s*=\s*", re.M)
CITE_RE = re.compile(r"\\(cite|citep|citet|citealt|citealp|citeauthor|citeyear|parencite|textcite|autocite|footcite|supercite|smartcite|nocite)\*?(?:\s*\[[^\]]*\]){0,2}\s*\{([^{}]*)\}")
OMIT_DIRS = {".git", ".agents", ".venv", "build", "out", ".latexmk", "node_modules"}


def die(msg):
    raise ValueError(msg)


def normalize_doi(raw):
    x = html.unescape(str(raw)).strip()
    x = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", x, flags=re.I).strip()
    x = urllib.parse.unquote(x).strip().rstrip(".,;")
    if not DOI_RE.fullmatch(x) or any(c.isspace() for c in x):
        die(f"无效 DOI: {raw!r}")
    return x.lower()


def fetch_json(url):
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    email = os.environ.get("CROSSREF_MAILTO", "").strip()
    if email:
        headers["User-Agent"] = USER_AGENT + " (mailto:" + email + ")"
    if email:
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode({"mailto": email})
    req = urllib.request.Request(url, headers=headers)
    for retry in range(3):
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503, 504) and retry < 2:
                time.sleep(1.0 + retry * 2)
                continue
            raise ValueError(f"Crossref HTTP {exc.code}: {url}") from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if retry < 2:
                time.sleep(1.0 + retry * 2)
                continue
            raise ValueError(f"Crossref 网络错误: {exc}") from exc


def crossref_doi(doi):
    doi = normalize_doi(doi)
    url = "https://api.crossref.org/works/" + urllib.parse.quote(doi, safe="")
    obj = fetch_json(url)["message"]
    returned = normalize_doi(obj["DOI"])
    if returned != doi:
        die(f"DOI 返回结果不一致: {doi} / {returned}")
    return obj


def one(value):
    if isinstance(value, list):
        return str(value[0]) if value else ""
    return str(value or "")


def clean_text(s):
    s = re.sub(r"<[^>]*>", "", html.unescape(str(s or "")))
    return re.sub(r"\s+", " ", s).strip()


def pub_year(work):
    for k in ("published-print", "published-online", "published", "issued"):
        date_parts = work.get(k, {}).get("date-parts", [[]])
        if date_parts and date_parts[0]:
            return str(date_parts[0][0])
    return ""


def metadata(work):
    return {
        "doi": normalize_doi(work.get("DOI", "")),
        "title": clean_text(one(work.get("title"))),
        "journal": clean_text(one(work.get("container-title"))),
        "year": pub_year(work),
        "type": work.get("type", ""),
        "authors": [clean_text((a.get("given", "") + " " + a.get("family", "")).strip() or a.get("name", "")) for a in work.get("author", [])],
        "publisher": clean_text(work.get("publisher", "")),
        "volume": clean_text(work.get("volume", "")),
        "issue": clean_text(work.get("issue", "")),
        "page": clean_text(work.get("page", "")),
        "relation": work.get("relation", {}),
        "update_to": work.get("update-to", []),
        "update_type": work.get("update-type", ""),
        "url": "https://doi.org/" + normalize_doi(work["DOI"]),
        "metadata_source": "Crossref Works API",
        "metadata_verified_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "content_support_verified": False,
        "retraction_status_checked": False,
        "sci_indexing_verified": False,
    }


def read_json(path, fallback=None):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.is_file() else (fallback if fallback is not None else {})


def read_preserve(path):
    with Path(path).open("r", encoding="utf-8-sig", newline="") as fh:
        return fh.read()


def atomic_write(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", delete=False, dir=path.parent) as fh:
        fh.write(text)
        temp = Path(fh.name)
    temp.replace(path)


def dump_json(path, payload):
    atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def balanced(s, pos, left="{", right="}"):
    if pos >= len(s) or s[pos] != left:
        die("Unexpected balanced field start")
    depth = 0
    for i in range(pos, len(s)):
        if s[i] == "\\":
            # Escaped brace is ignored by scanning just the following character.
            continue
        if s[i] == left and (i == 0 or s[i-1] != "\\"):
            depth += 1
        elif s[i] == right and (i == 0 or s[i-1] != "\\"):
            depth -= 1
            if depth == 0:
                return s[pos + 1:i], i + 1
    die("BibTeX 缺少配对括号")


def parse_fields(body):
    """Best-effort reading of normal @article field assignments; not a BibTeX expander."""
    result = {}
    i = 0
    while i < len(body):
        while i < len(body) and (body[i].isspace() or body[i] == ','):
            i += 1
        m = FIELD_RE.match(body, i)
        if not m:
            break
        key = m.group(1).lower()
        i = m.end()
        if i >= len(body):
            break
        if body[i] == "{":
            value, i = balanced(body, i)
        elif body[i] == '"':
            j = i + 1
            while j < len(body):
                if body[j] == '"' and body[j - 1] != "\\":
                    break
                j += 1
            if j >= len(body):
                die("BibTeX 缺少引号")
            value, i = body[i + 1:j], j + 1
        else:
            j = body.find(",", i)
            if j < 0:
                j = len(body)
            value, i = body[i:j].strip(), j
        result[key] = value.strip()
    return result


def bib_entries(path):
    p = Path(path)
    if not p.exists():
        return []
    text = read_preserve(p)
    out = []
    pos = 0
    while True:
        m = ENTRY_RE.search(text, pos)
        if not m:
            break
        kind, key = m.group(1).lower(), m.group(2)
        body, end = balanced(text, text.index("{", m.start(), m.end()))
        pos = end
        if kind in ("comment", "preamble", "string"):
            continue
        # body starts after the opening {; discard entry key through first comma
        sep = body.find(",")
        if sep < 0:
            continue
        fields = parse_fields(body[sep + 1:])
        doi_raw = re.sub(r"[{}]", "", fields.get("doi", "")).strip()
        try:
            doi = normalize_doi(doi_raw) if doi_raw else ""
        except ValueError:
            doi = ""
        out.append({"key": key, "kind": kind, "doi": doi, "doi_raw": doi_raw, "fields": fields})
    return out


def slug(s):
    return re.sub(r"[^a-zA-Z0-9]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii"))


def choose_key(work, used):
    family = (work.get("author") or [{}])[0].get("family", "Unknown")
    title = clean_text(one(work.get("title")))
    first = next((slug(w) for w in title.split() if len(slug(w)) >= 4), "Paper")
    base = slug(family).lower()[:20] + pub_year(work) + first[:16].capitalize()
    if not base:
        base = "ref" + pub_year(work)
    key = base
    count = 2
    while key.lower() in used:
        key = f"{base}{count}"
        count += 1
    used.add(key.lower())
    return key


def tex_escape(v):
    # Fields use UTF-8; Biber supports Unicode. BibTeX engines may require conversions.
    v = clean_text(v)
    esc = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(esc.get(c, c) for c in v)


def work_to_bib(work, key):
    meta = metadata(work)
    if not meta["title"] or not meta["year"]:
        die(f"元数据缺少标题或年份: {meta['doi']}")
    kind = work.get("type", "")
    typ = "article" if kind == "journal-article" else ("inproceedings" if kind == "proceedings-article" else "misc")
    authors = []
    for author in work.get("author", []):
        family = tex_escape(author.get("family", ""))
        given = tex_escape(author.get("given", ""))
        if family:
            authors.append(f"{family}, {given}".strip().rstrip(","))
        elif author.get("name"):
            authors.append("{" + tex_escape(author["name"]) + "}")
    fields = [
        ("title", "{" + tex_escape(meta["title"]) + "}"),
        ("author", " and ".join(authors)),
        ("year", meta["year"]),
    ]
    if typ == "article":
        fields.append(("journal", tex_escape(meta["journal"])))
    elif typ == "inproceedings":
        fields.append(("booktitle", tex_escape(meta["journal"])))
    fields += [("volume", meta["volume"]), ("number", meta["issue"]),
               ("pages", re.sub(r"(?<!-)-(?!-)", "--", meta["page"].replace("–", "--").replace("—", "--"))),
               ("publisher", tex_escape(meta["publisher"])),
               ("doi", meta["doi"]), ("url", meta["url"])]
    body = ",\n".join(f"  {field} = {{{value}}}" for field, value in fields if value)
    return f"@{typ}{{{key},\n{body}\n}}\n"


def cmd_search(args):
    params = {"query.bibliographic": args.query, "rows": str(args.limit), "select": "DOI,title,author,container-title,published,published-online,published-print,issued,type,URL"}
    if args.since:
        params["filter"] = "from-pub-date:" + args.since
    url = "https://api.crossref.org/works?" + urllib.parse.urlencode(params)
    items = fetch_json(url)["message"].get("items", [])
    results = []
    for x in items:
        try:
            m = metadata(x)
            results.append({k: m[k] for k in ("doi", "title", "journal", "year", "type", "authors", "url", "metadata_source")})
        except ValueError:
            pass
    output = {"query": args.query, "notice": "仅供候选筛选；搜索排序及 DOI 元数据不证明论点成立、SCI 收录或撤稿状态", "results": results}
    if args.out:
        dump_json(args.out, output)
        print(f"已写入 {args.out}，候选 {len(results)} 条")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))


def update_ledger(path, records):
    ledger = read_json(path, {"schema": 1, "records": {}})
    ledger.setdefault("records", {}).update(records)
    dump_json(path, ledger)


def cmd_import(args):
    bib = Path(args.bib)
    existing = bib_entries(bib)
    keys = {e["key"].lower() for e in existing}
    doi_map = {e["doi"]: e["key"] for e in existing if e["doi"]}
    entry_by_doi = {e["doi"]: e for e in existing if e["doi"]}
    new_entries = []
    ledger_entries = {}
    for raw in args.doi:
        doi = normalize_doi(raw)
        work = crossref_doi(doi)
        meta = metadata(work)
        if doi in doi_map:
            key = doi_map[doi]
            oldentry = entry_by_doi[doi]
            oldtitle = oldentry["fields"].get("title", "")
            oldyear = oldentry["fields"].get("year", "").strip("{} ")
            score = difflib.SequenceMatcher(None, plain_title(oldtitle), plain_title(meta["title"])).ratio()
            if not oldtitle or score < 0.8 or (oldyear and oldyear != meta["year"]):
                die(f"DOI 已存在但 .bib 标题/年份与 Crossref 不一致: {doi} => {key}; 先人工核查后执行 verify")
            print(f"已存在 DOI，跳过追加: {doi} => {key}")
        else:
            key = choose_key(work, keys)
            new_entries.append(work_to_bib(work, key))
            doi_map[doi] = key
            print(f"准备新增: {doi} => {key}")
        ledger_entries[doi] = {"key": key, "status": "metadata_verified", **meta}
    if new_entries:
        if bib.exists():
            stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
            backup = bib.with_name(bib.name + ".bak." + stamp)
            shutil.copy2(bib, backup)
            print(f"原始 .bib 已备份到 {backup}")
        old = read_preserve(bib) if bib.exists() else ""
        nl = "\r\n" if "\r\n" in old else "\n"
        separator = ("" if old.endswith(("\n", "\r")) else nl) + (nl if old.strip() else "")
        atomic_write(bib, old + separator + nl.join(x.replace("\n", nl) for x in new_entries))
    update_ledger(args.ledger, ledger_entries)
    print(f"BibTeX 新增 {len(new_entries)} 条；核验记录: {args.ledger}")


def plain_title(s):
    x = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    x = re.sub(r"[{}\\]", "", x)
    return re.sub(r"[^a-z0-9]+", "", unicodedata.normalize("NFKD", x).lower())


def cmd_verify(args):
    entries = bib_entries(args.bib)
    if args.key:
        wanted = set(args.key)
        entries = [e for e in entries if e["key"] in wanted]
        unknown = wanted - {e["key"] for e in entries}
        if unknown:
            die("Missing BibTeX keys: " + ", ".join(sorted(unknown)))
    ledger_entries, problems, report = {}, [], []
    for e in entries:
        if not e["doi"]:
            report.append({"key": e["key"], "status": "no_valid_doi", "detail": e["doi_raw"]})
            continue
        try:
            meta = metadata(crossref_doi(e["doi"]))
            title_in_bib = e["fields"].get("title", "")
            title_similarity = difflib.SequenceMatcher(None, plain_title(meta["title"]), plain_title(title_in_bib)).ratio() if title_in_bib else 0
            year_match = str(e["fields"].get("year", "")).strip("{} ") == meta["year"]
            mismatches = []
            if title_similarity < 0.8:
                mismatches.append("title_mismatch")
            if e["fields"].get("year") and not year_match:
                mismatches.append("year_mismatch")
            status = "metadata_verified" if not mismatches else "metadata_mismatch"
            report.append({"key": e["key"], "doi": e["doi"], "status": status,
                           "title_similarity": round(title_similarity, 3), "year_match": year_match, "flags": mismatches})
            ledger_entries[e["doi"]] = {"key": e["key"], "status": status, **meta}
            if mismatches:
                problems.append(f"{e['key']}: {', '.join(mismatches)}")
        except (ValueError, KeyError) as exc:
            report.append({"key": e["key"], "doi": e["doi"], "status": "lookup_failed", "error": str(exc)})
            problems.append(e["key"] + ": DOI lookup failed")
    update_ledger(args.ledger, ledger_entries)
    if args.out:
        dump_json(args.out, {"results": report, "problems": problems})
    print(json.dumps({"results": report, "problems": problems}, ensure_ascii=False, indent=2))
    if problems:
        return 1


def mask_tex(source):
    """Preserve offsets; ignore comments and standard verbatim-ish environments."""
    chars = list(source)
    def spaces(a, b):
        for n in range(a, b):
            if chars[n] not in ("\n", "\r"):
                chars[n] = " "
    for m in re.finditer(r"\\begin\{(verbatim\*?|lstlisting|minted|comment)\}(?:\[[^\]]*\])?(?:\{[^{}]*\})?.*?\\end\{\1\}", source, re.S):
        spaces(*m.span())
    # Turn off comments: unescaped '%' to end of line
    i = 0
    while i < len(source):
        if chars[i] == "%" and (i == 0 or source[i-1] != "\\"):
            j = source.find("\n", i)
            if j == -1:
                j = len(source)
            spaces(i, j)
            i = j
        else:
            i += 1
    return "".join(chars)


def tex_files(root):
    files = []
    for base, dirs, fs in os.walk(root):
        dirs[:] = [x for x in dirs if x not in OMIT_DIRS]
        files += [Path(base) / x for x in fs if x.lower().endswith(".tex")]
    return sorted(files)


def cmd_audit(args):
    root = Path(args.root).resolve()
    all_entries = []
    for name in args.bib:
        all_entries.extend(bib_entries(root / name if not Path(name).is_absolute() else name))
    key_names, doi_map, duplicate_keys, duplicate_dois = {}, {}, [], []
    for e in all_entries:
        k = e["key"].lower()
        if k in key_names:
            duplicate_keys.append([key_names[k], e["key"]])
        key_names[k] = e["key"]
        if e["doi"]:
            if e["doi"] in doi_map:
                duplicate_dois.append({"doi": e["doi"], "keys": [doi_map[e["doi"]], e["key"]]})
            doi_map[e["doi"]] = e["key"]
    used, citations = set(), []
    for file in tex_files(root):
        src = mask_tex(read_preserve(file))
        for m in CITE_RE.finditer(src):
            for key in m.group(2).split(","):
                key = key.strip()
                if key and key != "*":
                    used.add(key.lower())
                    citations.append({"file": str(file.relative_to(root)), "line": src.count("\n", 0, m.start()) + 1,
                                      "command": m.group(1), "key": key})
    missing = sorted({c["key"] for c in citations if c["key"].lower() not in key_names})
    unused = sorted({e["key"] for e in all_entries if e["key"].lower() not in used})
    invalid_dois = [{"key": e["key"], "doi": e["doi_raw"]} for e in all_entries if e["doi_raw"] and not e["doi"]]
    summary = {"tex_files": len(tex_files(root)), "bib_entries": len(all_entries), "citations": len(citations),
               "missing_citation_keys": missing, "duplicate_bib_keys": duplicate_keys,
               "duplicate_dois": duplicate_dois, "invalid_doi_fields": invalid_dois,
               "unused_bib_keys": unused,
               "limitations": ["此项为离线语法审计；不证明文献存在、SCI 收录或论点获支持", "复杂宏展开、\\input 的动态路径、\\verb 和特殊 BibTeX 表达式可能需要人工检查"]}
    if args.out:
        dump_json(args.out, {"summary": summary, "citations": citations})
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if missing or duplicate_keys or duplicate_dois or invalid_dois:
        return 1


def safe_tex_path(root, file):
    p = (root / file).resolve()
    if p.suffix.lower() != ".tex" or not p.is_relative_to(root.resolve()) or not p.is_file():
        die(f"不可写的 .tex 路径（须在项目目录内且存在）: {file}")
    return p


def check_proposal(item, known, ledger):
    keys = item.get("keys", [])
    if not keys or not isinstance(keys, list) or any(not isinstance(k, str) or not k for k in keys):
        die("proposal.keys 必须是非空 citation key 数组")
    if item.get("approved") is not True:
        die("引文计划未经用户批准: approved 必须为 true")
    evidence = item.get("evidence", [])
    if not isinstance(evidence, list) or {e.get("key") for e in evidence} != set(keys):
        die("每一个 citation key 必须有独立的 evidence 记录")
    for k in keys:
        if k not in known:
            die(f"BibTeX 中找不到 citation key: {k}")
        matches = [e for e in evidence if e.get("key") == k]
        if len(matches) != 1:
            die(f"evidence 必须恰好匹配一条: {k}")
        ev = matches[0]
        if ev.get("basis") not in ("abstract", "full_text") or ev.get("support") != "direct":
            die(f"引用 {k}: 证据必须为 abstract/full_text 且 support=direct")
        if not ev.get("locator") or len(ev.get("finding", "")) < 12:
            die(f"引用 {k}: 缺少证据定位或实质性结论")
        doi = known[k]["doi"]
        record = ledger.get("records", {}).get(doi, {})
        if not doi or record.get("status") != "metadata_verified" or record.get("key") != k:
            die(f"引用 {k}: 缺少与 citation key 匹配的 Crossref DOI 核验记录。先执行 verify/import")
        if ev.get("doi") and normalize_doi(ev["doi"]) != doi:
            die(f"引用 {k}: evidence DOI 与 BibTeX 不一致")


def cmd_insert(args):
    root = Path(args.root).resolve()
    known = {e["key"]: e for e in bib_entries(root / args.bib if not Path(args.bib).is_absolute() else args.bib)}
    ledger_path = root / args.ledger if not Path(args.ledger).is_absolute() else Path(args.ledger)
    plan_path = root / args.plan if not Path(args.plan).is_absolute() else Path(args.plan)
    ledger = read_json(ledger_path)
    payload = read_json(plan_path)
    proposals = payload.get("proposals", [])
    if not proposals:
        die("plan.json 中没有 proposals")
    staged = {}
    for item in proposals:
        check_proposal(item, known, ledger)
        file = safe_tex_path(root, item.get("file", ""))
        source = staged.get(file, read_preserve(file))
        anchor = item.get("anchor", "")
        if not isinstance(anchor, str) or len(anchor.strip()) < 12:
            die("anchor 必须是 >=12 字符的准确原文句子")
        masked = mask_tex(source)
        if masked.count(anchor) != 1:
            die(f"anchor 必须在有效正文中恰好出现 1 次: {file.name} / {anchor[:65]}")
        idx = masked.index(anchor)
        start, end = idx, idx + len(anchor)
        keys = item["keys"]
        cite = "\\" + item.get("cite_command", "cite") + "{" + ",".join(keys) + "}"
        if item.get("cite_command", "cite") not in {"cite", "citep", "citet", "parencite", "textcite", "autocite"}:
            die("仅允许白名单 citation command")
        placement = item.get("placement", "before_punctuation")
        if placement == "before_punctuation":
            m = re.search(r"([.!?。])([\s]*)$", anchor)
            if not m:
                die("before_punctuation 要求锚文本以句末标点结束")
            replacement = anchor[:m.start()] + " " + cite + anchor[m.start():]
        elif placement == "after_anchor":
            replacement = anchor + " " + cite
        else:
            die("placement 只支持 before_punctuation 或 after_anchor")
        staged[file] = source[:start] + replacement + source[end:]
    for file, new in staged.items():
        old = read_preserve(file)
        diff = difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile=str(file), tofile=str(file) + " (proposed)")
        print("".join(diff))
    if not args.apply:
        print("DRY RUN：未修改文件。检查证据和差异后添加 --apply。")
        return
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    for file, new in staged.items():
        backup = file.with_name(file.name + ".bak." + stamp)
        shutil.copy2(file, backup)
        atomic_write(file, new)
        print(f"已修改 {file}；备份 {backup}")


def build_parser():
    p = argparse.ArgumentParser(description="SCI bibliography tools; Python 3.10+ stdlib only")
    sub = p.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search", help="Crossref metadata discovery; not a content verification")
    search.add_argument("query"); search.add_argument("--limit", type=int, default=10)
    search.add_argument("--since", help="ISO date, e.g. 2021-01-01"); search.add_argument("--out"); search.set_defaults(func=cmd_search)
    imp = sub.add_parser("import", help="Get verified DOI metadata and append unique BibTeX entries")
    imp.add_argument("--doi", action="append", required=True); imp.add_argument("--bib", default="references.bib")
    imp.add_argument("--ledger", default="literature/doi-ledger.json"); imp.set_defaults(func=cmd_import)
    verify = sub.add_parser("verify", help="Verify existing BibTeX DOI/title/year against Crossref")
    verify.add_argument("--bib", default="references.bib"); verify.add_argument("--ledger", default="literature/doi-ledger.json")
    verify.add_argument("--out"); verify.add_argument("--key", action="append", help="Verify only selected bibliography keys")
    verify.set_defaults(func=cmd_verify)
    audit = sub.add_parser("audit", help="Offline checks for broken cite keys and duplicate BibTeX entries")
    audit.add_argument("--root", default="."); audit.add_argument("--bib", action="append", required=True)
    audit.add_argument("--out"); audit.set_defaults(func=cmd_audit)
    insert = sub.add_parser("insert", help="Evidence-gated, unique anchor, dry-run default")
    insert.add_argument("--root", default="."); insert.add_argument("--bib", default="references.bib")
    insert.add_argument("--ledger", default="literature/doi-ledger.json")
    insert.add_argument("--plan", required=True); insert.add_argument("--apply", action="store_true")
    insert.set_defaults(func=cmd_insert)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if getattr(args, "limit", 1) <= 0:
        die("limit 必须大于 0")
    try:
        outcome = args.func(args)
        return int(outcome or 0)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
