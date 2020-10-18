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

luck_min = -100
luck_max = 100

class Match:
    
    def __init__(self, players, aka = 3):
        self.player_order = random.sample(players, 4)
        self.round_wind = EAST
        self.round_number = 1
        self.aka = aka
        
    def round_progression(self):
        wind_rotation = [EAST, SOUTH, WEST, NORTH, EAST]
        self.round_number += 1
        if self.round_number == 5:
            self.round_number = 1
            self.round_wind = wind_rotation[wind_rotation.index(self.round_wind) + 1]
        players = self.player_order[1:]
        players.append(self.player_order[0])
        self.player_order = players
    
    def begin_game(self):
        
        game = Game(self.player_order, self.aka)

class Game:
    
    def __init__(self, players, aka = 3):
        self.wall = Wall(aka)
        
        self.east = players[0]
        self.east.seat = EAST
        self.south = players[1]
        self.south.seat = SOUTH
        self.west = players[2]
        self.west.seat = WEST
        self.north = players[3]
        self.north.seat = NORTH
        
        self.wall.deal_hand(self.east)
        self.wall.deal_hand(self.south)
        self.wall.deal_hand(self.west)
        self.wall.deal_hand(self.north)
        
        self.active_player = self.east
        
        self.dora = Dora()
        self.ura_dora = Dora()
        self.wall.dora(self.dora)
        self.wall.dora(self.ura_dora)
        
        #que
        #self.dora_tiles = Tiles()
                    
    def add_dora(self):
        self.wall.dora(self.dora)
        self.wall.dora(self.ura_dora)
        return
    
    def turn_progress(self):
        rotation = [self.east, self.south, self.west, self.north, self.east]
        self.active_player = rotation[rotation.index(self.active_player) + 1]
        
            
        
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
        target.paste(img, (left, 0))
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

calculator = HandCalculator()
config = HandConfig()

def countPoint(data):
    def getYakuInfo(yaku_id, ura):
        ids = [
            1, 2, 3, 4, 5, 6, 71, 72, 73, 74, 75, 8, 9, 10, 11, 12, 13, 14, 15,
            16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
            33, 34, 35, 36, 37, 38, 39, 40, 41
        ]
        names = [
            "Riichi", "Ippatsu", "Tsumo", "Pinfu", "Tanyao", "Iipeikou", "Prevalent wind", "Seat wind",
            "Haku", "Hatsu", "Chun", "Haitei", "Houtei", "Chankan", "Rinshan", "Double riichi", "Chiitoi",
            "Ittsu", "Sanshoku doujun", "Chanta", "Sanshoku doukou", "Sanankou", "Toitoi", "Shousangen", "Honroutou", "Sankantsu",
            "Honitsu", "Junchan", "Ryanpeikou", "Chinitsu", "Kokushi", "Daisangen", "Suuankou", "Shousuushi", "Tsuuiisou",
            "Ryuuiisou", "Chinroutou", "Chuuren", "Suukantsu", "Tenhou", "Chiihou", "Kokushi 13 waits", "Daisuushii", "Suuankou tanki",
            "Junsei Chuuren"
        ]
        fan_richi = [
            1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2,
            2, 2, 2, 2, 3, 3, 3, 6, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
            26, 26, 26, 26
        ]
        fan_fuuro = [
            0, 0, 0, 0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 2, 2,
            2, 2, 2, 2, 2, 2, 0, 5, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13, 13,
            26, 26, 26, 26
        ]
        if int(yaku_id) // 100 == 1:
            return "{}\t{} Han\n".format("Dora", int(yaku_id) % 100)
        elif int(yaku_id) // 100 == 2:
            return "{}\t{} Han\n".format("Akadora", int(yaku_id) % 100)
        elif int(yaku_id) // 100 == 3:
            return "{}\t{} Han\n".format("Uradora", int(yaku_id) % 100)
        return "{}\t{} Han\n".format(
            names[ids.index(yaku_id)], fan_richi[ids.index(yaku_id)]
            if ura else fan_fuuro[ids.index(yaku_id)])

    headers = {
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:68.0) Gecko/20100101 Firefox/68.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language':
        'zh-CN,zh;q=0.8,zh-TW;q=0.7,zh-HK;q=0.5,en-US;q=0.3,en;q=0.2',
        'Referer': 'https://www.diving-fish.com/mahjong/point',
        'Content-Type': 'application/json;charset=utf-8',
        'Origin': 'https://www.diving-fish.com',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    }
    result = requests.post('https://www.diving-fish.com:8000/cal',
                           headers=headers,
                           data=json.dumps(data)).json()
    
    print(result)
    
    if result.get('status') != 200:
        print('Error', 'Value not calculated, please recheck syntax.')
        return 'chombo'
    
    


    for x in result['data']['yakus']:
        print(INSERT, getYakuInfo(x, result['data']['inner']))
    print(
        INSERT, 'Value\t{} Fu - {} Han\n'.format(result['data']['fu'],
                                      result['data']['fan']))
    print(
        INSERT, 'Score\t{}\n'.format((
            "{} ALL".format(result['data']['perPoint'] * 2 // 100 *
                            100) if result['data']['tsumo'] else (
                                result['data']['perPoint'] * 6 // 100 * 100)
        ) if result['data']['isQin'] else ("{} - {}".format(
            result['data']['perPoint'], result['data']['perPoint'] *
            2) if result['data']['tsumo'] else (result['data']['perPoint'] *
                                                4 // 100 * 100))))
                                                
def makeData(hand = '44455m', riichi = False):
    postdata = {
        "inner": hand,
        "outer": '111m 222m 333m',
        "dora": '12m',
        "innerdora": '45m',
        "selfwind": 1,
        "placewind": 2,
        "reach": riichi,
        "wreach": False,
        "yifa": False,
        "tsumo": False,
        "lingshang": False,
        "qianggang": False,
        "haidi": False,
        "hedi": False,
        "tianhe": False,
        "dihe": False
    }
    return postdata