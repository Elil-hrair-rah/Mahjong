# -*- coding: utf-8 -*-
import json
import re
from functools import reduce
from tkinter import (END, INSERT, WORD, BooleanVar, StringVar, Tk, W,
                     messagebox, scrolledtext, ttk)
import numpy as np

from collections import OrderedDict

import random
import requests
from PIL import Image

from mahjong.hand_calculating.hand import HandCalculator
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.meld import Meld as mjMeld
from mahjong.shanten import Shanten

from mahjong.constants import EAST, SOUTH, WEST, NORTH

from player import Player
from tiles import Tile, Tiles, Wall, OneOfEach, Dora, Hand, Meld, Melds, Discards

''' testing code

alsonotbob = Player('anb',3)
bob = Player('bob', 1)
notbob = Player('notbob',2)
bob.hand.add_tiles('11p23s5505m666p777s123z')
tile1 = Tile('1','p')
tile2 = Tile('1','s')
tile3 = Tile('6','p')
tile4 = Tile('7','s')
bob.seat = SOUTH
game = Game([notbob, alsonotbob, alsonotbob, alsonotbob])
bob.pon(tile1, game)
bob.chii(tile2, game)
bob.seat = NORTH
bob.ckan()
bob.okan(tile3, game)
bob.seat = WEST
bob.pon(tile4, game)
bob.ckan()

'''

def player_image(player, *args):
    if not isinstance(player, Player):
        return False
    
    if player.melds.melds:
        image_list = []
        parts = [str(player.hand)]
        rotated = []
        rotated.append([0 for tile in player.hand.tiles])
        for arg in args:
            parts.append(arg)
            rotated.append([0 for tile in Tiles(arg).tiles])
        for meld in player.melds.melds:
            rotation = {'L': [1, 0, 0], 'M': [0, 1, 0], 'R': [0, 0, 1]}
            if meld.who:
                
                rotate = rotation[meld.who][:]
                if meld.shominkan:
                    rotate[rotate.index(1):rotate.index(1)+1] = [1,2]
                elif len(meld) == 4:
                    rotate.insert(2, 0)
                    

                tiles = sorted(meld.tiles, key=lambda tile:tile.true_value)
                remove = [index for index, tile in enumerate(tiles) if tile.suit == meld.called.suit and tile.value == meld.called.value]
                del tiles[remove[0]]                
                string = ''
                zero_counter = 0
                
                for ref in rotate:
                    if ref == 0:
                        string += tiles[zero_counter].value
                        zero_counter += 1
                    elif ref == 1:
                        string += meld.called.value
                    elif ref == 2:
                        string += meld.shominkan_tile.value
                string += meld.called.suit
                    
            else:
                rotate = [0 for tile in meld.tiles]
                string = str(meld)
                if string[0] == string[3]:
                    string = 'x'.join(string.rsplit(meld.tiles[0].value, 1))
                    string = string.replace(meld.tiles[0].value, 'x', 1)
                elif string[0] == string[1]:
                    string = 'x'.join(string.rsplit(meld.tiles[0].value, 2))
                else:
                    string = string.replace(meld.tiles[-1].value, 'x', 2)
                    
            rotated.append(rotate)
            parts.append(string)
        #return rotated, parts
        
        image_list = []
        for part in parts:
            results = re.findall(r'([0-9x]+[mpsz])', part)
            if part == parts[0]:
                results = list(
                    reduce(list.__add__,
                           [['{}{}'.format(x, result[-1]) for x in result[:-1]]
                            for result in results]))
            for result in results:
                image_list += [
                    './ui/{}{}.png'.format(x, result[-1]) for x in result[:-1]
                ]
            image_list.append('./ui/0.png')
        
        refs = []
        for block in rotated:
            refs.extend(block)
            refs.append(0)
        del refs[-1]
        
        #return image_list, ref
        
        imagefile = [Image.open(x) for x in image_list]
        
        image_length = refs.count(0) * 80 + refs.count(1) * 130
        if refs.count(2): image_height = 260 
        else: image_height = 130
        
        target = Image.new('RGBA', (image_length, image_height))
        left = 0
        for image, ref in zip(imagefile, refs):
            
            bottom = 0 + image.size[1]
            
            if ref:
                image = image.rotate(90, expand = True)
            
            if ref:
                bottom += image.size[0] - image.size[1]
            if ref == 2:
                bottom -= image.size[1]
                left -= image.size[0]
                
            target.paste(image, (left, bottom))
            
            left += image.size[0]
            
            '''
            if ref:

                
                image = image.transpose(Image.ROTATE_90)
                image = image.transpose(Image.ROTATE_90)
                image = image.transpose(Image.ROTATE_90)
            
            if ref:
                bottom += image.size[0] - image.size[1]
            if ref == 2:
                bottom -= image.size[1]
                target.paste(image, (left-image.size[0], bottom))
            else:
                target.paste(image, (left, bottom))
            
            left += image.size[0]
            '''
            
        target.save('{}-{}.png'.format(player.name, player.disc_id), quality=100)
                
            
            
        
    else:
        tiles = str(player.hand)
        for arg in args:
            tiles += str(arg)
        makeImage(tiles)
        
    
    image_list = []
    rotate_list = []
    
    

def makeImage(text):
    if not text:
        return 0
    image_list = []
    parts = text.split(' ')
    for i in range(len(parts)):
        part = parts[i]
        results = re.findall(r'([0-9x]+[mpsz])', part)
        if part == parts[0]:
            results = list(
                reduce(list.__add__,
                       [['{}{}'.format(x, result[-1]) for x in result[:-1]]
                        for result in results]))
            results = sorted(sorted(results), key=lambda x: x[-1])
        for result in results:
            image_list += [
                './ui/{}{}.png'.format(x, result[-1]) for x in result[:-1]
            ]
        image_list.append('./ui/0.png')
    # print(image_list)
    imagefile = [Image.open(x) for x in image_list]
    target = Image.new('RGBA', (len(image_list) * 80, 130))
    left = 0
    for img in imagefile:
        
        #if rotated:
        #img = img.rotate(270)
        
        target.paste(img, (left, 0))
        
        #if img on top:
        #   down += img.size[1]
        #   target.paste(img, (left, down))

        
        left += img.size[0]
        
    target.save('{}.png'.format(text.replace(' ', '_')), quality=100)


def makeYamaImage(text):
    if text:
        image_list = []
        results = re.findall(r'([0-9x]+[mpsz])', text)
        for result in results:
            image_list += [
                './ui/{}{}.png'.format(x, result[-1]) for x in result[:-1]
            ]
        imagefile = [Image.open(x) for x in image_list
                     ] + (5 - len(image_list)) * [Image.open('./ui/xz.png')]
    else:
        imagefile = 5 * [Image.open('./ui/xz.png')]
    target = Image.new('RGBA', (5 * 80, 130))
    left = 0
    for img in imagefile:
        target.paste(img, (left, 0))
        left += img.size[0]
    target.save('{}.png'.format(text if text else 'Yama'), quality=100)