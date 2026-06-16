"""GTU Paper Repository Client for searching and downloading PDFs.

This module provides HTTP client functionality for interfacing with GTU's 
paper repository service (Download1.aspx), including session bootstrap, 
PDF URL searching, and PDF download capabilities.
"""

from __future__ import annotations

import logging
import re
from html.parser import HTMLParser
from urllib.parse import urlparse

import requests

from ..config import GTUPYQConfig


class _GTUPageParser(HTMLParser):
    """HTML parser for extracting form inputs and PDF links from GTU pages.
    
    Extracts:
    - Form input names and values (for POST requests)
    - PDF download links (href attributes from anchor tags)
    """
    def __init__(self) -> None:
        super().__init__()
        self.inputs: dict[str, str] = {}
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = {name: value or "" for name, value in attrs}

        if tag == "input" and "name" in attributes:
            self.inputs[attributes["name"]] = attributes.get("value", "")

        if tag == "a" and "href" in attributes:
            self.links.append(attributes["href"])


class GTUPaperRepositoryClient:
    """HTTP client for GTU's paper repository service.
    
    Handles:
    - Session bootstrapping (cookie acquisition)
    - PDF URL searching via form submission
    - PDF download with proper referer headers
    
    The repository service returns PDF URLs matching the pattern:
    /uploads/{SESSION}/{COURSE}/{SUBJECT_CODE}.pdf
    """
    def __init__(self, config: GTUPYQConfig, logger: logging.Logger) -> None:
        """Initialize repository client with configuration and logger.
        
        Args:
            config: GTUPYQConfig with repository URLs and request settings
            logger: Logger instance for operation tracking
        """
        self._config = config
        self._logger = logger
        self._session = requests.Session()
        self._session.headers.update(config.request_headers)

    def close(self) -> None:
        """Close the HTTP session and release resources."""
        self._session.close()

    def bootstrap(self) -> None:
        """Bootstrap the session by visiting GTU main page to acquire cookies."""
        self._session.get(
            self._config.bootstrap_url,
            timeout=self._config.request_timeout,
            headers={"Referer": "https://gtu.ac.in/"},
        )

    def search_pdf_urls(self, subject_code: str, session_code: str) -> list[str]:
        """Search for PDF download URLs matching subject and session.
        
        Performs form submission to repository search with proper VIEWSTATE and 
        other ASP.NET form fields.
        
        Args:
            subject_code: GTU subject code (e.g., "3170719")
            session_code: Session code (e.g., "W2026")
            
        Returns:
            List of full PDF URLs matching the pattern 
            /uploads/{SESSION}/{COURSE}/{SUBJECT_CODE}.pdf.
            Returns empty list on network errors or parse failures.
        """
        page = self._session.get(
            self._config.repository_url,
            timeout=self._config.request_timeout,
            headers={"Referer": "https://gtu.ac.in/"},
        )

        if page.status_code != 200:
            self._logger.warning(
                "Repository page request failed for %s: HTTP %s",
                session_code,
                page.status_code,
            )
            return []

        parser = _GTUPageParser()
        parser.feed(page.text)

        payload = dict(parser.inputs)
        payload["ctl00$ContentPlaceHolder1$ddlsession"] = session_code
        payload["ctl00$ContentPlaceHolder1$drpextype"] = self._config.course_code
        payload["ctl00$ContentPlaceHolder1$txtsearch"] = subject_code
        payload["ctl00$ContentPlaceHolder1$btnsearch"] = "Search"

        response = self._session.post(
            self._config.repository_url,
            data=payload,
            timeout=self._config.request_timeout,
            headers={"Referer": self._config.repository_url},
        )

        if response.status_code != 200:
            self._logger.warning(
                "Repository search failed for %s/%s: HTTP %s",
                session_code,
                subject_code,
                response.status_code,
            )
            return []

        search_parser = _GTUPageParser()
        search_parser.feed(response.text)

        expected_suffix = f"/uploads/{session_code}/{self._config.course_code}/{subject_code}.pdf"
        exact_links: list[str] = []

        for href in search_parser.links:
            if not href.lower().endswith(".pdf"):
                continue

            parsed_href = urlparse(href)
            if parsed_href.path.endswith(expected_suffix):
                exact_links.append(href)

        return exact_links

    def download_bytes(self, pdf_url: str) -> bytes:
        """Download PDF bytes from a given URL with proper headers.
        
        Args:
            pdf_url: Full URL to the PDF file
            
        Returns:
            Raw PDF file bytes
            
        Raises:
            requests.HTTPError: If the HTTP response indicates an error
            requests.RequestException: If network error occurs
        """
        response = self._session.get(
            pdf_url,
            timeout=self._config.request_timeout,
            headers={"Referer": self._config.repository_url},
        )
        response.raise_for_status()
        return response.content
