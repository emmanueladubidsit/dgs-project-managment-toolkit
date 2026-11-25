# {name}

## Project tracker (read by the DGS workspace)

Keep a progress report and plan in `docs/project-management/PROGRESS-AND-PLAN-YYYY-MM-DD.md`
(the date is the day the file was written). The DGS workspace reads the newest one when you
press **Refresh tracker** and proposes task, milestone and work-log updates for approval. Use
exactly the structure below so it can be read reliably.

Rules:

1. **Never invent work, hours, dates or decisions.** Record only what was actually done, with
   evidence (worklog, commit, file). If a working day has no record, write `No record`.
2. **Working days are Monday to Friday.** Work done on a Saturday or Sunday goes in the
   following Monday's row, starting with `**Carried from Sat 21:**`.
3. **Work done:** one table per week, under a heading with the dates, e.g.
   `## 1. Week 1 (Mon 16 to Fri 20 Nov)`, then
   `| Day | What was done | Evidence |`. The day cell is `Wed 18`. Write each piece of work
   as its own short sentence ending with a full stop. Mention task IDs (e.g. `ISSUE-0004`)
   when the work relates to a tracked task.
4. **Milestone status:** under `**Week 1 milestone ("baseline and scope"):**`, one bullet per
   criterion: `- Criterion: **Verified**`, `**In progress**`, `**Not started**` or
   `**Blocked**`. Mark something Verified only when it has been checked.
5. **Plan:** one heading per week with the milestone code, e.g.
   `### Week 3 (30 Nov to 4 Dec), M3: identity and access`, then `| Day | Task |` rows (one
   row per working day). Holidays: `Holiday: no planned work.` Optional success criteria:
   `**M3 success criteria (Fri 4):** criterion one; criterion two`.
6. Label anything not yet agreed as **Proposed**. Update the file at the end of every working
   session; start a new dated file when you rewrite the plan.
