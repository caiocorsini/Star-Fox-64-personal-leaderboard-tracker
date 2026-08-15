import os
import csv
import json
import random
import tkinter as tk
from tkinter import messagebox

CSV_NAME = "Star Fox 64 - All Possible Routes - Sheet1.csv"
JSON_NAME = "sf64_records.json"
DIFFICULTIES = ["easy", "normal", "expert"]


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
    return paths


def load_data(json_path, paths):
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    else:
        data = {"paths": {}}

    # ensure all paths exist with difficulties
    for p in paths:
        if p not in data["paths"]:
            data["paths"][p] = {d: [] for d in DIFFICULTIES}
        else:
            for d in DIFFICULTIES:
                data["paths"][p].setdefault(d, [])

    return data


def save_data(json_path, data):
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


class RecorderApp:
    def __init__(self, root, csv_path, json_path):
        self.root = root
        self.csv_path = csv_path
        self.json_path = json_path

        self.paths = load_paths(csv_path)
        if not self.paths:
            messagebox.showerror("CSV not found", f"Could not find CSV: {csv_path}")
            root.destroy()
            return

        self.data = load_data(json_path, self.paths)

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

        for p in self.paths:
            self.lb.insert(tk.END, p)

        self.lb.bind('<<ListboxSelect>>', lambda e: self.refresh_display())

        self.rand_btn = tk.Button(left, text="Randomize Path", command=self.randomize)
        self.rand_btn.pack(pady=(6, 0), anchor='w')

        # Right: details and controls
        right = tk.Frame(root)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8, pady=8)

        tk.Label(right, text="Difficulty:").grid(row=0, column=0, sticky='w')
        self.diff_var = tk.StringVar(value=DIFFICULTIES[0])
        self.diff_menu = tk.OptionMenu(right, self.diff_var, *DIFFICULTIES, command=lambda e: self.refresh_display())
        self.diff_menu.grid(row=0, column=1, sticky='w')

        tk.Label(right, text="Player name (optional):").grid(row=1, column=0, sticky='w')
        self.name_entry = tk.Entry(right)
        self.name_entry.grid(row=1, column=1, sticky='we')

        # Per-level score inputs (generated dynamically)
        self.levels_frame = tk.Frame(right)
        self.levels_frame.grid(row=2, column=0, columnspan=2, sticky='we')
        self.level_entries = []

        self.add_btn = tk.Button(right, text="Add Score", command=self.add_score)
        self.add_btn.grid(row=3, column=0, columnspan=2, pady=6)

        tk.Label(right, text="Top 10:").grid(row=4, column=0, sticky='w')
        self.text = tk.Text(right, width=60, height=15, state=tk.DISABLED)
        self.text.grid(row=5, column=0, columnspan=2, sticky='nsew')

        right.grid_columnconfigure(1, weight=1)

        # select first
        if self.paths:
            self.lb.selection_set(0)
        self.refresh_display()

    def randomize(self):
        if not self.paths:
            return
        idx = random.randrange(len(self.paths))
        self.lb.selection_clear(0, tk.END)
        self.lb.selection_set(idx)
        self.lb.see(idx)
        self.refresh_display()
        messagebox.showinfo("Random Path", f"Selected: {self.paths[idx]}")

    def refresh_display(self):
        sel = self.lb.curselection()
        if not sel:
            return
        path = self.lb.get(sel[0])
        diff = self.diff_var.get()

        entries = self.data["paths"].get(path, {}).get(diff, [])

        # update top-10 display
        self.text.config(state=tk.NORMAL)
        self.text.delete('1.0', tk.END)
        if not entries:
            self.text.insert(tk.END, "(no scores yet)\n")
        else:
            for i, e in enumerate(entries, start=1):
                name = e.get('name') or '—'
                score = e.get('score')
                self.text.insert(tk.END, f"{i}. {name}: {score}\n")
        self.text.config(state=tk.DISABLED)

        # update per-level inputs based on selected path
        for w in self.levels_frame.winfo_children():
            w.destroy()
        self.level_entries = []
        levels = path.split(' > ')
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

        entries = self.data["paths"][path][diff]
        entries.append({"name": name, "score": total, "levels": level_vals})
        # sort by score desc
        entries.sort(key=lambda x: x.get('score', 0), reverse=True)
        # keep top 10
        self.data["paths"][path][diff] = entries[:10]
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
