import run_holeprogram as rh
import ipywidgets as widgets
from IPython.display import display, clear_output, HTML
import pandas as pd
import os
import traceback
import base64

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
    # load existing config but restrict to current directory's pdb files
    existing = rh.load_pdb_params() or {}
    pdb_files = rh.list_pdb_files()
    # Build cfg containing only current pdb files, preserving existing values if present
    cfg = {p: existing.get(p, {}) for p in pdb_files}
    # persist the regenerated config (in-memory)
    rh.save_pdb_params(cfg)

    out_df = widgets.Output()
    with out_df:
        clear_output()
        display(make_df(cfg))

    # output area for processing results (ensures displays appear in the notebook UI)
    proc_out = widgets.Output()

    sel_multi = widgets.SelectMultiple(options=pdb_files, description='To process', rows=8)
    # default select all pdb files
    try:
        sel_multi.value = tuple(pdb_files)
    except Exception:
        # some widget frontends may not accept setting value before display
        pass
    refresh_btn = widgets.Button(description='Refresh PDB list')

    def on_refresh(b=None):
        nonlocal pdb_files, cfg
        pdb_files = rh.list_pdb_files()
        cfg = {p: cfg.get(p, {}) for p in pdb_files}
        rh.save_pdb_params(cfg)
        sel_multi.options = pdb_files
        try:
            sel_multi.value = tuple(pdb_files)
        except Exception:
            pass
        with out_df:
            clear_output()
            display(make_df(cfg))

    refresh_btn.on_click(on_refresh)
    display(widgets.HBox([sel_multi, refresh_btn]))
    display(out_df)
    display(proc_out)

    pdb_names = sorted(cfg.keys())
    sel = widgets.Dropdown(options=pdb_names, description='PDB:')
    cpoint_in = widgets.Text(description='CPOINT (csv)')
    cvect_in = widgets.Text(description='CVECT (csv)')
    status = widgets.HTML('')

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
        # only update entry for existing pdbs
        if name in cfg:
            cfg[name] = entry
            rh.save_pdb_params(cfg)
            status.value = '<b style="color:green">Saved</b>'
            with out_df:
                clear_output()
                display(make_df(cfg))
        else:
            status.value = '<b style="color:red">Selected PDB not in current directory</b>'

    def delete_entry(b):
        name = sel.value
        if not name or name not in cfg:
            status.value = '<b style="color:red">Nothing to clear</b>'
            return
        # clear parameters but keep the pdb key (yaml should only include current pdbs)
        cfg[name] = {}
        rh.save_pdb_params(cfg)
        sel.options = sorted(cfg.keys())
        sel.value = name
        status.value = '<b style="color:green">Cleared</b>'
        with out_df:
            clear_output()
            display(make_df(cfg))

    def process_selected(b):
        targets = list(sel_multi.value)
        if not targets:
            status.value = '<b style="color:red">No PDBs selected for processing</b>'
            return
        status.value = '<b style="color:blue">Processing...</b>'
        # show processing output inside the proc_out output widget so it appears in the notebook UI
        with proc_out:
            clear_output()
            try:
                rh.save_pdb_params(cfg)
                folders = rh.process_pdbs(targets)
                zip_path = rh.make_zip_for_folders(folders)
                # for each folder, attempt to plot and display the result
                plots = []
                for fdir, pdb in zip(folders, targets):
                cv = rh.pdb_params.get(pdb, {}).get('CVECT') if isinstance(rh.pdb_params, dict) else None
                try:
                    # show folder contents for debugging
                    try:
                        files = os.listdir(fdir)
                        display(HTML(f"<b>Result folder: {fdir}</b><br>Files: {', '.join(files)}</br>"))
                    except Exception as e:
                        display(HTML(f"<b style='color:orange'>Could not list files in {fdir}: {e}</b>"))

                    result, _ = rh.plot_tsv(fdir, cvect=cv)
                    from IPython.display import Image, display as _display
                    if isinstance(result, str) and result.lower().endswith('.png'):
                        try:
                            # embed image bytes so it displays even if file path isn't accessible to the notebook server
                            with open(result, 'rb') as _f:
                                img_bytes = _f.read()
                            _display(Image(data=img_bytes))
                            # also include HTML <img> with base64 to maximize compatibility
                            b64 = base64.b64encode(img_bytes).decode('ascii')
                            display(HTML(f"<div><b>{pdb}</b><br><img src='data:image/png;base64,{b64}' style='max-width:100%;height:auto'/></div>"))
                        except Exception:
                            # fallback to filename-based display and try embedding
                            try:
                                _display(Image(filename=result))
                                with open(result, 'rb') as _f:
                                    img_bytes = _f.read()
                                b64 = base64.b64encode(img_bytes).decode('ascii')
                                display(HTML(f"<div><b>{pdb}</b><br><img src='data:image/png;base64,{b64}' style='max-width:100%;height:auto'/></div>"))
                            except Exception:
                                display(HTML(f"<b style='color:orange'>Could not display PNG for {pdb}</b>"))
                    elif isinstance(result, str) and result.lower().endswith('.csv'):
                        # matplotlib not available; show CSV preview and download link
                        try:
                            df_preview = pd.read_csv(result)
                            display(HTML(f"<b>{pdb} (CSV fallback)</b>"))
                            display(df_preview.head(20))
                            display(HTML(f"<a href='{result}'>Download CSV</a>"))
                        except Exception:
                            display(HTML(f"<b>CSV generated at {result}</b>"))
                    else:
                        # unknown result type; just echo
                        display(HTML(f"<b>Plot result: {result}</b>"))
                except Exception as e:
                    # show warning text with full traceback for debugging
                    tb = traceback.format_exc()
                    display(HTML(f"<b style='color:orange'>Plot failed for {pdb}: {e}</b><br><pre>{tb}</pre>"))
            display(HTML(f"</pre><b style='color:green'>Processing complete. Created: {zip_path}</b>"))
            status.value = f'<b style="color:green">Done. Zip: {zip_path}</b>'
        except Exception as e:
            display(HTML(f"</pre><b style='color:red'>Error: {e}</b>"))
            status.value = f'<b style="color:red">Error: {e}</b>'

    save_btn = widgets.Button(description='Save', button_style='success')
    del_btn = widgets.Button(description='Clear', button_style='danger')
    proc_btn = widgets.Button(description='Process selected', button_style='primary')

    save_btn.on_click(save_entry)
    del_btn.on_click(delete_entry)
    proc_btn.on_click(process_selected)

    ui = widgets.VBox([widgets.HBox([sel, del_btn]), cpoint_in, cvect_in, widgets.HBox([save_btn, proc_btn, status])])
    display(ui)
    on_select()
