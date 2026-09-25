"""The staged copies' index the observatory's pages read (ticket 0915).

The pages draw an archived link only for a copy ``documents/index.json``
lists, so the index must name exactly the files staged, in the registry's
``local_path`` form — a copy it misses loses its link, a copy it invents gets
a dead one.
"""

import json
import sys

import pytest
from jetp import build_documents_index
from jetp.build_documents_index import staged_objects

pytestmark = pytest.mark.wp_jetp

def stage(root):
    documents = root / "documents"
    (documents / "objects/aa").mkdir(parents=True)
    (documents / "objects/aa/aa11.pdf").write_bytes(b"%PDF-1.4\n")
    (documents / "objects/bb").mkdir()
    (documents / "objects/bb/bb22.html").write_text("<p>page</p>")
    return documents


def test_the_index_lists_each_staged_file_as_the_registry_names_it(tmp_path):
    documents = stage(tmp_path)
    (documents / "index.json").write_text("{}")  # never lists itself

    assert staged_objects(documents) == [
        "documents/objects/aa/aa11.pdf", "documents/objects/bb/bb22.html"]


def test_objects_reached_through_a_link_are_listed(tmp_path):
    # The no-reflink fallback links objects/ to the checkout.
    checkout = stage(tmp_path / "checkout")
    documents = tmp_path / "site/documents"
    documents.mkdir(parents=True)
    (documents / "objects").symlink_to(checkout / "objects")

    assert staged_objects(documents) == [
        "documents/objects/aa/aa11.pdf", "documents/objects/bb/bb22.html"]


def test_no_staged_copy_gives_an_empty_index(tmp_path):
    (tmp_path / "documents").mkdir()
    assert staged_objects(tmp_path / "documents") == []


def test_the_script_writes_the_index_beside_the_copies(tmp_path, monkeypatch):
    documents = stage(tmp_path)
    monkeypatch.setattr(sys, "argv", ["build_documents_index", "--documents", str(documents)])

    build_documents_index.main()

    assert json.loads((documents / "index.json").read_text())["objects"] == staged_objects(documents)


def test_a_linked_documents_directory_is_refused(tmp_path, monkeypatch):
    # An index written through the old whole-directory link would land in
    # data/jetp/documents, the DVC checkout.
    checkout = stage(tmp_path / "checkout")
    link = tmp_path / "documents"
    link.symlink_to(checkout)
    monkeypatch.setattr(sys, "argv", ["build_documents_index", "--documents", str(link)])

    with pytest.raises(SystemExit):
        build_documents_index.main()
    assert not (checkout / "index.json").exists()
