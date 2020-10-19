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

luck_min = -100
luck_max = 100

class Tile:
    
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        self.true_value = int(value)
        if self.value == '0':
            self.true_value = 5
        
    def __str__(self):
        return self.value + self.suit
    
    def __eq__(self, other):
        return self.true_value == other.true_value and self.suit == other.suit
    
    def influence(self, weights, wall, luck, luck_mode = 0):
        #surrounding = lambda x: range(max(i-2,1, min(i+3,10)))
        surrounding = {1:['1','2','3'],\
                       2:['1','2','3','4'],\
                       3:['1','2','3','4','5'],\
                       4:['2','3','4','5','6'],\
                       5:['3','4','5','6','7'],\
                       6:['4','5','6','7','8'],\
                       7:['5','6','7','8','9'],\
                       8:['6','7','8','9'],\
                       9:['7','8','9'],\
                       }
        surround = []
        if self.suit == 'z' or luck_mode == 1:
            surround.append(self)
        else:
            for value in surrounding[self.true_value]:
                surround.append(Tile(value, self.suit))
        print(surround, luck_mode)
        indices = [i for i in range(len(weights)) if wall.tiles[i] in surround]
        if luck > 0:
            array = np.zeros(len(weights))
            array[indices] = luck
        else:
            array = np.zeros(len(weights))
            array[indices] = (luck/abs(luck_min))*0.5*weights[indices]
        return weights + array
    
class Tiles:
    
    def __init__(self):
        self.tiles = []
    
    def add_tiles(self, tiles):
        
        if isinstance(tiles,str):
            suits = re.findall('[mpsz]', tiles)
            values = re.split('[mpsz]', tiles)
            for index, suit in enumerate(suits):
                for value in values[index]:
                    self.tiles.append(Tile(value, suit))
        elif issubclass(type(tiles),Tile) or issubclass(type(tiles),Tiles):
            self.add_tiles(str(tiles))
        elif isinstance(tiles,list):
            for tile in tiles:
                self.add_tiles(str(tile))
                
    def remove_tiles(self, tiles):
        
        if isinstance(tiles,str):
            suits = re.findall('[mpsz]', tiles)
            values = re.split('[mpsz]', tiles)
            for index, suit in enumerate(suits):
                for value in values[index]:
                    remove = [index for index, tile in enumerate(self.tiles) if tile.suit == suit and tile.value == value]
                    if len(remove) > 0:
                        del self.tiles[remove[0]]
                        #self.tiles.remove(remove[0])
                    else:
                        return False
        elif issubclass(type(tiles),Tile) or issubclass(type(tiles),Tiles):
            self.remove_tiles(str(tiles))
        elif isinstance(tiles,list):
            for tile in tiles:
                self.remove_tiles(str(tile))                
                
    def replace_tiles(self, add, remove):
        self.add_tiles(add)
        self.remove_tiles(remove)
        
    def add_tile_list(self, lst):
        self.tiles.extend(lst)
                
    def __str__(self):
        suits = ['m', 'p', 's', 'z']
        tiles = []
        string = ''
        for suit in suits:
            sort = sorted(self.tiles, key=lambda tile:tile.true_value)
            tiles.append([tile for tile in sort if tile.suit == suit])
            if tiles[-1]:
                string += ''.join([tile.value for tile in tiles[-1]]) + suit
        return string
        
    def __len__(self):
        return len(self.tiles)
    
class Wall(Tiles):
    
    def __init__(self, aka = 3):
        Tiles.__init__(self)
        self.add_tiles('123456789'*4 + 'm')
        self.add_tiles('123456789'*4 + 'p')
        self.add_tiles('123456789'*4 + 's')
        self.add_tiles('1234567'*4 + 'z')
        if aka != 0:
            self.replace_tiles('0m', '5m')
            self.replace_tiles('0p', '5p')
            self.replace_tiles('0s', '5s')
        if aka == 4:
            self.replace_tiles('0p', '5p')
        self.remaining = 70
            
    def deal_hand(self, player):
        hand = random.sample(self.tiles, 13)
        player.hand.add_tile_list(hand)
        self.remove_tiles(player.hand)
        
    def dora(self, dora):
        indicator = random.sample(self.tiles, 1)
        dora.add_tiles(str(indicator[0]))
        self.remove_tiles(str(indicator[0]))
        
    def draw_tile(self, player):
        
        draw = random.choices(self.tiles, k = 1)[0]
        if player.luck != 0:
            hand = player.hand.tiles
            weights = np.ones(len(self))
            for tile in hand:
                weights = tile.influence(weights, self, player.luck)
            draw = random.choices(self.tiles, weights = weights, k = 1)[0]
        self.remove_tiles(draw)
        self.remaining -= 1
        return draw
        
class OneOfEach(Tiles):
    
    def __init__(self):
        Tiles.__init__(self)
        self.add_tiles('123456789m123456789p123456789s1234567z')
    
class Dora(Tiles):
    
    def __init__(self):
        Tiles.__init__(self)
            
class Hand(Tiles):
    
    def __init__(self):
        Tiles.__init__(self)
    
class Meld(Tiles):
    
    def __init__(self, tiles, called = None, who = None, opened = False):
        Tiles.__init__(self)
        self.add_tiles(tiles)
        self.called = called
        self.who = who
        self.opened = opened
        self.shominkan = False
#        if called:
#            self.tiles.append(called)
        
class Melds:
    
    def __init__(self):
        self.melds = []
        
    def add_meld(self, meld):
        self.melds.append(meld)
        
    def __str__(self):
        return ' '.join(str(meld) for meld in self.melds)
    
    def __len__(self):
        return len(self.melds)
        
class Discards(Tiles):
    
    def __init__(self):
        Tiles.__init__(self)