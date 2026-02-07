## Development

Always use the hatch environment for running tests, linting, and other dev tasks:
- Run tests: `hatch run test`
- Format: `hatch run format`
- Lint: `hatch run lint`

Never use bare `pytest`, `black`, or `ruff` directly — always go through `hatch run`.

## Skills & Subagents

### General (shared across projects)
- Skills: .claude/general-skills/
- Subagents: .claude/general-subagents/

### Project-specific
- Skills: .claude/skills/

To invoke a subagent, read its .md file and follow its instructions.
General resources take precedence unless a project-specific skill covers the same topic.