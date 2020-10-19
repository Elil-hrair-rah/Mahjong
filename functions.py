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

from tiles import Tile, Tiles, Wall, OneOfEach, Dora, Hand, Meld, Melds, Discards

def winning_tiles(tiles):
    if isinstance(tiles,str):
        tiles = tiles.replace(' ','')
        test_tiles = OneOfEach()
        return [tile for tile in test_tiles.tiles if shanten_calculator(tiles + str(tile)) == -1]
    elif issubclass(type(tiles),Tiles):
        return winning_tiles(str(tiles))
    elif isinstance(tiles,list):
        temp = Tiles()
        temp.add_tiles(tiles)
        return winning_tiles(str(temp))
    
def ukeire(tiles):
    if isinstance(tiles,str):
        tiles = tiles.replace(' ','')
        test_tiles = OneOfEach()
        shanten = [shanten_calculator(str(tiles) + str(tile)) for tile in test_tiles.tiles]
        return [tile for index, tile in enumerate(test_tiles.tiles) if shanten[index] == min(shanten)]
    elif issubclass(type(tiles),Tiles):
        return ukeire(str(tiles))
    elif isinstance(tiles,list):
        temp = Tiles()
        temp.add_tiles(tiles)
        return ukeire(str(temp))
        
def hand_calculator(tiles, win_tile, config = HandConfig()):
    calculator = HandCalculator()
    tiles = TilesConverter.one_line_string_to_136_array(str(tiles))
    win_tile = TilesConverter.one_line_string_to_136_array(str(win_tile))[0]
    return calculator.estimate_hand_value(tiles, win_tile, config = config)

def shanten_calculator(tiles):
    shanten = Shanten()
    tiles = TilesConverter.one_line_string_to_34_array(str(tiles))
    result = shanten.calculate_shanten(tiles)
    return result