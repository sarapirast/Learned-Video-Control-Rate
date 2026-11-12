"""Shared machinery for experiment scripts: CLI flags, job-array sharding, process pools, per-stage .pkl caches.

Stage caches live in $RC_WORK/results_<name>[_quick]/<stage>[.<shard>of<n>].pkl. A finished stage is never recomputed;
delete its .pkl to redo it. A sharded stage is merged by `gather` once every shard file exists.
"""
import argparse
import glob
import multiprocessing as mp
import os
import pickle
import sys
import time
import traceback

from . import config as C


def args(extra=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="tiny version of every stage, separate results dir")
    ap.add_argument("--report", action="store_true", help="only write the report from cached results")
    ap.add_argument("--stage", default=None, help="run only this stage (default: all)")
    ap.add_argument("--shard", default=os.environ.get("SLURM_ARRAY_TASK_ID"), type=lambda s: None if s is None else int(s))
    ap.add_argument("--nshards", default=int(os.environ.get("RC_NSHARDS", 1)), type=int)
    if extra:
        extra(ap)
    a = ap.parse_args()
    if a.shard is None:
        a.shard = 0
    return a


class Stages:
    def __init__(self, name, quick=False):
        self.name = name + ("_quick" if quick else "")
        self.dir = C.results_dir(self.name)
        self.quick = quick

    def path(self, stage, shard=None, nshards=1):
        suf = f".{shard}of{nshards}" if nshards > 1 and shard is not None else ""
        return os.path.join(self.dir, f"{stage}{suf}.pkl")

    def done(self, stage, shard=None, nshards=1):
        return os.path.exists(self.path(stage, shard, nshards))

    def load(self, stage, shard=None, nshards=1):
        with open(self.path(stage, shard, nshards), "rb") as f:
            return pickle.load(f)

    def save(self, stage, obj, shard=None, nshards=1):
        p = self.path(stage, shard, nshards)
        tmp = f"{p}.{os.getpid()}.part"
        with open(tmp, "wb") as f:
            pickle.dump(obj, f, protocol=pickle.HIGHEST_PROTOCOL)
        os.replace(tmp, p)

    def run(self, stage, fn, shard=None, nshards=1):
        """Run fn() unless cached; returns its result."""
        if self.done(stage, shard, nshards):
            log(f"[{stage}] cached")
            return self.load(stage, shard, nshards)
        t = time.time()
        log(f"STAGE {stage} {'' if nshards == 1 else f'shard {shard}/{nshards}'} ...")
        out = fn()
        self.save(stage, out, shard, nshards)
        log(f"  [{stage}] {time.time() - t:.0f}s")
        return out

    def gather(self, stage, nshards, merge=None):
        """Merge shard results (dicts are updated, lists concatenated) into the unsharded stage file."""
        if self.done(stage):
            return self.load(stage)
        parts = [self.path(stage, i, nshards) for i in range(nshards)]
        missing = [p for p in parts if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(f"{len(missing)} of {nshards} shards missing for {stage}, e.g. {missing[0]}")
        objs = []
        for p in parts:
            with open(p, "rb") as f:
                objs.append(pickle.load(f))
        if merge:
            out = merge(objs)
        elif isinstance(objs[0], dict):
            out = {}
            for o in objs:
                out.update(o)
        else:
            out = [x for o in objs for x in o]
        self.save(stage, out)
        return out

    def shards_done(self, stage):
        return sorted(glob.glob(os.path.join(self.dir, f"{stage}.*of*.pkl")))


def log(msg):
    print(f"  {time.strftime('%H:%M:%S')} {msg}", flush=True)


def _safe(args):
    fn, x = args
    try:
        return fn(x)
    except Exception:  # noqa: BLE001
        return {"__error__": traceback.format_exc(), "__item__": repr(x)[:200]}


def pmap(fn, items, workers=None, desc="", every=None):
    """Parallel map with progress lines; a failing item is reported and re-raised at the end (others finish)."""
    workers = workers or C.WORKERS
    items = list(items)
    n = len(items)
    out = [None] * n
    t0 = time.time()
    every = every or max(1, n // 20)
    ctx = mp.get_context("forkserver" if sys.platform.startswith("linux") else "spawn")
    errors = []
    if workers <= 1 or n <= 1:
        it = map(_safe, [(fn, x) for x in items])
        indexed = enumerate(it)
    else:
        pool = ctx.Pool(workers, maxtasksperchild=200)
        indexed = pool.imap_unordered(_indexed, [(i, fn, x) for i, x in enumerate(items)], chunksize=1)
    done = 0
    for i, r in indexed:
        if isinstance(r, dict) and "__error__" in r:
            errors.append(r)
            log(f"ERROR in {desc} item {r['__item__']}:\n{r['__error__']}")
        out[i] = r
        done += 1
        if done % every == 0 or done == n:
            el = time.time() - t0
            log(f"{desc} {done}/{n}  {el:.0f}s elapsed, ~{el / done * (n - done):.0f}s left")
    if workers > 1 and n > 1:
        pool.close()
        pool.join()
    if errors:
        raise RuntimeError(f"{len(errors)} of {n} items failed in {desc}; first: {errors[0]['__error__'][-800:]}")
    return out


def _indexed(a):
    i, fn, x = a
    return i, _safe((fn, x))
