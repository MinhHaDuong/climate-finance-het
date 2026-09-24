# WARNING: AI-generated, not human-reviewed
"""Read the author's own Firefox profile: session cookies and download origins.

Two uses, both at the author's request and within the author's own access
(ticket 0926). A site that refuses the collector script but opens in the
author's browser is retried with that browser's cookies and a matching
User-Agent; and a document the author saved by hand is traced back to the
address it was downloaded from, as Firefox recorded it in ``places.sqlite``.

Firefox holds both databases open with a write-ahead log, so each is copied
with its ``-wal`` companion to a private temporary directory and read there,
never in place. No cookie value is ever logged or returned in a message: the
cookie jar goes straight into the HTTP session.
"""

import configparser
import http.cookiejar
import os
import shutil
import sqlite3
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse

DEFAULT_FIREFOX_ROOT = Path.home() / ".mozilla" / "firefox"
DOWNLOAD_DESTINATION = "downloads/destinationFileURI"


def default_profile(root: Path = DEFAULT_FIREFOX_ROOT) -> Path:
    """Return the profile ``profiles.ini`` marks as default.

    Falls back to the profile whose ``cookies.sqlite`` changed last when no
    entry is marked, which is the profile the author is using now.
    """
    ini = configparser.ConfigParser()
    ini.read(root / "profiles.ini")
    for section in ini.sections():
        entry = ini[section]
        if section.startswith("Profile") and entry.get("Default") == "1":
            path = Path(entry["Path"])
            return root / path if entry.get("IsRelative", "1") == "1" else path
    candidates = sorted(root.glob("*/cookies.sqlite"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"no Firefox profile with cookies under {root}")
    return candidates[-1].parent


def user_agent(profile: Path) -> str:
    """A Firefox User-Agent matching the version that last wrote the profile."""
    version = "128.0"
    ini = profile / "compatibility.ini"
    if ini.is_file():
        for line in ini.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("LastVersion="):
                parts = line.split("=", 1)[1].split("_", 1)[0].split(".")
                version = ".".join(parts[:2]) if len(parts) > 1 else parts[0] + ".0"
    return f"Mozilla/5.0 (X11; Linux x86_64; rv:{version}) Gecko/20100101 Firefox/{version}"


@contextmanager
def _database_copy(path: Path):
    """Yield a read-only connection to a private copy of a live Firefox database."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with tempfile.TemporaryDirectory(prefix="jetp-firefox-") as tmp:
        os.chmod(tmp, 0o700)
        copy = Path(tmp) / path.name
        shutil.copy2(path, copy)
        for suffix in ("-wal", "-shm"):
            companion = path.with_name(path.name + suffix)
            if companion.is_file():
                shutil.copy2(companion, copy.with_name(copy.name + suffix))
        connection = sqlite3.connect(copy)
        try:
            yield connection
        finally:
            connection.close()


def _host_matches(cookie_host: str, hosts: set[str]) -> bool:
    bare = cookie_host.lstrip(".").lower()
    return any(host == bare or host.endswith("." + bare) for host in hosts)


def load_cookies(profile: Path, hosts: set[str]) -> http.cookiejar.CookieJar:
    """Load the profile's cookies for the given hosts, and only those.

    Parameters
    ----------
    profile
        Firefox profile directory holding ``cookies.sqlite``.
    hosts
        Host names the retry will contact; a cookie is kept when its domain
        is one of them or a parent domain of one.

    Returns
    -------
    http.cookiejar.CookieJar
        The matching cookies, ready for ``requests.Session.cookies``.

    """
    wanted = {host.lower() for host in hosts}
    jar = http.cookiejar.CookieJar()
    with _database_copy(profile / "cookies.sqlite") as connection:
        rows = connection.execute(
            "SELECT host, name, value, path, expiry, isSecure FROM moz_cookies"
        ).fetchall()
    for host, name, value, path, expiry, secure in rows:
        if not _host_matches(host, wanted):
            continue
        # Firefox stores expiry in seconds on older profiles, milliseconds on
        # newer ones; http.cookiejar wants seconds.
        expires = int(expiry) // 1000 if expiry and int(expiry) > 10**11 else expiry
        jar.set_cookie(http.cookiejar.Cookie(
            version=0, name=name, value=value, port=None, port_specified=False,
            domain=host, domain_specified=host.startswith("."),
            domain_initial_dot=host.startswith("."), path=path or "/",
            path_specified=True, secure=bool(secure), expires=expires,
            discard=False, comment=None, comment_url=None, rest={},
        ))
    return jar


def downloads_dir() -> Path:
    """The desktop's download directory (``~/Téléchargements`` on padme)."""
    try:
        found = subprocess.run(["xdg-user-dir", "DOWNLOAD"], capture_output=True,
                               text=True, check=False, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        found = ""
    return Path(found) if found else Path.home() / "Downloads"


def download_origins(profile: Path) -> dict[Path, str]:
    """Map each downloaded file's path to the address Firefox fetched it from.

    Firefox records a download as an annotation on the source page's
    ``moz_places`` row: its ``content`` is the destination file URI.
    """
    with _database_copy(profile / "places.sqlite") as connection:
        rows = connection.execute(
            "SELECT p.url, a.content FROM moz_annos a "
            "JOIN moz_anno_attributes n ON n.id = a.anno_attribute_id "
            "JOIN moz_places p ON p.id = a.place_id WHERE n.name = ?",
            (DOWNLOAD_DESTINATION,),
        ).fetchall()
    origins = {}
    for url, destination in rows:
        parsed = urlparse(destination or "")
        if parsed.scheme != "file":
            continue
        origins[Path(unquote(parsed.path))] = url
    return origins
