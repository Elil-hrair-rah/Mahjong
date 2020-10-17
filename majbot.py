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

luck_min = -100
luck_max = 100

class Game:
    
    def __init__(self, players, aka = 3):
        self.wall = Wall(aka)
        self.east = players[0]
        self.south = players[1]
        self.west = players[2]
        self.north = players[3]
        self.active_player = self.east
        self.dora = Dora()
        self.ura_dora = Dora()
        self.dora_tiles = Tiles()
                    
    def dora_indicator(self):
        return
    
    def turn_progress(self):
        rotation = [self.east, self.south, self.west, self.north, self.east]
        self.active_player = rotation[rotation.index(self.active_player) + 1]
        
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
        
    def one_of_each(self):
        self.add_tiles('123456789m123456789p123456789s1234567z')
                
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
        return draw
        
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

class Player:
    
    def __init__(self, name, disc_id, luck = 0, points = 25000):
        self.name = name
        self.disc_id = disc_id
        self.luck = luck
        self.points = points
        self.hand = Hand()
        self.melds = Melds()
        self.discards = Discards()
        self.total_discards = Discards()
        self.riichi = False
        
    def __str__(self):
        return str(self.hand) + ' ' + str(self.melds)
    
    def chii_tiles(self, discard):
        if discard.suit == 'z':
            return False
        else:
            combinations = []
            
            tiles = [tile for tile in self.hand.tiles if tile.suit == discard.suit]
            prev1 = [tile for tile in tiles if tile.true_value == discard.true_value - 1]
            next1 = [tile for tile in tiles if tile.true_value == discard.true_value + 1]
            
            if prev1 and prev1[0].true_value != 5:
                prev1 = [prev1[0]]
            
            if prev1:
                prev2 = [tile for tile in tiles if tile.true_value == discard.true_value - 2]
                if prev2:
                    if prev2[0].true_value != 5:
                        prev2 = [prev2[0]]
                    for tile1 in prev1:
                        for tile2 in prev2:
                            chii = Tiles()
                            chii.add_tiles([tile2,tile1,discard])
                            combinations.append(chii)
                            
            if prev1 and next1:
                for tile1 in prev1:
                    for tile2 in next1:
                        chii = Tiles()
                        chii.add_tiles([tile1,discard,tile2])
                        combinations.append(chii)
                        
            if next1 and next1[0].true_value != 5:
                next1 = [next1[0]]
                        
            if next1:
                next2 = [tile for tile in tiles if tile.true_value == discard.true_value + 2]
                if next2:
                    if next2[0].true_value != 5:
                        next2 = [next2[0]]
                    for tile1 in next1:
                        for tile2 in next2:
                            chii = Tiles()
                            chii.add_tiles([discard,tile1,tile2])
                            combinations.append(chii)                
            return combinations
    
    def pon_tiles(self, discard):
        search = [tile for tile in self.hand.tiles if tile == discard]
        if len(search) > 1:
            return search
        else:
            return False
        
    def okan_tiles(self, discard):
        search = self.pon_tiles(discard)
        if len(search) > 2:
            return search
        else:
            return False
        
    def ckan_tiles(self):
        search = []
        quad = [tile for tile in self.hand.tiles if self.hand.tiles.count(tile) == 4]
        while len(quad) > 0:
            first_quad = [tile for tile in quad if tile == quad[0]]
            search.append(first_quad)
            for tile in first_quad:
                quad.remove(tile)
                
        pon = [meld for meld in self.melds.melds if meld.tiles.count(meld.tiles[0]) == 3]
        if pon:
            for meld in pon:
                if meld.tiles[0] in self.hand.tiles:
                    search.append([meld, meld.tiles[0]])
        if search:
            return search
        return False
            
    def chii(self, discard):
        chii_tiles = self.chii_tiles(discard)
        if chii_tiles:
            if len(chii_tiles) > 1:
                for options in chii_tiles:
                    print(options)
                print("Please choose your desired meld:")
                choice = input()
                if choice == 'cancel':
                    return False
                else:
                    matching = [meld for meld in chii_tiles if choice == str(meld)]
                    if matching:
                        match = matching[0]
                        meld = Meld(match, called = discard, opened = True)#TODO: who = global.player)
                        self.melds.add_meld(meld)
                        match.remove_tiles(discard)
                        self.hand.remove_tiles(match)
                    else:
                        return False
            else:
                match = chii_tiles[0]
                meld = Meld(match, called = discard, opened = True)#TODO: who = global.player)
                self.melds.add_meld(meld)
                match.remove_tiles(discard)
                self.hand.remove_tiles(match)
        else:
            return False
        
    def pon(self, discard):
        pon_tiles = self.pon_tiles(discard)
        if pon_tiles:
            if len(pon_tiles) > 2 and discard.true_value == 5 and discard.value != '0':
                red_five = [tile for tile in pon_tiles if tile.value == '0']
                reg_five = [tile for tile in pon_tiles if tile.value == '5']
                print('Pon with red 5?')
                choice = input()
                if choice == 'cancel':
                    return False
                elif choice == 'y' or choice == 'yes':
                    meld = Meld([discard,red_five[0], reg_five[0]], called = discard, opened = True)#TODO: who = global.player)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles([red_five[0], reg_five[0]])
                elif choice == 'n' or choice == 'no':
                    meld = Meld([discard, reg_five[0], reg_five[1]], called = discard, opened = True)#TODO: who = global.player)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles(reg_five)
            else:
                meld = Meld([discard, pon_tiles[0], pon_tiles[1]], called = discard, opened = True)#TODO: who = global.player)
                self.melds.add_meld(meld)
                self.hand.remove_tiles(pon_tiles[:2])
        else:
            return False
        
    def okan(self, discard):
        okan_tiles = self.okan_tiles(discard)
        if okan_tiles:
            self.hand.remove_tiles(okan_tiles)
            okan_tiles.append(discard)
            meld = Meld(okan_tiles, called = discard, opened = True)#TODO: who = global.player)
            self.melds.add_meld(meld)
        else:
            return False
        
    def ckan(self):
        ckan_tiles = self.ckan_tiles()
        if ckan_tiles:
            if len(ckan_tiles) > 1:
                for option in ckan_tiles:
                    print(option[1])
                print('Which kan?')
                choice = input()
                if choice == 'cancel':
                    return False
                chosen_kan = [kan for kan in ckan_tiles if str(kan[1]) == choice][0]
                if not chosen_kan:
                    return False
            else:
                chosen_kan = ckan_tiles[0]
                
            if len(chosen_kan) == 2:
                chosen_kan[0].add_tiles(chosen_kan[1])
                self.hand.remove_tiles(chosen_kan[1])
            else:
                meld = Meld(chosen_kan, opened = False)
                self.melds.add_meld(meld)
                self.hand.remove_tiles(chosen_kan)
        else:
            return False
        
    def furiten(self):
        return any(tile in winning_tiles(str(self.hand)) for tile in self.total_discards.tiles)
        
def winning_tiles(tiles):
    if isinstance(tiles,str):
        test_tiles = Tiles()
        test_tiles.one_of_each()
        return [tile for tile in test_tiles.tiles if shanten_calculator(tiles + str(tile)) == -1]
    elif issubclass(type(tiles),Tiles):
        return winning_tiles(str(tiles))
    elif isinstance(tiles,list):
        temp = Tiles()
        temp.add_tiles(tiles)
        return winning_tiles(str(temp))
    
def ukeire(tiles):
    if isinstance(tiles,str):
        test_tiles = Tiles()
        test_tiles.one_of_each()
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