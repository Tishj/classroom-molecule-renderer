"""Export the example collection to Word using the same settings as a notebook."""
from pathlib import Path

from chemistry_renderer import DocumentOptions, RenderOptions, parse_molecule_lines, to_docx


def main():
    entries = parse_molecule_lines("""Ethanol | CCO
Propaan-2-ol | CC(O)C
Ethaanzuur | CC(=O)O
Melkzuur | CC(O)C(=O)O
Ethylethanoaat | CC(=O)OCC
Glycerol | OCC(O)CO""")
    data = to_docx(entries, RenderOptions(), DocumentOptions())
    output = Path(__file__).resolve().parent / "output" / "structuurformules.docx"
    output.parent.mkdir(exist_ok=True)
    output.write_bytes(data)
    print(output)


if __name__ == "__main__":
    main()
