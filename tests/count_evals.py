import json, os, glob

total_e, total_s, total_a = 0, 0, 0
for f in sorted(glob.glob("tests/eval_datasets/skills_*.json")):
    d = json.load(open(f))
    e = d["evals"]
    s = set(x["skill_name"] for x in e)
    a = sum(len(x.get("assertions", [])) for x in e)
    total_e += len(e)
    total_s += len(s)
    total_a += a
    print(f"  {os.path.basename(f)}: {len(e)} evals, {len(s)} skills, {a} assertions")
print(f"TOTAL: {total_e} evals, {total_s} skills, {total_a} assertions")
