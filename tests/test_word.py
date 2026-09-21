from io import BytesIO
from zipfile import ZipFile

import pytest

docx = pytest.importorskip("docx")

from chemistry_renderer import (
    DocumentOptions, MoleculeEntry, MoleculeError, RenderOptions,
    parse_molecule_lines, to_docx, to_png,
)


def test_parse_lines_preserves_order_and_optional_names():
    assert parse_molecule_lines("Ethanol | CCO\n\n C#N \n | O") == [
        MoleculeEntry("Ethanol", "CCO"), MoleculeEntry("", "C#N"), MoleculeEntry("", "O")]


@pytest.mark.parametrize("text", ["", "  \n", "name |", "name | CCO | extra", "C\n" * 101])
def test_bad_list(text):
    with pytest.raises(ValueError):
        parse_molecule_lines(text)


def test_docx_contains_ordered_captions_and_embedded_images():
    entries = parse_molecule_lines("Ethanol | CCO\nPropaan-2-ol | CC(O)C")
    data = to_docx(entries, document_options=DocumentOptions(numbered=True))
    document = docx.Document(BytesIO(data))
    assert [p.text for p in document.paragraphs if p.text] == [
        "Structuurformules", "1. Ethanol", "2. Propaan-2-ol"]
    assert len(document.inline_shapes) == 2
    captions = [p for p in document.paragraphs if p.text.startswith(("1.", "2."))]
    assert all(p.paragraph_format.keep_with_next for p in captions)
    with ZipFile(BytesIO(data)) as archive:
        images = [name for name in archive.namelist() if name.startswith("word/media/")]
        assert len(images) == 2
        assert all(archive.read(name).startswith(b"\x89PNG") for name in images)


def test_optional_title_and_names_are_omitted():
    data = to_docx([MoleculeEntry("Secret answer", "CCO")],
                   document_options=DocumentOptions(title="", include_names=False))
    document = docx.Document(BytesIO(data))
    assert not any(p.text for p in document.paragraphs)
    assert len(document.inline_shapes) == 1
    assert "Secret answer" not in data.decode("latin1")


def test_common_scale_preserves_relative_size_and_fits_page():
    entries = [MoleculeEntry("small", "CCO"), MoleculeEntry("long", "C" * 25)]
    natural = docx.Document(BytesIO(to_docx(entries[:1]))).inline_shapes[0].width
    document = docx.Document(BytesIO(to_docx(entries)))
    section = document.sections[0]
    available = section.page_width - section.left_margin - section.right_margin
    assert document.inline_shapes[1].width <= available + 1
    assert document.inline_shapes[0].width < natural  # the whole set shares the fit scale


def test_font_and_scale_reach_word_image_dimensions():
    entries = [MoleculeEntry("ethanol", "CCO")]
    small = docx.Document(BytesIO(to_docx(entries, RenderOptions(font_size=12)))).inline_shapes[0]
    large = docx.Document(BytesIO(to_docx(entries, RenderOptions(font_size=24)))).inline_shapes[0]
    assert large.width > small.width
    assert large.height > small.height
    half = docx.Document(BytesIO(to_docx(entries, RenderOptions(font_size=24),
                                       DocumentOptions(scale=.5)))).inline_shapes[0]
    assert half.width == pytest.approx(large.width / 2, abs=1)


def test_invalid_entry_stops_whole_export():
    with pytest.raises(MoleculeError, match="Molecule 2"):
        to_docx([MoleculeEntry("good", "CCO"), MoleculeEntry("bad", "wrong")])
    with pytest.raises(ValueError):
        to_docx([])


def test_png_bytes():
    assert to_png("CCO").startswith(b"\x89PNG")
    with pytest.raises(ValueError):
        to_png("CCO", dpi=0)


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf"), 4])
def test_bad_document_scale(scale):
    with pytest.raises(ValueError):
        DocumentOptions(scale=scale)
