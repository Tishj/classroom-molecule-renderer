import marimo

__generated_with = "0.24.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    from uuid import uuid4
    from dataclasses import replace
    from chemistry_renderer import DocumentOptions, MoleculeEntry, RenderOptions, to_docx, to_png, to_svg
    return DocumentOptions, MoleculeEntry, RenderOptions, mo, replace, to_docx, to_png, to_svg, uuid4


@app.cell
def _(mo):
    # Edit these variables to change the initial collection and appearance.
    default_molecules = ["CCO", "CC(O)C", "CC(=O)O", "[NH4+]"]
    default_style = dict(font_size=20, bond_length=22, double_bond_spacing=3,
                         line_width=1.4, padding=14)
    get_molecules, set_molecules = mo.state([
        {"id": str(i), "smiles": smiles} for i, smiles in enumerate(default_molecules)
    ], allow_self_loops=True)
    return default_style, get_molecules, set_molecules


@app.cell(hide_code=True)
def _(default_style, mo):
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
    mo.accordion({"Formatting": mo.hstack([
        mo.vstack([font_size, bond_length, bond_spacing]), mo.vstack([line_width, padding, layout])
    ])})
    return bond_length, bond_spacing, font_size, layout, line_width, padding


@app.cell
def _(RenderOptions, bond_length, bond_spacing, font_size, layout, line_width, padding):
    render_options = RenderOptions(font_size=font_size.value, bond_length=bond_length.value,
                                   double_bond_spacing=bond_spacing.value, line_width=line_width.value,
                                   padding=padding.value, layout=layout.value)
    return (render_options,)


@app.cell
def _(get_molecules, layout, mo, set_molecules, uuid4):
    # Stable IDs keep edits and removals attached to the correct molecule.
    def update_molecule(key, field, value):
        set_molecules(lambda rows: [dict(row, **{field: value}) if row["id"] == key else row for row in rows])

    def remove_molecule(key):
        set_molecules(lambda rows: [row for row in rows if row["id"] != key])

    molecule_inputs = mo.ui.dictionary({
        row["id"]: mo.ui.text(value=row["smiles"], label="SMILES", full_width=True, debounce=True,
                              on_change=lambda value, key=row["id"]: update_molecule(key, "smiles", value))
        for row in get_molecules()
    })
    stereo_inputs = mo.ui.dictionary({
        row["id"]: mo.ui.dropdown(
            options={"Show stereochemistry": "show", "Omit stereochemistry": "omit"},
            value="Omit stereochemistry" if row.get("stereo") == "omit" else "Show stereochemistry",
            label="Stereo", disabled=layout.value != "rdkit",
            on_change=lambda value, key=row["id"]: update_molecule(key, "stereo", value))
        for row in get_molecules()
    })
    remove_buttons = mo.ui.dictionary({
        row["id"]: mo.ui.button(label="−", tooltip="Remove molecule",
                                on_click=lambda _, key=row["id"]: remove_molecule(key))
        for row in get_molecules()
    })
    add_button = mo.ui.button(label="+", tooltip="Add molecule", disabled=len(get_molecules()) >= 100,
                             on_click=lambda _: set_molecules(lambda rows: rows + [{"id": uuid4().hex, "smiles": ""}]))
    return add_button, molecule_inputs, remove_buttons, stereo_inputs


@app.cell(hide_code=True)
def _(MoleculeEntry, add_button, mo, molecule_inputs, remove_buttons, render_options, replace, stereo_inputs, to_png, to_svg):
    entries = []
    _sections = []
    collection_valid = bool(molecule_inputs.value)
    for _index, (_key, _smiles) in enumerate(molecule_inputs.value.items(), 1):
        _stereo = stereo_inputs.value[_key] if render_options.layout == "rdkit" else "omit"
        _entry = MoleculeEntry("", _smiles.strip(), stereochemistry=_stereo)
        _options = replace(render_options, stereochemistry=_entry.stereochemistry)
        entries.append(_entry)
        _content = [mo.hstack([molecule_inputs[_key], remove_buttons[_key]], align="end", widths=[1, .06])]
        if render_options.layout == "rdkit":
            _content.append(stereo_inputs[_key])
        try:
            _svg = to_svg(_entry.smiles, _options)
            _png = to_png(_entry.smiles, _options)
            _content.extend([
                mo.Html(_svg[_svg.index("<svg"):]).style({"overflow-x": "auto"}),
                mo.hstack([
                    mo.download(data=_svg.encode(), filename=f"molecule-{_index}.svg", mimetype="image/svg+xml", label="SVG"),
                    mo.download(data=_png, filename=f"molecule-{_index}.png", mimetype="image/png", label="PNG"),
                ], justify="start"),
            ])
        except ValueError as _exc:
            collection_valid = False
            _content.append(mo.callout(mo.plain_text(str(_exc)), kind="warn") if _smiles.strip()
                            else mo.md("Enter SMILES and press **Enter**."))
        _sections.append(mo.vstack(_content).style({"border": "1px solid #ddd", "border-radius": "8px", "padding": "16px"}))
    mo.vstack([*_sections, add_button], gap=1)
    return collection_valid, entries


@app.cell(hide_code=True)
def _(mo):
    document_title = mo.ui.text(value="", label="Word title", full_width=True)
    numbered = mo.ui.checkbox(value=False, label="Number molecules")
    document_scale = mo.ui.slider(.5, 1.5, step=.1, value=1, label="Word image scale",
                                 show_value=True, debounce=True)
    mo.accordion({"Word settings": mo.vstack([document_title, numbered, document_scale])})
    return document_scale, document_title, numbered


@app.cell(hide_code=True)
def _(DocumentOptions, collection_valid, document_scale, document_title, entries, mo, numbered, render_options, to_docx):
    document_options = DocumentOptions(title=document_title.value, include_names=False,
                                       numbered=numbered.value, scale=document_scale.value)
    mo.stop(not collection_valid, mo.md("Add valid molecules to download a Word document."))
    docx_bytes = to_docx(entries, render_options, document_options)
    mo.download(data=docx_bytes, filename="structuurformules.docx",
                mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                label="Download Word document")
    return document_options, docx_bytes


if __name__ == "__main__":
    app.run()
