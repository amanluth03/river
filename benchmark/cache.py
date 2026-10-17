"""Local copy of every EDGAR file we use, keyed by accession number, with a SHA-256 per file.

The hash is the chain of trust: a citation records the hash of the document it quotes,
and verification refuses a document whose bytes no longer match.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


class Cache:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.root / "manifest.json"
        self.manifest = json.loads(self.manifest_path.read_text()) if self.manifest_path.exists() else {}

    @staticmethod
    def _key(cik: str, accession: str, filename: str) -> str:
        return f"{int(cik)}/{accession.replace('-', '')}/{filename}"

    def path(self, cik: str, accession: str, filename: str) -> Path:
        return self.root / self._key(cik, accession, filename)

    def has(self, cik: str, accession: str, filename: str) -> bool:
        return self.path(cik, accession, filename).exists() and self._key(cik, accession, filename) in self.manifest

    def store(self, cik: str, accession: str, filename: str, content: bytes) -> str:
        target = self.path(cik, accession, filename)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        self.manifest[self._key(cik, accession, filename)] = {
            "sha256": digest,
            "bytes": len(content),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        self.manifest_path.write_text(json.dumps(self.manifest, indent=1, sort_keys=True))
        return digest

    def sha256(self, cik: str, accession: str, filename: str) -> str | None:
        entry = self.manifest.get(self._key(cik, accession, filename))
        return entry["sha256"] if entry else None

    def verify_hash(self, cik: str, accession: str, filename: str) -> bool:
        expected = self.sha256(cik, accession, filename)
        target = self.path(cik, accession, filename)
        if expected is None or not target.exists():
            return False
        return hashlib.sha256(target.read_bytes()).hexdigest() == expected
