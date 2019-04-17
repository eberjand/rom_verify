import hashlib
import os
import shutil
import zipfile

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
