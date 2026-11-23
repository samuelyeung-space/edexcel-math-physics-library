#!/usr/bin/env python3
"""Bulk-mirror PDF files already referenced in the user-maintained Edexcel catalogue.

Runs on GitHub Actions, stores PDF files as per-year GitHub Release assets,
and creates a browser-friendly direct PDF download index in this repository.
No mathematical/marking re-evaluation; only HTTP and PDF-byte checks.
"""
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "catalog" / "sources"
DEST = ROOT / "downloads"
DEST.mkdir(exist_ok=True)
REPO = os.environ.get("GITHUB_REPOSITORY", "samuelyeung-space/edexcel-math-physics-library")
FAMILIES = ["IAL-MATH", "IAL-PHYSICS", "UK-MATH", "UK-PHYSICS"]
MAX_BYTES = 35 * 1024 * 1024
BATCH_SIZE = 12

def command(*args, check=True):
    return subprocess.run(list(args), check=check, text=True, capture_output=True)

def filename(row):
    key = row["source_id"]
    key = re.sub(r"[^a-zA-Z0-9_.-]", "_", key)
    return key + ".pdf"

def year_from(row):
    m = re.search(r"20\d\d", row.get("title", ""))
    return int(m.group()) if m else None

def candidates():
    result = []
    for family in FAMILIES:
        j = json.loads((SOURCES / (family + ".json")).read_text(encoding="utf-8"))
        for row in j["rows"]:
            year = year_from(row)
            if year is None:
                continue
            result.append(dict(row, family=family, year=year))
            # The private 2026 Jan originals already exist, but these are
            # best-effort *public* URLs for additional downloadable full papers.
            if family in ("IAL-MATH", "IAL-PHYSICS") and year == 2025 and "1月" in row["title"] and "pmt.physicsandmathstutor.com" in row["source_url"]:
                u = row["source_url"].replace("2025", "2026")
                if u != row["source_url"]:
                    copy = dict(row, family=family, year=2026,
                                source_url=u,
                                source_id=row["source_id"].replace("2025", "2026"),
                                title=row["title"].replace("2025年", "2026年"))
                    result.append(copy)
    # One unique filename per family/year, prefer the first listed source.
    unique = {}
    for row in result:
        unique[(row["family"], row["year"], filename(row))] = row
    return list(unique.values())

def get_pdf(row, folder):
    name = filename(row)
    dest = folder / name
    last_error = "not tried"
    for attempt in range(2):
        try:
            req = urllib.request.Request(
                row["source_url"],
                headers={"User-Agent": "Mozilla/5.0 EdexcelArchive/1.0", "Accept": "application/pdf,*/*"})
            with urllib.request.urlopen(req, timeout=32) as rsp:
                data = rsp.read(MAX_BYTES + 1)
            if len(data) > MAX_BYTES:
                return {"row": row, "error": "over PDF size limit"}
            if not data.startswith(b"%PDF-"):
                return {"row": row, "error": "download did not return PDF"}
            dest.write_bytes(data)
            return {"row": row, "path": dest, "bytes": len(data)}
        except Exception as exc:
            last_error = str(exc)[:150]
            if attempt == 0:
                time.sleep(1)
    return {"row": row, "error": last_error}

def release_tag(family, year):
    return f"pdf-{family.lower()}-{year}"

def create_release(tag, family, year):
    v = command("gh", "release", "view", tag, "-R", REPO, check=False)
    if v.returncode == 0:
        return
    r = command("gh", "release", "create", tag, "-R", REPO,
                "--target", "main", "--title", f"Edexcel {family} {year} PDF past papers",
                "--notes", "Direct downloadable archived question papers and mark schemes collected from the user-maintained source index. Source and copyright remain with their respective owners.",
                check=False)
    if r.returncode:
        raise RuntimeError("Cannot create release " + tag + ": " + r.stderr[:500])

def upload(tag, files):
    good, errors = [], []
    for start in range(0, len(files), BATCH_SIZE):
        subset = files[start:start+BATCH_SIZE]
        paths = [str(x["path"]) for x in subset]
        r = command("gh", "release", "upload", tag, *paths, "--clobber", "-R", REPO, check=False)
        if r.returncode == 0:
            good += subset
            continue
        # Avoid one blocked asset losing a whole batch.
        for x in subset:
            v = command("gh", "release", "upload", tag, str(x["path"]), "--clobber", "-R", REPO, check=False)
            if v.returncode == 0:
                good.append(x)
            else:
                errors.append(dict(source_id=x["row"]["source_id"],
                                   error="release upload: " + v.stderr.strip()[:190]))
    return good, errors

def main():
    all_rows = candidates()
    groups = {}
    for row in all_rows:
        groups.setdefault((row["family"], row["year"]), []).append(row)
    order = sorted(groups, key=lambda p: (0 if p[1] == 2026 else 1, -p[1], FAMILIES.index(p[0])))
    uploaded = []
    failures = []
    for family, year in order:
        rows = groups[(family, year)]
        tag = release_tag(family, year)
        print(f"START {family} {year}: {len(rows)} registered sources -> {tag}", flush=True)
        with tempfile.TemporaryDirectory(prefix="edexcel-") as tmp:
            folder = Path(tmp)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                fetched = list(pool.map(lambda row: get_pdf(row, folder), rows))
            ready = [x for x in fetched if x.get("path")]
            failures.extend(dict(family=family, year=year, source_id=x["row"]["source_id"], error=x["error"])
                            for x in fetched if x.get("error"))
            if not ready:
                print(f"SKIPPED {tag} (no accessible PDF)", flush=True)
                continue
            try:
                create_release(tag, family, year)
                done, errors = upload(tag, ready)
            except Exception as exc:
                done = []
                errors = [dict(source_id="*", error=str(exc)[:350])]
            failures.extend(dict(family=family, year=year, **err) for err in errors)
            for x in done:
                row = x["row"]
                url = f"https://github.com/{REPO}/releases/download/{tag}/{filename(row)}"
                uploaded.append({"family": family, "year": year, "title": row["title"],
                                 "source_id": row["source_id"], "source_url": row["source_url"],
                                 "pdf_url": url, "bytes": x["bytes"]})
            print(f"DONE {tag}: uploaded {len(done)}/{len(rows)}, failures {len(errors)}", flush=True)
    obj = {"schema_version": 1, "repo": REPO, "generated": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "source_entries_attempted": len(all_rows), "pdf_assets_uploaded": len(uploaded),
           "pdf_files": uploaded, "failures": failures}
    (DEST / "index.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Edexcel 原题和 Mark Scheme PDF 直接下载", "",
             "这里的链接直接下载本 GitHub 仓库 Releases 内的 PDF，不是外部网站链接。",
             f"成功上传 **{len(uploaded)} 份 PDF**，未上传 {len(failures)} 条来源。", "",
             "## 直接下载", ""]
    for family in FAMILIES:
        items = [x for x in uploaded if x["family"] == family]
        if not items:
            continue
        lines += [f"### {family}（{len(items)} 份）", ""]
        for item in sorted(items, key=lambda x: (-x["year"], x["title"])):
            lines.append(f"- [{item['title']}]({item['pdf_url']})")
        lines.append("")
    lines += ["历史卷源登记存在重复。下载资源由原试卷和评分文件构成，不声称完成逐题审核。",
              "PDF 未找到、受限或上传失败项见 [下载状态 JSON](index.json)。"]
    (DEST / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"FINAL uploaded={len(uploaded)} failed={len(failures)}", flush=True)

if __name__ == "__main__":
    main()
