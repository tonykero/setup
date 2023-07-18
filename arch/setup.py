#!/bin/python

import disk
import shell

class Setup:

    def setup_arch(self, root_part):
        root_dir = next(iter(root_part.mountpoints()))
        fstab_dir = root_dir.rstrip('/') + '/etc/fstab'
        
        shell.Shell("pacstrap", ['-K', root_dir, 'base', 'linux', 'linux-firmware']).raise_run()
        shell.Shell("genfstab" ,["-U", "-p", root_dir]).redirect(fstab_dir).raise_run()

    
    def setup_passwd(self, pwd: str, root_dir: str):
        echo = shell.Shell("echo", [f"root:{pwd}"])
        chpasswd = shell.Shell('chpasswd', ['--root', root_dir])

        echo.pipe(chpasswd).raise_run()


    def setup_kbd_layout(self, layout: str, root_dir: str):
        shell.Shell("echo", [f"KEYMAP={layout}"])         \
            .redirect(f"{root_dir}/etc/vconsole.conf")  \
            .raise_run()

    def setup_locale(self, locale: str, root_dir: str):
        # generate locale
        shell.Shell("sed", ["-i", f"s/#{locale}/{locale}/", f"{root_dir}/etc/locale.gen"]) \
            .raise_run()
        self.chroot(root_dir, "locale-gen")

        # persistent
        shell.Shell("echo", [f"LANG={locale}"])                  \
            .redirect(f"{root_dir}/etc/locale.conf")             \
            .raise_run()

    def setup_network(self, root_dir: str):
        self.chroot(root_dir, "pacman", ["-S", "--noconfirm", "dhcpcd"])
        self.chroot(root_dir, "ln", ["-s", "/usr/lib/systemd/system/dhcpcd.service", "/etc/systemd/system/multi-user.target.wants/dhcpcd.service"])

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

        self.chroot(root_dir, "pacman", ["-Sy"])
        self.chroot(root_dir, "pacman", ["-S", "--noconfirm", "grub", "efibootmgr"])
        self.chroot(root_dir, "mount", ["--mkdir", efi_part.loc(), efi_dir])
        self.chroot(root_dir, "grub-install", ["--target=x86_64-efi", "--bootloader-id=GRUB", f"--efi-directory={efi_dir}"])
        self.chroot(root_dir, "grub-mkconfig", ["-o", "/boot/grub/grub.cfg"])

    def chroot(self, root_dir: str, cmd: str, args: list[str] = []):
            full_cmd = [cmd] + args
            base_cmd = "arch-chroot"
            base_args = [root_dir]
            return shell.Shell(base_cmd, base_args + full_cmd).raise_run()

    def __init__(self, dryrun):
        shell.BaseShell.dryrun = dryrun

        self.kbd_layout = 'fr-latin1'
        self.locale     = 'en_US.UTF-8'
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
        # Setup Disk
        mounted = self.setup_disk()
        root_part = mounted["root"]
        efi_part = mounted["efi"]

        # Bootstrap Arch Linux
        self.setup_arch(root_part)
        self.setup_grub(root_part, efi_part)

        root_dir = next(iter(root_part.mountpoints()), None)

        # Setup Base system
        self.setup_passwd(self.root_pwd, root_dir)
        # From now, arch can reboot and be minimal & fonctional
        self.setup_locale(self.locale, root_dir)
        self.setup_kbd_layout(self.kbd_layout, root_dir)
        
        # Setup network
        self.setup_network(root_dir)

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