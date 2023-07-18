#!/bin/python
from __future__ import annotations
from enum import Enum
from math import ceil
import json
import subprocess as sb

from shell import Shell

class PartType(Enum):
    EXT4        = 1
    FAT32       = 2
    SWAP        = 3

def parted(disk_name: str, cmd: str, args: list[str]) -> sb.Popen:
        return Shell("parted", ["--json", disk_name, "-s"] + [cmd] + args).run(stdout=sb.PIPE)

def align_to(x: int, multiple: int):
    return multiple * ceil(float(x)/float(multiple))

def unit_to_int(str: str) -> int:
    return int(str.replace('s',''))

class Disk:
    def __init__(self, name: str):
        self.name = name
        
        if not self.has_label():
            self.init_label()

    def wipe(self):
        partitions = self.get_partitions()
        numbers = list(map(lambda p: p["number"], partitions))
        for number in numbers:
            part_obj = self.get_partition(number)
            part_obj.umount()

        return Shell("wipefs", ["-a", self.name]).raise_run()

    def print(self) -> dict:
        parted_output = parted(self.name, "unit", ["s", "print"])
        parted_json = json.load(parted_output.stdout)
        if "disk" in parted_json:
            return parted_json["disk"]

        if Shell.dryrun:
            return {
      "path": "/dev/sda",
      "size": "266338304s",
      "model": "Msft Virtual Disk",
      "transport": "scsi",
      "logical-sector-size": 512,
      "physical-sector-size": 4096,
      "label": "gpt",
      "max-partitions": 128,
      "partitions": [
         {
            "number": 1,
            "start": "2048s",
            "end": "1026047s",
            "size": "1024000s",
            "type": "primary",
            "name": "efi",
            "filesystem": "fat32",
            "flags": [
                "boot", "esp"
            ]
         },{
            "number": 2,
            "start": "1026048s",
            "end": "5220351s",
            "size": "4194304s",
            "type": "primary",
            "name": "swap",
            "filesystem": "linux-swap(v1)",
            "flags": [
                "swap"
            ]
         },{
            "number": 3,
            "start": "5220352s",
            "end": "134195199s",
            "size": "128974848s",
            "type": "primary",
            "name": "root",
            "filesystem": "ext4"
         }
      ]
   }


        raise Exception(f"parted error: disk field was not found for device {self.name}")
    
    def sector_size(self) -> int:
        disk_json = self.print()
        key = "logical-sector-size"
        if key in disk_json:
            return disk_json[key]
        
        raise Exception(f"Disk data does not contain {key} information")
    
    def sectors_count(self) -> int:
        disk_json = self.print()
        key = "size"
        if key in disk_json:
            return int(disk_json[key].replace('s',''))
        
        raise Exception(f"Disk data does not contain {key} information")

    def bytes_to_sectors(self, bytes: int) -> int:
        bytes_f     = float(bytes)
        sectors_f   = float(self.sector_size())
        
        return ceil(bytes_f/sectors_f)

    def sectors_to_bytes(self, sectors: int) -> int:
        return sectors * self.sector_size()

    def init_label(self, label="gpt") -> sb.Popen:
        return parted(self.name, "mklabel", [label])
    
    def has_label(self) -> bool:
        disk_json   = self.print()
        key = "label"
        if key in disk_json:
            return disk_json[key] != "unknown"
        return False

    def create_partition(self, name: str, type: PartType, bytes: int) -> Partition:
        return Partition(self, name=name, type=type, bytes=bytes)
    
    def get_partition(self, number: int):
        return Partition(self, number=number)
    
    def get_partitions(self):
        disk_json = self.print()
        key = "partitions"
        if key in disk_json:
            return disk_json[key]
        
        raise Exception(f"Partitions field was not found for disk {self.name}")

class Partition:
    def __init__(self, disk: Disk, name: str = None, type: PartType = None, bytes: int = None, number=None):
        self.disk = disk

        if number == None or not isinstance(number, int):
            self.name = name
            self.type = type
            self.bytes = bytes
            self.number = self.create()
        else:
            is_the_one = lambda p: p["number"] == number
            part_json = next(filter(is_the_one, disk.get_partitions()), None)
            if part_json == None:
                raise Exception(f"Partition {number} was not found for disk {disk.name}")

            self.name = part_json["name"]
            self.type = Partition.mkpart_to_type(part_json["filesystem"])
            self.bytes = unit_to_int(part_json["size"])
            self.number = number

    @staticmethod
    def type_to_mkpart(type: PartType) -> str:
        type_dict = {
            PartType.EXT4:  "ext4",
            PartType.FAT32: "fat32",
            PartType.SWAP:  "linux-swap"
        }

        if type in type_dict:
            return type_dict[type]
        
        keys = list(type_dict.keys())

        raise Exception(f"Partition type {type} was not recognized, possible values are {keys}")

    @staticmethod
    def mkpart_to_type(str: str) -> PartType:
        type_dict = {
            "ext4":             PartType.EXT4,
            "fat32":            PartType.FAT32,
            "linux-swap":       PartType.SWAP,
            "linux-swap(v1)":   PartType.SWAP
        }

        if str in type_dict:
            return type_dict[str]
        
        keys = list(type_dict.keys())
        
        raise Exception(f"Partition type {str} was not recognized, possible values are {keys}")


    def compute_offsets(self, bytes: int) -> tuple[int,int]:
        partitions = self.disk.get_partitions()
        
        offset_start = 2048
        if len(partitions) > 0:
            last_part       = partitions[-1]
            last_end_offset = unit_to_int(last_part["end"])
            offset_start    = last_end_offset + 1
        
        offset_end = offset_start + self.disk.bytes_to_sectors(bytes) - 1
        offset_end = align_to(offset_end, 2048)-1
        

        max_sectors = self.disk.sectors_count()
        if offset_end >= max_sectors:
            raise Exception(f"Requested offset is higher than disk capacity: {offset_end} >= {max_sectors}")

        return (offset_start, offset_end)
    
    def mkpart(self, offset_start: int, offset_end: int):
        parted(self.disk.name, "mkpart", 
                                        [self.name, Partition.type_to_mkpart(self.type), f"{offset_start}s", f"{offset_end}s"])

        if self.type == PartType.SWAP:
            parted(self.disk.name, "set", ["1", "esp", "on"])


    def create(self):
        (offset_start, offset_end) = self.compute_offsets(self.bytes)
        self.mkpart(offset_start, offset_end)
        
        # assume number is the number of last partition
        parts = self.disk.get_partitions()
        last = next(reversed(parts), None)
        
        if last == None:
            raise Exception(f"No partitions were found")
        
        return last["number"]

    def loc(self):
        return f"{self.disk.name}{self.number}"

    def mountpoints(self):
        findmnt = Shell("findmnt", ["--json", "-S", self.loc(), "-o", "SOURCE,TARGET"]).run(stdout=sb.PIPE)
        if Shell.dryrun:
            return [f"/part_of{self.loc()}"]
        
        if findmnt.returncode == 0:
            fs_list = json.load(findmnt.stdout)["filesystems"]
            fs_to_mnt = lambda fs: fs["target"]
            mountpoints = list(map(fs_to_mnt, fs_list))
            return mountpoints

        return []

    def format(self):
        mk_dict = {
            PartType.EXT4: ("mkfs.ext4",    []),
            PartType.SWAP: ("mkswap",       []),
            PartType.FAT32:("mkfs.fat",     ["-F", "32"])
        }

        if self.type in mk_dict:
            (mk_cmd, mk_args) = mk_dict[self.type]
            mk_shell = Shell(mk_cmd, mk_args + [self.loc()])
            mk_shell.raise_run()

    def mount(self, mnt: str):
        mount = Shell("mount", ["--mkdir", self.loc(), mnt])
        if self.type == PartType.SWAP:
            mount = Shell("swapon", [self.loc()])
        mount.raise_run()

    def umount(self):
        if self.type == PartType.SWAP:
            umount = Shell("swapoff", [self.loc()])
            umount.run()
            return
        
        mountpoints = self.mountpoints()
        if len(mountpoints) > 0:
            umount = Shell("umount", ["-R"] + mountpoints)
            umount.run()

