"""Parse SMILES with RDKit; draw condensed groups with measured glyph outlines.

Coordinates and sizes are in points. Atom centers refer to the element symbol,
not to the center of its attached hydrogen text (in particular, O in OH).
"""

from dataclasses import dataclass
from io import BytesIO, StringIO
from math import hypot, isfinite
from pathlib import Path

from matplotlib.figure import Figure
from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.path import Path as GlyphPath
from matplotlib.textpath import TextPath
from matplotlib.transforms import Affine2D
from rdkit import Chem, rdBase
from rdkit.Chem import rdDepictor


class MoleculeError(ValueError):
    """Invalid chemistry or a representation this renderer cannot preserve."""


@dataclass(frozen=True)
class RenderOptions:
    font_size: float = 20
    bond_length: float = 22
    double_bond_spacing: float = 3
    line_width: float = 1.4
    padding: float = 14
    layout: str = "classroom"

    def __post_init__(self):
        for name in ("font_size", "bond_length", "double_bond_spacing", "line_width", "padding"):
            value = getattr(self, name)
            if not isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.layout not in ("classroom", "rdkit"):
            raise ValueError("layout must be 'classroom' or 'rdkit'")
        if self.double_bond_spacing * 2 >= self.font_size:
            raise ValueError("double_bond_spacing must be less than half font_size")


def parse_smiles(smiles):
    if not isinstance(smiles, str) or not smiles.strip():
        raise MoleculeError("Enter a non-empty SMILES string.")
    params = Chem.SmilesParserParams()
    params.parseName = False
    with rdBase.BlockLogs():
        mol = Chem.MolFromSmiles(smiles, params)
    if mol is None or mol.GetNumAtoms() == 0:
        raise MoleculeError(f"Invalid SMILES or valence: {smiles!r}")
    if mol.GetNumAtoms() > 100:
        raise MoleculeError("At most 100 atoms are supported per drawing.")
    if len(Chem.GetMolFrags(mol)) != 1:
        raise MoleculeError("Draw one connected molecule or ion at a time.")
    for atom in mol.GetAtoms():
        if atom.GetAtomicNum() == 0 or atom.GetNumRadicalElectrons():
            raise MoleculeError("Wildcard atoms and radicals are not supported.")
        if atom.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED:
            raise MoleculeError("Stereochemistry needs wedge bonds; omit stereo only if intentional.")
    for bond in mol.GetBonds():
        if bond.GetStereo() != Chem.BondStereo.STEREONONE:
            raise MoleculeError("E/Z stereochemistry is not supported by this notation.")
        if bond.GetBondType() not in (Chem.BondType.SINGLE, Chem.BondType.DOUBLE,
                                      Chem.BondType.TRIPLE, Chem.BondType.AROMATIC):
            raise MoleculeError("Only single, double, triple and aromatic bonds are supported.")
    # Aromatic molecules are displayed with one valid alternating-bond form.
    Chem.Kekulize(mol, clearAromaticFlags=True)
    return mol


SUB = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")
SUP = str.maketrans("0123456789+-", "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻")


def atom_label(atom, reverse=False):
    symbol = atom.GetSymbol()
    if atom.GetIsotope():
        symbol = str(atom.GetIsotope()).translate(SUP) + symbol
    count = atom.GetTotalNumHs()
    hydrogen = ("H" + (str(count).translate(SUB) if count > 1 else "")) if count else ""
    charge = atom.GetFormalCharge()
    suffix = ((str(abs(charge)) if abs(charge) > 1 else "") + ("+" if charge > 0 else "-")).translate(SUP) if charge else ""
    return (hydrogen + symbol if reverse else symbol + hydrogen) + suffix


def _glyph(text, size):
    return TextPath((0, 0), text, size=size, prop=FontProperties(family="DejaVu Sans"))


def _label_parts(atom, size, reverse=False):
    """Place scripts geometrically instead of relying on Unicode font metrics."""
    element = _glyph(atom.GetSymbol(), size)
    box = element.get_extents()
    element = Affine2D().translate(-(box.x0 + box.x1) / 2,
                                   -(box.y0 + box.y1) / 2).transform_path(element)
    parts = {"element": element}
    box = element.get_extents()
    gap = size * .06

    def place(text, font_size, left, center_y):
        path = _glyph(text, font_size)
        bounds = path.get_extents()
        return Affine2D().translate(left - bounds.x0,
                    center_y - (bounds.y0 + bounds.y1) / 2).transform_path(path)

    count = atom.GetTotalNumHs()
    if count:
        parts["hydrogen"] = place("H", size, box.x1 + gap, 0)
        if count > 1:
            parts["subscript"] = place(str(count), size * .65,
                                      parts["hydrogen"].get_extents().x1 + gap, box.y0)
        if reverse:
            right = max(p.get_extents().x1 for key, p in parts.items() if key != "element")
            shift = box.x0 - gap - right
            for key in ("hydrogen", "subscript"):
                if key in parts:
                    parts[key] = Affine2D().translate(shift, 0).transform_path(parts[key])
    charge = atom.GetFormalCharge()
    if charge:
        text = (str(abs(charge)) if abs(charge) > 1 else "") + ("+" if charge > 0 else "−")
        charge_path = place(text, size * .65, 0, box.y1)
        if "subscript" in parts and not reverse:
            sub = parts["subscript"].get_extents()
            left = (sub.x0 + sub.x1 - charge_path.get_extents().width) / 2
        else:
            left = max(p.get_extents().x1 for p in parts.values()) + gap
        parts["charge"] = Affine2D().translate(left, 0).transform_path(charge_path)
    if atom.GetIsotope():
        isotope = place(str(atom.GetIsotope()), size * .65, 0, box.y1)
        left = min(p.get_extents().x0 for p in parts.values()) - gap - isotope.get_extents().width
        parts["isotope"] = Affine2D().translate(left, 0).transform_path(isotope)
    return parts


def _label_path(atom, size, reverse=False):
    return GlyphPath.make_compound_path(*_label_parts(atom, size, reverse).values())


def _backbone(mol):
    """Choose the most carbon-rich path; keep terminal carbonyl O off it."""
    best, best_score = [], None
    for start in range(mol.GetNumAtoms()):
        stack = [(start, -1, [start])]
        while stack:
            node, parent, path = stack.pop()
            atoms = [mol.GetAtomWithIdx(i) for i in path]
            oxo = sum(a.GetSymbol() == "O" and a.GetDegree() == 1 and
                      a.GetBonds()[0].GetBondTypeAsDouble() == 2 for a in (atoms[0], atoms[-1]))
            score = (sum(a.GetAtomicNum() == 6 for a in atoms), -oxo, len(path))
            if best_score is None or score > best_score:
                best, best_score = path, score
            for neighbor in mol.GetAtomWithIdx(node).GetNeighbors():
                i = neighbor.GetIdx()
                if i != parent:
                    stack.append((i, node, path + [i]))
    return best


def layout_molecule(mol, options):
    """Return atom positions and glyph paths; never silently drop branches."""
    if options.layout == "rdkit":
        rdDepictor.Compute2DCoords(mol)
        conf = mol.GetConformer()
        scale = (options.font_size * 3 + options.bond_length) / 1.5
        positions = {a.GetIdx(): (conf.GetAtomPosition(a.GetIdx()).x * scale,
                                  conf.GetAtomPosition(a.GetIdx()).y * scale) for a in mol.GetAtoms()}
        paths = {a.GetIdx(): _label_path(a, options.font_size) for a in mol.GetAtoms()}
        return positions, paths
    if mol.GetRingInfo().NumRings():
        raise MoleculeError("Rings need layout='rdkit'; classroom layout supports open chains.")
    backbone = _backbone(mol)
    main = set(backbone)
    branches = {i: sorted(n.GetIdx() for n in mol.GetAtomWithIdx(i).GetNeighbors()
                          if n.GetIdx() not in main) for i in backbone}
    if any(mol.GetAtomWithIdx(j).GetDegree() != 1 for items in branches.values() for j in items):
        raise MoleculeError("Multi-atom side chains need layout='rdkit'.")
    if any(len(items) > 2 for items in branches.values()):
        raise MoleculeError("More than two side groups at one atom need layout='rdkit'.")
    paths = {a.GetIdx(): _label_path(a, options.font_size,
             reverse=(a.GetIdx() == backbone[0] and len(backbone) > 1 and
                      a.GetSymbol() in ("O", "N", "S"))) for a in mol.GetAtoms()}
    bounds = {i: path.get_extents() for i, path in paths.items()}
    # Reserve the full width of each column, including its branches.
    columns = {i: [i] + branches[i] for i in backbone}
    left = {i: min(bounds[j].x0 for j in columns[i]) for i in backbone}
    right = {i: max(bounds[j].x1 for j in columns[i]) for i in backbone}
    positions = {backbone[0]: (0.0, 0.0)}
    gap = options.bond_length + 6
    for prev, i in zip(backbone, backbone[1:]):
        positions[i] = (positions[prev][0] + right[prev] - left[i] + gap, 0.0)
    for i in backbone:
        for k, j in enumerate(branches[i]):
            dy = bounds[i].y1 - bounds[j].y0 + gap if k == 0 else bounds[i].y0 - bounds[j].y1 - gap
            positions[j] = (positions[i][0], dy)
    return positions, paths


def _exit_distance(box, dx, dy, margin=3):
    distances = []
    if dx:
        distances.append(((box.x1 + margin) if dx > 0 else (box.x0 - margin)) / dx)
    if dy:
        distances.append(((box.y1 + margin) if dy > 0 else (box.y0 - margin)) / dy)
    return min(distances)


def draw_molecule(ax, smiles, options=None):
    """Draw into a Matplotlib Axes, suitable for quiz grids and notebooks."""
    options = options or RenderOptions()
    mol = parse_smiles(smiles)
    positions, paths = layout_molecule(mol, options)
    bounds = {i: p.get_extents() for i, p in paths.items()}
    for bond in mol.GetBonds():
        i, j = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        x, y = positions[i]
        xx, yy = positions[j]
        length = hypot(xx - x, yy - y)
        dx, dy = (xx - x) / length, (yy - y) / length
        start = _exit_distance(bounds[i], dx, dy)
        end = _exit_distance(bounds[j], -dx, -dy)
        if start + end >= length:
            raise MoleculeError("Labels overlap; increase bond_length or use a simpler molecule.")
        order = int(bond.GetBondTypeAsDouble())
        for k in range(order):
            offset = (k - (order - 1) / 2) * options.double_bond_spacing
            ax.plot([x + dx * start - dy * offset, xx - dx * end - dy * offset],
                    [y + dy * start + dx * offset, yy - dy * end + dx * offset],
                    color="#111111", lw=options.line_width, solid_capstyle="butt")
    for i, path in paths.items():
        x, y = positions[i]
        ax.add_patch(PathPatch(path, transform=Affine2D().translate(x, y) + ax.transData,
                               color="#111111", linewidth=0))
    pad = options.padding
    xmin = min(positions[i][0] + b.x0 for i, b in bounds.items()) - pad
    xmax = max(positions[i][0] + b.x1 for i, b in bounds.items()) + pad
    ymin = min(positions[i][1] + b.y0 for i, b in bounds.items()) - pad
    ymax = max(positions[i][1] + b.y1 for i, b in bounds.items()) + pad
    ax.set(xlim=(xmin, xmax), ylim=(ymin, ymax), aspect="equal")
    ax.set_axis_off()
    return xmax - xmin, ymax - ymin


def _figure(smiles, options):
    fig = Figure()
    ax = fig.add_axes((0, 0, 1, 1))
    width, height = draw_molecule(ax, smiles, options)
    fig.set_size_inches(width / 72, height / 72)
    return fig


def to_svg(smiles, options=None):
    """Return a self-contained SVG string with portable font outlines."""
    stream = StringIO()
    _figure(smiles, options).savefig(stream, format="svg", facecolor="white")
    return stream.getvalue()


def to_png(smiles, options=None, *, dpi=300):
    """Return PNG bytes for notebooks, downloads and document insertion."""
    if not isfinite(dpi) or dpi <= 0:
        raise ValueError("dpi must be finite and positive")
    stream = BytesIO()
    _figure(smiles, options).savefig(stream, format="png", dpi=dpi, facecolor="white")
    return stream.getvalue()


def render(smiles, output, options=None, *, dpi=220):
    """Write SVG, PNG or PDF. PNG is suitable for insertion into Word."""
    output = Path(output)
    if output.suffix.lower() not in (".svg", ".png", ".pdf"):
        raise ValueError("Output extension must be .svg, .png or .pdf")
    if not isfinite(dpi) or dpi <= 0:
        raise ValueError("dpi must be finite and positive")
    fig = _figure(smiles, options)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=dpi, facecolor="white")
    return output
