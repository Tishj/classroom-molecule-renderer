# Classroom chemistry renderer

Render classroom structural formulas such as **CH₃—CH₂—OH** from SMILES. RDKit
validates the molecule and supplies hydrogen counts and bond orders; a custom
Matplotlib renderer places condensed groups and short, closely spaced bonds.
The **O** in OH is centered on vertical bonds. Carbonyls remain explicit C=O
groups, and every carbon is labeled.

## Install and run

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
chem-render 'CC(O)C' -o propaan-2-ol.svg
chem-render 'CC(=O)O' -o ethaanzuur.png --bond-length 18 --double-bond-spacing 2.5
python examples/gallery.py
python -m pytest
```

SVG is vector output with embedded glyph outlines, so it needs no installed font
to display correctly. PNG (220 dpi by default) is convenient for Word. PDF is
also supported. Exports have a white background and fit their contents.

## Python and notebooks

### Interactive marimo notebook

```sh
source .venv/bin/activate
python -m pip install -e '.[notebook,test]'
marimo edit notebooks/classroom.py
```

Use `marimo run notebooks/classroom.py` to open just the controls and results,
without the code editor. Run these commands from this project's directory.

The notebook provides:

- Individual sections combining a SMILES input, preview, and image downloads.
  Press Enter to apply an edit (leaving the field also applies it).
- A `+` button to add a section and a `−` button on each section to remove it.
  SMILES is passed directly to RDKit, including `|` in CXSMILES extensions.
- Sliders for atom font size, bond length, line width, double/triple bond spacing,
  and image padding, plus a classroom/RDKit layout selector.
- Live molecule previews and individual SVG/PNG downloads.
- A Word download for the complete collection, with optional title, numbering
  and image-scale controls. The default is formulas only.

The `default_molecules` and `default_style` Python variables set initial values.
The reactive `entries`, `render_options`, `document_options`, and `docx_bytes`
variables are available for use in additional cells. An empty or invalid section
prevents exporting a partial collection; valid sections retain their previews.
Formatting and Word settings are in collapsible panels.

Subscript numerals are positioned with their midpoint at the bottom of the main
letters. Charges are stacked above hydrogen counts, for example the `+` above
the `4` in `[NH4+]`. The same typography is used in previews and all exports.

The preview shows individual molecule images, not Word pagination. Word uses
A4 pages and 20 mm margins, keeps each name with its formula, and scales all
images together if necessary to fit. Captions and the title are editable Word
text; structural formulas are embedded 300 dpi PNGs, not editable chemical
objects. Image scale affects Word only, while rendering controls affect both
preview and export. Large image scales reduce effective print resolution.

### Export Word from Python

```python
from pathlib import Path
from chemistry_renderer import DocumentOptions, MoleculeEntry, RenderOptions, to_docx

molecules = [MoleculeEntry("", "CCO"), MoleculeEntry("", "CC(O)C(=O)O")]
data = to_docx(
    molecules,
    RenderOptions(bond_length=18, double_bond_spacing=2.5),
    DocumentOptions(title="", include_names=False),
)
Path("structures.docx").write_bytes(data)
```

For Word export without marimo, install `pip install -e '.[docx]'`.
`python examples/export_word.py` creates a sample collection. The core renderer
still works without marimo or python-docx installed.

### Jupyter and other Python notebooks

```python
from chemistry_renderer import RenderOptions, render, to_svg

options = RenderOptions(bond_length=18, double_bond_spacing=2.5)
render('CC(O)C(=O)O', 'melkzuur.png', options)

# In Jupyter:
from IPython.display import SVG, display
display(SVG(to_svg('CCO', options)))
```

For a quiz grid, call `draw_molecule(ax, smiles, options)` on each Matplotlib
Axes. See [examples/gallery.py](examples/gallery.py). Bond length, font size,
line width, double/triple bond spacing and padding use point-based layout units.
Embedding into an existing Axes scales the entire drawing to fit that Axes.
The bond length is the visible horizontal gap for plain chains; columns can
be wider to accommodate branches. Vertical branch bonds connect to the element
symbol center, while horizontal bonds stop outside the complete group label.

## Layout and scope

The default `classroom` layout chooses a carbon-rich horizontal backbone with
up to two single-atom side groups per position (including CH₃ and OH). It handles
alcohols, acids, esters, amines, simple branched alkanes, and double/triple bonds.
Terminal carbonyl oxygens are kept off the backbone when possible. Labels include
formal charges and isotope numbers. This is a layout heuristic, not IUPAC parent
chain selection or a chemical naming tool.

For rings or multi-atom side chains, explicitly select RDKit coordinates:

```sh
chem-render 'c1ccccc1' --layout rdkit -o benzene.svg
chem-render 'CCC(CC)CC' --layout rdkit -o branched.svg
```

That mode uses the same condensed labels and custom bond drawing with RDKit's
2D geometry; it does not keep the chain horizontal. Aromatic systems use one
Kekulé form. Dense structures may need a larger `--bond-length`; general label
and bond collision avoidance is not implemented for RDKit layouts.

Invalid SMILES, radicals, wildcard atoms, disconnected fragments, stereochemical
specifications, and molecules over 100 atoms produce errors. Stereo input is
rejected because this renderer does not yet implement wedges or E/Z depiction.
It does not render all hydrogens as separate atoms, condensed repeat units, or
polymer brackets. Ordinary explicit H atoms may be collapsed by RDKit on input.

The existing `build_quiz.py` is preserved as the original quiz generator. The new
package is independent and does not generate a quiz on import. Its PNG exports
can be inserted using `python-docx`, or its Axes API can replace hand-authored
drawings when migrating that script to SMILES.

## Background

The hybrid approach follows the referenced discussion: use RDKit for chemistry
and custom typography/layout for teaching notation. The [RDKit getting-started
guide](https://www.rdkit.org/docs/GettingStartedInPython.html) documents SMILES
parsing and molecule manipulation.
