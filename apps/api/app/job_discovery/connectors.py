from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from html.parser import HTMLParser
from typing import Optional
from urllib.parse import urlparse

import httpx

from .schemas import DiscoveredJob


class JobDiscoveryBlockedError(RuntimeError):
    pass


class BaseJobConnector(ABC):
    source_name: str

    @abstractmethod
    def discover(
        self,
        *,
        source_url: str,
        target_roles: list[str],
        client: httpx.Client,
    ) -> list[DiscoveredJob]:
        raise NotImplementedError

    def _role_matches(self, target_roles: list[str], title: str, description: str) -> bool:
        if not target_roles:
            return True
        haystack = f"{title}\n{description}".lower()
        return any(role.lower() in haystack for role in target_roles)

    def _stable_hash(
        self,
        *,
        source: str,
        title: str,
        company: str,
        location: Optional[str],
        apply_url: Optional[str],
        source_job_id: Optional[str],
    ) -> str:
        raw = source_job_id or apply_url or f"{source}:{title}:{company}:{location or ''}"
        normalized = re.sub(r"\s+", " ", raw.strip().lower())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def _blocked(self, response: httpx.Response, source_url: str) -> None:
        if response.status_code in {401, 403, 429}:
            raise JobDiscoveryBlockedError(
                f"Access blocked for {source_url} with HTTP {response.status_code}."
            )


class GreenhouseConnector(BaseJobConnector):
    source_name = "greenhouse"

    def discover(
        self,
        *,
        source_url: str,
        target_roles: list[str],
        client: httpx.Client,
    ) -> list[DiscoveredJob]:
        response = client.get(source_url)
        self._blocked(response, source_url)
        response.raise_for_status()
        payload = response.json()
        jobs = payload.get("jobs", [])
        discovered: list[DiscoveredJob] = []

        for item in jobs:
            title = str(item.get("title", "")).strip()
            description = str(item.get("content", "")).strip()
            company = str(payload.get("company_name") or payload.get("name") or "Unknown Company")
            location = None
            if isinstance(item.get("location"), dict):
                location = item["location"].get("name")
            elif item.get("location"):
                location = str(item["location"])
            apply_url = item.get("absolute_url")
            source_job_id = str(item.get("id")) if item.get("id") is not None else None
            if not self._role_matches(target_roles, title, description):
                continue
            discovered.append(
                DiscoveredJob(
                    source=self.source_name,
                    source_job_id=source_job_id,
                    stable_hash=self._stable_hash(
                        source=self.source_name,
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        source_job_id=source_job_id,
                    ),
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    apply_url=apply_url,
                )
            )

        return discovered


class LeverConnector(BaseJobConnector):
    source_name = "lever"

    def discover(
        self,
        *,
        source_url: str,
        target_roles: list[str],
        client: httpx.Client,
    ) -> list[DiscoveredJob]:
        response = client.get(source_url)
        self._blocked(response, source_url)
        response.raise_for_status()
        payload = response.json()
        items = payload if isinstance(payload, list) else payload.get("jobs", [])
        discovered: list[DiscoveredJob] = []

        for item in items:
            title = str(item.get("text") or item.get("title") or "").strip()
            description = str(item.get("descriptionPlain") or item.get("description") or "").strip()
            company = str(
                item.get("categories", {}).get("team") or item.get("company") or "Unknown Company"
            )
            location = (
                str(
                    item.get("categories", {}).get("location") or item.get("location") or ""
                ).strip()
                or None
            )
            apply_url = item.get("hostedUrl") or item.get("applyUrl") or item.get("url")
            source_job_id = str(item.get("id") or item.get("req_id") or item.get("hostedUrl") or "")
            if not self._role_matches(target_roles, title, description):
                continue
            discovered.append(
                DiscoveredJob(
                    source=self.source_name,
                    source_job_id=source_job_id or None,
                    stable_hash=self._stable_hash(
                        source=self.source_name,
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        source_job_id=source_job_id or None,
                    ),
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    apply_url=apply_url,
                )
            )

        return discovered


class AshbyConnector(BaseJobConnector):
    source_name = "ashby"

    def discover(
        self,
        *,
        source_url: str,
        target_roles: list[str],
        client: httpx.Client,
    ) -> list[DiscoveredJob]:
        response = client.get(source_url)
        self._blocked(response, source_url)
        response.raise_for_status()
        payload = response.json()
        jobs = payload if isinstance(payload, list) else payload.get("jobs", [])
        discovered: list[DiscoveredJob] = []

        for item in jobs:
            title = str(item.get("title") or item.get("jobTitle") or "").strip()
            description = str(item.get("descriptionHtml") or item.get("description") or "").strip()
            company = str(
                item.get("companyName") or payload.get("companyName") or "Unknown Company"
            )
            location = str(item.get("location") or item.get("locationName") or "").strip() or None
            apply_url = item.get("absoluteUrl") or item.get("applyUrl") or item.get("url")
            source_job_id = str(item.get("id") or item.get("jobId") or apply_url or "")
            if not self._role_matches(target_roles, title, description):
                continue
            discovered.append(
                DiscoveredJob(
                    source=self.source_name,
                    source_job_id=source_job_id or None,
                    stable_hash=self._stable_hash(
                        source=self.source_name,
                        title=title,
                        company=company,
                        location=location,
                        apply_url=apply_url,
                        source_job_id=source_job_id or None,
                    ),
                    title=title,
                    company=company,
                    location=location,
                    description=description,
                    apply_url=apply_url,
                )
            )

        return discovered


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        data = data.strip()
        if data:
            self.parts.append(data)


class GenericCareerPageConnector(BaseJobConnector):
    source_name = "generic"

    def discover(
        self,
        *,
        source_url: str,
        target_roles: list[str],
        client: httpx.Client,
    ) -> list[DiscoveredJob]:
        response = client.get(source_url)
        self._blocked(response, source_url)
        response.raise_for_status()
        html = response.text
        if not html.strip():
            return []

        extractor = _TextExtractor()
        extractor.feed(html)
        title = self._extract_title(html) or self._extract_from_text(extractor.parts)
        description = self._extract_meta_description(html) or "\n".join(extractor.parts)
        company = self._extract_company(html) or urlparse(source_url).hostname or "Unknown Company"
        location = self._extract_location(html)
        apply_url = source_url
        if not self._role_matches(target_roles, title, description):
            return []

        return [
            DiscoveredJob(
                source=self.source_name,
                source_job_id=None,
                stable_hash=self._stable_hash(
                    source=self.source_name,
                    title=title,
                    company=company,
                    location=location,
                    apply_url=apply_url,
                    source_job_id=None,
                ),
                title=title,
                company=company,
                location=location,
                description=description,
                apply_url=apply_url,
            )
        ]

    def _extract_title(self, html: str) -> str:
        match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        return self._clean(match.group(1)) if match else ""

    def _extract_meta_description(self, html: str) -> str:
        match = re.search(
            r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return self._clean(match.group(1)) if match else ""

    def _extract_company(self, html: str) -> str:
        match = re.search(
            r'<meta\s+property=["\']og:site_name["\']\s+content=["\'](.*?)["\']',
            html,
            re.IGNORECASE | re.DOTALL,
        )
        return self._clean(match.group(1)) if match else ""

    def _extract_location(self, html: str) -> Optional[str]:
        match = re.search(r"(?:location|remote|hybrid)[^<>{}]{0,40}", html, re.IGNORECASE)
        if match:
            cleaned = self._clean(match.group(0))
            return cleaned or None
        return None

    def _extract_from_text(self, parts: list[str]) -> str:
        return self._clean(" ".join(parts[:20]))

    def _clean(self, text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()
