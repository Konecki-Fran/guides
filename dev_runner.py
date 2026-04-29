#!/Library/Frameworks/Python.framework/Versions/Current/bin/python3
"""Dev Command Runner: tkinter UI to run common git/exploration commands.

Usage: /Library/Frameworks/Python.framework/Versions/Current/bin/python3 ~/dev_runner.py
"""

import os

os.environ.setdefault("TK_SILENCE_DEPRECATION", "1")

import shlex
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog


COMMANDS = [
    {
        "label": "1. Commits on current branch (vs master)",
        "template": "git log --oneline master..HEAD",
        "arg_label": None,
    },
    {
        "label": "2. Files changed vs master (diff stat)",
        "template": "git diff master...HEAD --stat",
        "arg_label": None,
    },
    {
        "label": "3. Search all commit messages",
        "template": "git log --all --oneline | grep -i -E -- {arg}",
        "arg_label": "Pattern (e.g. 'BT-542|PLD'):",
    },
    {
        "label": "4. Recursive grep for pattern",
        "template": (
            "grep -rnE "
            "--exclude-dir=.git --exclude-dir=node_modules "
            "--exclude-dir=.venv --exclude-dir=venv "
            "--exclude-dir=__pycache__ --exclude-dir=.tox "
            "--exclude-dir=dist --exclude-dir=build "
            "-- {arg} ."
        ),
        "arg_label": "Pattern (e.g. 'NoEventsFoundException'):",
    },
    {
        "label": "5. Recent commits (last 20)",
        "template": "git log -n 20 --oneline",
        "arg_label": None,
    },
]

TIMEOUT_SECONDS = 60


class DevRunner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Dev Command Runner")
        self.geometry("900x600")
        self._build_ui()

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Command:").grid(row=0, column=0, sticky="w")
        self.command_var = tk.StringVar()
        self.command_box = ttk.Combobox(
            top,
            textvariable=self.command_var,
            values=[c["label"] for c in COMMANDS],
            state="readonly",
            width=60,
        )
        self.command_box.grid(row=0, column=1, columnspan=2, sticky="we", padx=5)
        self.command_box.current(0)
        self.command_box.bind("<<ComboboxSelected>>", self._on_command_change)

        self.arg_label = ttk.Label(top, text="Argument:")
        self.arg_label.grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.arg_var = tk.StringVar()
        self.arg_entry = ttk.Entry(top, textvariable=self.arg_var, width=60)
        self.arg_entry.grid(row=1, column=1, columnspan=2, sticky="we", padx=5, pady=(8, 0))

        ttk.Label(top, text="Working dir:").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.cwd_var = tk.StringVar(value=os.getcwd())
        ttk.Entry(top, textvariable=self.cwd_var, width=50).grid(
            row=2, column=1, sticky="we", padx=5, pady=(8, 0)
        )
        ttk.Button(top, text="Browse...", command=self._pick_cwd).grid(
            row=2, column=2, sticky="w", pady=(8, 0)
        )

        btns = ttk.Frame(top)
        btns.grid(row=3, column=1, columnspan=2, sticky="w", pady=(10, 0))
        self.run_btn = ttk.Button(btns, text="Run", command=self.run_command)
        self.run_btn.pack(side=tk.LEFT)
        ttk.Button(btns, text="Clear output", command=self.clear_output).pack(side=tk.LEFT, padx=5)

        top.columnconfigure(1, weight=1)

        self.output = scrolledtext.ScrolledText(
            self, wrap=tk.NONE, font=("Menlo", 11), background="#1e1e1e", foreground="#e6e6e6",
            insertbackground="#e6e6e6",
        )
        self.output.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.output.tag_configure("cmd", foreground="#7fd3ff")
        self.output.tag_configure("err", foreground="#ff8a8a")
        self.output.tag_configure("meta", foreground="#a0a0a0")

        self._on_command_change()

    def _selected_command(self):
        return COMMANDS[self.command_box.current()]

    def _on_command_change(self, *_):
        cmd = self._selected_command()
        if cmd["arg_label"]:
            self.arg_label.configure(text=cmd["arg_label"])
            self.arg_entry.configure(state="normal")
        else:
            self.arg_label.configure(text="(no argument)")
            self.arg_var.set("")
            self.arg_entry.configure(state="disabled")

    def _pick_cwd(self):
        path = filedialog.askdirectory(initialdir=self.cwd_var.get() or os.path.expanduser("~"))
        if path:
            self.cwd_var.set(path)

    def clear_output(self):
        self.output.delete("1.0", tk.END)

    def run_command(self):
        cmd = self._selected_command()
        template = cmd["template"]
        if "{arg}" in template:
            arg = self.arg_var.get().strip()
            if not arg:
                self._write("ERROR: this command requires an argument.\n", "err")
                return
            shell_cmd = template.replace("{arg}", shlex.quote(arg))
        else:
            shell_cmd = template

        cwd = self.cwd_var.get().strip() or os.getcwd()
        if not os.path.isdir(cwd):
            self._write("ERROR: working dir does not exist: " + cwd + "\n", "err")
            return

        self._write("$ " + shell_cmd + "\n", "cmd")
        self._write("  (cwd: " + cwd + ")\n\n", "meta")

        self.run_btn.configure(state="disabled")
        thread = threading.Thread(target=self._run_in_thread, args=(shell_cmd, cwd), daemon=True)
        thread.start()

    def _run_in_thread(self, shell_cmd, cwd):
        try:
            result = subprocess.run(
                shell_cmd,
                shell=True,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
            self.after(0, self._render_result, result)
        except subprocess.TimeoutExpired:
            self.after(0, self._render_timeout)
        except Exception as exc:
            self.after(0, self._render_error, exc)

    def _render_result(self, result):
        if result.stdout:
            self._write(result.stdout)
        if result.stderr:
            self._write("[stderr]\n" + result.stderr, "err")
        self._write("\n[exit code: " + str(result.returncode) + "]\n\n", "meta")
        self.run_btn.configure(state="normal")

    def _render_timeout(self):
        self._write("ERROR: command timed out after " + str(TIMEOUT_SECONDS) + " seconds.\n\n", "err")
        self.run_btn.configure(state="normal")

    def _render_error(self, exc):
        self._write("ERROR: " + str(exc) + "\n\n", "err")
        self.run_btn.configure(state="normal")

    def _write(self, text, tag=None):
        if tag:
            self.output.insert(tk.END, text, tag)
        else:
            self.output.insert(tk.END, text)
        self.output.see(tk.END)


if __name__ == "__main__":
    DevRunner().mainloop()
