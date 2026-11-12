import pickle,glob,os,re,json,numpy as np
from collections import defaultdict
W="/scratch1/pbanga/rcwork_wide_causal/"
gops=json.load(open(W+"manifest.json"))["gops"]; gops=gops if isinstance(gops,list) else list(gops.values())
clip={g["id"]:g["clip"] for g in gops}
R=defaultdict(dict)
for p in glob.glob(W+"results_rl_lc/*/eval.pkl"):
    n=os.path.basename(os.path.dirname(p)); m=re.match(r"cql_ppo_k(\d+)_fixed_frac([\d.]+)_s(\d)",n)
    r=pickle.load(open(p,"rb")); d={}
    for key,v in r["res"].items():
        d[key[2]]=v
    R[(int(m[1]),float(m[2]))][int(m[3])]=(d,r["seconds"])
print("runs",sum(len(v) for v in R.values()))
sc=lambda v,f="score":float(np.mean([x[f] for x in v]))
for k in (0,5):
    print(f"k={k}: frac | train | val | test | test per seed | saving | over% | min")
    for fr in (0.125,0.25,0.5,1.0):
        s=R[(k,fr)]
        tr=[sc(d["train"]) for d,_ in s.values()];va=[sc(d["val"]) for d,_ in s.values()];te=[sc(d["test"]) for d,_ in s.values()]
        sv=[sc(d["test"],"saving") for d,_ in s.values()];ov=[100*np.mean([x["over"] for x in d["test"]]) for d,_ in s.values()]
        print(fr,round(np.mean(tr),2),round(np.mean(va),2),round(np.mean(te),2),[round(x,2) for x in te],round(np.mean(sv),2),round(np.mean(ov),1),round(np.mean([t for _,t in s.values()])/60))
# clip bootstrap, 100% minus 50% and 50 minus 12.5 on test (seed mean)
def tab(k,fr):
    s=R[(k,fr)]; t=defaultdict(list)
    for d,_ in s.values():
        for x in d["test"]: t[(x["gid"],x["budget"])].append(x["score"])
    return {a:np.mean(b) for a,b in t.items()}
def boot(a,b):
    A,B=tab(*a),tab(*b); ks=sorted(A); d=np.array([A[x]-B[x] for x in ks]); g=np.array([clip[x[0]] for x in ks])
    u,inv=np.unique(g,return_inverse=True); s=np.bincount(inv,d);c=np.bincount(inv)
    w=np.random.default_rng(0).multinomial(len(u),[1/len(u)]*len(u),4000); m=(w@s)/(w@c)
    return round(d.mean(),2),round(np.percentile(m,2.5),2),round(np.percentile(m,97.5),2),len(u)
for k in (0,5):
    for hi,lo in ((1.0,.5),(.5,.25),(1.0,.125)): print("k",k,hi,"-",lo,boot((k,hi),(k,lo)))
