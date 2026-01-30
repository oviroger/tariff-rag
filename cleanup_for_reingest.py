#!/usr/bin/env python3
"""Clean up and restart reingest"""

import os
import json
from pathlib import Path
from app.os_index import get_os_client

client = get_os_client()

# Delete existing index
try:
    client.indices.delete(index='tariff_fragments_2025')
    print('✓ Index tariff_fragments_2025 deleted')
except Exception as e:
    print(f'  Index does not exist: {e}')

# Delete checkpoint
checkpoint_file = Path('scripts/reingest_2025_corrected_checkpoint.json')
if checkpoint_file.exists():
    checkpoint_file.unlink()
    print('✓ Checkpoint deleted')

print('\n✅ Ready for clean reingest with table extraction')
