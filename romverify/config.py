from configparser import ConfigParser
import os

def get_config_file():
    home_dir = os.environ.get('HOME')
    config_dir = os.environ.get('XDG_CONFIG_HOME', os.path.join(home_dir, '.config'))
    config_dir = os.path.join(config_dir, 'eberjand')
    return os.path.join(config_dir, 'rom_verify.cfg')

class Config(ConfigParser):
    # pylint: disable=too-many-ancestors
    def __init__(self):
        self.filename = get_config_file()
        ConfigParser.__init__(self)
        ConfigParser.read(self, self.filename)
    def save(self):
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        ConfigParser.write(self, self.filename)
