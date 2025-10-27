# Task Dependencies

This document visualizes the task dependencies to help plan execution order.

## Dependency Graph

```
Phase 0: Project Setup ✅
├── 00-001: Init Python project ✅
│   ├── 00-002: Setup testing ✅
│   └── 00-003: Setup linting ✅

Phase 1: JLCPCB Integration ✅
├── 01-001: Research JLCPCB API ✅
│   ├── 01-002: JLCPCB client basic ✅
│   └── 01-003: Component data model ✅

Phase 2: Library Integration
├── 02-001: Copy libraries to KiCad projects

Phase 3: Component Search
├── 03-001: Basic search (depends on 01-002, 01-003)
│   ├── 03-002: Spec filtering
│   └── 03-003: Ranking algorithm

Phase 4: Library Downloading
├── 04-001: Integrate easyeda2kicad downloader

Phase 5: CLI Interface (optional)
├── 05-001: CLI framework
│   ├── 05-002: Search command (depends on 03-001)
│   │   └── 05-003: Interactive selection
│   │       └── 05-004: Add command (depends on 04-001, 02-001)
│   └── 05-005: Config command

Phase 6: Natural Language Processing ✅
├── 06-001: Query parser design ✅
├── 06-002: Pattern-based parser ✅
├── 06-003: LLM parser (obsolete)
└── 06-004: Integrate NLP search ✅

Phase 7: Performance Optimization ✅
├── 07-001: FTS5 search indexing ✅
└── 07-002: Pagination support ✅
```

## Recommended Execution Order

### Completed ✅
1. ✅ 00-001 (Init project)
2. ✅ 00-002 (Testing)
3. ✅ 00-003 (Linting)
4. ✅ 01-001 (Research JLCPCB)
5. ✅ 01-003 (Data models)
6. ✅ 01-002 (JLCPCB client)
7. ✅ 06-001 (Query parser design)
8. ✅ 06-002 (Pattern parser)
9. ✅ 06-004 (Integrate NLP)
10. ✅ 07-001 (FTS5 indexing)
11. ✅ 07-002 (Pagination)

### Remaining (Priority Order)
1. **02-001** (Copy libraries to KiCad projects) - Simple file operations
2. **04-001** (Integrate easyeda2kicad downloader) - Use existing tool
3. **03-001** (Basic search) - Core search without complex filtering
4. **03-002** (Spec filtering) - Add filtering to search
5. **03-003** (Ranking) - Improve result ordering
6. **05-001** (CLI framework) - Optional, MCP is primary interface
7. **05-002** (Search command) - Optional CLI feature
8. **05-003** (Interactive selection) - Optional CLI feature
9. **05-005** (Config command) - Optional CLI feature
10. **05-004** (Add command) - Optional CLI feature

## Parallelization Opportunities

Remaining tasks can mostly be done in parallel:
- **02-001** (Copy libraries) - Standalone, simple file operations
- **04-001** (Integrate downloader) - Standalone, wraps existing tool
- **03-001, 03-002, 03-003** - Can start after 02-001 and 04-001
- **05-001 through 05-005** - Optional CLI, can be done anytime

## Critical Path (Remaining Work)

```
02-001 (Copy libraries) ──┐
                          └→ 05-004 (Add command - optional)
04-001 (Downloader) ──────┘

03-001 (Basic search) ──→ 03-002 (Filtering) ──→ 03-003 (Ranking)
```

**Critical path for MVP:** 2-3 tasks (02-001, 04-001, 03-001)
**With filtering/ranking:** 5 tasks
**With optional CLI:** 10 tasks

## Estimated Timeline (Remaining)

- **Low complexity**: 1-2 hours per task
- **Medium complexity**: 2-4 hours per task

**Remaining core tasks (02-001, 04-001, 03-001):** 6-10 hours
**With filtering/ranking (03-002, 03-003):** 10-18 hours
**With optional CLI (05-001 through 05-005):** 20-35 hours
**Total remaining:** 10-35 hours depending on scope

**Note:** Phase 6 (MCP) and Phase 7 (FTS5/Pagination) are already complete and functional
