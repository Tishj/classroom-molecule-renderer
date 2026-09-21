import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from chemistry_renderer import (
        DocumentOptions,
        RenderOptions,
        parse_molecule_lines,
        to_docx,
        to_png,
        to_svg,
    )
    return DocumentOptions, RenderOptions, mo, parse_molecule_lines, to_docx, to_png, to_svg


@app.cell
def _():
    # Edit these Python variables to set your own starting molecules and style.
    default_molecules = """Ethanol | CCO
Propaan-2-ol | CC(O)C
Ethaanzuur | CC(=O)O
Melkzuur | CC(O)C(=O)O
Ethylethanoaat | CC(=O)OCC
Glycerol | OCC(O)CO"""
    default_style = dict(font_size=20, bond_length=22, double_bond_spacing=3,
                         line_width=1.4, padding=14)
    return default_molecules, default_style


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    # Classroom structural formulas

    Enter molecules, adjust their appearance, and download a Word document.
    The preview and export use the same rendering settings.
    Names and headings remain editable in Word; formulas are high-resolution images.
    """)
    return


@app.cell(hide_code=True)
def _(default_molecules, default_style, mo):
    molecules_input = mo.ui.text_area(value=default_molecules, label="Molecules — one name | SMILES per line",
                                      rows=8, full_width=True)
    font_size = mo.ui.slider(12, 32, value=default_style["font_size"], label="Atom font size (pt)",
                              show_value=True, debounce=True)
    bond_length = mo.ui.slider(8, 50, value=default_style["bond_length"], label="Bond length (pt)",
                                show_value=True, debounce=True)
    bond_spacing = mo.ui.slider(1, 5, step=.5, value=default_style["double_bond_spacing"],
                                 label="Double / triple bond spacing (pt)", show_value=True, debounce=True)
    line_width = mo.ui.slider(.5, 3, step=.1, value=default_style["line_width"],
                               label="Bond line width (pt)", show_value=True, debounce=True)
    padding = mo.ui.slider(4, 30, value=default_style["padding"], label="Image padding (pt)",
                            show_value=True, debounce=True)
    layout = mo.ui.dropdown(options=["classroom", "rdkit"], value="classroom", label="Layout")
    mo.vstack([molecules_input,
               mo.hstack([mo.vstack([font_size, bond_length, bond_spacing]),
                          mo.vstack([line_width, padding, layout])]),
               mo.md("Use **rdkit** for rings or multi-atom side chains. Stereo-specific SMILES are not supported.")])
    return bond_length, bond_spacing, font_size, layout, line_width, molecules_input, padding


@app.cell(hide_code=True)
def _(mo):
    document_title = mo.ui.text(value="Structuurformules", label="Word title (leave blank for none)", full_width=True)
    include_names = mo.ui.checkbox(value=True, label="Include molecule names")
    numbered = mo.ui.checkbox(value=False, label="Number molecules")
    document_scale = mo.ui.slider(.5, 1.5, step=.1, value=1, label="Word image scale",
                                   show_value=True, debounce=True)
    mo.vstack([mo.md("## Word document"), document_title,
               mo.hstack([include_names, numbered]), document_scale,
               mo.md("A4 pages with 20 mm margins. Large formulas are fitted using a common scale. Page breaks are handled by Word.")])
    return document_scale, document_title, include_names, numbered


@app.cell
def _(DocumentOptions, RenderOptions, bond_length, bond_spacing, document_scale,
      document_title, font_size, include_names, layout, line_width, mo,
      molecules_input, numbered, padding, parse_molecule_lines):
    _error = None
    try:
        entries = parse_molecule_lines(molecules_input.value)
        render_options = RenderOptions(font_size=font_size.value, bond_length=bond_length.value,
                                       double_bond_spacing=bond_spacing.value, line_width=line_width.value,
                                       padding=padding.value, layout=layout.value)
        document_options = DocumentOptions(title=document_title.value, include_names=include_names.value,
                                           numbered=numbered.value, scale=document_scale.value)
    except ValueError as _exc:
        _error = str(_exc)
    mo.stop(_error is not None, mo.callout(mo.plain_text(_error or ""), kind="warn"))
    return document_options, entries, render_options


@app.cell
def _(document_options, entries, mo, render_options, to_docx, to_png, to_svg):
    # Export bytes are reactive variables too: use them in your own cells.
    _error = None
    try:
        docx_bytes = to_docx(entries, render_options, document_options)
        svg_images = [to_svg(_entry.smiles, render_options) for _entry in entries]
        png_images = [to_png(_entry.smiles, render_options) for _entry in entries]
    except ValueError as _exc:
        _error = str(_exc)
    mo.stop(_error is not None, mo.callout(mo.plain_text(_error or ""), kind="warn"))
    return docx_bytes, png_images, svg_images


@app.cell(hide_code=True)
def _(docx_bytes, mo):
    mo.download(data=docx_bytes, filename="structuurformules.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                label="Download Word document")
    return


@app.cell(hide_code=True)
def _(entries, mo, png_images, svg_images):
    _previews = []
    for _index, (_entry, _svg, _png) in enumerate(zip(entries, svg_images, png_images), 1):
        _previews.append(mo.vstack([
            mo.plain_text(_entry.name or f"Molecule {_index}"),
            mo.Html(_svg[_svg.index("<svg"):]).style({"overflow-x": "auto"}),
            mo.hstack([
                mo.download(data=_svg.encode(), filename=f"molecule-{_index}.svg", mimetype="image/svg+xml", label="SVG"),
                mo.download(data=_png, filename=f"molecule-{_index}.png", mimetype="image/png", label="PNG"),
            ], justify="start"),
        ]))
    mo.vstack([mo.md("## Molecule previews"), *_previews], gap=2)
    return


if __name__ == "__main__":
    app.run()
