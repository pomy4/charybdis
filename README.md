# Charybdis
Tiny Hi-Rez API Python wrapper that I wrote to use in my Smite related projects
(and to play around with async).

Hi-Rez API documentation: https://webcdn.hirezstudios.com/hirez-studios/legal/smite-api-developer-guide.pdf

See the Hi-Rez API documentation for available methods and their parameters.
The structure of the returned values is not described though, so some work is
required to figure out what information can actually be obtained from the API.

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
    auth_key=os.getenv("SMITE_AUTH_KEY"),
)

# Returns deserialized JSON.
scylla_skins = api.call_method(
    "getgodskins",  # Method name.
    "1988",  # God ID - Scylla.
    "1",  # Language ID - English.
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


async def main() -> None:
    async with charybdis.Api() as api:
        patch_info_task = asyncio.create_task(api.acall_method("getpatchinfo"))
        gods_task = asyncio.create_task(api.acall_method("getgods", "1"))

        patch_info = await patch_info_task
        gods = await gods_task

    newest_god = ""
    for god in gods:
        if god["latestGod"] == "y":
            newest_god = god["Name"]
            break

    print(
        f"The current patch is {patch_info['version_string']}"
        + f" and the newest god is {newest_god}."
    )


asyncio.run(main())

# Output:
# The current patch is 9.12 and the newest god is Maui.
```
