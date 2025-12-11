# OneTaskAtATime
**A project to create a focused, no-frills to-do list GUI desktop app**

Many users spend too much time managing task *lists*, when they should just pick a single task and execute it. The overarching goal of this app is to aid the user in focusing on one task.

---

In David Allen's popular "Getting Things Done" (GTD) system, strong emphasis is placed on filtering a to-do list to determine the "Next Action" that is appropriate for your current working environment (referred to as "Context"). In theory, this makes perfect sense: it is well-known that "multitasking" is counter-productive, and therefore people should strive to focus on doing one thing at a time. Therefore, THE core feature of this app is a Focus Mode that presents the user with one task at a time, hence the app's name-sake.

Note: In a true dogmatic GTD system, a user would have an inbox for all of their informational inputs, which would then be sorted into Actionable Inputs and Non-Actionable Inputs. This is why many practitioners of GTD insist on incorporating their system into an email inbox or filing system. In my opinion, this sorting just adds an unnecessary step for most people. This app assumes that users are inputting actual tasks, not unsorted Inputs.

---

**Several usability problems need to be addressed in this app:**

1. **Problem/Background:** Many do-to apps allow users to rank priority and urgency in an attempt to enforce a logical order of presentation, but in practice users often end up with a lot of high-priority / high-urgency tasks, defeating the purpose of ranking tasks in the first place.
**Proposed Solution:** The app will attempt to resolve this issue by presenting the user with a list of two tasks that have equal top-ranked importance (highest priority and highest urgency), asking them to choose the task that is higher priority. The app will then decrement the other task's priority (by half a point by default, or by a user-specified value > 0). The app will continue this process, comparing the top-ranked tasks until the user has only one option or completes a task.
- Priority will be scored on a 3-point scale, where High = 3, Medium = 2, and Low = 1
- Urgency will be scored based on a count of days until the task due date. The task(s) with the lowest counts (including negative values for overdue tasks) shall be assigned an urgency score of 3, with the other tasks scored on a normalized scale (latest due date = 1).

1. **Problem/Background:** Tasks that are not immediately actionable or low-priority/low-urgency tend to end up in a purgatory state, left to rot and fester. GTD argues that these tasks should be sorted into the following states:
- Deferred Tasks, which can only be completed after a specified Start Date
- Delegated Tasks, which are assigned to another person and require a scheduled follow-up conversation (which in and of itself is a separate Deferred Task)
- Someday/Maybe, for tasks that are not currently actionable, but *might* become actionable at an unknown date in the future
- Trash, for tasks that the user deems unnecessary and which therefore should be removed from consideration
The problem with this bucketing approach is that most apps fail to routinely resurface tasks in those buckets to the user. 
**Proposed Solution:** This app will attempt to fix that problem by resurfacing tasks in those buckets strategically.

1. **Problem/Background:** In attempting to execute the Next Action, GTD practitioners often find that their next task is comprised of multiple complex steps -- and therefore must be considered as a collection of tasks within a "Project". The heirarchy imposed can lead to difficulties with both prioritization and navigation, as tasks become buried within Projects, Phases, and ever-deeper levels of "organization". Task heirarchies add needless complexity and are detrimental to productivity.
**Proposed Solution:** While there may be some value in tracking Projects as a form of tag meta-data (for filtering purposes), the structure of the master task list should be kept flat.
Similarly, organizing tasks by work environment "Context" should also be done with tagging, rather than a hierarchy. A task may have only one Context, while a given Context may apply to as many tasks as the user desires.

1. **Problem/Background:** Tasks can also be difficult to complete due to various blockers and/or dependencies on other tasks. In failing to confront users when they delay a task, most to-do list apps fail to capture the user's reason for doing so. 
**Proposed Solution:** This app proposes to fix this problem by presenting users with prompts to explain their decision when they delay a task.
- If a user responds (with a button) that a delayed task involves multiple subtasks, the interface should prompt them to enter those tasks, pick the Next Action and then delete the original task. Again, the goal here is to reduce task heirarchy.
- If a user responds (with a button) that they encountered a blocker, the interface should prompt the user to create a new task to log and address that blocker.
- If a user responds (with a button) that the task depends on completion of one or more tasks, the interface should prompt the user to choose or create the upstream task(s).

