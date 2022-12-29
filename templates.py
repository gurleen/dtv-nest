import asyncio
import json
import shlex
import os
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from itertools import chain
from typing import Callable, List, Literal, Optional, Tuple

IS_WINDOWS = os.name == "nt"
AERENDER_PATH = "/Applications/Adobe\ After\ Effects\ 2023/aerender"
OUTPUT_MODULE = "DragonsTV Graphics" if IS_WINDOWS else "DTV Output"


ASSET_VALUE_NAME = {
    "image": "src",
    "text": "value",
    "expression": "expression"
}


class KeepRefs(object):
    __refs__ = defaultdict(list)

    def __init__(self):
        self.__refs__[self.__class__].append(self)

    @classmethod
    def get_all_instances(cls):
        return list(chain(*cls.__refs__.values()))

    @classmethod
    def get_instances(cls):
        return cls.__refs__[cls]


class Template(ABC, KeepRefs):
    name: str

    def __init__(self, name: str) -> None:
        super(Template, self).__init__()
        self.name = name

    @abstractmethod
    def do_render(self) -> None:
        pass


@dataclass
class AEAsset:
    kind: Literal["text", "image", "expression"]
    layer: str
    value: str
    getter_func: Optional[Callable] = None
    prop: Optional[str] = None

    def resolve_asset(self) -> str:
        if self.getter_func:
            return self.getter_func(self.value)
        return self.value

    def get_asset_json(self) -> dict:
        value_name = ASSET_VALUE_NAME.get(self.kind)
        json = {
            "type": "image" if self.kind == "image" else "data",
            value_name: self.resolve_asset(),
            "layerName": self.layer
        }

        if self.kind == "text":
            json["property"] = "Source Text"
        elif self.kind == "expression":
            json["property"] = self.prop
    
        return json
        


class AERender(Template):
    name: str
    project_file: str
    composition: str
    output_file: str
    assets: List[AEAsset]
    uses_live_keys: bool

    def __init__(
        self,
        name: str,
        project_file: str,
        composition: str,
        output_file: str,
        assets: List[AEAsset] = None,
        uses_live_keys: bool = False
    ) -> None:
        super().__init__(name)
        self.name = name
        self.project_file = project_file
        self.composition = composition
        self.output_file = output_file
        self.assets = assets if assets is not None else []
        self.uses_live_keys = uses_live_keys

    def update_data(self, data: dict):
        for asset in self.assets:
            if asset.layer in data:
                asset.value = data[asset.layer]

    def to_nexrender_json(self) -> str:
        return {
            "template": {
                "src": f"file://{self.project_file}",
                "composition": self.composition,
                "outputModule": OUTPUT_MODULE,
                "outputExt": "mov"
            },
            "assets": [a.get_asset_json() for a in self.assets],
            "actions": {
                "postrender": [
                    {
                        "module": "@nexrender/action-copy",
                        "input": "result.mov",
                        "output": f"{self.output_file}"
                    }
                ]
            }
        }

    async def read_stream(self, proc: asyncio.subprocess.Process, cb: Optional[Callable] = None):
        last_amount = 0
        stream = proc.stdout
        while True:
            try:
                line = await asyncio.wait_for(stream.readline(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
            if proc.returncode != None:
                print(f"proc ended with code {proc.returncode}")
                return  # subprocess ended, go back
            line = line.decode()
            if not line.isspace() and line != "":
                print(line)
            if "rendering took" in line:
                cb(1)
                break
            if "rendering progress" in line:
                index = line.index("rendering progress") + len("rendering progress")
                pct_str = line[index:].replace("%...", "")
                amount = int(pct_str) / 100
                cb(amount - last_amount)
                last_amount = amount
                if amount >= 1:
                    break

    async def do_render(self, progress_callback: Optional[Callable] = None) -> Tuple[int, str]:
        template_json = json.dumps(self.to_nexrender_json())
        if IS_WINDOWS:
            with open("job.json", "w") as f:
                f.write(template_json)
            command = f"nexrender-cli --file job.json"
            proc = await asyncio.create_subprocess_shell(command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        else:
            command = f"nexrender-cli -b {AERENDER_PATH} '{template_json}'"
            args = shlex.split(command)
            proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        
        await asyncio.wait([self.read_stream(proc, progress_callback)])
        await proc.wait()
        if proc.returncode != 0:
            err = await proc.stderr.read()
            return proc.returncode, err.decode()
        return 0, "ok"



matchup = AERender(
    "Matchup",
    "/Users/gurleen/Creative/Matchup.aep",
    "Matchup Comp",
    "/Apps/CasparCG/media",
    [
        AEAsset("text", "Home Name", "Drexel"),
        AEAsset("text", "Away Name", "Delaware")
    ]
)

"""
starting_five = AERender(
    "Starting Five",
    "/Users/gurleen/Creative/StartingFive.aep",
    "Starting Five Comp",
    "/Apps/CasparCG/media",
    [
        AEAsset("text", "Player Name 1", "Keishana Washington")
    ]
)
"""

halftime_stats = AERender(
    "Halftime Stats",
    "/Users/gurleen/Creative/HalftimeStats/Halftime Stats.aep",
    "Halftime Stats 2022",
    "/Users/gurleen/Creative/HalftimeStats.mov",
    [
        AEAsset("text", "Home Score", "20"),
        AEAsset("text", "Away Score", "10")
    ]
)