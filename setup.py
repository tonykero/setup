#!/bin/python

import disk
import shell

class Setup:
    def setup_kbd_layout(self, layout: str):
        return shell.Shell('loadkeys', [layout])

    def setup_arch(self, root_part):
        root_dir = next(iter(root_part.mountpoints()))
        fstab_dir = root_dir.rstrip('/') + '/etc/fstab'
        
        shell.Shell("pacstrap", ['-K', root_dir, 'base', 'linux', 'linux-firmware']).raise_run()
        shell.Shell("genfstab" ,["-U", "-p", root_dir]).redirect(fstab_dir).raise_run()

    
    def setup_passwd(self, pwd: str, root_part):
        root_dir = next(iter(root_part.mountpoints()))
        echo = shell.Shell("echo", [f"root:{pwd}"])
        chpasswd = shell.Shell('chpasswd', ['--root', root_dir])

        echo.pipe(chpasswd).raise_run()
    
    def setup_disk(self) -> dict:
        self.disk.init_label()
        ret = {}
        for part_dict in self.partitions:
            part_name = part_dict["name"]
            part_size = part_dict["size"]
            part_type = part_dict["type"]

            part = self.disk.create_partition(part_name, part_type, part_size)
            print(part.number)
            part.format()
            if part_type != disk.PartType.SWAP and "mount" in part_dict:
                part.mount(part_dict["mount"])
            ret[part_name] = part
        return ret

    def setup_grub(self, root_part, efi_part):
        part_root_mnt = root_part.mountpoints()
        part_efi_mnt  = efi_part.mountpoints()

        root_dir = next(iter(part_root_mnt),None)
        efi_dir  = next(iter(part_efi_mnt),None)

        if (root_dir == None or efi_dir == None):
            raise Exception(f"Partitions root or efi were not found")

        def chroot(cmd: str, args: list[str]):
            full_cmd = [cmd] + args
            base_cmd = "arch-chroot"
            base_args = [root_dir]
            shell.Shell(base_cmd, base_args + full_cmd).raise_run()

        chroot("pacman", ["-Sy"])
        chroot("pacman", ["-S", "--noconfirm", "grub", "efibootmgr"])
        chroot("mount", ["--mkdir", efi_part.loc(), efi_dir])
        chroot("grub-install", ["--target=x86_64-efi", "--bootloader-id=GRUB", f"--efi-directory={efi_dir}"])
        chroot("grub-mkconfig", ["-o", "/boot/grub/grub.cfg"])


    def __init__(self, dryrun):
        shell.BaseShell.dryrun = dryrun

        self.kbd_layout = 'fr-latin1'
        self.device     = '/dev/sda'
        self.root_pwd   = "root"


        MiB = lambda x: x * 1024 * 1024
        GiB = lambda x: MiB(x) * 1024
        self.partitions = [
            {
                "name": "efi",
                "size": MiB(500),
                "type": disk.PartType.FAT32,
                "mount": "/boot/efi"
            },
            {
                "name": "swap",
                "size": GiB(2),
                "type": disk.PartType.SWAP
            },
            {
                "name": "root",
                "size": GiB(61.5),
                "type": disk.PartType.EXT4,
                "mount": "/mnt"
            }
        ]

        self.disk = disk.Disk(self.device)

    def exec(self):
        mounted = self.setup_disk()

        root_part = mounted["root"]
        efi_part = mounted["efi"]

        self.setup_arch(root_part)
        self.setup_grub(root_part, efi_part)

        print("Setting up passwd")
        self.setup_passwd(self.root_pwd, root_part)


    def reset(self):
        self.disk.wipe()

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--reset", action='store_true', default=False)
parser.add_argument("--dry", action='store_true', default=False)
args = parser.parse_args()

dryrun = args.dry

setup = Setup(dryrun)
if args.reset:
    setup.reset()
setup.exec()