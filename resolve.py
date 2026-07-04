import os
import re

layout_file = 'frontend/src/routes/(dashboard)/+layout.svelte'
with open(layout_file, 'r') as f:
    content = f.read()

content = re.sub(
    r'<<<<<<< conflict.*?>>>>>>> conflict 1 of 1 ends\n?',
    '<div class="flex min-h-screen bg-surface text-ink transition-colors overflow-x-hidden">\n',
    content,
    flags=re.DOTALL
)

with open(layout_file, 'w') as f:
    f.write(content)

dashboard_file = 'frontend/src/routes/(dashboard)/dashboard/+page.svelte'
with open(dashboard_file, 'r') as f:
    content = f.read()

content = re.sub(
    r'<<<<<<< conflict.*?>>>>>>> conflict 1 of 1 ends\n?',
    '<div class="flex flex-col gap-6 tall-xl:min-h-0">\n',
    content,
    flags=re.DOTALL
)

with open(dashboard_file, 'w') as f:
    f.write(content)
