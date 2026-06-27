import os
import re

dashboard_file = 'frontend/src/routes/(dashboard)/dashboard/+page.svelte'
with open(dashboard_file, 'r') as f:
    content = f.read()

content = re.sub(
    r'<<<<<<< conflict.*?>>>>>>> conflict 1 of 1 ends\n?',
    '<div class="flex flex-col gap-6 tall-xl:min-h-0">\n        \n        <!-- Orbit Decay AI Preview -->\n        {#if decayData && decayData.forecasts}\n          {@const drop7 = decayData.forecasts.find((f: any) => f.horizon === \'P7D\' || f.horizon === \'7 days, 0:00:00\')?.predicted_decay_km || 0}\n',
    content,
    flags=re.DOTALL
)

with open(dashboard_file, 'w') as f:
    f.write(content)
