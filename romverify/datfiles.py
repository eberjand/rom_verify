import os
import xml.etree.ElementTree as ET
from .filehandler import FileHandler

def get_data_dir():
    home_dir = os.environ.get('HOME')
    data_dir = os.environ.get('XDG_DATA_HOME', os.path.join(home_dir, '.local/share'))
    data_dir = os.path.join(data_dir, 'eberjand/rom_dats')
    return data_dir

def clean_file_name(name):
    # TODO deal with Windows filename restrictions too
    return name.replace('/', '_')

class DatReader:
    def __init__(self):
        self.clear()

    def get_rominfo(self, sha1sum):
        return self.games_by_sha1.get(sha1sum)

    def clear(self):
        self.consoles = {}
        self.games_by_sha1 = {}

    def readfiles(self, data_dir=None, header_only=False):
        if data_dir is None:
            data_dir = get_data_dir()
        for datfile in os.listdir(data_dir):
            self.readfile(os.path.join(data_dir, datfile), header_only, True)

    def readfile(self, datfile, header_only=False, verify_filename=False):
        try:
            tree = ET.parse(FileHandler(datfile).open())
        except:
            # A parse error occurred such as xml.etree.ElementTree.ParseError
            return (None, None)
        root = tree.getroot()
        header = root.find('header')
        console_name = header.find('name').text
        version = header.find('version').text
        if verify_filename:
            basename = os.path.basename(datfile)
            if clean_file_name(console_name) + '.dat' != basename:
                print('WARNING: Stray file ignored:', basename)
                return (None, None)
        self.consoles[console_name] = version

        if not header_only:
            self.readfile_checksums(root, console_name)
        return (console_name, version)

    def readfile_checksums(self, xml_root, console_name):
        for game_entry in xml_root.findall('game'):
            rom = game_entry.find('rom')
            romfile = rom.attrib.get('name')
            sha1 = rom.attrib.get('sha1')
            if romfile is None or sha1 is None:
                continue
            #if sha1 in self.games_by_sha1:
            #    print('WARNING: Duplicate checksum in both "%s" and "%s"' %
            #        (self.games_by_sha1[sha1][0], console_name))
            #    print('         For ROM: %s' % romfile)
            self.games_by_sha1[sha1] = (console_name, romfile)

def install_dat_file(datfile, force=False):
    print('Processing:', datfile)
    (console_name, version) = DatReader().readfile(datfile, header_only=True)
    if console_name is None:
        print('  Invalid DAT file')
        return
    print('  Console:', console_name)
    print('  Version:', version)
    store_filename = clean_file_name(console_name) + '.dat'
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    store_filepath = os.path.join(data_dir, store_filename)
    success_message = None
    if os.path.exists(store_filepath):
        oldheader = DatReader().readfile(store_filepath, header_only=True)
        oldversion = oldheader[1]
        print('  Current:', oldversion)
        if version > oldversion:
            success_message = 'Installed updated dat file'
        elif force:
            success_message = 'Overwrote previous dat file'
        elif version == oldversion:
            print('  Skipping because installed dat file is already up to date')
            print('  Use --force to replace it')
        else:
            print('  Skipping because installed dat file is newer')
            print('  Use --force to force a downgrade')
    else:
        success_message = 'Installed successfully'
    if success_message is not None:
        FileHandler(datfile).move(store_filepath, None)
        print('  ' + success_message)
