import os
import json
import argparse
from datetime import datetime

# --- Configuration for file handling ---
# Add extensions of binary files you want to exclude from content capture
BINARY_FILE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico', '.webp',
    '.mp3', '.wav', '.ogg', '.mp4', '.avi', '.mov', '.mkv',
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
    '.zip', '.tar', '.gz', '.rar', '.7z',
    '.exe', '.dll', '.so', '.o', '.a', '.lib', '.jar',
    '.pyc', '.pyd', '.egg', '.whl',
    '.db', '.sqlite3',
    '.ipynb' # Jupyter notebooks can contain binary data and are large
}

def capture_project_as_markdown(project_path, ignore_dirs, ignore_files):
    """
    Analyzes a project directory and creates a human-readable Markdown representation.
    """
    snapshot_content = []
    project_name = os.path.basename(os.path.normpath(project_path))
    
    # --- 1. Header Information ---
    snapshot_content.append(f"# [PROMPT] ANALYZE THE FOLLOWING PYTHON PROJECT: {project_name}\n")
    snapshot_content.append(f"# SNAPSHOT CAPTURED ON: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    snapshot_content.append("-" * 80 + "\n")

    # --- 2. Directory Structure ---
    snapshot_content.append("## PROJECT DIRECTORY STRUCTURE\n\n")
    
    files_to_read = []
    for root, dirs, files in os.walk(project_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        level = root.replace(project_path, '').count(os.sep)
        if level > 0:
            indent = ' ' * 4 * (level - 1) + '|-- '
            snapshot_content.append(f"{indent}{os.path.basename(root)}/\n")
        
        sub_indent = ' ' * 4 * level + '|-- '
        for f in sorted(files):
            if f in ignore_files:
                continue
            snapshot_content.append(f"{sub_indent}{f}\n")
            if f.endswith('.py'):
                files_to_read.append(os.path.join(root, f))
    
    snapshot_content.append("\n" + "-" * 80 + "\n")

    # --- 3. Python File Contents ---
    snapshot_content.append("## PYTHON SCRIPT CONTENTS\n\n")
    if not files_to_read:
        snapshot_content.append("No Python (.py) files found in the project directory.\n")
    else:
        for file_path in sorted(files_to_read):
            relative_path = os.path.relpath(file_path, project_path)
            snapshot_content.append(f"### FILE: {relative_path}\n")
            snapshot_content.append("```python\n")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    snapshot_content.append(f.read())
            except Exception as e:
                snapshot_content.append(f"# Error reading file: {e}")
            snapshot_content.append("\n```\n\n")

    return "".join(snapshot_content)

def capture_project_as_json(project_path, ignore_dirs, ignore_files):
    """
    Analyzes a project directory and creates a size-efficient JSON representation.
    """
    project_name = os.path.basename(os.path.normpath(project_path))
    
    snapshot_data = {
        "metadata": {
            "projectName": project_name,
            "snapshotTimestampUTC": datetime.utcnow().isoformat() + "Z",
            "sourcePath": project_path
        },
        "files": []
    }

    for root, dirs, files in os.walk(project_path, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for filename in sorted(files):
            if filename in ignore_files:
                continue

            file_path = os.path.join(root, filename)
            relative_path = os.path.relpath(file_path, project_path).replace('\\', '/')
            
            file_info = {
                "path": relative_path,
                "content": None
            }

            _, extension = os.path.splitext(filename)
            if extension.lower() in BINARY_FILE_EXTENSIONS:
                file_info["encoding"] = "binary"
            else:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        file_info["content"] = f.read()
                    file_info["encoding"] = "utf-8"
                except UnicodeDecodeError:
                    file_info["encoding"] = "binary"
                except Exception as e:
                    file_info["error"] = f"Could not read file: {e}"

            snapshot_data["files"].append(file_info)
    
    return json.dumps(snapshot_data, indent=2)

def main():
    """
    Main function to parse command-line arguments and run the snapshot process.
    """
    # --- Hardcode your paths here ---
    # IMPORTANT: Use forward slashes `/` for paths, even on Windows.
    
    
    HARCODED_PROJECT_PATH = r"C:\Users\kkorz\Desktop\btesting\v1engine"
    HARCODED_OUTPUT_PATH = r"C:\Users\kkorz\Desktop\btesting\0snapshot\v1engine_snapshots"

    # --- Argument parser setup ---
    parser = argparse.ArgumentParser(
        description="Capture a snapshot of a project's structure and file contents.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '-f', '--format',
        type=str,
        choices=['md', 'json'],
        default='md', 
        help='The output format. `json` for machine-readable, `md` for Markdown. Defaults to json.'
    )

    args = parser.parse_args()

    # --- Use the hardcoded paths ---
    project_path = os.path.abspath(HARCODED_PROJECT_PATH)
    output_path = os.path.abspath(HARCODED_OUTPUT_PATH)

    # --- Path validation ---
    if HARCODED_PROJECT_PATH == "REPLACE_WITH_YOUR_FULL_PROJECT_PATH":
        print("Error: Please open the script and set the `HARCODED_PROJECT_PATH` variable.")
        return
        
    if not os.path.isdir(project_path):
        print(f"Error: Hardcoded project path '{project_path}' is not a valid directory.")
        return
    if not os.path.isdir(output_path):
        print(f"Error: Hardcoded output path '{output_path}' is not a valid directory.")
        return

    # --- Files/Dirs to ignore ---
    ignore_dirs = {'venv', '.venv', 'env', '__pycache__', '.git', '.idea', 'build', 'dist', 'node_modules', '.vscode'}
    ignore_files = {'.DS_Store'}
    
    snapshot_data = None
    file_extension = args.format

    # --- Generate snapshot ---
    if args.format == 'md':
        snapshot_data = capture_project_as_markdown(project_path, ignore_dirs, ignore_files)
    elif args.format == 'json':
        snapshot_data = capture_project_as_json(project_path, ignore_dirs, ignore_files)
    
    if snapshot_data:
        # Create the output file
        project_name = os.path.basename(os.path.normpath(project_path))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{project_name}_{timestamp}.{file_extension}"
        output_file_path = os.path.join(output_path, filename)

        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                f.write(snapshot_data)
            print(f"\nSuccessfully created project snapshot!")
            print(f"Format: {args.format.upper()}")
            print(f"File saved to: {output_file_path}")
        except IOError as e:
            print(f"Error writing to file: {e}")

if __name__ == "__main__":
    main()