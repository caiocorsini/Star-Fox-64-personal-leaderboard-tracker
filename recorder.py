import os
import csv
import json
import datetime
import random
import tkinter as tk
from tkinter import messagebox

CSV_NAME = "Star Fox 64 - All Possible Routes - Sheet1.csv"
JSON_NAME = "sf64_records.json"
DIFFICULTIES = ["easy", "normal", "expert"]
VERSIONS = ["n64", "3ds", "switch 2"]
SPECIAL_PATH_NAME = "All Levels (3DS / Switch 2)"
SPECIAL_LEVELS = [
    "Corneria", "Meteo", "Sector Y", "Fichina", "Katina", "Aquas",
    "Zoness", "Sector X", "Titania", "Solar", "Macbeth", "Sector Z",
    "Area 6", "Venom 1", "Venom 2"
]
# Map each version to available difficulties
VERSION_DIFFICULTIES = {
    "n64": ["normal", "expert"],
    "3ds": ["normal", "expert"],
    "switch 2": ["easy", "normal", "expert"]
}


def load_paths(csv_path):
    paths = []
    seen = set()
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            for row in reader:
                # join all non-empty columns; strip parenthetical difficulty from last item
                cleaned = []
                for i, cell in enumerate(row):
                    if not cell:
                        continue
                    cell = cell.strip()
                    if i == len(row) - 1:
                        # remove trailing parenthesis like " (Easy)" or " (Hard)"
                        if "(" in cell:
                            cell = cell.split("(", 1)[0].strip()
                    cleaned.append(cell)
                if not cleaned:
                    continue
                path_str = " > ".join(cleaned)
                if path_str not in seen:
                    seen.add(path_str)
                    paths.append(path_str)
    except FileNotFoundError:
        return []
    paths.append(SPECIAL_PATH_NAME)
    return paths


def load_data(json_path, paths):
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"paths": {}}

    # ensure all paths exist with valid difficulty+version combinations
    for p in paths:
        if p not in data.get("paths", {}):
            data.setdefault("paths", {})[p] = {}
            for v in VERSIONS:
                if p == SPECIAL_PATH_NAME and v == "n64":
                    continue
                data["paths"][p][v] = {}
                for d in VERSION_DIFFICULTIES.get(v, []):
                    data["paths"][p][v][d] = []
        else:
            pdata = data.setdefault("paths", {})[p]
            # ensure version keys exist
            for v in VERSIONS:
                if v not in pdata:
                    pdata[v] = {}
                # migrate old difficulty-based structure to new version-based structure
                for d in DIFFICULTIES:
                    if d in pdata and isinstance(pdata[d], (list, dict)):
                        # old format: path -> difficulty -> [entries] or path -> difficulty -> version -> [entries]
                        if isinstance(pdata[d], list):
                            # very old format: path -> difficulty -> [entries]
                            if not pdata[v].get(d):
                                pdata[v][d] = []
                            for e in pdata[d]:
                                if isinstance(e, dict):
                                    ver = e.get('version', v)
                                    if ver in VERSIONS:
                                        pdata.setdefault(ver, {}).setdefault(d, []).append(e)
                        elif isinstance(pdata[d], dict):
                            # intermediate format: path -> difficulty -> version -> [entries]
                            for ver, entries in pdata[d].items():
                                if ver in VERSIONS and isinstance(entries, list):
                                    pdata.setdefault(ver, {}).setdefault(d, []).extend(entries)
                # remove old difficulty keys after migration
                for d in DIFFICULTIES:
                    if d in pdata and d not in VERSIONS:
                        del pdata[d]
            # ensure only valid difficulty+version combinations exist
            for v in VERSIONS:
                if p == SPECIAL_PATH_NAME and v == "n64":
                    pdata.pop(v, None)
                    continue
                valid_diffs = VERSION_DIFFICULTIES.get(v, [])
                for d in list(pdata.get(v, {}).keys()):
                    if d not in valid_diffs:
                        del pdata[v][d]
                for d in valid_diffs:
                    pdata[v].setdefault(d, [])

    return data


def save_data(json_path, data):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


class RecorderApp:
    def __init__(self, root, csv_path, json_path):
        self.root = root
        self.csv_path = csv_path
        self.json_path = json_path

        self.all_paths = load_paths(csv_path)
        if not self.all_paths:
            messagebox.showerror("CSV not found", f"Could not find CSV: {csv_path}")
            root.destroy()
            return

        self.paths = self.all_paths[:]
        self.data = load_data(json_path, self.all_paths)

        root.title("Star Fox 64 Record Recorder")

        # Left: list of paths with scrollbars and randomizer
        left = tk.Frame(root)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=8, pady=8)

        tk.Label(left, text="Select Path:").pack(anchor='w')
        list_frame = tk.Frame(left)
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.lb = tk.Listbox(list_frame, width=80, height=25, exportselection=False)
        self.lb.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        vscroll = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.lb.yview)
        vscroll.pack(side=tk.RIGHT, fill=tk.Y)
        hscroll = tk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.lb.xview)
        hscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.lb.config(yscrollcommand=vscroll.set, xscrollcommand=hscroll.set)

        self.lb.bind('<<ListboxSelect>>', lambda e: self.refresh_display())

        self.rand_btn = tk.Button(left, text="Randomize Path", command=self.randomize)
        self.rand_btn.pack(pady=(6, 0), anchor='w')

        # Right: details and controls
        self.right = tk.Frame(root)
        self.right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(self.right, text="Difficulty:").grid(row=0, column=0, sticky='w')
        self.diff_var = tk.StringVar(value="normal")
        self.diff_menu = tk.OptionMenu(self.right, self.diff_var, "normal", command=lambda e: self.refresh_display())
        self.diff_menu.grid(row=0, column=1, sticky='w')

        tk.Label(self.right, text="Version:").grid(row=0, column=2, sticky='w', padx=(10,0))
        self.version_var = tk.StringVar(value=VERSIONS[0])
        self.version_menu = tk.OptionMenu(self.right, self.version_var, *VERSIONS, command=lambda e: self.update_difficulties())
        self.version_menu.grid(row=0, column=3, sticky='w')

        tk.Label(self.right, text="Player name (optional):").grid(row=1, column=0, sticky='w')
        self.name_entry = tk.Entry(self.right)
        self.name_entry.grid(row=1, column=1, sticky='we')

        # Per-level score inputs (generated dynamically)
        self.levels_frame = tk.Frame(self.right)
        self.levels_frame.grid(row=2, column=0, columnspan=2, sticky='we')
        self.level_entries = []

        self.add_btn = tk.Button(self.right, text="Add Score", command=self.add_score)
        self.add_btn.grid(row=3, column=0, columnspan=2, pady=6)

        tk.Label(self.right, text="Top 10:").grid(row=4, column=0, sticky='w')
        self.text = tk.Text(self.right, width=60, height=15, state=tk.DISABLED)
        self.text.grid(row=5, column=0, columnspan=2, sticky='nsew')

        self.right.grid_columnconfigure(1, weight=1)

        self.update_difficulties()

    def randomize(self):
        if not self.paths:
            return
        idx = random.randrange(len(self.paths))
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(idx)
        self.lb.see(idx)
        self.refresh_display()
        messagebox.showinfo("Random Path", f"Selected: {self.paths[idx]}")

    def update_path_list(self):
        """Show the special path only on consoles that support it."""
        version = self.version_var.get()
        self.paths = [
            path for path in self.all_paths
            if path != SPECIAL_PATH_NAME or version in ("3ds", "switch 2")
        ]
        self.lb.delete(0, tk.END)
        for path in self.paths:
            self.lb.insert(tk.END, path)
        if self.paths:
            self.lb.selection_set(0)
            self.lb.see(0)

    def update_difficulties(self):
        """Update the difficulty dropdown based on selected version."""
        version = self.version_var.get()
        available_diffs = VERSION_DIFFICULTIES.get(version, ["normal", "expert"])

        self.update_path_list()
        
        # Recreate the difficulty dropdown with only available options
        self.diff_menu.destroy()
        self.diff_var.set(available_diffs[0])
        self.diff_menu = tk.OptionMenu(self.right, self.diff_var, *available_diffs, command=lambda e: self.refresh_display())
        self.diff_menu.grid(row=0, column=1, sticky='w')
        
        self.refresh_display()

    def refresh_display(self):
        sel = self.lb.curselection()
        if not sel:
            return
        path = self.lb.get(sel[0])
        diff = self.diff_var.get()
        version_val = self.version_var.get()

        pdata = self.data.get("paths", {}).get(path, {})
        # handle both old format (path -> difficulty -> version) and new format (path -> version -> difficulty)
        if version_val in pdata and isinstance(pdata[version_val], dict):
            # new format: path -> version -> difficulty -> [entries]
            entries = pdata[version_val].get(diff, [])
        else:
            # old format fallback: path -> difficulty -> version -> [entries]
            diff_bucket = pdata.get(diff, {})
            if isinstance(diff_bucket, dict):
                entries = diff_bucket.get(version_val, [])
            else:
                entries = []

        # prepare level names for display; the special path has separate Venom 1 and Venom 2
        level_names = SPECIAL_LEVELS if path == SPECIAL_PATH_NAME else path.split(' > ')

        # update top-10 display
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        if not entries:
            self.text.insert(tk.END, "(no scores yet)\n")
        else:
            for i, e in enumerate(entries, start=1):
                name = e.get('name') or '—'
                score = e.get('score')
                levels = e.get('levels') or []
                recorded_at = e.get('recorded_at')
                # pair level names with scores when possible
                if levels and len(levels) == len(level_names):
                    pairs = [f"{ln}: {sc}" for ln, sc in zip(level_names, levels)]
                    level_str = ' | ' + ', '.join(pairs)
                elif levels:
                    level_str = ' | levels: ' + ', '.join(str(x) for x in levels)
                else:
                    level_str = ''
                # do not show console/version here per request
                timestamp_str = f" ({recorded_at})" if recorded_at else ""
                self.text.insert(tk.END, f"{i}. {name}: {score}{level_str}{timestamp_str}\n")
        self.text.config(state=tk.DISABLED)

        # update per-level inputs based on selected path
        for w in self.levels_frame.winfo_children():
            w.destroy()
        self.level_entries = []
        levels = level_names
        for i, lvl in enumerate(levels):
            lbl = tk.Label(self.levels_frame, text=f"{lvl}:")
            lbl.grid(row=i, column=0, sticky='w', padx=(0,6), pady=2)
            ent = tk.Entry(self.levels_frame)
            ent.grid(row=i, column=1, sticky='we', pady=2)
            self.levels_frame.grid_columnconfigure(1, weight=1)
            self.level_entries.append(ent)

    def add_score(self):
        sel = self.lb.curselection()
        if not sel:
            messagebox.showwarning("No path", "Please select a path first.")
            return
        path = self.lb.get(sel[0])
        diff = self.diff_var.get()
        version_val = self.version_var.get()
        name = self.name_entry.get().strip()
        # validate per-level inputs (mandatory)
        level_vals = []
        for ent in self.level_entries:
            txt = ent.get().strip()
            if txt == '' or not txt.lstrip('-').isdigit():
                messagebox.showwarning("Invalid input", "Please enter a numeric score for every level.")
                return
            level_vals.append(int(txt))

        total = sum(level_vals)

        # append to the specific version+difficulty leaderboard
        timestamp = datetime.datetime.now().isoformat()
        entries = self.data.setdefault("paths", {}).setdefault(path, {}).setdefault(version_val, {}).setdefault(diff, [])
        entries.append({"name": name, "score": total, "levels": level_vals, "version": version_val, "recorded_at": timestamp})
        # sort by score desc and keep top 10 for this version+difficulty
        entries.sort(key=lambda x: x.get('score', 0), reverse=True)
        self.data["paths"][path][version_val][diff] = entries[:10]
        save_data(self.json_path, self.data)
        messagebox.showinfo("Saved", "Score saved and leaderboard updated.")
        self.refresh_display()


def main():
    base = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base, CSV_NAME)
    json_path = os.path.join(base, JSON_NAME)

    root = tk.Tk()
    app = RecorderApp(root, csv_path, json_path)
    # if CSV missing, app will destroy root
    if app.paths:
        root.mainloop()


if __name__ == '__main__':
    main()
