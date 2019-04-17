#!/usr/bin/env python3
import argparse
from .config import Config
from .romsorter import RomSorter, set_sorting_dirs
from .datfiles import DatReader, install_dat_file

#TODO support redump.org DAT files too, not just no-intro
#TODO use config files for default options
#TODO figure out what's going on with No-Intro's DATs for "Nintendo 3DS (Digital)"
#TODO option to move all unmatched files
#TODO option to only check one console by name
#TODO import the No-Intro daily zips with every console
#TODO add option to delete dats

def print_consoles():
    config = Config()
    config = config['sorting'] if 'sorting' in config else None
    reader = DatReader()
    reader.readfiles(header_only=True)
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
    # TODO Improve the command-line interface with subcommands
    #      romverify [-ozd] organize file1.bin file2.bin
    #      romverify [-ozd] rename file1.bin file2.bin
    #      romverify list
    #      romverify [-f] install file1.dat file2.dat
    #      romverify set_dirs Console1:/path1
    usage = '%(prog)s [options] file [file ...]\n       %(prog)s --list'
    parser = argparse.ArgumentParser(
        description='Verifies and organizes ROMs with No-Intro DAT files.',
        usage=usage)
    parser.add_argument(
        'files', metavar='file', nargs='+',
        help='Source ROM files or directories')
    parser.add_argument(
        '-i', '--install-dats', action='store_true', dest='installing',
        help='Installs DAT files from No-Intro DAT-o-MATIC')
    parser.add_argument(
        '-f', '--force', action='store_true', dest='force',
        help='Allows overwriting newer DAT files with older ones.')
    parser.add_argument(
        '-m', '--move', action='store_true', dest='moving',
        help='Moves all matching files.')
    parser.add_argument(
        '--rename', action='store_true', dest='rename',
        help='Renames all matching files without moving them to another directory')
    parser.add_argument(
        '-s', '--set-output-dirs', action='store_true', dest='set_output_dirs',
        help='Sets ')
    parser.add_argument(
        '-l', '--list', action=ListAction,
        help='Lists all consoles that have installed dat files')
    parser.add_argument(
        '-o', '--output-dir', dest='outdir',
        help='Destination directory for renamed ROMs')
    parser.add_argument(
        '-d', '--dat', dest='datfile',
        help='Source DAT file from No-Intro DAT-o-MATIC')
    parser.add_argument(
        '--no-compress', action='store_true', dest='no_compress',
        help='Disables zip compression for --rename and --move operations')
    args = parser.parse_args()
    return args

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
        reader.readfiles()

    if args.set_output_dirs:
        set_sorting_dirs(reader, args.files)
        return

    compress_type = None if args.no_compress else 'zip'
    sorter = RomSorter(reader, compress_type=compress_type)
    if args.outdir:
        sorter.move_files(args.files, args.outdir)
    elif args.moving:
        sorter.organize_files(args.files)
    elif args.rename:
        sorter.rename_files(args.files)
    else:
        sorter.check_files(args.files)

if __name__ == '__main__':
    main()
