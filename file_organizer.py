"""
File Organizer
Sorts the files directly inside a chosen folder into subfolders by year,
based on each file's last-modified date. Subfolders are left alone, so it
won't touch anything that's already organized.

"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

LOG_FILENAME = ".file_organizer_log.json"


def organize_by_year(folder: Path, dry_run: bool = False) -> None:
    if not folder.is_dir():
        print(f"'{folder}' is not a valid folder.")
        return

    moved_count = 0
    moves = []

    for item in folder.iterdir():
        if item.is_dir() or item.name == LOG_FILENAME:
            continue  # leave existing subfolders (and our own log file) untouched

        year = datetime.fromtimestamp(item.stat().st_mtime).year
        target_dir = folder / str(year)
        target_path = target_dir / item.name

        if target_path.exists():
            print(f"Skipped (already exists): {item.name}")
            continue

        if dry_run:
            print(f"Would move: {item.name} -> {year}/")
        else:
            target_dir.mkdir(exist_ok=True)
            shutil.move(str(item), str(target_path))
            moves.append({"src": str(item), "dst": str(target_path)})
            print(f"Moved: {item.name} -> {year}/")

        moved_count += 1

    action = "Would move" if dry_run else "Moved"
    print(f"\n{action} {moved_count} file(s).")

    if not dry_run and moves:
        log_path = folder / LOG_FILENAME
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(moves, f, indent=2)
        print(f"Logged this run to {log_path.name} -- run with --undo to reverse it.")


def undo_last_run(folder: Path) -> None:
    log_path = folder / LOG_FILENAME
    if not log_path.exists():
        print("No previous run found to undo in this folder.")
        return

    with open(log_path, "r", encoding="utf-8") as f:
        moves = json.load(f)

    restored = 0
    for move in reversed(moves):
        current_path = Path(move["dst"])
        original_path = Path(move["src"])

        if not current_path.exists():
            print(f"Skipped (already missing): {current_path.name}")
            continue

        shutil.move(str(current_path), str(original_path))
        print(f"Restored: {current_path.name} -> {original_path.parent}")
        restored += 1

    # clean up year folders left empty by the undo
    for move in moves:
        year_dir = Path(move["dst"]).parent
        if year_dir.exists() and not any(year_dir.iterdir()):
            year_dir.rmdir()

    log_path.unlink()
    print(f"\nRestored {restored} file(s). Undo log cleared.")


def flatten_years(folder: Path, dry_run: bool = False) -> None:
    """Fallback undo for runs made before the log existed: moves files back
    out of any top-level 4-digit year folder (e.g. '2024') and removes the
    folder if it ends up empty. Other subfolders are left untouched."""
    if not folder.is_dir():
        print(f"'{folder}' is not a valid folder.")
        return

    restored = 0
    for sub in sorted(folder.iterdir()):
        if not (sub.is_dir() and sub.name.isdigit() and len(sub.name) == 4):
            continue

        for item in sub.iterdir():
            target = folder / item.name
            if target.exists():
                print(f"Skipped (name collision): {item.name}")
                continue

            if dry_run:
                print(f"Would restore: {item.name} -> {folder}\\")
            else:
                shutil.move(str(item), str(target))
                print(f"Restored: {item.name} -> {folder}\\")
            restored += 1

        if not dry_run and sub.exists() and not any(sub.iterdir()):
            sub.rmdir()

    action = "Would restore" if dry_run else "Restored"
    print(f"\n{action} {restored} file(s) from year folders.")


def main():
    parser = argparse.ArgumentParser(description="Sort files in a folder into subfolders by year.")
    parser.add_argument("folder", help="Path to the folder you want organized")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without moving files")
    parser.add_argument("--undo", action="store_true", help="Undo the last real run in this folder (needs the log)")
    parser.add_argument(
        "--flatten-years",
        action="store_true",
        help="Fallback undo: move files out of 4-digit year folders back to the top level (use when no log exists)",
    )
    args = parser.parse_args()

    folder = Path(args.folder)
    if args.undo:
        undo_last_run(folder)
    elif args.flatten_years:
        flatten_years(folder, dry_run=args.dry_run)
    else:
        organize_by_year(folder, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
