#!/usr/bin/env python

# -*- coding: utf-8 -*-

import os
from PIL import Image

TESTDRIVE_SOURCE_DIR = 'testdrive'
ARC_SOURCE_DIR = 'arcfiles'
SPRITE_DEST_DIR = 'sprites'

COLORSPACE_CGA = \
    [ (  0,  0,  0, 255), (  0, 255, 255, 255), (255,   0, 255, 255), (255, 255, 255, 255) ]

COLORSPACE_EGA = \
    [ (  0,  0,  0, 255), # black
      (  0,   0, 170, 255), # blue
      (  0, 170,   0, 255), # green
      (  0, 170, 170, 255), # cyan
      (170,  0,  0, 255), # red
      (170,   0, 170, 255), # magenta
      (170, 170, 170, 255), # lightgrey
      (255, 255,  85, 255), # yellow

      (  0,  0,  0, 255), # black (there is no bright magenta)
      ( 85, 85, 85, 255), # darkgrey
      (170,  85,   0, 255), # brown
      ( 85, 255,  85, 255), # bright green
      ( 85, 255, 255, 255), # bright cyan
      (255, 85, 85, 255), # bright red
      ( 85,  85, 255, 255), # bright blue
      (255, 255, 255, 255) # white
    ]

class PackedSpriteFile:
    def __init__(self, filename):
        self.__color_space = None
        self.__detect_color_space(filename)

        # file header
        self.__packed_content_length = 0
        self.__unpacked_content_length = 0
        # unpacked contents
        self.__contents = [ ]
        self.__load_contents(filename)

        # table of contents
        self.__sprites = { }
        self.__parse_sprite_list()


    def __detect_color_space(self, filename):
        (base, ext) = os.path.splitext(filename)
        if ext.upper() == '.CMP':
            self.__color_space = COLORSPACE_CGA
        elif ext.upper() == '.EMP':
            self.__color_space = COLORSPACE_EGA
        else:
            raise Exception('Unsupported file type')


    def __read_bytes(self, f, length):
        return int.from_bytes(f.read(length), byteorder='little')


    def __read_header(self, f):
        self.__unpacked_content_length = self.__read_bytes(f, 4)
        # subtract the first 4 bytes containing the length
        self.__unpacked_content_length -= 4


    def __unpack_content(self, f):
        # CGA: runlength encoding, 0x83 is the magic byte
        # EGA: files are considered decompressed by arc
        while len(self.__contents) < self.__unpacked_content_length:
            b = self.__read_bytes(f, 1)
            if self.__color_space == COLORSPACE_CGA and b == 0x83:
                next_b = self.__read_bytes(f, 1)
                amount = self.__read_bytes(f, 1)
                self.__contents += [ next_b ] * amount
            else:
                self.__contents.append(b)


    def __load_contents(self, filename):
        with open(filename, 'rb') as f:
            self.__read_header(f)
            self.__unpack_content(f)


    def __get_string(self, offset, length):
        return ''.join([ chr(c) for c in self.__contents[offset : offset + length] if c != 0 ])


    def __get_int(self, offset, length):
        return int.from_bytes(self.__contents[offset : offset + length], byteorder='little')


    def __parse_sprite_list(self):
        amount_sprites = int.from_bytes(self.__contents[0:2], byteorder='little')
        for i in range(amount_sprites):
            sprite_name = self.__get_string(2+i*4, 4)
            sprite_offset = self.__get_int(2+amount_sprites*4+i*4, 4)
            if sprite_offset > self.__unpacked_content_length:
                raise Exception('Sprite offset beyond end of unpacked contents (%d > %d)' \
                                    % (sprite_offset, self.__unpacked_content_length))
            if sprite_name not in self.__sprites:
                self.__sprites[sprite_name] = sprite_offset
            else:
                # this happens in P911TSB.CMP for sprite ndD, both images are the same
                # we rely on the length of self.__sprites to calculate offsets though
                self.__sprites[sprite_name + '_2'] = sprite_offset


    def get_sprite_list(self):
        return list(self.__sprites.keys())


    def __get_pixel_color_cga(self, offset, layer_info, width, height, x, y):
        # CGA non-interlaced horiz-first
        pixel_byte = self.__contents[offset + (x // 4) + y * (width // 4)]
        return self.__color_space[(pixel_byte >> (2 * (3 - x%4))) % 4]


    def __get_pixel_color_ega(self, offset, layer_info, width, height, x, y):
        # EGA layered BGRI
        # layer mapping:
        # layer_info & 0xf0000000: not used
        # layer_info & 0x0f000000: color(s) on layer 3
        # layer_info & 0x00f00000: color(s) to suppress
        # layer_info & 0x000f0000: color(s) on layer 2
        # layer_info & 0x0000f000: background color
        # layer_info & 0x00000f00: color(s) on layer 1
        # layer_info & 0x000000f0: layer(s) stored vertically
        # layer_info & 0x0000000f: color(s) on layer 0
        vert_offset = (x // 8) * height + y
        horiz_offset = (x // 8) + y * (width // 8)
        plane_size = width * height // 8

        rgb_plane = 4
        pixel_color = 0
        while rgb_plane > 0:
            rgb_plane -= 1

            layer_info_mask = 1 << rgb_plane
            mapped_plane = -1
            for i in range(4):
                if (layer_info >> (i*8)) & layer_info_mask == layer_info_mask:
                    mapped_plane = i

            if mapped_plane != -1:
                plane_direction_mask = pow(2, mapped_plane) << 20
                if layer_info & plane_direction_mask == plane_direction_mask:
                    pixel_byte = self.__contents[offset + mapped_plane * plane_size + vert_offset]
                else:
                    pixel_byte = self.__contents[offset + mapped_plane * plane_size + horiz_offset]
                #pixel_byte = self.__contents[offset + mapped_plane * plane_size + horiz_offset]
                pixel_color = (pixel_color << 1) + ((pixel_byte >> (7 - x % 8)) % 2)
            else:
                pixel_color = (pixel_color << 1)

        background_color = (layer_info >> 12) & 0xf

        return self.__color_space[background_color ^ pixel_color]


    def __get_bitmap(self, spritename):
        base_offset = 2 + 8 * len(self.__sprites)
        offset = base_offset + self.__sprites[spritename]
        width = self.__get_int(offset, 2)
        height = self.__get_int(offset + 2, 2)
        print('%s: ' % spritename, end='')
        for i in range(12):
            print('%02x ' % self.__get_int(offset + 4 + i, 1), end='')
        print()
        # TODO offset 4-7 ???
        pos_x = self.__get_int(offset + 8, 2)
        pos_y = self.__get_int(offset + 10, 2)
        layer_info = self.__get_int(offset + 12, 4)

        get_pixel_color = lambda offset, layer_info, width, height, x, y: 0
        if self.__color_space == COLORSPACE_CGA:
            width *= 4 # CGA 4 pixels per byte
            get_pixel_color = self.__get_pixel_color_cga
        elif self.__color_space == COLORSPACE_EGA:
            width *= 8 # EGA 2 pixels per byte * 4 color planes
            get_pixel_color = self.__get_pixel_color_ega

        bitmap = [ ]
        for x in range(width):
            bitmap_column = [ ]
            for y in range(height):
                pixel_color = get_pixel_color(offset + 16, layer_info, width, height, x, y)
                bitmap_column.append(pixel_color)
            bitmap.append(bitmap_column)

        return (width, height, pos_x, pos_y, bitmap)


    def save_image(self, spritename, filename):
        (width, height, pos_x, pos_y, bitmap) = self.__get_bitmap(spritename)

        if width == 0 and height == 0:
            print('Empty sprite %s, not saving' % spritename)
            return

        image = Image.new('RGBA', (width, height))
        for x in range(width):
            for y in range(height):
                image.putpixel((x, y), bitmap[x][y])
        image.save(filename)


    def build_screen(self, spritenames, filename):
        image = Image.new('RGBA', (320, 200))
        for spritename in spritenames:
            (width, height, pos_x, pos_y, bitmap) = self.__get_bitmap(spritename)

            for x in range(width):
                for y in range(height):
                    image.putpixel((pos_x + x, pos_y + y), bitmap[x][y])

        image.save(filename)


    def dump_unpacked_contents(self, filename):
        print('Dumping %d bytes to %s' % (len(self.__contents), filename))
        with open(filename, 'wb') as f:
            f.write(bytearray(self.__contents))



def main():
    # create directory for the extracted sprites
    try:
        os.mkdir(SPRITE_DEST_DIR)
    except FileExistsError:
        pass

    # CGA
    for filename in os.listdir(TESTDRIVE_SOURCE_DIR):
        (basename, ext) = os.path.splitext(filename)
        if ext in [ '.CMP' ]:
            full_path_name = os.path.join(TESTDRIVE_SOURCE_DIR, filename)
            print('Processing %s' % full_path_name)
            try:
                sprite_file = PackedSpriteFile(full_path_name)
                for sprite in sprite_file.get_sprite_list():
                    output_filename = os.path.join(SPRITE_DEST_DIR, filename) + '.' + sprite + '.png'
                    sprite_file.save_image(sprite, output_filename)
            except Exception as e:
                # continue to the next file
                print(e)
                pass

    # EGA
    for filename in os.listdir(ARC_SOURCE_DIR):
        (basename, ext) = os.path.splitext(filename)
        if ext in [ '.EMP' ]:
            full_path_name = os.path.join(ARC_SOURCE_DIR, filename)
            print('Processing %s' % full_path_name)
            try:
                sprite_file = PackedSpriteFile(full_path_name)
                for sprite in sprite_file.get_sprite_list():
                    output_filename = os.path.join(SPRITE_DEST_DIR, filename) + '.' + sprite + '.png'
                    sprite_file.save_image(sprite, output_filename)
            except Exception as e:
                # continue to the next file
                print(e)
                pass



main()
