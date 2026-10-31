#!/usr/bin/env bash
set -euo pipefail

project_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
backup_dir="${project_root%/*}/FOMUWISE-legacy-backup-$(date +%Y%m%d-%H%M%S)"
move_anything=0

if [[ -e "$project_root/vite@latest" || -e "$project_root/package-lock.json" ]]; then
  mkdir -p "$backup_dir"
  if [[ -e "$project_root/vite@latest" ]]; then
    mv -- "$project_root/vite@latest" "$backup_dir/"
    move_anything=1
  fi
  if [[ -e "$project_root/package-lock.json" ]]; then
    mv -- "$project_root/package-lock.json" "$backup_dir/"
    move_anything=1
  fi
fi

if [[ "$move_anything" -eq 1 ]]; then
  printf 'Moved the old Vite starter files to: %s\n' "$backup_dir"
else
  printf 'No old Vite starter files found; nothing to archive.\n'
fi
