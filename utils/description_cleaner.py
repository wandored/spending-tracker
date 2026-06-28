import yaml
import re


class DescriptionCleaner:
    def __init__(self, config_path: str):

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        self.prefixes = [
            p.lower().strip() for p in config.get("cleanup", {}).get("prefixes", [])
        ]

        self.merchants = config.get("cleanup", {}).get("normalize", {})

    def clean(self, description: str) -> str:

        if not description:
            return ""

        description = description.strip()

        # -------------------------
        # 1. Remove prefixes
        # -------------------------
        description = self._remove_prefix(description)

        # -------------------------
        # 2. Normalize merchant
        # -------------------------
        description = self._normalize_merchant(description)

        return description.strip()

    def _remove_prefix(self, description: str) -> str:

        lower = description.lower()

        for prefix in self.prefixes:
            prefix = prefix.lower().strip()

            if prefix in lower:
                # remove first occurrence of prefix
                idx = lower.find(prefix)

                before = description[:idx].strip()
                after = description[idx + len(prefix) :].strip()

                # rebuild clean string
                cleaned = f"{before} {after}".strip()

                # collapse double spaces
                cleaned = " ".join(cleaned.split())

                return cleaned

        return description

    def _normalize_merchant(self, description: str) -> str:

        lower = description.lower()

        for entry in self.merchants:
            canonical = entry["name"]
            for variant in entry["match"]:
                if variant in lower:
                    return canonical

        return description
