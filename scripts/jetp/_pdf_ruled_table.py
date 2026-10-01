"""Ruled-table text layer for born-digital PDF registers (extraction section 5).

A spreadsheet printed to PDF draws its grid as filled rectangles; the rows of
the grid are the horizontal rules that run across the full width of the
table. This adapter reads, page by page, the words of the text layer (with
their positions) and those full-width rules, and cuts a page into *bands*,
the space between two consecutive rules. Which band is a record, a header or
a continuation, and which column a word belongs to, is the parser's business
(``build_zaf_grants_register.py``), never this adapter's.

One repair is made at the character level: a space glyph drawn over a
printing glyph (the padding of an accounting number format, ``$  1 62,000``
in the text layer for a printed ``$ 162,000``) is dropped. Nothing else of
the text is changed.
"""

from collections import defaultdict
from dataclasses import dataclass, field

import pdfplumber

ADAPTER = 'jetp-pdf-ruled-table'
VERSION = '1'
WORD_OPTIONS = {'x_tolerance': 1.5, 'y_tolerance': 2, 'keep_blank_chars': False}


@dataclass
class Word:
    text: str
    x0: float
    x1: float
    top: float
    bottom: float

    @property
    def middle(self):
        return (self.top + self.bottom) / 2


@dataclass
class Page:
    number: int                 # 1-based page index in the bytes
    width: float
    rules: list                 # y of the full-width rules, ascending
    words: list                 # Word, in reading order
    chars: list = field(default_factory=list)   # (text, x0, top, bottom), stream order

    def bands(self):
        return list(zip(self.rules, self.rules[1:]))

    def words_between(self, top, bottom):
        return [w for w in self.words if top < w.middle < bottom]


def _overprinted_space(char, printing):
    """A space glyph drawn mostly over a printing glyph of the same line."""
    if char['text'] != ' ':
        return False
    width = max(char['x1'] - char['x0'], 0.01)
    for other in printing:
        if abs(other['top'] - char['top']) < 1 and \
                min(other['x1'], char['x1']) - max(other['x0'], char['x0']) > width / 2:
            return True
    return False


def _full_width_rules(page):
    """y of every horizontal rule spanning the table's whole width."""
    horizontal = [e for e in page.edges if e['orientation'] == 'h']
    if not horizontal:
        return []
    left = min(e['x0'] for e in horizontal)
    right = max(e['x1'] for e in horizontal)
    if right - left < page.width * 0.5:
        return []
    spans = defaultdict(list)
    for edge in horizontal:
        spans[round(edge['top'])].append((edge['x0'], edge['x1']))
    found = []
    for y, pieces in spans.items():
        reach = None
        for start, end in sorted(pieces):
            if reach is None:
                if start > left + 2:
                    break
                reach = end
            elif start <= reach + 2:
                reach = max(reach, end)
            else:
                break
        if reach is not None and reach >= right - 2:
            found.append(y)
    merged = []
    for y in sorted(found):
        if not merged or y - merged[-1] > 2:
            merged.append(y)
    return merged


def read_page(page, number):
    chars = page.chars
    printing = [c for c in chars if c['text'] != ' ']
    kept = page.filter(lambda obj: obj.get('object_type') != 'char'
                       or not _overprinted_space(obj, printing))
    words = [Word(w['text'], w['x0'], w['x1'], w['top'], w['bottom'])
             for w in kept.extract_words(**WORD_OPTIONS)]
    stream = [(c['text'], c['x0'], c['top'], c['bottom']) for c in kept.chars]
    return Page(number, page.width, _full_width_rules(page), words, stream)


def read_pdf(path):
    """Every page of a PDF as a ``Page``; raises ``ValueError`` on unreadable bytes."""
    try:
        with pdfplumber.open(path) as pdf:
            return [read_page(page, number) for number, page in enumerate(pdf.pages, 1)]
    except Exception as exc:  # pdfminer raises a family of its own
        if isinstance(exc, ValueError):
            raise
        raise ValueError(f'unreadable PDF: {exc}') from exc


def cell_text(words):
    """Words of one cell joined in reading order: line by line, then left to right."""
    lines = []
    for word in sorted(words, key=lambda w: (w.top, w.x0)):
        if lines and abs(lines[-1][0] - word.top) < 2:
            lines[-1][1].append(word)
        else:
            lines.append([word.top, [word]])
    return ' '.join(' '.join(w.text for w in sorted(ws, key=lambda w: w.x0))
                    for _, ws in lines)
