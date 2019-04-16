#!/usr/bin/env python3
import argparse
import hashlib
import os
import shutil
import sys
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description='Renames ROMs with No-Intro DAT files.')
parser.add_argument('rompaths', metavar='ROM', nargs='+',
    help='Source ROM files or directories')
parser.add_argument('-o', '--output-dir', dest='outdir',
    help='Destination directory for renamed ROMs')
parser.add_argument('-d', '--dat', dest='datfile',
    help='Source DAT file from No-Intro DAT-o-MATIC')
args = parser.parse_args()

def sort_rom(romfile):
    m = hashlib.sha1()
    with open(romfile, 'rb', buffering=0) as fp:
        while True:
            data = fp.read(64*1024)
            if not data:
                break
            m.update(data)
    sha1sum = m.hexdigest().upper()
    destfile = games_by_sha1.get(sha1sum)
    if destfile is not None:
        print('%s -> %s' % (romfile, destfile))
        shutil.move(romfile, os.path.join(args.outdir, destfile))
    else:
        print('No match found: %s (%s)' % (romfile, sha1sum))

# Parse the DAT file into a games_by_sha1 dict
tree = ET.parse(args.datfile)
root = tree.getroot()
header = root.find('header')
console_name = header.find('name').text
games_by_sha1 = {}
for game_entry in root.findall('game'):
    rom = game_entry.find('rom')
    romfile = rom.attrib['name']
    crc = rom.attrib['crc']
    md5 = rom.attrib['md5']
    sha1 = rom.attrib['sha1']
    games_by_sha1[sha1] = romfile

for rompath in args.rompaths:
    if os.path.isfile(rompath):
        sort_rom(rompath)
    for root, dirs, files in os.walk(rompath):
        for romfile in files:
            sort_rom(os.path.join(root, romfile))

