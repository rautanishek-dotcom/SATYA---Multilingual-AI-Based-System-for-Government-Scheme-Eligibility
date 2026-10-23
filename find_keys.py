with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Let's search for "Secure Document Vault" or "Accepted"
lines = content.split('\n')
for i, line in enumerate(lines[:100]):
    if 'Vault' in line or 'Accepted' in line or 'title' in line.lower():
        print(f"Line {i+1}: {line}")
