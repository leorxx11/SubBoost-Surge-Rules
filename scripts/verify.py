#!/usr/bin/env python3
"""Check generated files, HTTP delivery, and representative routing decisions."""

import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parent.parent


def load_rules(root, manifest):
    parsed = {}
    expected = {item["file"] for item in manifest["rules"]} | {"manifest.json"}
    actual = {path.name for path in (root / "rules").iterdir()}
    if expected != actual:
        raise ValueError("Generated file set differs from manifest")
    for item in manifest["rules"]:
        data = (root / "rules" / item["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError("Hash mismatch: " + item["file"])
        lines = [line for line in data.decode("utf-8").splitlines() if line and not line.startswith("#")]
        if len(lines) != item["entries"] or len(set(lines)) != len(lines):
            raise ValueError("Entry count or duplicates: " + item["file"])
        exact, suffixes, networks = set(), set(), []
        for line in lines:
            parts = line.split(",")
            if parts[0] in ("DOMAIN", "DOMAIN-SUFFIX") and len(parts) == 2:
                (exact if parts[0] == "DOMAIN" else suffixes).add(parts[1])
            elif parts[0] in ("IP-CIDR", "IP-CIDR6") and len(parts) == 3 and parts[2] == "no-resolve":
                network = ipaddress.ip_network(parts[1])
                if (network.version == 4) != (parts[0] == "IP-CIDR"):
                    raise ValueError("Wrong IP version: " + line)
                networks.append(network)
            else:
                raise ValueError("Invalid generated rule: " + line)
        parsed[item["file"]] = (exact, suffixes, networks)
    return parsed


def load_order(root, catalog, manifest):
    lines = [line for line in (root / "examples/rules.conf").read_text(encoding="utf-8").splitlines() if line and not line.startswith("#")]
    if lines[0] != "[Rule]" or lines[-1] != "FINAL," + catalog["final_policy"]:
        raise ValueError("Rule example must contain one final policy at the end")
    order = []
    policies = {group["id"]: group["policy"] for group in catalog["groups"]}
    by_file = {item["file"]: item for item in manifest["rules"]}
    for line in lines[1:-1]:
        kind, url, policy = line.split(",")
        name = urlsplit(url).path.rsplit("/", 1)[1]
        if kind != "RULE-SET" or url != catalog["publish_url"] + "/" + name:
            raise ValueError("Invalid rule reference: " + line)
        if policy != policies[by_file[name]["group"]]:
            raise ValueError("Wrong policy: " + line)
        order.append(name)
    if len(order) != len(set(order)) or set(order) != set(by_file):
        raise ValueError("Rule references are duplicated or incomplete")
    first_ip = next(index for index, name in enumerate(order) if name.endswith("-ip.list"))
    if any(not name.endswith("-ip.list") for name in order[first_ip:]):
        raise ValueError("A domain rule appears after the IP phase")
    domain_order = [group["id"] + ".list" for group in catalog["groups"] if any(source.startswith("geosite/") for source in group["sources"])]
    if order[:first_ip] != domain_order:
        raise ValueError("Domain order differs from catalogue")
    return order


def match(target, parsed, order):
    # This verifier independently reads the published rule syntax, rather than
    # importing the generator's conversion routines.
    try:
        address = ipaddress.ip_address(target)
    except ValueError:
        address = None
    labels = target.lower().split(".")
    parents = {".".join(labels[index:]) for index in range(len(labels))}
    for name in order:
        exact, suffixes, networks = parsed[name]
        if address is None:
            if target.lower() in exact or parents & suffixes:
                return name
        elif any(address.version == network.version and address in network for network in networks):
            return name
    return None


def verify(root, base_url=None):
    catalog = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))
    manifest = json.loads((root / "rules/manifest.json").read_text(encoding="utf-8"))
    parsed = load_rules(root, manifest)
    order = load_order(root, catalog, manifest)
    cases = json.loads((ROOT / "tests/routes.json").read_text(encoding="utf-8"))
    for case in cases:
        result = match(case["target"], parsed, order)
        if result != case["file"]:
            raise ValueError("{}: expected {}, got {}".format(case["target"], case["file"], result))
    if base_url:
        for name in list(parsed) + ["manifest.json"]:
            with urlopen(base_url.rstrip("/") + "/" + name, timeout=30) as response:
                delivered = response.read()
            if delivered != (root / "rules" / name).read_bytes():
                raise ValueError("HTTP content differs: " + name)
    return dict(rule_sets=len(parsed), entries=sum(item["entries"] for item in manifest["rules"]), routes=len(cases), http=bool(base_url))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Root containing generated artifacts")
    parser.add_argument("--base-url", help="Verify HTTP delivery from this rules URL")
    args = parser.parse_args()
    print(json.dumps(verify(args.root, args.base_url), ensure_ascii=False))


if __name__ == "__main__":
    main()
