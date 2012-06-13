#!/usr/bin/python
import os
import time
from subprocess import Popen,PIPE

# Globals
lvm_key = "create_lvm_snapshot"
# avoid multiple snapshot-merge checks via inspect_volume_lvm()
dm_snapshot_merge_checked = 0
dm_snapshot_merge_support = 0
lvcreate_size_args = "-l 10%ORIGIN"
excluded_mntpnts = ""
snapshot_tag = "yic_" + time.strftime("%Y%m%d%H%M%S")

def kernel_supports_dm_snapshot_merge():
    global dm_snapshot_merge_checked, dm_snapshot_merge_support
    if dm_snapshot_merge_checked:
        return dm_snapshot_merge_support
    os.system("modprobe dm-snapshot")
    p = Popen(["/sbin/dmsetup", "targets"], stdout=PIPE, stderr=PIPE)
    err = p.wait()
    if not err:
        output = p.communicate()[0]
        if not output.find("snapshot-merge") == -1:
            dm_snapshot_merge_support = 1
        dm_snapshot_merge_checked = 1
    return dm_snapshot_merge_support

def inspect_volume_lvm(volume):
    device = volume["device"]
    
    if device.startswith("/dev/dm-"):
        print "fs-snapshot: unable to snapshot DM device: " + device
        return 0
    if device.startswith("/dev/mapper/"):
        p = Popen(["/sbin/dmsetup", "splitname", "--separator", "/",
                   "--noheadings",
                   "-o", "vg_name,lv_name", device], stdout=PIPE, stderr=PIPE)
        err = p.wait()
        if err:
            return 0
        output = p.communicate()[0]
        device = output.strip().replace("/dev/mapper/", "/dev/")
        volume["device"] = device

    p = Popen(["/sbin/lvs", device], stdout=PIPE, stderr=PIPE)
    err = p.wait()
    if not err:
        if not kernel_supports_dm_snapshot_merge():
            print "fs-snapshot: skipping volume: %s, " "kernel doesn't support snapshot-merge" % (device)
            return 0
        volume[lvm_key] = 1
    return 1

def get_volumes():
    volumes = []

    try:
        mtabfile = open('/etc/mtab', 'r')
        for line in mtabfile.readlines():
            device, mntpnt, fstype, rest = line.split(' ', 3)
            volume = { "device" : device,
                       "mntpnt" : mntpnt,
                       "fstype" : fstype }

            if mntpnt in excluded_mntpnts:
                continue

            if not rest.find("bind") == -1:
                continue

            if not device.find("/") == 0:
                continue

            if not inspect_volume_lvm(volume):
                continue

            volumes.append(volume)
        mtabfile.close()

    except Exception, e:
        print "fs-snapshot: error processing mounted volumes: %s" % e
    return volumes

def create_lvm_snapshot(snapshot_tag, volume):

    if not lvcreate_size_args.startswith("-L") and not lvcreate_size_args.startswith("-l"):
        print "fs-snapshot: 'lvcreate_size_args' did not use -L or -l"
        return 1

    device = volume["device"]
    if device.count('/') != 3:
        return 1

    mntpnt = volume["mntpnt"]
    
    snap_device = device + "_" + snapshot_tag
    snap_lvname = snap_device.split('/')[3]
    print snap_device
    print snap_lvname

    print "fs-snapshot: snapshotting %s (%s): %s" % (mntpnt, device, snap_lvname)

    # Create snapshot LV
    lvcreate_cmd = ["/sbin/lvcreate", "-s", "-n", snap_lvname]
    lvcreate_cmd.extend(lvcreate_size_args.split())
    lvcreate_cmd.append(device)
    p = Popen(lvcreate_cmd, stdout=PIPE, stderr=PIPE)
    err = p.wait()
    if err:
        print "fs-snapshot: failed command: %s\n%s" % (" ".join(lvcreate_cmd), p.communicate()[1])
        return 1
    p = Popen(["/sbin/lvchange", "--addtag", snapshot_tag, snap_device],
              stdout=PIPE, stderr=PIPE)
    err = p.wait()
    if err:
        print "fs-snapshot: couldn't add tag to snapshot: %s" % (snap_device)
        return 1
    return 2

def main():
  snapshot_tag = "yic_" + time.strftime("%Y%m%d%H%M%S")
  volumes = get_volumes()
  for volume in volumes:
    create_lvm_snapshot(snapshot_tag, volume)

if __name__ == '__main__':
    main()
