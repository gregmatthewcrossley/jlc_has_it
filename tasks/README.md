# Task Management

This directory contains atomic user stories/tasks for building JLC Has It.

## Structure

- Each task is a YAML file with a unique ID
- Tasks are organized by phase (00-setup, 01-jlcpcb, 02-kicad, etc.)
- Dependencies are explicitly listed
- Each task should be completable within a single Claude Code session

## Task Format

```yaml
id: task-001
phase: 0
title: Short descriptive title
description: Detailed description of what needs to be done
dependencies: []  # List of task IDs that must be completed first
acceptance_criteria:
  - Criterion 1
  - Criterion 2
estimated_complexity: low|medium|high
status: pending|in_progress|completed
notes: Additional context for implementers
```

## Phases

- **Phase 0**: Project Setup
- **Phase 1**: JLCPCB Integration
- **Phase 2**: KiCad File Handling
- **Phase 3**: Component Search
- **Phase 4**: Library Source Integration
- **Phase 5**: CLI Interface
- **Phase 6**: Natural Language Processing

## Usage

Subagents should:
1. Read the task YAML file
2. Follow acceptance criteria strictly
3. Update status field when complete
4. Note any deviations in the notes field
