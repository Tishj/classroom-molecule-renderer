import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
from matplotlib.figure import Figure

from chemistry_renderer import MoleculeError, RenderOptions, draw_molecule, render, to_svg
from chemistry_renderer.renderer import atom_label, layout_molecule, parse_smiles


@pytest.mark.parametrize("smiles,labels", [
    ("CCO", ["CH₃", "CH₂", "OH"]),
    ("CC(O)C", ["CH₃", "CH", "OH", "CH₃"]),
    ("CC(=O)O", ["CH₃", "C", "O", "OH"]),
    ("C#N", ["CH", "N"]),
    ("[NH4+]", ["NH₄⁺"]),
    ("[13CH3]O", ["¹³CH₃", "OH"]),
])
def test_chemistry_labels(smiles, labels):
    assert [atom_label(a) for a in parse_smiles(smiles).GetAtoms()] == labels


@pytest.mark.parametrize("smiles", ["", "garbage", "CC name", "C(C)(C)(C)(C)C", "[CH3]", "*C",
                                          "C[C@H](O)C(=O)O", "F/C=C/F", "[Na+].[Cl-]"])
def test_invalid_or_unrepresentable_inputs(smiles):
    with pytest.raises(MoleculeError):
        to_svg(smiles)


def test_classroom_positions():
    positions, _ = layout_molecule(parse_smiles("CC(O)C"), RenderOptions())
    assert positions[0][1] == positions[1][1] == positions[3][1] == 0
    assert positions[2][0] == positions[1][0]
    assert positions[2][1] > 0


def test_oxygen_glyph_is_centered_on_vertical_bond():
    from chemistry_renderer.renderer import _label_path
    # The O glyph is the first two closed contours in both O and OH.
    oxygen = _label_path(parse_smiles("O=O").GetAtomWithIdx(0), 20)
    hydroxyl = _label_path(parse_smiles("CO").GetAtomWithIdx(1), 20)
    import numpy as np
    np.testing.assert_allclose(oxygen.vertices, hydroxyl.vertices[:len(oxygen.vertices)])
    assert abs((oxygen.get_extents().x0 + oxygen.get_extents().x1) / 2) < 1e-8


def test_carbonyl_is_vertical_and_has_two_close_lines():
    ax = Figure().subplots()
    draw_molecule(ax, "CC(=O)O")
    assert len(ax.lines) == 4
    double = ax.lines[1:3]
    assert all(line.get_xdata()[0] == line.get_xdata()[1] for line in double)
    assert abs(double[0].get_xdata()[0] - double[1].get_xdata()[0]) == pytest.approx(3)


def test_bond_length_option_controls_visible_gap():
    for length in (12, 22, 40):
        ax = Figure().subplots()
        draw_molecule(ax, "CCO", RenderOptions(bond_length=length))
        for line in ax.lines:
            x1, x2 = line.get_xdata()
            assert x2 - x1 == pytest.approx(length)


@pytest.mark.parametrize("smiles", ["C1CCCCC1", "c1ccccc1", "CCC(CC)CC"])
def test_explicit_complex_layout(smiles):
    with pytest.raises(MoleculeError):
        to_svg(smiles)
    assert ET.fromstring(to_svg(smiles, RenderOptions(layout="rdkit"))).tag.endswith("svg")


def test_exports(tmp_path):
    for extension, magic in [("png", b"\x89PNG"), ("svg", b"<?xml"), ("pdf", b"%PDF")]:
        path = render("CC(O)C(=O)O", tmp_path / f"molecule.{extension}")
        assert path.read_bytes().startswith(magic)


def test_cli(tmp_path):
    path = tmp_path / "ethanol.svg"
    result = subprocess.run([sys.executable, "-m", "chemistry_renderer", "CCO", "-o", str(path)],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert path.exists()
    bad = subprocess.run([sys.executable, "-m", "chemistry_renderer", "invalid"], capture_output=True, text=True)
    assert bad.returncode == 2
    assert "Invalid SMILES" in bad.stderr


@pytest.mark.parametrize("kwargs", [{"bond_length": 0}, {"font_size": float("nan")},
                                    {"layout": "unknown"}, {"double_bond_spacing": 20}])
def test_option_validation(kwargs):
    with pytest.raises(ValueError):
        RenderOptions(**kwargs)
