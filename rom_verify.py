#!/usr/bin/env python3
import argparse
import configparser
import hashlib
import os
import shutil
import zipfile
import xml.etree.ElementTree as ET

#TODO support redump.org DAT files too, not just no-intro
#TODO use config files for default options
#TODO figure out what's going on with No-Intro's DATs for "Nintendo 3DS (Digital)"
#TODO option to move all unmatched files
#TODO option to only check one console by name
#TODO make sure the single-dat and single-out-dir options work right
#TODO import the No-Intro daily zips with every console
#TODO add option to delete dats

def get_config_file():
    home_dir = os.environ.get('HOME')
    config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.join(home_dir, '.config'))
    config_dir = os.path.join(config_dir, 'eberjand')
    return os.path.join(config_dir, 'rom_verify.cfg')

def read_config():
    parser = configparser.ConfigParser()
    parser.read(get_config_file())
    return parser

def write_config(parser):
    config_file = get_config_file()
    os.makedirs(os.path.dirname(config_file), exist_ok=True)
    with open(config_file, 'w') as cfg_out:
        parser.write(cfg_out)

def get_data_dir():
    home_dir = os.environ.get('HOME')
    data_dir = os.environ.get('XDG_DATA_HOME', os.path.join(home_dir, '.local/share'))
    data_dir = os.path.join(data_dir, 'eberjand/rom_dats')
    return data_dir

def clean_file_name(name):
    # TODO deal with Windows filename restrictions too
    return name.replace('/', '_')

class FileHandler:
    # TODO support reading gz,xz,bz2,7z files
    def __init__(self, filename):
        self.filename = filename
        self.is_zipfile = zipfile.is_zipfile(filename)

    def open(self):
        if self.is_zipfile:
            with zipfile.ZipFile(self.filename) as zip_fp:
                namelist = zip_fp.namelist()
                if len(namelist) != 1:
                    raise ValueError('Invalid name list in zip file: ' + self.filename)
                return zip_fp.open(namelist[0])
        else:
            return open(self.filename, 'rb', buffering=0)

    def get_sha1sum(self):
        hasher = hashlib.sha1()
        with self.open() as fp_in:
            while True:
                data = fp_in.read(64*1024)
                if not data:
                    break
                hasher.update(data)
        sha1sum = hasher.hexdigest().upper()
        return sha1sum

    def move(self, dest_path, compress_type):
        if compress_type is not None:
            #TODO support writing gz/xz/bz2
            #TODO add an option to set zip's compresslevel (0-9)
            dest_zip = os.path.splitext(dest_path)[0] + '.zip'
            dest_basename = os.path.basename(dest_path)

            if self.is_zipfile:
                # Don't mess with an existing zipfile if its filename is good
                #TODO an option to force a rewrite may be useful for better compression settings
                with zipfile.ZipFile(self.filename) as zf_in:
                    file_list = zf_in.namelist()
                    if len(file_list) == 1 and file_list[0] == dest_basename:
                        shutil.move(self.filename, dest_zip)
                        print('  Keeping original zip file')
                        return dest_zip
                # zipfile needs the uncompressed input files to be either in memory or on disk
                # as a regular file, not a file-like object.
                # This extracted data can be too large for RAM or some systems' tmpfs, so we
                # put it in the same directory (and filesystem) as the result zip.
                with open(dest_path, 'wb') as ext_fp:
                    shutil.copyfileobj(self.open(), ext_fp)
                os.remove(self.filename)
                self.filename = dest_path
            # Create the resulting zip file
            with zipfile.ZipFile(dest_zip, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                zip_out.write(self.filename, dest_basename)
            os.remove(self.filename)
            self.filename = dest_zip
            self.is_zipfile = True
            return dest_zip
        else:
            if self.is_zipfile:
                # Extract the uncompressed file
                with open(dest_path, 'wb') as out_fp:
                    with self.open() as in_fp:
                        shutil.copyfileobj(in_fp, out_fp)
                os.remove(self.filename)
            else:
                shutil.move(self.filename, dest_path)
            self.filename = dest_path
            return dest_path

class DatReader:
    def __init__(self):
        self.clear()

    def get_rominfo(self, sha1sum):
        return self.games_by_sha1.get(sha1sum)

    def clear(self):
        self.consoles = {}
        self.games_by_sha1 = {}

    def readfiles(self, data_dir, header_only=False):
        for datfile in os.listdir(data_dir):
            self.readfile(os.path.join(data_dir, datfile), header_only, True)

    def readfile(self, datfile, header_only=False, verify_filename=False):
        tree = ET.parse(FileHandler(datfile).open())
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
            romfile = rom.attrib['name']
            sha1 = rom.attrib['sha1']
            #crc = rom.attrib['crc']
            #md5 = rom.attrib['md5']
            #if sha1 in self.games_by_sha1:
            #    print('WARNING: Duplicate checksum in both "%s" and "%s"' %
            #        (self.games_by_sha1[sha1][0], console_name))
            #    print('         For ROM: %s' % romfile)
            self.games_by_sha1[sha1] = (console_name, romfile)

def print_consoles():
    config = read_config()
    config = config['sorting'] if 'sorting' in config else None
    reader = DatReader()
    reader.readfiles(get_data_dir(), header_only=True)
    for console in sorted(reader.consoles):
        print(console)
        print('  Version:', reader.consoles[console])
        if config is not None:
            sort_to = config.get(console)
            if sort_to is not None:
                print('  Sort to:', sort_to)

class ListAction(argparse.Action):
    # pylint: disable=too-few-public-methods,redefined-builtin
    def __init__(self, option_strings, dest, default=argparse.SUPPRESS, help=None):
        super(ListAction, self).__init__(
            option_strings=option_strings,
            dest=dest,
            default=default,
            nargs=0,
            help=help)
    def __call__(self, parser, namespace, values, option_string=None):
        print_consoles()
        parser.exit()

def parse_args():
    # pylint: disable=bad-continuation
    usage = '%(prog)s [options] file [file ...]\n       %(prog)s --list'
    parser = argparse.ArgumentParser(
        description='Verifies and organizes ROMs with No-Intro DAT files.',
        usage=usage)
    parser.add_argument('files', metavar='file', nargs='+',
        help='Source ROM files or directories')
    parser.add_argument('-i', '--install-dats', action='store_true', dest='installing',
        help='Installs DAT files from No-Intro DAT-o-MATIC')
    parser.add_argument('-f', '--force', action='store_true', dest='force',
        help='Allows overwriting newer DAT files with older ones.')
    parser.add_argument('-m', '--move', action='store_true', dest='moving',
        help='Moves all matching files.')
    parser.add_argument('--rename', action='store_true', dest='rename',
        help='Renames all matching files without moving them to another directory')
    parser.add_argument('-s', '--set-output-dirs', action='store_true', dest='set_output_dirs',
        help='')
    parser.add_argument('-l', '--list', action=ListAction,
        help='Lists all consoles that have installed dat files')
    parser.add_argument('-o', '--output-dir', dest='outdir',
        help='Destination directory for renamed ROMs')
    parser.add_argument('-d', '--dat', dest='datfile',
        help='Source DAT file from No-Intro DAT-o-MATIC')
    parser.add_argument('--no-compress', action='store_true', dest='no_compress',
        help='Disables zip compression for --rename and --move operations')
    args = parser.parse_args()
    return args

def install_dat_file(datfile, force=False):
    print('Processing:', datfile)
    (console_name, version) = DatReader().readfile(datfile, header_only=True)
    if console_name is None:
        return
    print('  Console:', console_name)
    print('  Version:', version)
    store_filename = clean_file_name(console_name) + '.dat'
    data_dir = get_data_dir()
    os.makedirs(data_dir, exist_ok=True)
    store_filepath = os.path.join(data_dir, store_filename)
    success_message = None
    if os.path.exists(store_filepath):
        oldheader = ET.parse(store_filepath).getroot().find('header')
        oldversion = oldheader.find('version').text
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

def set_sorting_dirs(datreader, opt_list):
    config = read_config()
    if 'sorting' not in config:
        config['sorting'] = {}
    is_modified = False
    # Allow shortened names without vendor, like "Nintendo DS" for "Nintendo - Nintendo DS"
    shortened_consoles = {}
    for console in datreader.consoles:
        splits = console.split(' - ', maxsplit=1)
        if len(splits) == 2:
            shortname = splits[1]
            # Don't allow ambiguous short names
            if shortname in shortened_consoles:
                shortened_consoles[shortname] = None
                continue
            shortened_consoles[shortname] = console
    for opt in opt_list:
        splits = opt.split(':', maxsplit=1)
        if len(splits) != 2:
            print('ERROR: Invalid format in "%s"', opt)
            print('       Sorting directories should be specified as "Console Name:/path/to/dir"')
            continue
        console = splits[0]
        if console not in datreader.consoles:
            console = shortened_consoles.get(console)
            if console is None:
                print('ERROR: Unknown console:', splits[0])
                print('       Please install a DAT file before setting a sorting directory')
                continue
        config['sorting'][console] = os.path.realpath(splits[1])
        is_modified = True
    if is_modified:
        write_config(config)

class RomSorter:
    def __init__(self,
                 datreader,
                 moving=False,
                 rename=False,
                 compress_type=None):
        self.datreader = datreader
        self.moving = moving
        self.rename = rename
        self.compress_type = compress_type
        self.output_dir = None
        self.sort_config = None

    def set_output_dir(self, output_dir):
        self.output_dir = output_dir

    def read_sort_config(self):
        parser = read_config()
        self.sort_config = parser['sorting'] if 'sorting' in parser else {}

    def process_file(self, filename):
        print('Processing:', filename)
        if not os.path.exists(filename):
            print('  ERROR: File does not exist')
            return
        elif os.path.isdir(filename):
            print('  Skipping directory')
            return
        elif os.path.islink(filename):
            print('  Skipping symbolic link')
            return
        elif not os.path.isfile(filename):
            print('  Skipping special file')
            return
        try:
            romfile = FileHandler(filename)
            sha1sum = romfile.get_sha1sum()
            print('  sha1sum: ', sha1sum)
        except ValueError:
            print('  ERROR: Archives may not have more than one file')
            return
        rom_desc = self.datreader.get_rominfo(sha1sum=sha1sum)
        if rom_desc is None:
            print('  No match found')
            return
        console = rom_desc[0]
        rom_name = rom_desc[1]
        print('  Console: ', console)
        print('  ROM name:', rom_name)
        move_to = None
        if self.output_dir:
            move_to = os.path.join(self.output_dir, rom_name)
        elif self.moving or self.rename:
            dest_dir = os.path.dirname(os.path.realpath(filename))
            if self.moving:
                if self.sort_config is None:
                    self.read_sort_config()
                dest_dir = self.sort_config.get(console, dest_dir)
            move_to = os.path.join(dest_dir, rom_name)
        if move_to is not None:
            result = romfile.move(move_to, self.compress_type)
            print('  Moved to:', result)

def main():
    args = parse_args()
    if args.installing:
        for datfile in args.files:
            install_dat_file(datfile, force=args.force)
        return

    reader = DatReader()
    if args.datfile is not None:
        reader.readfile(args.datfile)
    else:
        reader.readfiles(get_data_dir())

    if args.set_output_dirs:
        set_sorting_dirs(reader, args.files)
        return

    compress_type = None if args.no_compress else 'zip'
    sorter = RomSorter(reader, moving=args.moving, rename=args.rename, compress_type=compress_type)
    sorter.set_output_dir(args.outdir)
    for filename in args.files:
        sorter.process_file(filename)

if __name__ == '__main__':
    main()
