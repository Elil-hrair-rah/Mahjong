# -*- coding: utf-8 -*-

import io
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
from graphics import player_image, makeImage, makeYamaImage

import discord
from discord.ext import commands

class Match:
    
    def __init__(self, players, match_id, aka = 3):
        self.match_id = match_id
        self.players = players
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
        
        game = Game(self.player_order, self.match_id, self.aka)

class Game:
    
    def __init__(self, players, match_id, aka = 3):
        self.players = players
        self.match_id = match_id
        
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

whitelist = [422108792923095050,
             634524535957356574,
             120552456626241536,
             606746521538527234]

pending_games = dict()
active_users = dict()
pending_users = []
active_games = []
active_matches = []

intents = discord.Intents(messages = True, guilds = True, members = True, reactions = True)
discordclient = commands.Bot(command_prefix = 'm!', intents = intents)


async def user_input(query, player):
    dm = player.disc_id.dm_channel
    if not dm:
        dm = await player.disc_id.create_dm()
    await dm.send(query)
    def check(msg):
        return msg.channel == dm
    response = await discordclient.wait_for('message', check = check, timeout = 25.0)
    return response
    
@discordclient.command()
async def input_test(ctx, args):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        response = await user_input(args, player)
        print(response.content)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def player_input(ctx, args):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        response = await player.user_input(args, discordclient)
        print(response.content)
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def graphics_test(ctx):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([player, otherplayer, otherplayer, otherplayer])
        hand_picture = player_image(player, False, True)
        hand = discord.File(hand_picture, filename = "hand.png")
        await ctx.send('hand', file = hand)
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def print_hand(ctx, arg):
    if ctx.author.id in whitelist:
        hand_picture = makeImage(arg)
        hand = discord.File(hand_picture, filename = arg + ".png")
        await ctx.send('hand', file = hand)
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def create_player(ctx):
    global active_users;
    if ctx.author.id in whitelist and ctx.author not in active_users:
        global active_games
        player = Player(ctx.author.id, ctx.author, discordclient, ctx.message.id)
        otherplayer = Player(0, discordclient.user, discordclient, ctx.message.id)
        game = Game([player, otherplayer, otherplayer, otherplayer], ctx.message.id)
        active_games.append(game)
        active_users[ctx.author] = ctx.message.id
        await ctx.send('Player object created')
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def player_hand(ctx):
    if ctx.author.id in whitelist:
        if ctx.author in active_users:
            game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
            player = [player for player in game.players if player.disc == ctx.author]
            await player[0].show_hand()
        await ctx.send('Hand Shown')
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def player_dd(ctx):
    if ctx.author.id in whitelist:
        if ctx.author in active_users:
            game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
            player = [player for player in game.players if player.disc == ctx.author]
            await player[0].draw_discard(game.wall)
        await ctx.send('Draw and Discard')
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def chii_test(ctx):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient, ctx.message.id)
        otherplayer = Player('notbob', 1, discordclient, ctx.message.id)
        game = Game([player, otherplayer, otherplayer, otherplayer], ctx.message.id)
        player.hand.add_tiles('1234506m')
        await player.chii(Tile('4','m'), game)
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def pon_test(ctx):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([player, otherplayer, otherplayer, otherplayer])
        player.hand.add_tiles('111550m')
        await player.pon(Tile('1','m'), game)
        await player.pon(Tile('5','m'), game)
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def kan_test(ctx):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([player, otherplayer, otherplayer, otherplayer])
        player.hand.add_tiles('111550m9999m')
        player.okan(Tile('1','m'), game)
        await player.pon(Tile('5','m'), game)
        await player.ckan()
        await player.ckan()
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def riichi_test(ctx):
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        player.hand.add_tiles('1112345678999m2s')
        await player.riichi()
        await ctx.send(str(player))
        await ctx.send(player.points)
        await ctx.send(player.in_riichi)
    else:
        await ctx.send("Administrator command")

@discordclient.event
async def on_ready():
    print('Connected to bot: {}'.format(discordclient.user.name))
    print('Bot ID: {}'.format(discordclient.user.id))


@discordclient.event
async def on_message(message):
    if str(message.channel.type) == "private":
        global pending_users
        if message.author in pending_users:
            await message.channel.send(message.content)
            pending_users.remove(message.author)
        #if message.author.id != discordclient.user.id:
        #    await message.channel.send('is dm')
    await discordclient.process_commands(message)

@discordclient.event
async def on_raw_reaction_add(reaction):
    global pending_games
    global active_users
    user = reaction.member
    message_id = reaction.message_id
    channel = discordclient.get_channel(reaction.channel_id)
    if message_id in pending_games and str(reaction.emoji) == '✅':
        if user not in active_users and user.id != discordclient.user.id:
            pending_games[message_id].append(user)
        if len(pending_games[message_id]) == 4:
            users = pending_games[message_id][:]
            del pending_games[message_id]
            players = []
            for user in users:
                active_users[user] = message_id
                players.append(Player(user.id, user, discordclient))
                for ids in pending_games.values():
                    try:
                        ids.remove(user)
                    except ValueError:
                        pass
            game = Game(players, message_id)
            active_games.append(game)
            
            await channel.send('game started')
            #TODO: start game
        
@discordclient.event
async def on_raw_reaction_remove(reaction):
    global pending_games
    message_id = reaction.message_id
    user = [user for user in pending_games[message_id] if user.id == reaction.user_id]
    if message_id in pending_games and str(reaction.emoji) == '✅':
        if user:
            pending_games[message_id].remove(user[0])
            
@discordclient.command()
async def dm(ctx, *arg):
    if ctx.author.id in whitelist:
        if arg:
            target = discordclient.get_user(int(arg[0]))
            dm = target.dm_channel
            if not dm:
                await target.create_dm()
            await dm.send('testing targeted dm functionality')
        else:
            await ctx.author.send('testing dm functionality')
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def pending_dm(ctx, key):
    if ctx.author.id in whitelist:
        for user in pending_games[int(key)]:
            dm = user.dm_channel
            if not dm:
                dm = await user.create_dm()
            await dm.send('testing targeted dm functionality')
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def pending_game(ctx):
    if ctx.author.id in whitelist:
        await ctx.send(pending_games)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def active_user(ctx):
    if ctx.author.id in whitelist:
        await ctx.send(active_users)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def active_game(ctx):
    if ctx.author.id in whitelist:
        await ctx.send(active_games)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def pending_user(ctx):
    if ctx.author.id in whitelist:
        await ctx.send(pending_users)
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def add_pending_user(ctx, arg):
    global pending_users
    if ctx.author.id in whitelist:
        for user in active_users:
            if int(arg) == user.id:
                pending_users.append(user)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def game(ctx):
    if str(ctx.message.channel.type) == "private":
        await ctx.send("This command does not work in DMs, as a game of mahjong requires 4 people to play. AI functionality does not yet exist.")
    else:
        global pending_games
        msg = await ctx.send("React to this message with ✅ to join the game. You cannot join a game while participating in another one.")
        pending_games[msg.id] = []
        await msg.add_reaction('✅')
        
@discordclient.command()
async def invite(ctx):
    ''' The invite link for this bot.
    If the link doesn't work, it's probably because the bot is in 100 servers and I haven't verified it.
    '''
    print('https://discord.com/oauth2/authorize?client_id=769708017993121822&permissions=387136&scope=bot')
    await ctx.send('https://discord.com/oauth2/authorize?client_id=769708017993121822&permissions=387136&scope=bot')

@discordclient.command()
async def os(ctx):
    ''' The invite link for the official server.
    It probably doesn't exist yet.
    '''
    pass
    
discordclient.run("NzY5NzA4MDE3OTkzMTIxODIy.X5S8cw.tSClXF6i-4i0Kl9bAyA3euDQciw")
