import re

with open('frontend/src/i18n.js', 'r', encoding='utf-8') as f:
    text = f.read()

hi_start = text.find('  hi: {\n    translation: {')
bn_start = text.find('  bn: {\n    translation: {')
hi_block = text[hi_start:bn_start]

matches = dict(re.findall(r'"([^"]+)":\s*"([^"]+)"', hi_block))

vault_keys = [
    'AIPoweredVault', 'SATYADisclaimer', 'Accepted', 'Pending', 'Rejected',
    'AvgConfidence', 'FullName', 'DateOfBirth', 'Gender', 'VerificationStatus',
    'Confidence', 'VerificationDate', 'DocumentType', 'VerificationMethod',
    'Capabilities', 'DocVerificationCapabilities', 'Policy', 'VerificationPolicy',
    'PersonalInformation', 'SelectGender', 'Male', 'Female', 'Other'
]

for k in vault_keys:
    val = matches.get(k)
    print(k, ":", val)
