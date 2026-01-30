import os

def is_empty(path):
    """Check if a file or folder is empty."""
    if os.path.isdir(path):
        return len(os.listdir(path)) == 0
    else:
        return os.path.getsize(path) == 0


def generate_tree(path, prefix=""):
    entries = sorted(os.listdir(path))
    files = [e for e in entries if not os.path.isdir(os.path.join(path, e))]
    folders = [e for e in entries if os.path.isdir(os.path.join(path, e))]
    ordered = files + folders  # Files first, folders after

    tree_lines = []

    for i, entry in enumerate(ordered):
        full_path = os.path.join(path, entry)
        connector = "├── " if i < len(ordered) - 1 else "└── "
        is_dir = os.path.isdir(full_path)

        # Determine display name
        display_name = entry + "/" if is_dir else entry

        # Handle .git folder special case
        if is_dir and (entry == ".git") or entry == "__pycache__":
            comment = "  # children ignored"
            tree_lines.append(prefix + connector + display_name + comment)
            continue  # do not recurse into .git

        # Normal empty check
        empty_comment = "  # Empty" if is_empty(full_path) else ""
        tree_lines.append(prefix + connector + display_name + empty_comment)

        # Recurse only if it's a directory and not .git
        if is_dir:
            extension = "│   " if i < len(ordered) - 1 else "    "
            sub_tree = generate_tree(full_path, prefix + extension)
            tree_lines.extend(sub_tree)

            if i < len(ordered) - 1:
                tree_lines.append(prefix + "│")

    return tree_lines


def export_hierarchy(root_folder):
    if not os.path.exists(root_folder):
        print(f"Error: '{root_folder}' does not exist.")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, "folder_hierarchy.txt")

    folder_name = os.path.basename(os.path.normpath(root_folder))
    empty_comment = "  # Empty" if is_empty(root_folder) else ""
    tree = [f"{folder_name}/" + empty_comment]
    tree.extend(generate_tree(root_folder))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(tree))

    print(f"✅ Folder hierarchy exported to '{output_file}'")


if __name__ == "__main__":
    folder_path = input("Enter the folder path: ").strip()
    export_hierarchy(folder_path)
