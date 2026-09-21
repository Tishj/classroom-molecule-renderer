"""Run with: python examples/gallery.py"""
from pathlib import Path

from matplotlib.figure import Figure

from chemistry_renderer import draw_molecule, render

EXAMPLES = [
    ("Ethanol", "CCO"),
    ("Propaan-2-ol", "CC(O)C"),
    ("Ethaanzuur", "CC(=O)O"),
    ("Melkzuur", "CC(O)C(=O)O"),
    ("Ethylethanoaat", "CC(=O)OCC"),
    ("Glycerol", "OCC(O)CO"),
    ("Butaan-1,3-dieen", "C=CC=C"),
    ("2,2-dimethylpropaan", "CC(C)(C)C"),
    ("Ethyn", "C#C"),
    ("Ethylacrylaat", "C=CC(=O)OCC"),
]


def main():
    output = Path(__file__).resolve().parent / "output"
    output.mkdir(exist_ok=True)
    fig = Figure(figsize=(12, 12), facecolor="white")
    axes = fig.subplots(5, 2)
    sizes = []
    for ax, (name, smiles) in zip(axes.flat, EXAMPLES):
        sizes.append(draw_molecule(ax, smiles))
        ax.set_title(name, fontsize=13, color="#374151", pad=16)
        render(smiles, output / f"{name.lower()}.svg")
    # Use the same physical scale in every cell, regardless of molecule size.
    width = max(size[0] for size in sizes)
    height = max(size[1] for size in sizes)
    for ax in axes.flat:
        cx, cy = sum(ax.get_xlim()) / 2, sum(ax.get_ylim()) / 2
        ax.set_xlim(cx - width / 2, cx + width / 2)
        ax.set_ylim(cy - height / 2, cy + height / 2)
    fig.subplots_adjust(hspace=.8, wspace=.25, left=.04, right=.96, top=.94, bottom=.04)
    fig.suptitle("Classroom structural formulas", fontsize=20, y=.99)
    fig.savefig(output / "gallery.png", dpi=160)
    fig.savefig(output / "gallery.svg")
    print(output / "gallery.png")


if __name__ == "__main__":
    main()
