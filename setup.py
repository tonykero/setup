#!/bin/python

from typing import TypedDict
import subprocess
import os.path

dryrun = False

class Object(object):
    pass

def pname(name: str):
        return f"\'{name}\'"



def shell(cmd: str, args: list[str] = [], stdin = None, stdout=None, chroot=None, script=False):
    if chroot != None:
        chroot_args = " ".join([cmd] + args)
        cmd = "arch-chroot"
        args = [chroot, '/bin/bash']
        if not script:
            args += ['-c', f"\"{chroot_args}\""]
        else:
            args += [chroot_args]
    global dryrun
    if dryrun:
        cmd_str = " ".join([cmd] + args)
        print(f"DRYRUN: {cmd_str}")
        obj = Object()
        setattr(obj, "stdout", None)
        return obj
    out = subprocess.Popen([cmd] + args, stdin=stdin, stdout=stdout, stderr=subprocess.PIPE)
    out.wait()
    if(out.returncode != 0):
        output_str = out.stderr.read().decode("utf-8")
        raise Exception(f"Command failed {out} with message:\n{output_str}")
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
                shell('mount', ['--mkdir', _loc, partition["mount"]])

    def finalize_partitions(self, root_dir):
        fstab_dir = root_dir.rstrip('/') + '/etc/fstab'
        shell("pacstrap", ['-K', root_dir, 'base', 'linux', 'linux-firmware'])
        p = shell("genfstab", ['-U', '-p', root_dir], stdout=subprocess.PIPE)
        if dryrun:
            return
        with open(fstab_dir, "w") as fstab_file:
            fstab_file.write(p.stdout.read().decode("utf-8"))

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
        shell('chpasswd', ['--root', '/mnt'], stdin=_stdout)
    
    def setup_grub(self):
        script_str = """\
#!/bin/bash
pacman -Sy
pacman -S --noconfirm grub os-prober efibootmgr
mount --mkdir /dev/sda1 /boot/efi
grub-install --target=x86_64-efi --bootloader-id=GRUB --efi-directory=/boot/efi
grub-mkconfig -o /boot/grub/grub.cfg
"""     
        with open("/mnt/home/setup.sh", "w") as script_file:
            script_file.write(script_str)
            shell("/home/setup.sh", chroot='/mnt', script=True)
        
        #shell('arch-chroot', ['/mnt', '/bin/bash', '/home/setup.sh'], chroot='/mnt')


    def __init__(self):
        self.kbd_layout = 'fr-latin1'
        self.device     = '/dev/sda'
        self.root_pwd   = "root"

        self.partitions: list[Partition] = [
            {
                "name": "EFI System",
                "size": "500",
                "type": "efi",
                "mount": "/boot/efi"
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
                "mount": "/mnt"
            }
        ]

    def exec(self):
        print("Setting up keyboard layout")
        self.setup_kbd_layout(self.kbd_layout)
        print("Setting up partitions")
        self.setup_partitions(self.device, self.partitions)
        
        self.setup_grub()

        print("Setting up passwd")
        self.setup_passwd(self.root_pwd)


    def reset(self):
        for idx, partition in enumerate(self.partitions, start=1):
            if partition["type"] == "swap":
                
                out = shell("swapon", ["--show=NAME"], stdout=subprocess.PIPE)
                if dryrun:
                    continue
                out_str = out.stdout.read().decode("utf-8").strip()
                swap_list = out_str.split('\n')
                if len(swap_list) > 0:
                    swap_list = swap_list[1:]
                print(swap_list)

                _loc = f"{self.device}{idx}"
                if _loc in swap_list:
                    shell("swapoff", [_loc])
            else:
                if os.path.ismount(partition["mount"]):
                    shell("umount", ["-R", partition["mount"]])

        shell("wipefs", ["-a", self.device])

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--reset", action='store_true', default=False)
parser.add_argument("--dry", action='store_true', default=False)
args = parser.parse_args()

dryrun = args.dry

setup = Setup()
if args.reset:
    setup.reset()
setup.exec()