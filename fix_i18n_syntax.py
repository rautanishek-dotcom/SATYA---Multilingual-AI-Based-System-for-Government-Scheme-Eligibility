import re

with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    text = f.read()

# Fix cases where a translation value ends with double quote, followed by whitespace (like newlines)
# and then the next translation key starts with double quote.
# E.g.: "StateScheme": "State Scheme" \n "VaultPageTitle": ...
text = re.sub(r'(\"[^\"]*\")(\s*\n\s*)(\"[^\"]*\":)', r'\1,\2\3', text)

with open('frontend/src/i18n.js', 'w', encoding='utf-8') as f:
    f.write(text)

print('Syntax errors fixed across all languages')
