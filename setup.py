#!/bin/python

from typing import TypedDict
import subprocess

dryrun = False

class Object(object):
    pass

def pname(name: str):
        return f"\'{name}\'"



def shell(cmd: str, args: list[str], stdin = None, stdout=None):
    global dryrun
    if dryrun:
        cmd_str = " ".join([cmd] + args)
        print(f"DRYRUN: {cmd_str}")
        obj = Object()
        setattr(obj, "stdout", None)
        return obj
    out = subprocess.Popen([cmd] + args, stdin=stdin, stdout=stdout)
    out.wait()
    return out

class Partition(TypedDict):
    name: str
    type: str
    size: str
    mount: str

def get_fs_type(p: Partition):
    fs_types = {
        "efi":      "fat32",
        "swap":     "linux-swap",
        "normal":   "ext4",
        "root":     "ext4"
    }
    p_type = p["type"]
    if p_type in fs_types:
        return fs_types[p_type]
    
    keys = ",".join(fs_types.keys())
    raise Exception(f"Partition type {p_type} is not valid {keys}")

def get_part_end_offset(p: Partition, offset: int):
    p_size = p["size"]
    if p_size == "remainder":
        return ["100%", 0]
    else:
        end_offset = offset + int(p_size)
        return [f"{end_offset}MiB", end_offset]
    
def get_root_partition(partitions: list[Partition]):
    f_parts = list(filter(lambda p: p['type'] == 'root', partitions))
    if len(f_parts) > 0:
        return f_parts[0]

    raise Exception("No root partition were found")

class Setup:
    def setup_kbd_layout(self, layout: str):
        return shell('loadkeys', [layout])
    
    def create_partitions(self, device:str, partitions: list[Partition]):
        args = [
            '--script', device,
            "mklabel", "gpt"
            ]
        offset = 1
        for partition in partitions:
            name            = pname(partition['name'])
            fs_type         = get_fs_type(partition)
            start_offset    = f"{offset}MiB"
            [end_offset, offset]   = get_part_end_offset(partition, offset)
            args += ["mkpart", name, fs_type, start_offset, end_offset]

            if partition["type"] == "efi":
                args += ['set',      '1', 'esp', 'on']

        return shell('parted', args)

    def format_partitions(self, device, partitions):
        for idx, partition in enumerate(partitions, start=1):
            _loc = f"{device}{idx}"
            if partition["type"] in ["root", "normal"]:
                shell("mkfs.ext4", [_loc])
            elif partition["type"] == "swap":
                shell("mkswap", [_loc])
            elif partition["type"] == "efi":
                shell("mkfs.fat", ['-F', '32', _loc])
    
    def mount_partitions(self, device, partitions):
        for idx, partition in enumerate(partitions, start=1):
            _loc = f"{device}{idx}"
            if partition["type"] == "swap":
                shell('swapon', [_loc])
            else:
                shell('mount', [_loc, partition["mount"]])

    def finalize_partitions(self, root_dir):
        fstab_dir = root_dir.rstrip('/') + '/etc/fstab'
        shell("genfstab", ['-U', root_dir, '>>', fstab_dir])
        shell("systemctl", ['daemon-reload'])
        shell("arch-chroot", [root_dir])

    def setup_partitions(self, device: str, partitions: list[Partition]):
        
        self.create_partitions(device, partitions)
        self.format_partitions(device, partitions)
        self.mount_partitions(device, partitions)

        root_dir = get_root_partition(partitions)["mount"]
        self.finalize_partitions(root_dir)
    
    def setup_passwd(self, pwd: str):
        p1 = shell('echo', [f"root:{pwd}"], stdout=subprocess.PIPE)
        _stdout = None
        if not dryrun:
            _stdout = p1.stdout
        p2 = shell('chpasswd', [], stdin=_stdout)
        return p2
    
    def __init__(self):
        self.kbd_layout = 'fr-latin1'
        self.device     = '/dev/sda'
        self.root_pwd   = "root"

        self.partitions: list[Partition] = [
            {
                "name": "EFI System",
                "size": "500",
                "type": "efi",
                "mount": "/boot"
            },
            {
                "name": "swap",
                "size": "2000",
                "type": "swap"
            },
            {
                "name": "root",
                "size": "remainder",
                "type": "root",
                "mount": "/"
            }
        ]

    def exec(self):
        print("Setting up keyboard layout")
        self.setup_kbd_layout(self.kbd_layout)
        print("Setting up partitions")
        self.setup_partitions(self.device, self.partitions)
        print("Setting up passwd")
        self.setup_passwd(self.root_pwd)

setup = Setup()
setup.exec()