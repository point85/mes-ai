"""Remove StepTransition hooks from useProductDef.ts"""
import re

path = "clients/design_time/src/hooks/useProductDef.ts"
content = open(path, encoding="utf-8").read()

# Remove 4 API import lines
content = content.replace(
    "  fetchStepTransitions,\n  createStepTransition,\n  updateStepTransition,\n  deleteStepTransition,\n",
    ""
)
# Remove 2 type import lines
content = content.replace("  StepTransitionCreate,\n  StepTransitionUpdate,\n", "")
# Remove KEYS.transitions line
transitions_key = '  transitions: (stepId: string) => ["stepTransitions", stepId] as const,\n'
content = content.replace(transitions_key, "")

# Remove the hook functions block (Step Transitions section)
section_start = "\n// \u2500\u2500\u2500 Step Transitions"
section_end = "\n// \u2500\u2500\u2500 Route\u2013Material Assignments"
si = content.index(section_start)
ei = content.index(section_end)
print(f"Removing block from {si} to {ei}")
content = content[:si] + content[ei:]

open(path, "w", encoding="utf-8").write(content)
print("Done")
