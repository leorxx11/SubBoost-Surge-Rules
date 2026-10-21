from pathlib import Path
import tempfile
import unittest

from scripts.build import convert_source, make_artifacts, write_artifacts


class ConversionTests(unittest.TestCase):
    def test_exact_and_suffix_are_distinct_and_duplicates_are_removed(self):
        rules = convert_source("geosite/service.list", b"# comment\n\nexample.com\n+.example.com\nexample.com\n")
        self.assertEqual(rules, {"DOMAIN,example.com", "DOMAIN-SUFFIX,example.com"})

    def test_ip_versions_keep_no_resolve(self):
        rules = convert_source("geoip/service.list", b"91.108.4.0/22\n2001:b28:f23c::/47\n")
        self.assertEqual(rules, {
            "IP-CIDR,91.108.4.0/22,no-resolve",
            "IP-CIDR6,2001:b28:f23c::/47,no-resolve",
        })

    def test_unsupported_domain_does_not_silently_change_matching(self):
        for value in (b"*.example.com", b"DOMAIN,example.com", b"regexp:example.*"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                convert_source("geosite/service.list", value)

    def test_empty_source_fails_the_build(self):
        with self.assertRaises(ValueError):
            convert_source("geosite/service.list", b"# no rules\n")

    def test_invalid_network_is_rejected(self):
        with self.assertRaises(ValueError):
            convert_source("geoip/service.list", b"91.108.4.1/22")

    def test_merge_keeps_cross_group_overlaps_and_separates_ip_phase(self):
        catalog = {
            "upstream": {"repository": "example/rules", "branch": "meta", "directory": "geo"},
            "publish_url": "https://example.com/rules",
            "final_policy": "Proxy",
            "groups": [
                {"id": "private", "name": "Private", "policy": "DIRECT", "sources": ["geoip/private.list"]},
                {"id": "cn", "name": "CN", "policy": "DIRECT", "sources": ["geosite/cn.list", "geoip/cn.list"]},
                {"id": "video", "name": "Video", "policy": "Video", "sources": ["geosite/video.list", "geoip/video.list", "geosite/music.list"]},
                {"id": "parent", "name": "Parent", "policy": "Parent", "sources": ["geosite/parent.list"]},
            ],
        }
        sources = {
            "geoip/private.list": b"10.0.0.0/8",
            "geosite/cn.list": b"+.example.cn",
            "geoip/cn.list": b"1.0.1.0/24",
            "geosite/video.list": b"+.video.example.com\n+.shared.example.com",
            "geoip/video.list": b"192.0.2.0/24",
            "geosite/music.list": b"+.music.example.com\n+.shared.example.com",
            "geosite/parent.list": b"+.example.com\n+.shared.example.com",
        }
        artifacts = make_artifacts(catalog, "a" * 40, sources)
        self.assertEqual(artifacts["rules/video.list"].count("DOMAIN-SUFFIX,shared.example.com"), 1)
        self.assertIn("DOMAIN-SUFFIX,shared.example.com", artifacts["rules/parent.list"])
        refs = [line.split(",")[1].rsplit("/", 1)[1] for line in artifacts["examples/rules.conf"].splitlines() if line.startswith("RULE-SET,")]
        self.assertEqual(refs, ["cn.list", "video.list", "parent.list", "private-ip.list", "video-ip.list", "cn-ip.list"])
        self.assertNotIn("IP-CIDR", artifacts["rules/video.list"])
        self.assertNotIn("DOMAIN", artifacts["rules/video-ip.list"])
        with tempfile.TemporaryDirectory() as directory:
            write_artifacts(artifacts, Path(directory))
            first = {path: (Path(directory) / path).read_bytes() for path in artifacts}
            write_artifacts(make_artifacts(catalog, "a" * 40, dict(reversed(list(sources.items())))), Path(directory))
            self.assertEqual(first, {path: (Path(directory) / path).read_bytes() for path in artifacts})


if __name__ == "__main__":
    unittest.main()
