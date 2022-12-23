# Charybdis
Tiny Hi-Rez API Python wrapper that I wrote to use in my Smite related projects (and to play around with async).

Hi-Rez API docs: https://webcdn.hirezstudios.com/hirez-studios/legal/smite-api-developer-guide.pdf

Other Python wrappers:
* https://github.com/luissilva1044894/Pyrez
* https://github.com/DevilXD/aRez

## Installation
`pip install charybdis`

## Usage
### Sync
```python
import os

import charybdis


api = charybdis.Api(
    # These are also the default values.
    base_url=charybdis.Api.SMITE_PC_URL,
    dev_id=os.getenv("SMITE_DEV_ID"),
    auth_key=os.getenv("SMITE_AUTH_KEY")
)

# Returns deserialized JSON.
scylla_skins = api.call_method(
    "getgodskins",  # Method name.
    "1988",  # God ID - Scylla.
    "1"  # Language ID - English.
)

for scylla_skin in scylla_skins:
    print(scylla_skin["skin_name"])

# Output:
# Standard Scylla
# Bewitching Bunny
# Child's Play
# COG Scylla
# and many more...
```
### Async
```python
import asyncio

import charybdis


async def main():
    async with charybdis.Api() as api:
        patch_info = await api.acall_method("getpatchinfo")
    print(patch_info["version_string"])

asyncio.run(main())

# Output:
# 9.6
```
