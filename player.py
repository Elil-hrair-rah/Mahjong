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

class Player:
    
    def __init__(self, name, disc_id, seat = None, luck = 0, points = 25000):
        self.name = name
        self.disc_id = disc_id
        self.seat = seat
        self.luck = luck
        self.points = points
        self.hand = Hand()
        self.melds = Melds()
        self.discards = Discards()
        self.total_discards = Discards()
        self.in_riichi = False
        self.double_riichi = False
        self.ippatsu = False
        self.tenhou = True
        self.chiihou = True
        self.renhou = True
        
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
            
    def chii(self, discard, game):
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
                        meld = Meld(match, called = discard, opened = True, who = game.active_player)
                        self.melds.add_meld(meld)
                        match.remove_tiles(discard)
                        self.hand.remove_tiles(match)
                    else:
                        return False
            else:
                match = chii_tiles[0]
                meld = Meld(match, called = discard, opened = True, who = game.active_player)
                self.melds.add_meld(meld)
                match.remove_tiles(discard)
                self.hand.remove_tiles(match)
        else:
            return False
        
    def pon(self, discard, game):
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
                    meld = Meld([discard,red_five[0], reg_five[0]], called = discard,\
                                opened = True, who = game.active_player)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles([red_five[0], reg_five[0]])
                elif choice == 'n' or choice == 'no':
                    meld = Meld([discard, reg_five[0], reg_five[1]], called = discard,\
                                opened = True, who = game.active_player)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles(reg_five)
            else:
                meld = Meld([discard, pon_tiles[0], pon_tiles[1]], called = discard,\
                            opened = True, who = game.active_player)
                self.melds.add_meld(meld)
                self.hand.remove_tiles(pon_tiles[:2])
        else:
            return False
        
    def okan(self, discard, game):
        okan_tiles = self.okan_tiles(discard)
        if okan_tiles:
            self.hand.remove_tiles(okan_tiles)
            okan_tiles.append(discard)
            meld = Meld(okan_tiles, called = discard, opened = True, who = game.active_player)
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
    
    def riichi(self):
        
        #this *should* check the hand to make sure its closed        
        opened = [meld for meld in self.melds.melds if meld.opened]
        if opened:
            return False
        
        if winning_tiles(self.hand):
            self.in_riichi == True
        else:
            return False
        
    def ron(self, discard, game):
        if discard in winning_tiles(self.hand) and self.furiten() == False:
            
            dora = str(game.dora)
            if self.in_riichi:
                dora += str(game.ura_dora)
                
            dora_indicators = TilesConverter.one_line_string_to_136_array(dora)
            
            calculator = HandCalculator()
            #if (is last tile in wall):
            #   houtei = True
            #if (no actions previously):
            #   renhou = True
            #if (shominkan):
            #   chankan = True
            #player wind
            #round wind
            houtei = False
            renhou = False
            chankan = False
            config = HandConfig(is_riichi = self.in_riichi,\
                                is_ippatsu = self.ippatsu,\
                                is_daburu_riichi = self.double_riichi,\
                                is_houtei = houtei,\
                                is_renhou = renhou,\
                                is_chankan = chankan,\
                                player_wind = self.seat,\
                                round_wind = game.round_wind\
                                )
            
            melds = []
            meld_string = ''
            for meld in self.melds.melds:
                opened = True
                if len(meld) == 4:
                    meld_type = mjMeld.KAN
                    opened = meld.opened
                elif meld.tiles.count(meld.tiles[0]) == 3:
                    meld_type = mjMeld.PON
                else:
                    meld_type = mjMeld.CHII
                    
                    #not sure if the meld_type is necessary, but since it's not a hassle i'll leave it in
                new_meld = mjMeld(meld_type = meld_type,\
                                  tiles = TilesConverter.one_line_string_to_136_array(str(meld)),\
                                  opened = opened)
                melds.append(new_meld)
                
                #really dumb workaround because the hand is supposed to be exactly 14 tiles
                #and adding the kan as a string directly to the rest of the hand
                #causes the hand to exceed 14 tiles
                
                #this would subtract by 4 if len(meld) referred to the length of the
                #string associated with the meld, but len(meld) actually refers
                #to the number of tiles in the meld (aka it ignores the suit)
                #so the length of '222p' is 3 and the length of '1111m' is 4
                meld_string += str(meld)[len(meld)-3:]
                
            hand = TilesConverter.one_line_string_to_136_array(str(self.hand) + str(discard) + str(meld_string))
            discard = TilesConverter.one_line_string_to_136_array(str(discard))[0]
            
            result = calculator.estimate_hand_value(hand, discard, melds = melds, \
                                                    dora_indicators = dora_indicators, config = config)
            if result.yaku:
                return result
            else:
                return 'No yaku'
        else:
            return False
    
    def tsumo(self, draw, game):
        if draw in winning_tiles(self.hand):
            calculator = HandCalculator()
            
            dora = str(game.dora)
            if self.in_riichi:
                dora += str(game.ura_dora)
                
            dora_indicators = TilesConverter.one_line_string_to_136_array(dora)
        
            #if (is last tile in wall):
            #   haitei = True
            #if (no actions previously):
            #   if (is dealer):
            #       tenhou = True
            #   else:
            #       chiihou = True
            #if ():
            #   chankan = True
            #player wind
            #round wind
            rinshan = False
            haitei = False
            tenhou = False
            chiihou = False
            config = HandConfig(is_tsumo = True,\
                                is_riichi = self.in_riichi,\
                                is_ippatsu = self.ippatsu,\
                                is_rinshan = rinshan,\
                                is_haitei = haitei,\
                                is_daburu_riichi = self.double_riichi,\
                                is_tenhou = tenhou,\
                                is_chiihou = chiihou,\
                                player_wind = self.seat,\
                                round_wind = game.round_wind\
                                )
            
            melds = []
            meld_string = ''
            for meld in self.melds.melds:
                opened = True
                if len(meld) == 4:
                    meld_type = mjMeld.KAN
                    opened = meld.opened
                elif meld.tiles.count(meld.tiles[0]) == 3:
                    meld_type = mjMeld.PON
                else:
                    meld_type = mjMeld.CHII
                    
                    #not sure if the meld_type is necessary, but since it's not a hassle i'll leave it in
                new_meld = mjMeld(meld_type = meld_type,\
                                  tiles = TilesConverter.one_line_string_to_136_array(str(meld)),\
                                  opened = opened)
                melds.append(new_meld)
                
                #really dumb workaround because the hand is supposed to be exactly 14 tiles
                #and adding the kan as a string directly to the rest of the hand
                #causes the hand to exceed 14 tiles
                
                #this would subtract by 4 if len(meld) referred to the length of the
                #string associated with the meld, but len(meld) actually refers
                #to the number of tiles in the meld (aka it ignores the suit)
                #so the length of '222p' is 3 and the length of '1111m' is 4
                meld_string += str(meld)[len(meld)-3:]
                
            hand = TilesConverter.one_line_string_to_136_array(str(self.hand) + str(draw) + str(meld_string))
            draw = TilesConverter.one_line_string_to_136_array(str(draw))[0]
            result = calculator.estimate_hand_value(hand, draw, melds = melds, \
                                                    dora_indicators = dora_indicators, config = config)
            if result.yaku:
                return result
            else:
                return 'No yaku'
        else:
            return False
            
            