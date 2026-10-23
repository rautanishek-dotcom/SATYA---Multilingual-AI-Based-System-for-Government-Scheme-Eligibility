with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

import re
matches = re.findall(r'\"([^\"]*Vault[^\"]*)\"\s*:\s*\"([^\"]*)\"', content)
for m in matches[:10]:
    print(m)

matches2 = re.findall(r'\"([^\"]*Accepted[^\"]*)\"\s*:\s*\"([^\"]*)\"', content)
for m in matches2[:10]:
    print(m)
