#!/usr/bin/env python

import os

TESTDRIVE_SOURCE_DIR = 'testdrive'
ARCFILES_DEST_DIR = 'arcfiles'

def convert(infilename, outf, outfilename):
    with open(infilename, 'rb') as f:
        header = f.read(16)

        outf.write(b'\x1a') # magic byte
        outf.write(bytes([header[0x0c]])) # compression type
        outf.write(outfilename.encode('utf8'))
        outf.write(bytes( [ 0x00 ] * (13 - len(outfilename)) ))
        # pad string to 12 chars + end of c-string
        outf.write(bytes(header[0x04:0x08])) # compressed size
        outf.write(b'\xa8') # date
        outf.write(b'\x3c') # date
        outf.write(b'\x0b') # time
        outf.write(b'\x75') # time
        outf.write(bytes(header[0x0e:0x10])) # crc
        outf.write(bytes(header[0x08:0x0c])) # uncompressed size

        packed_content_length = \
            header[0x07]*256*256*256 + \
            header[0x06]*256*256 + \
            header[0x05]*256 + \
            header[0x04]
        for i in range(packed_content_length):
            # inefficient copy
            b = f.read(1)
            outf.write(b)



def main():
    with open(os.path.join(ARCFILES_DEST_DIR, 'TESTDRIVE.ARC'), 'wb') as outf:
        for filename in os.listdir(TESTDRIVE_SOURCE_DIR):
            (basename, ext) = os.path.splitext(filename)
            if ext in [ '.PES' ]:
                full_path_name = os.path.join(TESTDRIVE_SOURCE_DIR, filename)
                print('Processing %s' % full_path_name)

                convert(full_path_name, outf, basename + '.EMP')

        # write end of archive
        outf.write(b'\x1a') # magic end byte
        outf.write(b'\x00') # 0x00 means no following file



main()
