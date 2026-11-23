#!/usr/bin/env python3
"""Copy directly downloadable January 2026 Edexcel maths papers to this repo's Releases."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import os
import subprocess
import tempfile
import urllib.request

REPO=os.environ.get("GITHUB_REPOSITORY", "samuelyeung-space/edexcel-math-physics-library")
TAG="pdf-ial-math-2026"
UNITS=["P1","P2","P3","P4","F1","F2","F3","M1","M2","M3","S1","S2","S3","D1"]
BASE="https://edemat.alevelclouds.com/"

def process(item, folder):
    u, variant, kind = item
    suffix = u + variant
    source = f"{BASE}26_01_{kind}_{suffix}.pdf"
    unit = "FP"+u[1:] if u.startswith("F") else u
    label = "01A" if variant else "01"
    name=f"Edexcel_IAL_2026_January_{unit}_{label}_{kind}.pdf"
    path=folder/name
    try:
        req=urllib.request.Request(source,headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req,timeout=40) as f:
            data=f.read(36*1024*1024)
        if not data.startswith(b"%PDF-"):
            return name,None,"Not a PDF"
        path.write_bytes(data)
        return name,path,None
    except Exception as e:
        return name,None,str(e)[:180]

def gh(*args):
    return subprocess.run(["gh",*args,"-R",REPO],text=True,capture_output=True)

def main():
    with tempfile.TemporaryDirectory(prefix="edexcel2026-") as d:
        folder=Path(d)
        todo=[(unit,variant,kind) for unit in UNITS for variant in ("","A") for kind in ("QP","MS")]
        with ThreadPoolExecutor(max_workers=10) as ex:
            rows=list(ex.map(lambda item:process(item,folder),todo))
        files=[x for _,x,e in rows if x is not None]
        failed=[(name,e) for name,path,e in rows if path is None]
        print(f"DOWNLOADED {len(files)} PDFs; errors {len(failed)}",flush=True)
        if not files:raise RuntimeError("No PDF source accessible")
        exists=gh("release","view",TAG)
        if exists.returncode!=0:
            c=gh("release","create",TAG,"--target","main","--title","Edexcel IAL Mathematics January 2026 QP and Mark Scheme PDFs","--notes","P1-P4, FP1-FP3, M1-M3, S1-S3, D1: 01 and 01A paper versions, original question paper and Mark Scheme PDF downloads.")
            if c.returncode:raise RuntimeError(c.stderr[:450])
        good=0
        for i in range(0,len(files),10):
            batch=files[i:i+10]
            r=gh("release","upload",TAG,*map(str,batch),"--clobber")
            if r.returncode==0: good+=len(batch)
            else:
                print("BATCH ERROR",r.stderr[:450],flush=True)
                for file in batch:
                    one=gh("release","upload",TAG,str(file),"--clobber")
                    if one.returncode==0:good+=1
                    else:failed.append((file.name,one.stderr[:100]))
        print(f"UPLOADED {good}/56 PDF files to https://github.com/{REPO}/releases/tag/{TAG}",flush=True)
        print("FAILURES",failed[:30],flush=True)
        if good<1:raise RuntimeError("No files uploaded")

if __name__=="__main__":
    main()
