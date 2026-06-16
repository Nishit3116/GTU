def progress_bar(current: int, total: int, label: str = "", width: int = 40) -> None:
    """Display a simple text progress bar."""
    if total == 0:
        return
    pct = min(100, int(100 * current / total))
    filled = int(width * current / total)
    bar = "█" * filled + "░" * (width - filled)
    print(f"{label}\n{bar} {current}/{total} ({pct}%)\n", end="")


def format_file_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
