"""FEC API client shape (v0: NOT wired into the registry).

The registry runs without candidacy data; this module defines the ingestion
path for when live candidacies are wanted. Requires an api.data.gov key in
the FEC_API_KEY environment variable.
"""

from __future__ import annotations

import os
from typing import Iterator, Optional

import requests

FEC_API_BASE = "https://api.open.fec.gov/v1"


class FECClient:
    def __init__(self, api_key: Optional[str] = None,
                 session: Optional[requests.Session] = None):
        self.api_key = api_key or os.environ.get("FEC_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "FEC_API_KEY is not set; get a key at https://api.data.gov/signup/"
            )
        self.session = session or requests.Session()

    def _get(self, path: str, **params) -> dict:
        params.setdefault("api_key", self.api_key)
        resp = self.session.get(f"{FEC_API_BASE}{path}", params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    def candidates(self, state: str, office: str, cycle: int = 2026,
                   district: Optional[str] = None) -> Iterator[dict]:
        """Yield candidate records for one state/office/cycle.

        office: "S" (Senate) or "H" (House); district: two-digit string
        for House races (e.g. "05"), omitted for Senate.
        """
        page = 1
        while True:
            params = dict(state=state, office=office, cycle=cycle,
                          page=page, per_page=100, sort="name")
            if district is not None:
                params["district"] = district
            data = self._get("/candidates/", **params)
            yield from data.get("results", [])
            pagination = data.get("pagination", {})
            if page >= pagination.get("pages", 0):
                return
            page += 1
