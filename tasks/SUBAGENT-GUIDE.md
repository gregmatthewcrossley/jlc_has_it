# Using Subagents to Execute Tasks

This guide explains how to use Claude Code subagents to work through the task list efficiently.

## Basic Workflow

### 1. Select a Task

Review `INDEX.md` or `DEPENDENCIES.md` to choose an appropriate task. Consider:
- Dependencies (all prerequisite tasks must be complete)
- Your current focus area (stay in one phase for context)
- Parallelization opportunities

### 2. Launch Subagent with Task

Pass the task file contents to a subagent:

```
Read task file tasks/00-001-init-python-project.yaml and execute it fully.
Follow all acceptance criteria. Update the status field to 'completed' when done.
```

Or more directly:

```
Complete task 00-001 from the tasks directory.
```

### 3. Monitor Progress

Subagents should:
- Update task status from `pending` → `in_progress` → `completed`
- Add notes about any deviations or issues
- Run tests to verify acceptance criteria
- Not move to next task without explicit instruction

### 4. Verify Completion

After subagent completes:
- Check all acceptance criteria are met
- Run tests yourself if skeptical
- Review code quality
- Mark task as complete in your tracking system

## Tips for Effective Subagent Usage

### Provide Clear Context

Good prompt:
```
Complete task 02-002 (Implement S-expression parser).
You'll find the full spec in tasks/02-002-sexpr-parser.yaml.
Follow all acceptance criteria exactly.
Reference docs/kicad-formats.md from task 02-001 for context.
```

### Handle Dependencies Explicitly

```
Before starting task 05-002 (search command), verify that:
- Task 05-001 (CLI framework) is complete
- Task 03-001 (basic search) is complete
If not, complete those first.
```

### Batch Related Tasks

For efficiency, you can have subagents complete sequential tasks:

```
Complete tasks 00-001, 00-002, and 00-003 in order.
These are all Phase 0 setup tasks with clear dependencies.
```

### Parallelize Independent Work

Launch multiple subagents simultaneously for independent tasks:

**Session 1:**
```
Complete task 01-001 (Research JLCPCB API)
```

**Session 2:**
```
Complete task 02-001 (Research KiCad formats)
```

**Session 3:**
```
Complete task 04-001 (Research library sources)
```

All three research tasks can run in parallel.

## Task Status Management

### Update Status in YAML

Subagents should update the `status` field:

```yaml
# Before starting
status: pending

# While working
status: in_progress

# After completion
status: completed
```

### Track Outside YAML (Optional)

You may prefer to track status externally:
- Spreadsheet
- Project management tool
- Git commit messages
- Separate status.yaml file

The YAML status field is optional - it's there for convenience.

## Common Patterns

### Pattern 1: Research Task
```
Research tasks (01-001, 02-001, 04-001, 06-001) produce documentation.
Subagent should:
1. Investigate thoroughly (web search, library exploration)
2. Create docs/ file with findings
3. Include code examples, URLs, sample data
4. Mark as complete only when doc is comprehensive
```

### Pattern 2: Implementation Task
```
Implementation tasks need working code.
Subagent should:
1. Write code following acceptance criteria
2. Write tests that verify each criterion
3. Run tests and ensure they pass
4. Run linting tools
5. Mark complete only when all criteria met
```

### Pattern 3: Integration Task
```
Integration tasks (05-004, 06-004) connect multiple components.
Subagent should:
1. Verify all dependencies exist and work
2. Create integration layer
3. Write integration tests
4. Test end-to-end workflow
5. Document usage
```

## Troubleshooting

### "Dependency not met"
If a task depends on incomplete work, either:
- Complete the dependency first, or
- Mock the dependency for now and add TODO

### "Acceptance criteria unclear"
Ask the user for clarification. Update the task YAML with clarifications for future reference.

### "Task too large for context"
If a task is too complex:
1. Break it into subtasks
2. Create new task files (e.g., 02-002a, 02-002b)
3. Update dependencies
4. Complete incrementally

### "External service unavailable"
For tasks requiring external APIs (JLCPCB, library sources):
- Document the API structure
- Create comprehensive mocks
- Add TODO for live testing
- Mark task complete with note about mocking

## Example Session

```
User: I want to get started on this project. What should we do first?

Claude: Let's start with Phase 0 setup tasks. I'll complete tasks 00-001, 00-002,
and 00-003 to establish the Python project structure.

[Claude completes tasks, updates status to 'completed']

User: Great! Now let's work on JLCPCB integration.

Claude: I'll start with task 01-001 to research the JLCPCB API, then move to
01-003 and 01-002. Should I launch these as separate subagents or work through
them sequentially?

User: Launch 01-001 and 02-001 in parallel since they're both research tasks.

Claude: [Launches two subagents, both research tasks complete in parallel]
```

## Quality Standards

Ensure subagents follow these standards:

### Code Quality
- Type hints on all functions
- Docstrings for public APIs
- Pass black, ruff, mypy checks
- Follow SOLID principles (per global CLAUDE.md)

### Testing
- Every module has test coverage
- Tests are independent and can run in isolation
- Use mocks for external services
- pytest runs without errors

### Documentation
- README updated if user-facing changes
- Code comments for complex logic
- Task notes updated with any issues or decisions

## Quick Reference Commands

```bash
# View all tasks
cat tasks/INDEX.md

# View dependencies
cat tasks/DEPENDENCIES.md

# Start a specific task
cat tasks/00-001-init-python-project.yaml

# Check current status (if using YAML tracking)
grep -r "status: completed" tasks/*.yaml | wc -l
grep -r "status: in_progress" tasks/*.yaml
grep -r "status: pending" tasks/*.yaml

# Update task status manually
# Edit the YAML file and change status field
```

## Next Steps

1. Read `INDEX.md` for task overview
2. Read `DEPENDENCIES.md` for execution order
3. Start with Phase 0 tasks (00-001, 00-002, 00-003)
4. Use subagents for parallel research tasks
5. Build incrementally, testing as you go