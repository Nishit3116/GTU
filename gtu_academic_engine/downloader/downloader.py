import logging
from pathlib import Path
import requests
from typing import Optional, Tuple
from ..config import config
from ..constants import DownloadError

logger = logging.getLogger(__name__)


class Downloader:
    """HTTP downloader with error categorization and retry support."""
    
    def __init__(self, download_dir: Path = None):
        self.download_dir = download_dir or config.downloads_dir
        self.download_dir.mkdir(parents=True, exist_ok=True)

    def download_to_bytes(self, url: str, timeout: int = None) -> Tuple[Optional[bytes], str]:
        """Download URL to bytes with error categorization.
        
        Args:
            url: URL to download
            timeout: Request timeout in seconds
            
        Returns:
            Tuple of (bytes or None, error_code string)
            - error_code: 404, 403, "timeout", "network_error", "invalid_pdf", or ""
        """
        timeout = timeout or config.timeout_seconds
        try:
            r = requests.get(url, timeout=timeout)
            logger.info("GET %s -> %s", url, r.status_code)
            
            # Categorize HTTP errors
            if r.status_code == 404:
                logger.debug("PDF not found (404): %s", url)
                return None, str(DownloadError.NOT_FOUND)
            
            if r.status_code == 403:
                logger.warning("Access forbidden (403): %s", url)
                return None, str(DownloadError.FORBIDDEN)
            
            if r.status_code != 200:
                logger.warning("HTTP error %d: %s", r.status_code, url)
                return None, DownloadError.UNKNOWN
            
            if not r.content:
                logger.warning("Empty response: %s", url)
                return None, DownloadError.UNKNOWN
            
            return r.content, ""  # Success
            
        except requests.Timeout:
            logger.error("Request timeout: %s", url)
            return None, DownloadError.TIMEOUT
        except requests.ConnectionError as e:
            logger.error("Network error: %s", e)
            return None, DownloadError.NETWORK_ERROR
        except requests.RequestException as exc:
            logger.error("Download failed %s: %s", url, exc)
            return None, DownloadError.UNKNOWN

    def download_to_bytes_legacy(self, url: str, timeout: int = None) -> Optional[bytes]:
        """Legacy method for backward compatibility.
        
        Returns bytes directly, ignoring error details.
        """
        data, _ = self.download_to_bytes(url, timeout)
        return data

    def save_bytes(self, data: bytes, path: Path) -> None:
        """Save bytes to file.
        
        Args:
            data: Bytes to write
            path: Destination file path
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fh:
            fh.write(data)
        logger.info("Saved %s (%d bytes)", path, len(data))
