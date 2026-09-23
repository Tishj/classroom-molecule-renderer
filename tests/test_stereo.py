import numpy as np
import pytest
from matplotlib.figure import Figure
from matplotlib.patches import Polygon
from rdkit import Chem

from chemistry_renderer import MoleculeEntry, RenderOptions, draw_molecule, to_png
from chemistry_renderer.renderer import layout_molecule, parse_smiles
from chemistry_renderer.word import _prepare_images


ALANINE = "C[C@@H](N)C(=O)O"


def test_omit_stereo_retains_connectivity_and_hydrogens():
    mol = parse_smiles(ALANINE, "omit")
    assert Chem.MolToSmiles(mol) == Chem.MolToSmiles(Chem.MolFromSmiles("CC(N)C(=O)O"))
    positions, _ = layout_molecule(mol, RenderOptions(stereochemistry="omit"))
    assert positions[0][1] == positions[1][1] == positions[3][1] == 0


def test_enantiomers_receive_opposite_wedge_directions():
    directions = []
    for smiles in (ALANINE, ALANINE.replace("@@", "@")):
        mol = parse_smiles(smiles, "show")
        layout_molecule(mol, RenderOptions(layout="rdkit", stereochemistry="show"))
        wedges = [b for b in mol.GetBonds() if b.GetBondDir() in
                  (Chem.BondDir.BEGINWEDGE, Chem.BondDir.BEGINDASH)]
        assert len(wedges) == 1
        assert mol.GetAtomWithIdx(wedges[0].GetBeginAtomIdx()).GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED
        directions.append(wedges[0].GetBondDir())
        # Verify that coordinates and assigned wedges round-trip as the same stereoisomer.
        restored = Chem.MolFromMolBlock(Chem.MolToMolBlock(mol))
        assert Chem.MolToSmiles(restored) == Chem.MolToSmiles(Chem.MolFromSmiles(smiles))
    assert directions[0] != directions[1]


def test_wedges_draw_differently_for_enantiomers():
    polygons = []
    for smiles in (ALANINE, ALANINE.replace("@@", "@")):
        ax = Figure().subplots()
        draw_molecule(ax, smiles, RenderOptions(layout="rdkit", stereochemistry="show"))
        polygons.append(sum(isinstance(p, Polygon) for p in ax.patches))
    assert sorted(polygons) == [0, 1]


def test_ez_preserved_in_coordinates():
    signs = []
    for smiles in ("F/C=C/F", "F/C=C\\F"):
        mol = parse_smiles(smiles, "show")
        coords, _ = layout_molecule(mol, RenderOptions(layout="rdkit", stereochemistry="show"))
        axis = np.array(coords[2]) - coords[1]
        def side(index):
            vector = np.array(coords[index]) - coords[1]
            return axis[0] * vector[1] - axis[1] * vector[0]
        signs.append(np.sign(side(0) * side(3)))
    assert signs == [-1, 1]


def test_docx_uses_each_molecules_stereo_setting():
    images = _prepare_images([MoleculeEntry("", ALANINE, "show"), MoleculeEntry("", ALANINE, "omit")], RenderOptions(layout="rdkit"))
    assert images[0].png == to_png(ALANINE, RenderOptions(layout="rdkit", stereochemistry="show"))
    assert images[1].png == to_png(ALANINE, RenderOptions(layout="rdkit", stereochemistry="omit"))
    assert images[0].png != images[1].png


def test_invalid_stereo_mode():
    with pytest.raises(ValueError):
        RenderOptions(stereochemistry="invalid")


def test_classroom_never_switches_layout_to_show_stereo():
    with pytest.raises(ValueError, match="requires layout='rdkit'"):
        to_png(ALANINE, RenderOptions(stereochemistry="show"))
