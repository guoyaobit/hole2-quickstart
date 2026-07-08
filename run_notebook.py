import run_holeprogram as rh
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import pandas as pd

CONFIG_PATH = 'pdb_params.yaml'


def make_df(data):
    rows = []
    for name, vals in (data or {}).items():
        rows.append({
            'pdb': name,
            'CPOINT': vals.get('CPOINT'),
            'CVECT': vals.get('CVECT'),
        })
    return pd.DataFrame(rows)


def launch():
    cfg = rh.load_pdb_params()
    pdb_files = rh.list_pdb_files()
    for f in pdb_files:
        if f not in cfg and rh.list_pdb_files and f not in cfg:
            cfg[f] = {}

    out_df = widgets.Output()
    with out_df:
        clear_output()
        display(make_df(cfg))

    sel_multi = widgets.SelectMultiple(options=pdb_files, description='To process', rows=8)
    refresh_btn = widgets.Button(description='Refresh PDB list')

    def on_refresh(b=None):
        nonlocal pdb_files
        pdb_files = rh.list_pdb_files()
        for f in pdb_files:
            if f not in cfg and f not in cfg:
                cfg[f] = {}
        sel_multi.options = pdb_files
        with out_df:
            clear_output()
            display(make_df(cfg))

    refresh_btn.on_click(on_refresh)
    display(widgets.HBox([sel_multi, refresh_btn]))
    display(out_df)

    pdb_names = sorted(cfg.keys())
    sel = widgets.Dropdown(options=pdb_names, description='PDB:')
    cpoint_in = widgets.Text(description='CPOINT (csv)')
    cvect_in = widgets.Text(description='CVECT (csv)')
    status = widgets.HTML('')
    new_name_in = widgets.Text(description='New name')

    def parse_csv_list(s):
        if s is None:
            return None
        s = str(s).strip()
        if s == '':
            return None
        parts = [p for p in s.replace(',', ' ').split() if p]
        try:
            return [float(x) for x in parts]
        except ValueError:
            return parts

    def on_select(change=None):
        name = sel.value
        if not name:
            cpoint_in.value = ''
            cvect_in.value = ''
            return
        vals = cfg.get(name, {})
        cp = vals.get('CPOINT')
        cv = vals.get('CVECT')
        cpoint_in.value = ', '.join(map(str, cp)) if cp else ''
        cvect_in.value = ', '.join(map(str, cv)) if cv else ''
        status.value = ''

    sel.observe(on_select, names='value')

    def save_entry(b):
        name = sel.value
        if not name:
            status.value = '<b style="color:red">No PDB selected</b>'
            return
        cp = parse_csv_list(cpoint_in.value)
        cv = parse_csv_list(cvect_in.value)
        entry = {}
        if cp is not None:
            entry['CPOINT'] = cp
        if cv is not None:
            entry['CVECT'] = cv
        cfg[name] = entry
        rh.save_pdb_params(CONFIG_PATH, cfg)
        status.value = '<b style="color:green">Saved</b>'
        with out_df:
            clear_output()
            display(make_df(cfg))

    def add_entry(b):
        new_name = new_name_in.value.strip()
        if not new_name:
            status.value = '<b style="color:red">Provide name</b>'
            return
        if new_name in cfg:
            status.value = '<b style="color:orange">Already exists</b>'
            return
        cfg[new_name] = {}
        rh.save_pdb_params(CONFIG_PATH, cfg)
        sel.options = sorted(cfg.keys())
        sel.value = new_name
        sel_multi.options = rh.list_pdb_files() + tuple(sorted(k for k in cfg.keys() if k not in rh.list_pdb_files()))
        status.value = '<b style="color:green">Added</b>'
        with out_df:
            clear_output()
            display(make_df(cfg))

    def delete_entry(b):
        name = sel.value
        if not name or name not in cfg:
            status.value = '<b style="color:red">Nothing to delete</b>'
            return
        del cfg[name]
        rh.save_pdb_params(CONFIG_PATH, cfg)
        sel.options = sorted(cfg.keys())
        sel.value = None
        status.value = '<b style="color:green">Deleted</b>'
        sel_multi.options = rh.list_pdb_files() + tuple(sorted(k for k in cfg.keys() if k not in rh.list_pdb_files()))
        with out_df:
            clear_output()
            display(make_df(cfg))

    def process_selected(b):
        targets = list(sel_multi.value)
        if not targets:
            status.value = '<b style="color:red">No PDBs selected for processing</b>'
            return
        status.value = '<b style="color:blue">Processing...</b>'
        display(HTML('<pre>'))
        try:
            rh.save_pdb_params(CONFIG_PATH, cfg)
            folders = rh.process_pdbs(targets)
            zip_path = rh.make_zip_for_folders(folders)
            display(HTML(f"</pre><b style='color:green'>Processing complete. Created: {zip_path}</b>"))
            status.value = f'<b style="color:green">Done. Zip: {zip_path}</b>'
        except Exception as e:
            display(HTML(f"</pre><b style='color:red'>Error: {e}</b>"))
            status.value = f'<b style="color:red">Error: {e}</b>'

    save_btn = widgets.Button(description='Save', button_style='success')
    add_btn = widgets.Button(description='Add', button_style='info')
    del_btn = widgets.Button(description='Delete', button_style='danger')
    proc_btn = widgets.Button(description='Process selected', button_style='primary')

    save_btn.on_click(save_entry)
    add_btn.on_click(add_entry)
    del_btn.on_click(delete_entry)
    proc_btn.on_click(process_selected)

    ui = widgets.VBox([widgets.HBox([sel, new_name_in, add_btn, del_btn]), cpoint_in, cvect_in, widgets.HBox([save_btn, proc_btn, status])])
    display(ui)
    on_select()
