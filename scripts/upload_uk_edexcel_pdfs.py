#!/usr/bin/env python3
"""Add UK Edexcel 9MA0, 9FM0 and 9PH0 official-paper PDF links as release assets."""
import concurrent.futures
import html
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
SOURCES = [
    ("UK-MATH", "9MA0", "https://revisionmaths.com/level-maths/level-maths-past-papers/edexcel-level-maths-past-papers"),
    ("UK-FURTHER-MATH", "9FM0", "https://revisionmaths.com/level-maths/level-maths-past-papers/edexcel-level-further-maths-past-papers"),
    ("UK-PHYSICS", "9PH0", "https://revisionscience.com/a2-level-level-revision/physics-level-revision/physics-level-past-papers/edexcel-level-physics-past-papers"),
]

def gh(*args):
    return subprocess.run(["gh", *args, "-R", REPO], capture_output=True, text=True)

def get_page(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=40) as response:
        return response.read().decode("utf-8", "replace")

def source_list():
    items = []
    for family, spec, url in SOURCES:
        html_text = get_page(url)
        year, active = None, False
        found = {}
        for part in re.split(r"</p>", html_text, flags=re.I):
            plain = html.unescape(re.sub(r"<[^>]*>", " ", part))
            m = re.search(r"(?:June|November)\s+(20\d\d)", plain)
            if m and (
                (family == "UK-PHYSICS" and "Physics A-Level Pearson Edexcel Past Papers" in plain)
                or (family == "UK-MATH" and "A-Level Maths Past Papers (9MA0)" in plain)
                or (family == "UK-FURTHER-MATH" and "A-Level Further Maths Past Papers (9FM0)" in plain)
            ):
                year = int(m[1]); active = True
            elif m and ("AS-Level" in plain or (family != "UK-PHYSICS" and "A-Level" in plain and "Past Papers" in plain and spec not in plain)):
                active = False
            if not active or year not in range(2021, 2026):
                continue
            if "A-Level Paper" not in plain and "A-Level Physics: Paper" not in plain:
                continue
            if family == "UK-PHYSICS":
                code_match = re.search(r"A-Level Physics:\s*Paper\s*(\d)", plain)
            else:
                code_match = re.search(spec + r"[/-]([0-9A-Z]+)", plain)
            hrefs = re.findall(r'href=["\']([^"\']+)["\']', part)
            if code_match and len(hrefs) >= 2:
                code = code_match[1].zfill(2) if family == "UK-PHYSICS" else code_match[1]
                found[(year, code)] = [urllib.parse.urljoin(url, hrefs[0]), urllib.parse.urljoin(url, hrefs[1])]
        for (year, code), pdf_urls in found.items():
            for kind, pdf_url in zip(("QP", "MS"), pdf_urls):
                items.append({"family": family, "year": year, "code": spec+"-"+code,
                              "kind": kind, "url": pdf_url, "release": f"pdf-uk-{'physics' if family=='UK-PHYSICS' else 'math'}-{year}"})
        print("SOURCE LINKS", family, len(found)*2, flush=True)
    return items

def download(item, folder):
    name = f"Edexcel_{item['code']}_{item['year']}_{item['kind']}.pdf"
    dest = folder / name
    try:
        req = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=50) as response:
            data = response.read(35*1024*1024)
        if not data.startswith(b"%PDF-"):
            return None
        dest.write_bytes(data)
        return item, dest
    except Exception as exc:
        print("UNAVAILABLE", name, str(exc)[:160], flush=True)
        return None

def main():
    sources=source_list()
    groups={}
    for x in sources:
        groups.setdefault(x["release"], []).append(x)
    uploaded=0
    for release, tasks in sorted(groups.items()):
        with tempfile.TemporaryDirectory(prefix="edexcel-uk-") as directory:
            folder=Path(directory)
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                files=[x for x in pool.map(lambda t:download(t, folder), tasks) if x]
            if not files:
                continue
            if gh("release","view",release).returncode:
                x=gh("release","create",release,"--target","main","--title",f"UK Edexcel past papers {release}","--notes","A-level Edexcel examination question papers and mark schemes, PDF direct downloads.")
                if x.returncode:raise RuntimeError(x.stderr[:300])
            succeeded=0
            for i in range(0,len(files),10):
                sub=files[i:i+10]
                x=gh("release","upload",release,*[str(item[1]) for item in sub],"--clobber")
                if x.returncode==0:succeeded+=len(sub)
                else:
                    for item,path in sub:
                        y=gh("release","upload",release,str(path),"--clobber")
                        if y.returncode==0:succeeded+=1
                        else:print("UPLOAD_FAIL",path.name,y.stderr[:160],flush=True)
            print("RELEASE",release,"uploaded",succeeded,"of",len(tasks),flush=True)
            uploaded+=succeeded
    print("UK TOTAL ADDED",uploaded,flush=True)

if __name__=="__main__":
    main()
