import os
from .config import Config
from .filehandler import FileHandler

class RomSorter:
    def __init__(self,
                 datreader,
                 compress_type=None):
        self.datreader = datreader
        self.compress_type = compress_type
        self.sort_config = None

    def read_sort_config(self):
        parser = Config()
        self.sort_config = parser['sorting'] if 'sorting' in parser else {}

    def move_files(self, filenames, output_dir):
        for filename in filenames:
            (_, rom_name) = self.process_file(filename)
            if rom_name is None:
                continue
            romfile = FileHandler(filename)
            result = romfile.move(os.path.join(output_dir, rom_name), self.compress_type)
            print('  Moved to:', result)

    def organize_files(self, filenames, using_config=True):
        for filename in filenames:
            (console, rom_name) = self.process_file(filename)
            if rom_name is None:
                continue
            dest_dir = os.path.dirname(os.path.realpath(filename))
            if using_config:
                if self.sort_config is None:
                    self.read_sort_config()
                dest_dir = self.sort_config.get(console, dest_dir)
            romfile = FileHandler(filename)
            result = romfile.move(os.path.join(dest_dir, rom_name), self.compress_type)
            print('  Moved to:', result)

    def rename_files(self, filenames):
        self.organize_files(filenames, using_config=False)

    def check_files(self, filenames):
        for filename in filenames:
            self.process_file(filename)

    def process_file(self, filename):
        print('Processing:', filename)
        sha1sum = None
        if not os.path.exists(filename):
            print('  ERROR: File does not exist')
        elif os.path.isdir(filename):
            print('  Skipping directory')
        elif os.path.islink(filename):
            print('  Skipping symbolic link')
        elif not os.path.isfile(filename):
            print('  Skipping special file')
        else:
            try:
                romfile = FileHandler(filename)
                sha1sum = romfile.get_sha1sum()
                print('  sha1sum: ', sha1sum)
            except ValueError:
                print('  ERROR: Archives must have exactly one file')
        if sha1sum is None:
            return (None, None)
        rom_desc = self.datreader.get_rominfo(sha1sum=sha1sum)
        if rom_desc is None:
            print('  No match found')
            return (None, None)
        print('  Console: ', rom_desc[0])
        print('  ROM name:', rom_desc[1])
        return rom_desc

def set_sorting_dirs(datreader, opt_list):
    config = Config()
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
        config.save()
