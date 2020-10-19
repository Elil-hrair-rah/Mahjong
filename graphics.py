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

def player_image(player, *args):
    if not isinstance(player, Player):
        return False
    
    if player.melds.melds:
        image_list = []
        parts = [player.hand]
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
                print(rotate)
            
        
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