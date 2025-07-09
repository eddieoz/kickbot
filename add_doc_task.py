#!/usr/bin/env python

"""
Script to add a documentation task to tasks.md
"""

import re

# The task to add
new_task = """- [x] 7. **[Documentation]** Create comprehensive authentication documentation
   * Document both traditional username/password authentication
   * Document OAuth 2.0 with PKCE authentication process
   * Include examples and explanations of security features
"""

# Read the tasks.md file
with open('docs/tasks.md', 'r') as f:
    content = f.read()

# Find the position to insert the new task
target_section = "**Remaining Tasks:**"
task_6_end = "   * Add automatic refresh before token expiration"

# Create a pattern to find the right position
pattern = f"{task_6_end}\n\n"
replacement = f"{task_6_end}\n{new_task}\n\n"

# Replace the pattern with our new content
modified_content = content.replace(pattern, replacement)

# Write the modified content back to the file
with open('docs/tasks.md', 'w') as f:
    f.write(modified_content)

print("Documentation task added to tasks.md") 