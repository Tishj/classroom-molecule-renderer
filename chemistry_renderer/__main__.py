import argparse

from .renderer import RenderOptions, render


def main():
    parser = argparse.ArgumentParser(description="Render SMILES as a classroom structural formula.")
    parser.add_argument("smiles", help="SMILES, e.g. 'CC(O)C'")
    parser.add_argument("-o", "--output", default="molecule.svg")
    parser.add_argument("--layout", choices=("classroom", "rdkit"), default="classroom")
    parser.add_argument("--font-size", type=float, default=20)
    parser.add_argument("--bond-length", type=float, default=22)
    parser.add_argument("--double-bond-spacing", type=float, default=3)
    parser.add_argument("--dpi", type=float, default=220)
    args = parser.parse_args()
    try:
        options = RenderOptions(font_size=args.font_size, bond_length=args.bond_length,
                                double_bond_spacing=args.double_bond_spacing, layout=args.layout)
        path = render(args.smiles, args.output, options, dpi=args.dpi)
    except (ValueError, OSError) as error:
        parser.exit(2, f"chem-render: {error}\n")
    print(path)


if __name__ == "__main__":
    main()
