import os
import subprocess
import json
import requests

SERVER_URL = "http://192.168.1.16:8000"
NODE_INFO_PATH = "/etc/node_info.json"
LUKS_PARTITION = "/dev/mmcblk0p3"
LUKS_MAPPER_NAME = "encrypted_root"
XZ_PATH = "/home/filio/ARDSD/rasp-lite-os.img.xz"
IMG_PATH = "/home/filio/ARDSD/rasp-lite-os.img"
ROOT_PARTITION = "/dev/mmcblk0p2"
BOOT_PARTITION = "/dev/mmcblk0p1"
NEW_ROOT_SIZE_GB = 10
LUKS_START_GB = 26

def run_cmd(cmd):
    print(f"Running: {cmd}")
    subprocess.check_call(cmd, shell=True)

def ensure_requirements():
    run_cmd("sudo apt-get update && sudo apt-get install -y cryptsetup parted e2fsprogs curl xz-utils initramfs-tools")

def register_node():
    response = requests.post(f"{SERVER_URL}/register")
    response.raise_for_status()
    return response.json()["node_id"], response.json()["secret_token"]

def init_luks_key(node_id, secret_token):
    response = requests.post(f"{SERVER_URL}/init-luks", json={"node_id": node_id, "secret_token": secret_token})
    response.raise_for_status()
    return response.json()["luks_key"]

def get_luks_key(node_id, secret_token):
    response = requests.post(f"{SERVER_URL}/get-key", json={"node_id": node_id, "secret_token": secret_token})
    response.raise_for_status()
    return response.json()["luks_key"]

def create_luks_partition():
    run_cmd(f"sudo cryptsetup luksFormat {LUKS_PARTITION}")
    run_cmd(f"sudo cryptsetup luksOpen {LUKS_PARTITION} {LUKS_MAPPER_NAME}")

def setup_cmdline_txt():
    boot_mount = "/mnt/boot"
    root_mapper_path = f"/dev/mapper/{LUKS_MAPPER_NAME}"
    cmdline_txt = f"root={root_mapper_path} rootfstype=ext4 rootwait cryptdevice={LUKS_PARTITION}:{LUKS_MAPPER_NAME}\n"
    
    run_cmd(f"sudo mount {BOOT_PARTITION} {boot_mount}")
    with open(f"{boot_mount}/cmdline.txt", "w") as f:
        f.write(cmdline_txt)
    run_cmd(f"sudo umount {boot_mount}")

def install_initramfs_tools():
    luks_hook_path = "/usr/share/initramfs-tools/hooks/luks"
    luks_hook_script = """#!/bin/sh
set -e
PREREQ="udev"
prereqs() { echo "$PREREQ"; }
case "$1" in
    prereqs) prereqs; exit 0 ;;
esac
. /usr/share/initramfs-tools/hook-functions
copy_exec /sbin/cryptsetup /sbin
exit 0
"""
    with open("/tmp/luks_hook", "w") as f:
        f.write(luks_hook_script)
    run_cmd(f"sudo mv /tmp/luks_hook {luks_hook_path} && sudo chmod +x {luks_hook_path}")
    run_cmd("sudo update-initramfs -u")

def setup_os_image():
    if not os.path.exists(XZ_PATH):
        run_cmd(f"curl -L -o {XZ_PATH} https://downloads.raspberrypi.com/raspios_arm64/images/raspios_arm64-2024-11-19/2024-11-19-raspios-bookworm-arm64.img.xz")
    if not os.path.exists(IMG_PATH):
        run_cmd(f"xz -d {XZ_PATH}")
    run_cmd(f"sudo dd if={IMG_PATH} of=/dev/mapper/{LUKS_MAPPER_NAME} bs=4M status=progress conv=fsync")
    setup_cmdline_txt()
    install_initramfs_tools()

def store_node_info(node_id, secret_token):
    with open("/tmp/node_info.json", "w") as f:
        json.dump({"node_id": node_id, "secret_token": secret_token}, f)
    run_cmd("sudo mv /tmp/node_info.json /etc/node_info.json")

def first_boot_setup():
    ensure_requirements()
    node_id, secret_token = register_node()
    luks_key = init_luks_key(node_id, secret_token)
    create_luks_partition()
    setup_os_image()
    store_node_info(node_id, secret_token)
    print("First boot setup complete.")
    run_cmd("sudo reboot")

def subsequent_boot():
    ensure_requirements()
    with open(NODE_INFO_PATH, "r") as f:
        node_info = json.load(f)
    node_id, secret_token = node_info["node_id"], node_info["secret_token"]
    luks_key = get_luks_key(node_id, secret_token)
    run_cmd(f"echo '{luks_key}' | sudo cryptsetup luksOpen {LUKS_PARTITION} {LUKS_MAPPER_NAME}")
    run_cmd(f"sudo mount /dev/mapper/{LUKS_MAPPER_NAME} /mnt")
    print("Encrypted partition mounted.")

if __name__ == "__main__":
    if not os.path.exists(NODE_INFO_PATH):
        first_boot_setup()
    else:
        subsequent_boot()
