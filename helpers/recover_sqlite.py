import sqlite3
import subprocess
import sys
import os
from pathlib import Path
import argparse


def parse_args():
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent  # assumes this script lives in core/
    default_src = repo_root / "db_files" / "metrics.db"
    default_out_dir = repo_root / "db_files"

    p = argparse.ArgumentParser(description="Recover/clone a potentially corrupt SQLite database.")
    p.add_argument("--src", type=Path, default=default_src,
                   help="Path to source .db (default: repo_root/db_files/metrics.db)")
    p.add_argument("--out-dir", type=Path, default=default_out_dir,
                   help="Directory to write outputs (default: repo_root/db_files)")
    p.add_argument("--base-name", default="metrics", help="Base name for output files (default: metrics)")
    return p.parse_args()


def quick_check(path: Path) -> bool:
    try:
        con = sqlite3.connect(str(path))
        cur = con.execute("PRAGMA quick_check;")
        res = cur.fetchone()
        con.close()
        return bool(res) and res[0] == "ok"
    except Exception:
        return False


def try_backup(src: Path, dst: Path) -> bool:
    try:
        if dst.exists():
            dst.unlink()
        src_con = sqlite3.connect(str(src))
        dst_con = sqlite3.connect(str(dst))
        src_con.backup(dst_con)
        dst_con.close()
        src_con.close()
        print(f"[info] Backup clone written: {dst}")
        return True
    except Exception as e:
        print(f"[warn] backup failed: {e}")
        return False


def try_dump(src: Path, dump_path: Path) -> bool:
    try:
        con = sqlite3.connect(str(src))
        with open(dump_path, "w", encoding="utf-8") as f:
            for line in con.iterdump():
                f.write(f"{line}\n")
        con.close()
        print(f"[info] SQL dump written: {dump_path}")
        return True
    except Exception as e:
        print(f"[warn] iterdump failed: {e}")
        return False


def try_cli_recover(src: Path, dst: Path) -> bool:
    try:
        if dst.exists():
            dst.unlink()
        p1 = subprocess.Popen(["sqlite3", str(src), ".recover"], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["sqlite3", str(dst)], stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p1.stdout.close()
        out, err = p2.communicate()
        if p2.returncode == 0:
            print(f"[info] CLI .recover wrote: {dst}")
            if not quick_check(dst):
                print("[warn] recovered.db quick_check is not ok")
            return True
        else:
            print(f"[warn] .recover failed: {err.decode('utf-8', errors='ignore')}")
            return False
    except FileNotFoundError:
        print("[warn] sqlite3 CLI not found; cannot run .recover")
        return False
    except Exception as e:
        print(f"[warn] .recover exception: {e}")
        return False


def main():
    args = parse_args()
    src: Path = args.src
    out_dir: Path = args.out_dir
    base = args.base_name

    out_dir.mkdir(parents=True, exist_ok=True)

    clone = out_dir / f"{base}_clone.db"
    dump = out_dir / f"{base}_recovered.sql"
    recovered = out_dir / "recovered.db"

    print(f"[info] CWD: {Path.cwd()}")
    print(f"[info] Using source DB: {src}")
    print(f"[info] Outputs will be written to: {out_dir}")

    if not src.exists():
        print(f"[error] source db not found: {src}")
        sys.exit(1)

    print("[step] Attempting backup clone …")
    if try_backup(src, clone):
        ok = quick_check(clone)
        print(f"[info] quick_check({clone}) = {'ok' if ok else 'NOT OK'}")
        if ok:
            print(f"[next] Use {clone} as your working database.")
            sys.exit(0)
        else:
            print("[info] clone exists but integrity not ok; proceeding to dump")

    print("[step] Attempting SQL dump …")
    dumped = try_dump(src, dump)
    if dumped:
        print(f"[next] You can load the dump into a fresh DB:\n"
              f"       sqlite3 {recovered} \".read {dump}\"\n"
              f"       sqlite3 {recovered} \"PRAGMA quick_check;\"")
    else:
        print("[info] Dump failed; proceeding to CLI .recover")

    print("[step] Attempting CLI .recover …")
    recovered_ok = try_cli_recover(src, recovered)
    if recovered_ok:
        ok = quick_check(recovered)
        print(f"[info] quick_check({recovered}) = {'ok' if ok else 'NOT OK'}")
        if ok:
            print(f"[next] Use {recovered} as your working database.")
            sys.exit(0)

    if dumped:
        print("[fallback] Dump succeeded. Load it into a new DB as shown above and inspect the schema/data.")
        sys.exit(0)

    print("[fatal] All recovery attempts failed. Consider restoring from backup.")
    sys.exit(2)


if __name__ == "__main__":
    main()
