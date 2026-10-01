"""Text layers and locators for the panel reference set (ticket 1895).

The panel reads a document from its text layer only (extraction § 5): a PDF
through ``pdftotext -layout``, one page per form feed; an HTML page through
the standard library parser, scripts and styles never run, as one page.
Markup that the page itself hides (the ``hidden`` attribute, an inline
``display:none``) is left out of the panel's declared scope; the layer
records that it did so.

A locator is derived by code from a member's verbatim quote, never written by
the member: the quote and the page text are normalised alike (Unicode NFKC,
whitespace runs joined into one space), the quote is found in the page, and
the locator gives the page, the character span in the normalised page and the
occurrence when the quote appears more than once. A quote that is not in the
page, or a label or field value that is not inside the quote, does not
resolve, and the row is dropped and counted.
"""

import hashlib
import re
import subprocess
import unicodedata
from dataclasses import dataclass
from html.parser import HTMLParser

ADAPTER_PDF = 'pdftotext -layout'
ADAPTER_HTML = 'html.parser (stdlib), scripts and hidden markup dropped'

_WS = re.compile(r'\s+')


def normalise(text):
    """NFKC and whitespace runs joined into one space, ends stripped."""
    return _WS.sub(' ', unicodedata.normalize('NFKC', text or '')).strip()


def tidy(text):
    """Layout text as shown to a member: lines kept, trailing blanks and blank runs cut."""
    lines = [line.rstrip() for line in unicodedata.normalize('NFKC', text).splitlines()]
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(lines)).strip('\n')


@dataclass(frozen=True)
class Layer:
    """A text layer: the pages as shown (``raw``), the adapter, the layer's hash.

    ``pages`` are the normalised pages that locators index into.
    """

    raw: tuple
    adapter: str

    @property
    def pages(self):
        return tuple(normalise(page) for page in self.raw)

    @property
    def sha256(self):
        digest = hashlib.sha256(self.adapter.encode())
        for page in self.raw:
            digest.update(b'\f' + page.encode())
        return digest.hexdigest()

    @property
    def chars(self):
        return sum(len(page) for page in self.raw)


def pdftotext_version():
    out = subprocess.run(['pdftotext', '-v'], capture_output=True, text=True)
    return (out.stderr or out.stdout).splitlines()[0].strip()


def pdf_layer(path):
    out = subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', str(path), '-'],
                         capture_output=True, check=True)
    pages = out.stdout.decode('utf-8', 'replace').split('\f')
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return Layer(tuple(tidy(page) for page in pages),
                 f'{ADAPTER_PDF} ({pdftotext_version()})')


_SKIP = {'script', 'style', 'noscript', 'template', 'svg', 'head', 'iframe'}
_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
         'meta', 'param', 'source', 'track', 'wbr'}
_HIDDEN_STYLE = re.compile(r'display\s*:\s*none', re.I)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in _VOID:
            if tag == 'br':
                self.parts.append('\n')
            return
        attrs = dict(attrs)
        hidden = ('hidden' in attrs
                  or _HIDDEN_STYLE.search(attrs.get('style') or '') is not None)
        self.stack.append((tag, tag in _SKIP or hidden))
        self.parts.append('\n')

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break
        self.parts.append('\n')

    def handle_data(self, data):
        if not any(skip for _, skip in self.stack):
            self.parts.append(data)


def html_text(markup):
    parser = _Text()
    parser.feed(markup)
    parser.close()
    return ''.join(parser.parts)


def html_layer(path):
    raw = open(path, 'rb').read().decode('utf-8', 'replace')
    text = '\n'.join(re.sub(r'[ \t\r\f\v]+', ' ', line).strip()
                     for line in html_text(raw).splitlines())
    return Layer((tidy(text),), ADAPTER_HTML)


def layer_of(path):
    """The text layer of a stored object, the format decided from the bytes."""
    head = open(path, 'rb').read(1024)
    if head.lstrip().startswith(b'%PDF'):
        return pdf_layer(path)
    return html_layer(path)


def parts(layer, max_chars):
    """Part plan on page boundaries: lists of 1-based page numbers.

    A page longer than ``max_chars`` is a part alone; the plan is the same for
    every member.
    """
    plan, current, size = [], [], 0
    for number, page in enumerate(layer.raw, start=1):
        if current and size + len(page) > max_chars:
            plan.append(current)
            current, size = [], 0
        current.append(number)
        size += len(page)
    if current:
        plan.append(current)
    return plan


@dataclass(frozen=True)
class Locator:
    page: int
    start: int
    end: int
    occurrence: int
    occurrences: int

    def __str__(self):
        text = f'page {self.page}; chars {self.start}-{self.end}'
        if self.occurrences > 1:
            text += f'; occurrence {self.occurrence} of {self.occurrences}'
        return text


def resolve(layer, page, quote, label='', values=()):
    """``(Locator, None)`` when the quote resolves, else ``(None, reason)``.

    The quote is searched on the page the member named, then on every page,
    so a wrong page number is corrected by code, not trusted.
    """
    needle = normalise(quote)
    if len(needle) < 3:
        return None, 'quote empty or too short'
    for value in (label, *values):
        value = normalise(value)
        if value and value not in needle:
            return None, f'value not inside the quote: {value[:60]!r}'
    normalised = layer.pages
    pages = [page] if isinstance(page, int) and 1 <= page <= len(normalised) else []
    pages += [n for n in range(1, len(normalised) + 1) if n not in pages]
    for number in pages:
        text = normalised[number - 1]
        starts = [m.start() for m in re.finditer(re.escape(needle), text)]
        if starts:
            return Locator(number, starts[0], starts[0] + len(needle),
                           1, len(starts)), None
    return None, 'quote not found in the text layer'
