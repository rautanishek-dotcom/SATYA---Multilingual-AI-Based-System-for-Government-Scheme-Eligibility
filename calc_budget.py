"""
WORKLOAD CALCULATION for BHASHINI translation.
Prints estimated API calls required.
Does NOT make any changes.
"""

# Confirmed state from audit_i18n_results.json
TOTAL_EN_KEYS = 594
PLACEHOLDER_PER_LANG = 585   # English-identical strings per non-en/hi/bn language
TARGET_UI_LANGS = 20          # mr, te, ta, gu, kn, ml, as, brx, doi, ks, kok, mai, mni, ne, or, pa, sa, sat, sd, ur
TOTAL_SCHEMES = 342
SCHEME_TARGET_LANGS = 20      # same 20 languages

# BHASHINI confirmed supports 10 strings per call
BATCH_SIZE = 10
APPROVED_CALLS = 1000

import math

ui_batches_per_lang = math.ceil(PLACEHOLDER_PER_LANG / BATCH_SIZE)
total_ui_calls = ui_batches_per_lang * TARGET_UI_LANGS

scheme_batches_per_lang = math.ceil(TOTAL_SCHEMES / BATCH_SIZE)
total_scheme_calls = scheme_batches_per_lang * SCHEME_TARGET_LANGS

total_calls = total_ui_calls + total_scheme_calls

print("=" * 60)
print("BHASHINI API CALL WORKLOAD ESTIMATE")
print("=" * 60)
print(f"Batch size confirmed:          {BATCH_SIZE} strings/call")
print(f"Approved call budget:          {APPROVED_CALLS}")
print()
print("UI TRANSLATIONS:")
print(f"  Placeholder strings/lang:    {PLACEHOLDER_PER_LANG}")
print(f"  Target languages:            {TARGET_UI_LANGS}")
print(f"  Total UI translations:       {PLACEHOLDER_PER_LANG * TARGET_UI_LANGS:,}")
print(f"  Batches/lang:                {ui_batches_per_lang}")
print(f"  Total UI API calls:          {total_ui_calls}")
print()
print("SCHEME NAME TRANSLATIONS:")
print(f"  Total schemes:               {TOTAL_SCHEMES}")
print(f"  Target languages:            {SCHEME_TARGET_LANGS}")
print(f"  Total scheme translations:   {TOTAL_SCHEMES * SCHEME_TARGET_LANGS:,}")
print(f"  Batches/lang:                {scheme_batches_per_lang}")
print(f"  Total scheme API calls:      {total_scheme_calls}")
print()
print(f"GRAND TOTAL API CALLS:         {total_calls}")
print(f"APPROVED BUDGET:               {APPROVED_CALLS}")
print(f"OVER BUDGET BY:                {max(0, total_calls - APPROVED_CALLS)}")
print()

if total_calls > APPROVED_CALLS:
    print("⚠️  EXCEEDS BUDGET — STOPPING before full run")
    print()
    print("PRIORITY STRATEGIES:")
    print()
    # Strategy: UI only
    str_ui_only = f"  UI only: {total_ui_calls} calls — " + ("EXCEEDS" if total_ui_calls > APPROVED_CALLS else "FITS")
    print(str_ui_only)
    print(f"  Scheme only: {total_scheme_calls} calls — " + ("EXCEEDS" if total_scheme_calls > APPROVED_CALLS else "FITS"))
    print()
    # Can we fit UI if we increase batch to 20?
    b20_ui = math.ceil(PLACEHOLDER_PER_LANG / 20) * TARGET_UI_LANGS
    b20_sh = math.ceil(TOTAL_SCHEMES / 20) * SCHEME_TARGET_LANGS
    print(f"  If batch=20: UI={b20_ui} + Schemes={b20_sh} = {b20_ui+b20_sh} calls total")
    b30_ui = math.ceil(PLACEHOLDER_PER_LANG / 30) * TARGET_UI_LANGS
    b30_sh = math.ceil(TOTAL_SCHEMES / 30) * SCHEME_TARGET_LANGS
    print(f"  If batch=30: UI={b30_ui} + Schemes={b30_sh} = {b30_ui+b30_sh} calls total")
    b50_ui = math.ceil(PLACEHOLDER_PER_LANG / 50) * TARGET_UI_LANGS
    b50_sh = math.ceil(TOTAL_SCHEMES / 50) * SCHEME_TARGET_LANGS
    print(f"  If batch=50: UI={b50_ui} + Schemes={b50_sh} = {b50_ui+b50_sh} calls total")
else:
    print("✅ Within approved budget. Safe to proceed.")
