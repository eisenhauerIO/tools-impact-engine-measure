# Full Validation Workflow

This workflow ensures the overall integrity of the repository. If any step fails, stop immediately and ask for user input before proceeding.

All steps must be run inside a freshly pruned hatch environment to ensure a clean and reproducible state.

## Steps

### 1. Prune the Hatch Environment

Run:
```bash
hatch env prune
```
This removes all existing environments and ensures a clean start.

### 2. Check for Uncommitted or Untracked Files

Run:
```bash
git status --porcelain
```
If any files are listed (output is not empty), STOP. This means there are either uncommitted changes or files not under version control (untracked files).

Ask the user how to proceed (commit, stash, discard changes, or add untracked files to version control).

### 3. Run the Full Test Suite

Run:
```bash
hatch run pytest science/tests/ -v
```
If any test fails (non-zero exit code), STOP. Ask the user for input before continuing.

### 4. Run Demo Workflow Scripts

Run all workflow scripts in the demo directory:
```bash
cd science/demo && for f in workflow*.py; do hatch run python "$f"; done
```
If any demo script fails (non-zero exit code), STOP. Ask the user for input before continuing.

### 5. Verify Documentation Builds

Build the Sphinx documentation:
```bash
cd documentation && hatch -e docs run sphinx-build -b html . _build/html
```
If the build fails (non-zero exit code), STOP. Warnings are acceptable, only errors require stopping.

### 6. Clean Untracked Files and Directories

Run:
```bash
git clean -xdf
```
This removes all untracked files and directories, ensuring a pristine working directory.

## Notes

- CI/CD already validates tests and documentation on push/PR (see `.github/workflows/`)
