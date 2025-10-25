# Task Dependencies

This document visualizes the task dependencies to help plan execution order.

## Dependency Graph

```
Phase 0: Project Setup
├── 00-001: Init Python project
│   ├── 00-002: Setup testing
│   └── 00-003: Setup linting

Phase 1: JLCPCB Integration
├── 01-001: Research JLCPCB API
│   ├── 01-002: JLCPCB client basic
│   └── 01-003: Component data model

Phase 2: KiCad File Handling
├── 02-001: Research KiCad formats
│   ├── 02-002: S-expression parser
│   │   ├── 02-003: Symbol reader
│   │   │   └── 02-004: Symbol writer
│   │   └── 02-005: Footprint handler
│   └── 02-006: Project integration

Phase 3: Component Search
├── 03-001: Basic search (depends on 01-002, 01-003)
│   ├── 03-002: Spec filtering
│   └── 03-003: Ranking algorithm

Phase 4: Library Source Integration
├── 04-001: Research library sources
│   └── 04-002: Library downloader
└── 04-003: Generic symbol generator (depends on 02-004)

Phase 5: CLI Interface
├── 05-001: CLI framework
│   ├── 05-002: Search command (depends on 03-001)
│   │   └── 05-003: Interactive selection
│   │       └── 05-004: Add command (depends on 04-002, 02-006)
│   └── 05-005: Config command

Phase 6: Natural Language Processing
├── 06-001: Query parser design (depends on 03-001)
│   ├── 06-002: Pattern-based parser
│   │   ├── 06-003: LLM parser (optional)
│   │   └── 06-004: Integrate NLP search (depends on 05-002)
```

## Recommended Execution Order

### Sprint 1: Foundation (Phase 0-1)
1. 00-001 (Init project)
2. 00-002 (Testing)
3. 00-003 (Linting)
4. 01-001 (Research JLCPCB) - can start in parallel with 00-002/00-003
5. 01-003 (Data models)
6. 01-002 (JLCPCB client)

### Sprint 2: KiCad Integration (Phase 2)
7. 02-001 (Research KiCad) - can start early in parallel
8. 02-002 (S-expr parser)
9. 02-003 (Symbol reader)
10. 02-004 (Symbol writer)
11. 02-005 (Footprint handler)
12. 02-006 (Project integration)

### Sprint 3: Search & Library Sources (Phases 3-4)
13. 03-001 (Basic search)
14. 03-002 (Spec filtering)
15. 03-003 (Ranking)
16. 04-001 (Research library sources) - can start in parallel
17. 04-002 (Library downloader)
18. 04-003 (Generic symbol generator)

### Sprint 4: CLI (Phase 5)
19. 05-001 (CLI framework)
20. 05-002 (Search command)
21. 05-003 (Interactive selection)
22. 05-005 (Config command) - can be done in parallel with 05-002/05-003
23. 05-004 (Add command) - final integration

### Sprint 5: Natural Language (Phase 6)
24. 06-001 (Query parser design)
25. 06-002 (Pattern parser)
26. 06-004 (Integrate NLP)
27. 06-003 (LLM parser) - optional, can be skipped initially

## Parallelization Opportunities

These tasks can be worked on in parallel by different agents/sessions:

**Early parallel work:**
- 01-001 (Research JLCPCB) + 02-001 (Research KiCad) + 04-001 (Research library sources)
- All Phase 0 tasks (00-001, 00-002, 00-003) after initial project creation

**Mid-project parallel work:**
- 03-002 + 03-003 (both depend on 03-001)
- 02-005 + 02-004 (both depend on 02-002)
- 05-005 + 05-002 (both depend on 05-001)

## Critical Path

The longest dependency chain (critical path):
```
00-001 → 01-001 → 01-002 → 03-001 → 05-001 → 05-002 → 05-003 → 05-004
                                                                    ↑
                                    02-001 → 02-002 → 02-004 → 04-003
                                                        ↓
                                                     02-006 ────────┘
                                                        ↑
                                                     04-001 → 04-002
```

Total: ~17 tasks in critical path

## Estimated Timeline

- **Low complexity**: 1-2 hours per task
- **Medium complexity**: 2-4 hours per task
- **High complexity**: 4-8 hours per task

**Total estimated effort**: 70-120 hours
**With parallelization**: 50-80 hours
**MVP (without Phase 6)**: 50-70 hours
