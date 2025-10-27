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

Phase 2: Library Integration ✅
├── 02-001: Copy libraries to KiCad projects ✅

Phase 3: Component Search
├── 03-001: Basic search (depends on 01-002, 01-003)
│   ├── 03-002: Spec filtering
│   └── 03-003: Ranking algorithm

Phase 4: Library Downloading ✅
├── 04-001: Integrate easyeda2kicad downloader ✅

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

Phase 8: Schema Optimization & Advanced Filtering 🚀
├── 08-001: Optimize schema (denormalization + indexes)
│   ├── 08-002: Package filtering (depends on 08-001)
│   └── 08-003: Attribute filtering (depends on 08-001)
```

## Recommended Execution Order

### Completed ✅ (15 tasks)
1. ✅ 00-001 (Init project)
2. ✅ 00-002 (Testing)
3. ✅ 00-003 (Linting)
4. ✅ 01-001 (Research JLCPCB)
5. ✅ 01-003 (Data models)
6. ✅ 01-002 (JLCPCB client)
7. ✅ 02-001 (Copy libraries to KiCad projects)
8. ✅ 04-001 (Integrate easyeda2kicad downloader)
9. ✅ 06-001 (Query parser design)
10. ✅ 06-002 (Pattern parser)
11. ✅ 06-004 (Integrate NLP)
12. ✅ 07-001 (FTS5 indexing)
13. ✅ 07-002 (Pagination)

### Remaining (Priority Order) - 8 tasks

#### HIGH PRIORITY - Phase 8 (3 tasks)
1. **08-001** (Schema optimization) - CRITICAL! Fixes slow pagination tests (18s → <1s)
2. **08-002** (Package filtering) - Fast package filtering once schema is optimized
3. **08-003** (Attribute filtering) - Electrical spec-based filtering

#### OPTIONAL - Phase 5 (5 tasks)
4. **05-001** (CLI framework) - Optional, MCP is primary interface
5. **05-002** (Search command) - Optional CLI feature
6. **05-003** (Interactive selection) - Optional CLI feature
7. **05-004** (Add command) - Optional CLI feature
8. **05-005** (Config command) - Optional CLI feature

**Note:** Phase 3 tasks (03-001, 03-002, 03-003) are now complete. All MVP functionality is implemented!

## Critical Path (Remaining Work)

```
✅ ALL MVP PHASES COMPLETE! (Phases 0-7)

🚀 HIGH PRIORITY - Phase 8 (Schema Optimization):
08-001 (Optimize schema) ──→ 08-002 (Package filter) ──→ 08-003 (Attribute filter)
      ↓
   Fixes slow pagination tests (17-38s → <1s)
   Enables fast category/package/spec filtering

Optional enhancements:
05-001 (CLI framework) ──→ 05-002 (Search cmd) ──→ 05-003 (Selection)
                                                         ↓
                                                  05-004 (Add cmd)
                                                  05-005 (Config)
```

**MVP COMPLETE!** All 7 required phases are done (Phases 0-7)!

**Recommended next work:**
- **Phase 8 (3 tasks)**: Schema optimization and advanced filtering (10-14 hours, HIGH PRIORITY)
- **Phase 5 (5 tasks)**: Optional CLI interface (10-20 hours, OPTIONAL)

## Estimated Timeline (Remaining)

- **Low complexity**: 1-2 hours per task
- **Medium complexity**: 2-4 hours per task
- **High complexity**: 4-6 hours per task

**Phase 8 (08-001 through 08-003):** 10-14 hours (RECOMMENDED)
**Phase 5 CLI (05-001 through 05-005):** 10-20 hours (optional)
**Total remaining:** 10-34 hours depending on scope

**Recommendation:** Do Phase 8 first to fix slow pagination tests and enable advanced filtering. Then do Phase 5 CLI if scripting/automation is needed.
