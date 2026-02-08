# Plan A: Generalize add-feature Skill + Create Shared refactor.md

## Context

The `add-feature` skill in `utils-agentic-support` currently assumes "add" semantics (branch names, commit messages, PR titles). It needs to support other verbs like "refactor" so the same workflow engine can drive architectural improvements, not just new feature scaffolding.

Additionally, feature-type files currently only live in project-specific `.claude/skills/feature-types/`. Generic cross-project feature-types (like `refactor.md`) should live in the shared `utils-agentic-support` repo.

## Changes

### 1. Generalize `SKILL.md` verb handling

**File**: `_external/utils-agentic-support/runtime/skills/add-feature/SKILL.md`

Allow the feature-type file to optionally define a `## Git` section with:

```markdown
## Git

- branch_prefix: refactor
- verb: Refactor
```

If absent, default to `branch_prefix: add`, `verb: Add`.

Update the hardcoded references:
- Step 7 branch: `git checkout -b {branch_prefix}-{FEATURE_TYPE}-{FEATURE_NAME}`
- Step 7 commit: `git commit -m "{verb} {FEATURE_NAME} {FEATURE_TYPE}"`
- Step 9 push: `git push -u origin {branch_prefix}-{FEATURE_TYPE}-{FEATURE_NAME}`
- Step 9 PR title: `"{verb} {FEATURE_NAME} {FEATURE_TYPE}"`
- Step 9 PR body: use `{verb}` instead of hardcoded "New"

### 2. Add shared feature-type lookup fallback

**File**: `_external/utils-agentic-support/runtime/skills/add-feature/SKILL.md`

Update Step 1 to check two locations in order:

1. `.claude/skills/feature-types/{FEATURE_TYPE}.md` (project-specific, takes precedence)
2. `.claude/general-skills/add-feature/feature-types/{FEATURE_TYPE}.md` (shared fallback)

If neither exists, list available types from both locations.

### 3. Create shared feature-types directory

**Directory**: `_external/utils-agentic-support/runtime/skills/add-feature/feature-types/`

This will be reachable via the symlink at `.claude/general-skills/add-feature/feature-types/`.

### 4. Create `refactor.md` shared feature-type

**File**: `_external/utils-agentic-support/runtime/skills/add-feature/feature-types/refactor.md`

A generic refactoring feature-type template:

```markdown
# Feature Type: Refactor

Instructions for executing a codebase refactoring or architectural improvement.

## Git

- branch_prefix: refactor
- verb: Refactor

## Naming

Derive these values from `FEATURE_NAME`:

- `REFACTOR_NAME`: The snake_case name (e.g., `get_fit_params`, `extract_config`)
- `BRANCH_NAME`: `refactor-{REFACTOR_NAME}`

## Requirements

Ask the user these questions:

1. **Goal**: What is the architectural problem this refactor solves?
2. **Scope**: Which files/modules are affected?
3. **Constraints**: Are there backward compatibility requirements?
4. **Prior analysis**: Is there an existing plan or design document? (If yes, read it.)

## References

Ask the user which files to read for context. At minimum, read:
- All files that will be modified
- The test files for those modules
- `DESIGN-PHILOSOPHY.md` if it exists

## Plan

The implementation plan should include:

1. **Files to modify** - every file path and what changes
2. **Files to create** - any new files needed
3. **Backward compatibility** - what breaks, what doesn't
4. **Migration** - do existing tests need updating?

## Implementation

Follow the plan. For each file:
1. Make the change
2. Verify tests still pass for that module before moving to the next

## Verification

Before declaring done, verify:

- [ ] Work is on a feature branch (not `main`)
- [ ] All modified files have corresponding test coverage
- [ ] No existing tests were deleted (only updated)
- [ ] All tests pass
- [ ] Lint passes
- [ ] PR created targeting `main`
- [ ] CI is green
```

### 5. Update skill metadata

**File**: `_external/utils-agentic-support/runtime/skills/add-feature/SKILL.md`

Update the description and name to reflect generalized usage:

```yaml
---
name: add-feature
description: Execute a feature workflow (add, refactor, etc.) following project-specific or shared feature-type patterns from .claude/skills/feature-types/.
argument-hint: [feature-type] [feature-name-in-snake-case]
allowed-tools: Read, Grep, Write, Edit, Bash, Glob
---
```

## Verification

1. `ls .claude/general-skills/add-feature/feature-types/` shows `refactor.md`
2. `/add-feature refactor test_name` picks up the shared `refactor.md`
3. `/add-feature model test_name` still picks up project-specific `model.md`
4. Branch names use `refactor-` prefix for refactor type, `add-` for model type
