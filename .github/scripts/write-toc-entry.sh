#!/bin/bash

# Build a two-level TOC: part (top folder) -> subfolder intro (real file) -> sections (pages/notebooks)
#
# NOTE: Jupyter Book's external TOC schema requires every item under `chapters:` to contain one of:
#   - file
#   - url
#   - glob
# Caption-only headings are not valid at that position.

set -eo pipefail

# Function to capitalize the first letter of each word (snake_case -> Title Case)
capitalize() {
  echo "$1" | awk -F'_' '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1' OFS=' '
}

# Collect notebooks/markdown files, ignoring build/git artifacts and the root intro
readarray -t notebook_list < <(find . -type f \( -name "*.ipynb" -o -name "*.md" \) \
  ! -path "./_build/*" ! -path "./.git/*" | sed 's|^\./||' | sort)

declare -A section_entries   # key: "parent|||subfolder" -> list of section lines (4-space indent)
declare -A direct_entries    # key: parent -> list of direct chapter lines (2-space indent)
declare -A subfolders        # key: parent -> space-delimited subfolder list
declare -A subfolder_intro   # key: "parent|||subfolder" -> intro file path (no ext)
declare -A parents_seen
parents=()

for file in "${notebook_list[@]}"; do
  # Skip the global intro; it is the book root
  [[ "$file" == "intro.md" ]] && continue

  # Require at least one slash so we know the parent folder
  [[ "$file" != */* ]] && continue

  parent=${file%%/*}
  rest=${file#*/}

  # Track parents in stable order of discovery
  if [[ -z "${parents_seen[$parent]}" ]]; then
    parents_seen[$parent]=1
    parents+=("$parent")
  fi

  # If there is no deeper subfolder, treat the file as a direct chapter under the part
  if [[ "$rest" != */* ]]; then
    file_no_ext="${file%.*}"
    direct_entries[$parent]+="  - file: $file_no_ext\n"
    continue
  fi

  # Otherwise capture the subfolder and section entry
  subfolder=${rest%%/*}
  file_no_ext="${file%.*}"
  key="$parent|||$subfolder"

  # Skip subfolder intro pages from the nested section list (they are used as the parent item)
  if [[ "${rest}" == "${subfolder}/intro.md" ]]; then
    subfolder_intro[$key]="${parent}/${subfolder}/intro"
    continue
  fi

  # Track unique subfolders per parent
  if [[ " ${subfolders[$parent]} " != *" ${subfolder} "* ]]; then
    subfolders[$parent]+=" ${subfolder}"
  fi

  section_entries[$key]+="    - file: $file_no_ext\n"
done

# Write the TOC
{
  echo "format: jb-book"
  echo "root: intro"
  echo "parts:"

  # Sort parents alphabetically for deterministic output
  for parent in $(printf "%s\n" "${parents[@]}" | sort); do
    echo "- part: $(capitalize "$parent")"
    echo "  chapters:"

    # Direct chapters (files directly under the parent folder)
    if [[ -n "${direct_entries[$parent]:-}" ]]; then
      echo -e "${direct_entries[$parent]}"
    fi

    # Subfolder intro + sections per subfolder
    read -ra subs <<< "${subfolders[$parent]:-}"
    if (( ${#subs[@]} )); then
      for subfolder in $(printf "%s\n" "${subs[@]}" | sort); do
        key="$parent|||$subfolder"
        intro_no_ext="${subfolder_intro[$key]:-${parent}/${subfolder}/intro}"
        if [[ ! -f "${intro_no_ext}.md" ]]; then
          echo "ERROR: Missing required subfolder intro page: ${intro_no_ext}.md" >&2
          echo "Create it (minimal is fine) so the TOC can reference a real file." >&2
          exit 1
        fi

        echo "  - file: ${intro_no_ext}"
        echo "    sections:"
        # Only emit sections if there are pages/notebooks under this subfolder
        if [[ -n "${section_entries[$key]:-}" ]]; then
          echo -e "${section_entries[$key]}"
        fi
      done
    fi
  done
} > _toc.yml