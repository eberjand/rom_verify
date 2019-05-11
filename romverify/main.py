#!/usr/bin/env python3
import argparse
import os
import sys
from romverify.config import Config
from romverify.romsorter import RomSorter, set_sorting_dir
from romverify.datfiles import DatReader, install_dat_file

#TODO use config files for default options
#TODO support DAT lists that have more than one file in a single game (eg PS2, 3DS Digital)
#TODO option to only check one console by name (for organize/rename/check)

def parser_organize(subparsers):
    """Adds parser for the `organize` subcommand."""

    subhelp = \
        'Organizes a list of ROM files by using the names matching each file\'s checksum ' + \
        'in DAT files and moving them to the appropriate collections directory, if applicable.'
    parser = subparsers.add_parser('organize', description=subhelp, help=subhelp)
    parser.add_argument('files', metavar='file', nargs='+', help='Source ROM files')
    parser.add_argument(
        '--no-compress', action='store_true',
        help='Disables zip compression')
    parser.add_argument(
        '-d', '--dat', dest='datfile',
        help='Source DAT file from No-Intro. Ignores installed DATs.')
    parser.add_argument(
        '-o', '--output-dir',
        help='Destination directory for matching ROMs (overrides collection)')

def parser_rename(subparsers):
    """Adds parser for the `rename` subcommand."""

    subhelp = \
        'Renames a list of ROM files by using the names matching each file\'s checksum ' + \
        'in DAT files.'
    parser = subparsers.add_parser('rename', description=subhelp, help=subhelp)
    parser.add_argument('files', metavar='file', nargs='+', help='Source ROM files')
    parser.add_argument(
        '--no-compress', action='store_true', dest='no_compress',
        help='Disables zip compression')
    parser.add_argument(
        '-d', '--dat', dest='datfile',
        help='Source DAT file from No-Intro. Ignores installed DATs.')

def parser_check(subparsers):
    """Adds parser for the `check` subcommand."""

    subhelp = \
        'Verifies the checksums of ROM files against installed DATs and displays the name ' + \
        'of any matching game'
    parser = subparsers.add_parser('check', description=subhelp, help=subhelp)
    parser.add_argument('files', metavar='file', nargs='+', help='ROM files')
    parser.add_argument(
        '-d', '--dat', dest='datfile',
        help='Source DAT file from No-Intro. Ignores installed DATs.')

def parsers_collection(subparsers):
    """Adds parser for the `collection-` subcommands."""

    help_c_add = \
        'Add a collection directory for organizing all verified ROMs that belong to the ' + \
        'specified console name'
    sub_c_add = subparsers.add_parser('collection-add', description=help_c_add, help=help_c_add)
    sub_c_add.add_argument('console', metavar='console_name')
    sub_c_add.add_argument('path', metavar='organize_path')

    help_c_rem = \
        'Removes a console collection so that `organize` no longer will move ROMs for the ' + \
        'specified console. Existing ROMs are not deleted.'
    sub_c_rem = subparsers.add_parser('collection-remove', description=help_c_rem, help=help_c_rem)
    sub_c_rem.add_argument('console', metavar='console_name')

    help_c_mis = \
        "Lists all games present in the specified console's DAT that don't have ROMs " + \
        "archived in its respective collections directory."
    sub_c_mis = subparsers.add_parser(
        'collection-missing', description=help_c_mis, help=help_c_mis)
    sub_c_mis.add_argument('console', metavar='console_name')

    # TODO add subcommand 'collection-strays' to list (and optionally move) files that are
    #      present in but don't belong in the collection directory

def parsers_dat(subparsers):
    """Adds parser for the `dat-` subcommands."""

    help_d_add = \
        'Install DAT files whose checksums and filenames will be used in future invocations ' + \
        'of `organize` and `rename`. Replaces any existing DAT file for the same console ' + \
        'unless the specified DAT file is older and `--force` is not given.'
    sub_d_add = subparsers.add_parser('dat-add', description=help_d_add, help=help_d_add)
    sub_d_add.add_argument('datfile', nargs='+')
    sub_d_add.add_argument(
        '-f', '--force', action='store_true',
        help='Allow overwriting newer DAT files with older ones')

    help_d_rem = \
        'Remove an installed DAT file so that its games will no longer be recognized by ' + \
        'future invocations of `organize` and `rename`'
    sub_d_rem = subparsers.add_parser('dat-remove', description=help_d_rem, help=help_d_rem)
    sub_d_rem.add_argument('console', metavar='console_name')

def parser_list(subparsers):
    """Adds parser for the `list` subcommand."""

    subhelp = \
        'Lists all consoles with an installed DAT and any associated collection directory'
    subparsers.add_parser('list', description=subhelp, help=subhelp)

def parse_args():
    """Parses commandline arguments."""

    parser = argparse.ArgumentParser(
        description='Verifies and organizes ROMs with No-Intro DAT files.')
    subparsers = parser.add_subparsers(
        dest='subcommand', metavar='subcommand',
        description='Show extended help on each subcommand with `<subcommand> -h`')

    parser_organize(subparsers)
    parser_rename(subparsers)
    parser_check(subparsers)
    parsers_collection(subparsers)
    parsers_dat(subparsers)
    parser_list(subparsers)

    args = parser.parse_args()
    return args

def verify_roms(files, action, datfile=None, compress_type='zip', outdir=None):
    """Verifies ROM checksums and optionally uses them to rename or move the ROMs."""

    reader = DatReader()
    if datfile is not None:
        (dat_console, dat_version) = reader.readfile(datfile)
        if dat_console is None:
            print('Invalid DAT file:', datfile)
            return
        print('Checking console:', dat_console)
        print('DAT version:', dat_version)
    else:
        reader.readfiles()

    sorter = RomSorter(reader, compress_type=compress_type)
    if outdir:
        os.makedirs(outdir, exist_ok=True)
        sorter.move_files(files, outdir)
    elif action == 'organize':
        sorter.organize_files(files)
    elif action == 'rename':
        sorter.rename_files(files)
    else:
        sorter.check_files(files)

def print_consoles():
    """Prints installed DAT consoles and their collection directories."""

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

def main():
    """Main entry point."""

    args = parse_args()

    if args.subcommand == 'organize':
        compress_type = None if args.no_compress else 'zip'
        verify_roms(args.files, 'organize', args.datfile, compress_type, args.output_dir)
    elif args.subcommand == 'rename':
        compress_type = None if args.no_compress else 'zip'
        verify_roms(args.files, 'rename', args.datfile, compress_type)
    elif args.subcommand == 'check':
        verify_roms(args.files, 'check', args.datfile)
    elif args.subcommand == 'collection-add':
        reader = DatReader()
        reader.readfiles(header_only=True)
        set_sorting_dir(reader, args.console, args.path)
    elif args.subcommand == 'collection-remove':
        raise NotImplementedError #TODO
    elif args.subcommand == 'collection-missing':
        raise NotImplementedError #TODO
    elif args.subcommand == 'dat-add':
        #TODO support importing a No-Intro daily zip that includes every console
        for datfile in args.datfile:
            install_dat_file(datfile, force=args.force)
    elif args.subcommand == 'dat-remove':
        raise NotImplementedError #TODO
    elif args.subcommand == 'list':
        print_consoles()
    else:
        raise RuntimeError('Unknown subcommand: %s' % args.subcommand)

if __name__ == '__main__':
    main()
