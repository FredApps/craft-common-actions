import hashlib, json, os, pathlib, subprocess, tomllib
root = pathlib.Path(".")
original = pathlib.Path("sccache198-warm-manifest.txt").read_bytes()
current = pathlib.Path("Cargo.toml").read_bytes()
prefix = "validation198-20261113-"
def version(data):
    return prefix + hashlib.sha256(hashlib.sha256(data).digest()).hexdigest()
assert os.environ["SCCACHE_GHA_ENABLED"] == "true"
assert os.environ["SCCACHE_GHA_VERSION"] == version(current), "actual gate hashFiles differs"
print("Public cache namespace:", os.environ["SCCACHE_GHA_VERSION"], flush=True)
pathlib.Path("target").mkdir(exist_ok=True)
base = ["rustc", "--crate-name", "cfg_probe", "--crate-type", "lib", "--edition=2021", "--emit=dep-info,metadata,link", "src/lib.rs", "--out-dir", "target", "-Dunexpected_cfgs"]
known = tomllib.loads(current.decode())["lints"]["rust"]["unexpected_cfgs"]["check-cfg"]
flags = sum((["--check-cfg", item] for item in known), []) or ["--check-cfg", "cfg()"]
def run(cached, expected):
    result = subprocess.run((["sccache"] if cached else []) + base + flags, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(result.stdout, flush=True)
    assert (result.returncode == 0) == (expected == 0), result.returncode
    if expected: assert "unexpected" in result.stdout and "known" in result.stdout
def stats():
    out = subprocess.check_output(["sccache", "--show-stats", "--stats-format", "json"], text=True)
    print(out, flush=True)
    data = json.loads(out)["stats"]["cache_hits"]
    def total(obj):
        if isinstance(obj, dict): return sum(total(x) for x in obj.values())
        if isinstance(obj, int): return obj
        return 0
    return total(data)
if current == original:
    run(True, 0)
    run(True, 0)
    assert stats() >= 1, "No real GHA cache hit observed"
    print("WARM_GHA_PROOF_PASS", flush=True)
else:
    run(True, 1)
    run(False, 1)
    print("CHANGED_NAMESPACE_MATCHES_UNCACHED_PASS", flush=True)
    subprocess.run(["sccache", "--stop-server"], check=True)
    os.environ["SCCACHE_GHA_VERSION"] = version(original)
    flags = ["--check-cfg", "cfg()"]
    run(True, 0)
    assert stats() >= 1, "Old namespace did not retrieve warm GHA success"
    print("OLD_NAMESPACE_NEGATIVE_CONTROL_PASS", flush=True)