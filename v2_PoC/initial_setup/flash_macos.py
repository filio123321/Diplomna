import os
import subprocess
import re

def run_cmd(cmd):
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout.strip()

def list_devices():
    print("Available storage devices:")
    output = run_cmd("diskutil list")
    print(output)
    
    devices = []
    for line in output.splitlines():
        if '/dev/disk' in line:
            devices.append(line.split()[0].replace('/dev/', ''))
    return devices

def get_device_size(device):
    # Run 'diskutil info' to get detailed information about the device
    output = run_cmd(f"diskutil info /dev/{device}")
    
    # Regex to match the size line and extract the size value (e.g., "251.0 GB")
    size_pattern = re.compile(r"^\s*Disk Size:\s*(\d+(\.\d+)?)\s*(GB|MB)", re.MULTILINE)
    match = size_pattern.search(output)
    if match:
        size_value = float(match.group(1))
        unit = match.group(3)
        
        # Convert the size to GB (handling MB and GB)
        if unit == "GB":
            return size_value
        elif unit == "MB":
            return size_value / 1024  # Convert MB to GB
        else:
            print(f"Unsupported unit: {unit}")
            return 0
    else:
        print("Size information not found")
        return 0

def combine_partitions(device):
    print(f"Combining all partitions on /dev/{device}...")
    
    # Unmount the disk before attempting any operations
    run_cmd(f"sudo diskutil unmountDisk /dev/{device}")
    
    # Delete all existing partitions and create a single partition using the entire disk
    run_cmd(f"sudo diskutil partitionDisk /dev/{device} 1 GPT exFAT 'RaspberryPi' 100%")

def create_partitions(device):
    print(f"Creating two partitions on /dev/{device}...")
    # Unmount the disk before partitioning
    run_cmd(f"sudo diskutil unmountDisk /dev/{device}")
    
    # Delete all existing partitions on the device (this ensures a clean slate)
    run_cmd(f"sudo diskutil eraseDisk exFAT RaspberryPi GPT /dev/{device}")
    
    # Create two partitions: 10GB for Raspberry Pi OS and the rest for data
    run_cmd(f"sudo diskutil partitionDisk /dev/{device} 2 GPT exFAT 'PiOS' 10GB exFAT 'Data' R")

def flash_image(image_path, device):
    # Unmount the specific partition first
    print(f"Unmounting /dev/{device}s2...")
    run_cmd(f"sudo diskutil unmount /dev/{device}s2")
    
    # Flash the image to the unmounted partition
    print(f"Flashing {image_path} to /dev/{device}s2...")
    run_cmd(f"sudo dd if={image_path} of=/dev/{device}s2 bs=4M status=progress conv=fsync")


def main():
    print("Welcome to the Raspberry Pi Setup Script")
    devices = list_devices()
    if not devices:
        print("No storage devices found.")
        return

    print("Select a device from the list above (e.g., disk0):")
    selected_device = input("Device: ").strip()
    if selected_device not in devices:
        print("Invalid device selected.")
        return

    device_size = get_device_size(selected_device)
    print(f"Device size: {device_size} GB")
    if device_size < 30:
        print("Device must be at least 30GB.")
        return

    image_path = input("Enter the path to the Raspberry Pi image: ").strip()
    if not os.path.exists(image_path):
        print("Invalid image path.")
        return

    # Combine all partitions first
    combine_partitions(selected_device)

    # Create two partitions: 10GB for Raspberry Pi OS and the rest for data
    create_partitions(selected_device)

    # Flash Raspberry Pi OS to the 10GB partition
    flash_image(image_path, selected_device)

    print("Setup complete.")

if __name__ == "__main__":
    main()

# disk4
# /Users/filio/raspi_os.img