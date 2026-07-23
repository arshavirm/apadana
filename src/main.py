import tkinter as tk
from tkinter import ttk
import apt


def on_select(event):
    item = tree.focus()
    if not item:
        return

    values = tree.item(item)

    name_var.set(values["text"])
    version_var.set(values["values"][0])

    description.delete("1.0", tk.END)
    description.insert(tk.END, f"{apt.get_package_info(values["text"])}")


root = tk.Tk()
root.title("Apadana Package Manager")
root.geometry("1100x700")
root.minsize(900, 600)

style = ttk.Style()
style.theme_use("clam")

style.configure(
    "Treeview",
    rowheight=28,
    font=("Segoe UI", 10),
)

style.configure(
    "Treeview.Heading",
    font=("Segoe UI", 10, "bold"),
)


header = ttk.Frame(root, padding=15)
header.pack(fill="x")

ttk.Label(
    header,
    text="Apadana Package Manager",
    font=("Segoe UI", 22, "bold"),
).pack(anchor="w")

ttk.Label(
    header,
    text="Install, remove and update software on your computer.",
    font=("Segoe UI", 10),
).pack(anchor="w", pady=(5, 0))


toolbar = ttk.Frame(root, padding=(15, 8))
toolbar.pack(fill="x")

ttk.Button(toolbar, text="Install").pack(side="left", padx=4)

ttk.Button(toolbar, text="Remove").pack(side="left", padx=4)

ttk.Button(toolbar, text="Update").pack(side="left", padx=4)

ttk.Label(toolbar).pack(side="left", expand=True)

ttk.Label(toolbar, text="Search").pack(side="left")

search = ttk.Entry(toolbar, width=35)
search.insert(0, "Search packages...")
search.pack(side="left", padx=(5, 0))

main = ttk.PanedWindow(root, orient="horizontal")
main.pack(fill="both", expand=True, padx=10, pady=10)


left = ttk.Frame(main)
main.add(left, weight=3)

tree = ttk.Treeview(
    left,
    columns=("Version",),
    show="tree headings",
)

tree.heading("#0", text="Package")
tree.heading("Version", text="Version")

tree.column("#0", width=350)
tree.column("Version", width=180, anchor="center")

scrollbar = ttk.Scrollbar(left, command=tree.yview)

tree.configure(yscrollcommand=scrollbar.set)

tree.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

pkgs = apt.get_installed_packages()

for pkg in pkgs:
    tree.insert(
        "",
        "end",
        text=pkg["name"],
        values=(pkg["version"],),
    )

tree.bind("<<TreeviewSelect>>", on_select)

right = ttk.Frame(main, padding=15)
main.add(right, weight=2)

ttk.Label(
    right,
    text="Package Information",
    font=("Segoe UI", 15, "bold"),
).pack(anchor="w")

ttk.Separator(right).pack(fill="x", pady=10)

name_var = tk.StringVar(value="No package selected")
version_var = tk.StringVar(value="-")

ttk.Label(
    right,
    text="Name",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

ttk.Label(
    right,
    textvariable=name_var,
).pack(anchor="w", pady=(0, 10))

ttk.Label(
    right,
    text="Installed Version",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

ttk.Label(
    right,
    textvariable=version_var,
).pack(anchor="w", pady=(0, 10))

ttk.Label(
    right,
    text="Description",
    font=("Segoe UI", 10, "bold"),
).pack(anchor="w")

description = tk.Text(
    right,
    height=14,
    wrap="word",
)

description.pack(fill="both", expand=True)

description.insert(
    "1.0",
    "Select a package to view information.",
)

status = ttk.Label(
    root,
    text=f"✓ Ready\t|\t{len(pkgs)} installed packages",
    relief="sunken",
    anchor="w",
    padding=6,
)

status.pack(fill="x", side="bottom")


if __name__ == "__main__":
    root.mainloop()
