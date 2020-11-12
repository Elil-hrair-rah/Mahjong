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
from mahjong.hand_calculating.hand_config import HandConfig, OptionalRules
from mahjong.meld import Meld as mjMeld
from mahjong.shanten import Shanten

from mahjong.constants import EAST, SOUTH, WEST, NORTH

import discord

from graphics import player_image, makeImage, makeYamaImage
from tiles import Tile, Tiles, Wall, OneOfEach, Dora, Hand, Meld, Melds, Discards
from functions import shanten_calculator, winning_tiles 
from errorhandling import GameOver

import asyncio




        

class Player:
    
    def __init__(self, disc_id, disc, client, match_id = 1, seat = None, luck = 0, points = 25000):
        self.disc_id = disc_id
        self.disc = disc
        self.client = client
        self.match_id = match_id
        self.seat = seat
        self.luck = luck
        self.points = points
        self.hand = Hand()
        self.melds = Melds()
        self.discards = Discards()
        self.total_discards = Discards()
        self.rinshan = False
        self.in_riichi = False
        self.double_riichi = False
        self.ippatsu = False
        self.tenhou = True
        self.chiihou = True
        self.renhou = True
        self.temp_furiten = False
        self.riichi_furiten = False
        
    def __str__(self):
        return str(self.hand) + ' ' + str(self.melds)
    
    def draw_tile(self, wall):
        draw = wall.draw_tile(self)
        #image = makeImage(' '.join([str(self.hand), str(draw)]))
        self.hand.add_tiles(draw)
        
    #TODO: test this function
    async def discard_tile(self):
        dm = self.disc.dm_channel
        hand_picture = player_image(self, False, False)
        hand = discord.File(hand_picture, filename = "hand.png")
        if not dm:
            dm = await self.disc.create_dm()
        await dm.send('your hand', file = hand)
        
        discard = Tile('8','z')
        
        query = "What tile do you want to discard?\n" + str(self.hand)
        
        while discard not in self.hand.tiles:
            try:
                discard = await self.user_input(query)
                discard = Tile(discard[0],discard[1])
            except asyncio.exceptions.TimeoutError:
                discard = random.choice(self.hand.tiles)
            except ValueError:
                discard = Tile('8','z')
            except IndexError:
                discard = Tile('8','z')
            query = "Invalid discard, please try again."
        
        self.temp_furiten = False
        
        self.hand.remove_tiles(discard)
        self.total_discards.add_tiles(discard)
        #if tile is not stolen:
        self.discards.add_tiles(discard)
        
        hand_picture = player_image(self, True, True, str(discard))
#        hidden_hand = discord.File(hand_picture, filename = "hand.png")
#        await dm.send('opp vision', file = hidden_hand)
        
        return discard, hand_picture
        
    async def show_hand(self, dm = None):
        
        if dm is None:
            dm = self.disc.dm_channel
        hand_picture = player_image(self, False, False)
        hand = discord.File(hand_picture, filename = "hand.png")
        if not dm:
            dm = await self.disc.create_dm()
        await dm.send(str(self.disc) + "'s hand", file = hand)
    
    #TODO: account for melds (done?)
    async def draw_discard(self, game):
        draw = game.wall.draw_tile(self)
        
        discard = Tile('8','z')
        
        dm = self.disc.dm_channel
        hand_picture = player_image(self, False, False, draw)
        hand_picture.seek(0)
        hand = discord.File(hand_picture, filename = "hand.png")
        if not dm:
            dm = await self.disc.create_dm()
        await dm.send('your hand', file = hand)
        
        tsumo = self.tsumo(draw, game)
        if tsumo:
            try:
                choice = await self.user_input("Would you like to tsumo?")
            except asyncio.exceptions.TimeoutError:
                choice = 'y'
            if choice == 'y' or choice == 'yes':
                #TODO: figure out how to end the game and interrupt gameflow
                result = dict()
                result[self] = tsumo
                raise GameOver(result, draw)
        
        ckan = self.ckan_tiles()
        if ckan:
            try:
                choice = await self.user_input("Would you like to closed kan?")
            except asyncio.exceptions.TimeoutError:
                choice = 'n'
            if choice == 'y' or choice == 'yes':
                call = await self.ckan()
                if call:
                    discard, hidden_picture = self.draw_discard(game)
                    self.rinshan = False
                    return discard, hidden_picture
                    
        if self.in_riichi:
            discard = draw
        else:
            discard = await self.riichi(draw, game)
        
        if not discard:
            #image = makeImage(' '.join([str(self.hand), str(draw)]))
            discard = Tile('8','z')
            query = "What tile do you want to discard?\n" + str(self.hand) + ' ' + str(draw)
            
            while discard not in self.hand.tiles and discard != draw:
                try:
                    discard = await self.user_input(query)
                    discard = Tile(discard[0],discard[1])
                except asyncio.exceptions.TimeoutError:
                    discard = draw
                except ValueError:
                    discard = Tile('8','z')
                except IndexError:
                    discard = Tile('8','z')
                query = "Invalid discard, please try again."
        
        
        
        if discard == draw:
            hidden_picture = player_image(self, True, True, str(discard))
        else:
            hidden_picture = player_image(self, True, False, str(discard))
        
#        hidden_hand = discord.File(hidden_picture, filename = "hand.png")
#        await dm.send('opp vision', file = hidden_hand)
        
        self.temp_furiten = False
        
        self.hand.add_tiles(draw)
        self.hand.remove_tiles(discard)
        self.total_discards.add_tiles(discard)
        
        hand_picture = player_image(self, False, False)
        final_hand = discord.File(hand_picture, filename = "hand.png")
        
        await dm.send('final hand', file = final_hand)
        return discard, hidden_picture
    
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
        if search:
            if len(search) > 1:
                return search
        return False
        
    def okan_tiles(self, discard):
        search = self.pon_tiles(discard)
        if search:
            if len(search) > 2:
                return search
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
                    search.append([meld, [tile for tile in self.hand.tiles if tile == meld.tiles[0]][0]])
        if search:
            return search
        return False
            
    async def chii(self, discard, game):
        chii_tiles = self.chii_tiles(discard)
        if chii_tiles:
            if len(chii_tiles) > 1:
                try:
                    query = "Please choose your desired meld or type cancel:\n" + ' '.join(map(str, chii_tiles))
                    choice = await self.user_input(query)
                except asyncio.exceptions.TimeoutError:
                    choice = 'cancel'

                if choice == 'cancel':
                    return False
                else:
                    matching = [meld for meld in chii_tiles if choice == str(meld)]
                    if matching:
                        match = matching[0]
                        meld = Meld(match, called = discard, opened = True, who = "L")
                        self.melds.add_meld(meld)
                        match.remove_tiles(discard)
                        self.hand.remove_tiles(match)
                        return True
                    else:
                        return False
            else:
                match = chii_tiles[0]
                meld = Meld(match, called = discard, opened = True, who = "L")
                self.melds.add_meld(meld)
                match.remove_tiles(discard)
                self.hand.remove_tiles(match)
                return True
        else:
            return False
        
    async def pon(self, discard, game):
        pon_tiles = self.pon_tiles(discard)
        if pon_tiles:
            rotation = [EAST, SOUTH, WEST, NORTH]
            relative_direction = ["N", "L", "M", "R"]
            who = rotation.index(self.seat) - rotation.index(game.active_player.seat)
            who = relative_direction[who % 4]
            
            if len(pon_tiles) > 2 and discard.true_value == 5 and discard.value != '0':
                red_five = [tile for tile in pon_tiles if tile.value == '0']
                reg_five = [tile for tile in pon_tiles if tile.value == '5']
                try:
                    choice = await self.user_input('Pon with red 5? Type cancel to cancel pon.')
                except asyncio.exceptions.TimeoutError:
                    choice = 'cancel'
                if choice == 'cancel':
                    return False
                elif choice == 'y' or choice == 'yes':
                    print('choice yes')
                    meld = Meld([discard,red_five[0], reg_five[0]], called = discard,\
                                opened = True, who = who)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles([red_five[0], reg_five[0]])
                    return True
                elif choice == 'n' or choice == 'no':
                    print('choice no')
                    meld = Meld([discard, reg_five[0], reg_five[1]], called = discard,\
                                opened = True, who = who)
                    self.melds.add_meld(meld)
                    self.hand.remove_tiles(reg_five)
                    return True
            else:
                meld = Meld([discard, pon_tiles[0], pon_tiles[1]], called = discard,\
                            opened = True, who = who)
                self.melds.add_meld(meld)
                self.hand.remove_tiles(pon_tiles[:2])
                return True
        else:
            return False
        
    def okan(self, discard, game):
        okan_tiles = self.okan_tiles(discard)
        if okan_tiles:
            rotation = [EAST, SOUTH, WEST, NORTH]
            relative_direction = ["N", "L", "M", "R"]
            who = rotation.index(self.seat) - rotation.index(game.active_player.seat)
            who = relative_direction[who % 4]
            
            self.hand.remove_tiles(okan_tiles)
            okan_tiles.append(discard)
            meld = Meld(okan_tiles, called = discard, opened = True, who = who)
            self.melds.add_meld(meld)
            return True
        else:
            return False
        
    async def ckan(self):
        ckan_tiles = self.ckan_tiles()
        if ckan_tiles:
            if len(ckan_tiles) > 1:
                try:
                    query = 'Which kan?\n' + ' '.join(map(str, [tile[-1] for tile in ckan_tiles]))
                    choice = await self.user_input(query)
                except asyncio.exceptions.TimeoutError:
                    choice = 'cancel'
                
                if choice == 'cancel':
                    return False
                chosen_kan = [kan for kan in ckan_tiles if str(kan[1]) == choice][0]
                if not chosen_kan:
                    return False
            else:
                chosen_kan = ckan_tiles[0]
                
            if len(chosen_kan) == 2:
                chosen_kan[0].add_tiles(chosen_kan[1])
                chosen_kan[0].shominkan = True
                chosen_kan[0].shominkan_tile = chosen_kan[1]
                self.hand.remove_tiles(chosen_kan[1])
            else:
                meld = Meld(chosen_kan, opened = False)
                self.melds.add_meld(meld)
                self.hand.remove_tiles(chosen_kan)
            self.rinshan = True
            return True
        else:
            return False
        
    def furiten(self):
        perm_furiten = any(tile in winning_tiles(str(self.hand)) for tile in self.total_discards.tiles)
        return perm_furiten or self.temp_furiten or self.riichi_furiten
    
    async def riichi(self, draw, game):
        
        #this *should* check the hand to make sure its closed        
        opened = [meld for meld in self.melds.melds if meld.opened]
        
        if opened:
            return False
        
        #determine what tiles are discardable to be in tenpai
        
        shanten = shanten_calculator(str(self.hand) + str(draw))
        if (shanten == 0 or shanten == -1) and self.points >= 1000 and not self.in_riichi:
            riichi_tiles = []
            temp_hand = Tiles()
            temp_hand.tiles = self.hand.tiles[:]
            temp_hand.add_tiles(draw)
            for tile in temp_hand.tiles:
                temp = Tiles()
                temp.tiles = temp_hand.tiles[:]
                temp.remove_tiles(tile)
                if winning_tiles(str(temp)) and tile not in riichi_tiles:
                    riichi_tiles.append(tile)
            
            if riichi_tiles:
                try:
                    reach = await self.user_input('Would you like to riichi?')
                except asyncio.exceptions.TimeoutError:
                    reach = 'n'
                if reach != 'y' and reach != 'yes':
                    return False
            else:
                return False
            
            discard = Tile('8','z')
            while discard not in self.hand.tiles and discard != draw:
                try:
                    query = "Which tile would you like to riichi on? Type cancel to cancel riichi.\n" + ' '.join(map(str, riichi_tiles))
                    discard = await self.user_input(query)
                    discard = Tile(discard[0],discard[1])
                except asyncio.exceptions.TimeoutError:
                    return False
                except ValueError:
                    discard = Tile('8','z')
                except IndexError:
                    discard = Tile('8','z')

            #self.discard_tile(choice)
            if game.tenhou and game.wall.remaining > 65:
                self.double_riichi = True
            self.in_riichi = True
            self.ippatsu = True
            self.points -= 1000
            game.riichi += 1
            return discard
        else:
            return False
                
        '''
        if winning_tiles(self.hand) :
            self.in_riichi == True
            self.points -= 1000
        else:
            return False
        '''
        
    def ron(self, discard, game):
        if discard in winning_tiles(str(self.hand)) and self.furiten() == False:
            
            dora = str(game.dora)
            if self.in_riichi:
                dora += str(game.ura_dora)
                
            dora_indicators = TilesConverter.one_line_string_to_136_array(dora)
            
            calculator = HandCalculator()
            houtei = False
            renhou = False
            
            if game.wall.remaining == 0:
               houtei = True
            if game.tenhou and game.wall.remaining > 65:
               renhou = True
            #if (shominkan):
            #   chankan = True
            chankan = False
            config = HandConfig(options = OptionalRules(has_open_tanyao = True),\
                                is_riichi = self.in_riichi,\
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
                return False
        else:
            return False
    
    def tsumo(self, draw, game):
        if draw in winning_tiles(str(self.hand)):
            calculator = HandCalculator()
            
            dora = str(game.dora)
            if self.in_riichi:
                dora += str(game.ura_dora)
                
            dora_indicators = TilesConverter.one_line_string_to_136_array(dora)
            
            haitei = False
            tenhou = False
            chiihou = False
            if game.wall.remaining == 0:
               haitei = True
            if game.tenhou and game.wall.remaining > 65:
               if self.seat == EAST:
                   tenhou = True
               else:
                   chiihou = True
                   
            config = HandConfig(options = OptionalRules(has_open_tanyao = True),\
                                is_tsumo = True,\
                                is_riichi = self.in_riichi,\
                                is_ippatsu = self.ippatsu,\
                                is_rinshan = self.rinshan,\
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
                return False
        else:
            return False
            
    async def user_input(self, query, timeout = 25.0):
        dm = self.disc.dm_channel
        if not dm:
            dm = await self.disc.create_dm()
        await dm.send(query)
        def check(msg):
            return msg.channel == dm and msg.author == self.disc
        response = await self.client.wait_for('message', check = check, timeout = timeout)
        return response.content
    