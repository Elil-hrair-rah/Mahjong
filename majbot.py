import json

import random
import requests

from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig

from mahjong.constants import EAST, SOUTH, WEST, NORTH

from player import Player
from tiles import Tile, Wall, Dora, Hand, Melds, Discards
from graphics import player_image, makeImage, makeYamaImage
from functions import winning_tiles, ukeire, shanten_calculator
from errorhandling import GameOver, EndGame

import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

import asyncio

intents = discord.Intents(messages = True, guilds = True, members = True, reactions = True)
discordclient = commands.Bot(command_prefix = 'm!', intents = intents)

load_dotenv()

#will implement full hanchans at some point
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
        
        #temporary
        self.round_wind = EAST
        
        self.wall = Wall(aka)
        
        self.east = players[0]
        self.east.seat = EAST
        self.south = players[1]
        self.south.seat = SOUTH
        self.west = players[2]
        self.west.seat = WEST
        self.north = players[3]
        self.north.seat = NORTH
        
        for player in players:
            player.hand = Hand()
            player.melds = Melds()
            player.discards = Discards()
            player.total_discards = Discards()
            player.rinshan = False
            player.in_riichi = False
            player.double_riichi = False
            player.ippatsu = False
            player.tenhou = True
            player.chiihou = True
            player.renhou = True
            player.temp_furiten = False
            player.riichi_furiten = False
        
        self.wall.deal_hand(self.east)
        self.wall.deal_hand(self.south)
        self.wall.deal_hand(self.west)
        self.wall.deal_hand(self.north)
        
        self.active_player = self.east
        
        self.dora = Dora()
        self.ura_dora = Dora()
        
        self.tenhou = True
        
        self.honba = 0
        self.riichi = 0
        
        self.num_kan = 0
        
        #que
        #self.dora_tiles = Tiles()
                    
    async def add_dora(self):
        self.wall.dora(self.dora)
        self.wall.dora(self.ura_dora)
        for player in self.players:            
            dora_img = makeYamaImage(str(self.dora))
            dora_img.seek(0)
            dora = discord.File(dora_img, filename = "dora.png")
            dm = player.disc.dm_channel
            if not dm:
                dm = await player.disc.create_dm()
            await dm.send("Dora indicator:", file = dora)
        return
    
    def turn_progress(self):
        rotation = [self.east, self.south, self.west, self.north, self.east]
        self.active_player = rotation[rotation.index(self.active_player) + 1]
        
    def next_player(self):
        rotation = [self.east, self.south, self.west, self.north, self.east]
        return rotation[rotation.index(self.active_player) + 1]
        
        
    async def start(self):
        
        await self.add_dora()
        
        for player in self.players:
            if player is not self.active_player:
                await player.show_hand()
                print(player)
            
            
            
        while self.wall.remaining > 0:
            try:                
                discard, hidden_hand = await self.active_player.draw_discard(self)
                
                other_players = [player for player in self.players if player is not self.active_player]
                
                for player in other_players:
                    dm = player.disc.dm_channel
                    if not dm:
                        dm = await player.disc.create_dm()
                    hidden_hand.seek(0)
                    hidden = discord.File(hidden_hand, filename = str(player.disc) + "'s hand.png")
                    
                    await dm.send(self.active_player.disc, file = hidden)
                    if self.active_player.in_riichi:
                        await dm.send(str(self.active_player.disc) + ' is in riichi!')
                    
                await self.process_discard(discard)     
                self.turn_progress()
            except GameOver as result:
                win_string = ''
                for winner, score in result.winner_result_dict.items():
                    
                    #ron
                    if score.cost['additional'] == 0:
                        self.active_player.points -= score.cost['main']
                        winner.points += score.cost['main']
                        win_string += str(winner.disc) + ' has won by ron off ' + str(self.active_player.disc) +\
                                          ' and won ' + str(score.cost['main']) + ' points.\n'
                    #tsumo
                    else:
                        other_players = [player for player in self.players if player is not self.active_player]
                        score_change = 0
                        for player in other_players:
                            if player.seat == EAST:
                                player.points -= score.cost['main']
                                winner.points += score.cost['main']
                                score_change += score.cost['main']
                            else:
                                player.points -= score.cost['additional']
                                winner.points += score.cost['additional']
                                score_change += score.cost['additional']
                        win_string += str(winner.disc) + ' has won by tsumo and won ' + str(score_change) + ' points.\n'

                details = str(score) + '\nYaku:\n' + str(score.yaku) + '\nFu:\n' + str(score.fu_details)
                    
                scores = 'Scores:\n'
                for player in self.players:
                    scores += str(player.disc) + ': ' + str(player.points) + '\n'
                    
                global active_users
                global active_games            
                
                #might need to compact this part due to discord's ratelimits
                for player in self.players:
                    dm = player.disc.dm_channel
                    if not dm:
                        dm = await player.disc.create_dm()
                    final_string = win_string + '\n\n' + details + '\n\n' + scores
                    for winner in result.winner_result_dict.keys():
                        await winner.show_hand(dm = dm, message = final_string)
                    active_users.pop(player.disc)
                active_games.remove(self)
                self.wall.remaining = -1
        if self.wall.remaining == 0:
            #TODO: add nagashi
            tenpai_players = [player for player in self.players if winning_tiles(player.hand)]
            noten_players = [player for player in self.players if player not in tenpai_players]
            
            draw_string = 'Draw\n'
            
            if 0 < len(tenpai_players) < 4:
                payment = 3000 // len(noten_players)
                payout = 3000 // len(tenpai_players)
                
                draw_string += 'The following players were in tenpai:\n'
                
                for player in tenpai_players:
                    draw_string += str(player.disc) + '\n'
                    player.points += payout
                for player in noten_players:
                    player.points -= payment
            
            if len(tenpai_players) == 0:
                draw_string += 'No players were in tenpai.'
            
            if len(tenpai_players) == 4:
                draw_string += 'All players were in tenpai.'
            
            scores = 'Scores:\n'
            for player in self.players:
                scores += str(player.disc) + ': ' + str(player.points) + '\n'
                
            #may also need to compact this due to discord's ratelimits
            for player in self.players:
                
                final_string = draw_string + '\n\n' + scores
                
                dm = player.disc.dm_channel
                if not dm:
                    dm = await player.disc.create_dm()
                await dm.send(final_string)
                for player in tenpai_players:
                    await player.show_hand(dm = dm)
                
                    

    #processes player discards
    #gives priority to ron
    #kan and pon have the same priority for obvious reasons
    #gives next player in line the option to chii if available
    #two players should not be able to call the same tile unless someone cheated a bunch of tiles into their hand
    async def process_discard(self, discard):
        called = False
        other_players = [player for player in self.players if player is not self.active_player]
        
        rons = dict()
        for player in other_players:
            ron = player.ron(discard, self)
            if ron:
                try:
                    choice = await player.user_input('Would you like to ron on the ' + str(discard) + '?')
                except asyncio.exceptions.TimeoutError:
                    choice = 'y'
                if choice == 'yes' or choice == 'y':
                    rons[player] = ron
                else:
                    player.temp_furiten = True
                    if player.in_riichi:
                        player.riichi_furiten = True
        
        if rons:
            raise GameOver(rons, discard)
        
        for player in other_players:
            if not player.in_riichi:
                kan = player.okan_tiles(discard)
                if kan and self.num_kan < 4:
                    try:
                        choice = await player.user_input('Would you like to kan on the ' + str(discard) + '?')
                    except asyncio.exceptions.TimeoutError:
                        choice = 'n'
                    if choice == 'yes' or choice == 'y':
                        called = await player.okan(discard, self)
                        if called:
                            self.active_player = player
                            discard, hidden_hand = await self.active_player.draw_discard(self.wall)
                            self.add_dora()
                        
                pon = player.pon_tiles(discard)
                if pon:
                    try:
                        choice = await player.user_input('Would you like to pon on the ' + str(discard) + '?')
                    except asyncio.exceptions.TimeoutError:
                        choice = 'n'
                    if choice == 'yes' or choice == 'y':
                        called = await player.pon(discard, self)
                        if called:
                            self.active_player = player
                            discard, hidden_hand = await self.active_player.discard_tile()
        next_player = self.next_player()
        if not next_player.in_riichi:
            chii = next_player.chii_tiles(discard)
            if chii and not called:
                try:
                    choice = await next_player.user_input('Would you like to chii on the ' + str(discard) + '?')
                except asyncio.exceptions.TimeoutError:
                    choice = 'n'
                if choice == 'yes' or choice == 'y':
                    called = await next_player.chii(discard, self)
                    if called:
                        self.active_player = next_player
                        discard, hidden_hand = await self.active_player.discard_tile()
        if called:
            
            for player in self.players:
                player.ippatsu = False
                self.tenhou = False
            
            other_players = [player for player in self.players if player is not self.active_player]
            for player in other_players:
                dm = player.disc.dm_channel
                if not dm:
                    dm = await player.disc.create_dm()
                hidden_hand.seek(0)
                hidden = discord.File(hidden_hand, filename = "hand.png")
                await dm.send(self.active_player.disc, file = hidden)
            await self.process_discard(discard)




calculator = HandCalculator()
config = HandConfig()

#test discord ids xd
whitelist = os.getenv("WHITELIST").split(' ')
whitelist = [int(disc_id) for disc_id in whitelist]

pending_games = dict()
active_users = dict()
pending_users = []
active_games = []
active_matches = []


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
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        response = await user_input(args, player)
        print(response.content)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def player_input(ctx, args):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        response = await player.user_input(args, discordclient)
        print(response.content)
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def graphics_test(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
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
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
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
    if ctx.author in active_users:
        game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
        player = [player for player in game.players if player.disc == ctx.author]
        await player[0].show_hand()
        await ctx.send('Hand Shown')
    else:
        await ctx.send('You are not in a game')
        
@discordclient.command()
async def game_dora(ctx):
    if ctx.author in active_users:
        game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
        dora_image = makeYamaImage(str(game.dora))
        dora = discord.File(dora_image, filename = "hand.png")
        dm = ctx.author.dm_channel
        if not dm:
            dm = await ctx.author.create_dm()
        await dm.send("Dora", file = dora)
    else:
        await ctx.send('You are not in a game')
    
@discordclient.command()
async def player_dd(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        if ctx.author in active_users:
            game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
            player = [player for player in game.players if player.disc == ctx.author]
            await player[0].draw_discard(game.wall)
            await ctx.send('Draw and Discard')
        else:
            await ctx.send('You are not in a game')
    else:
        await ctx.send("Administrator command")
    
@discordclient.command()
async def chii_test(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient, ctx.message.id)
        otherplayer = Player('notbob', 1, discordclient, ctx.message.id)
        game = Game([player, otherplayer, otherplayer, otherplayer], ctx.message.id)
        player.hand.add_tiles('1234506m')
        active_games.append(game)
        active_users[ctx.author] = ctx.message.id
        await player.chii(Tile('4','m'), game)
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def pon_test(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([player, otherplayer, otherplayer, otherplayer], 1)
        player.hand.add_tiles('111550m')
        active_games.append(game)
        active_users[ctx.author] = ctx.message.id
        await player.pon(Tile('1','m'), game)
        await player.pon(Tile('5','m'), game)
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def kan_test(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player('bob', ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([player, otherplayer, otherplayer, otherplayer], 1)
        player.hand.add_tiles('111550m9999m')
        player.okan(Tile('1','m'), game)
        active_games.append(game)
        active_users[ctx.author] = ctx.message.id
        await player.pon(Tile('5','m'), game)
        await player.ckan()
        await player.ckan()
        await ctx.send(str(player))
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def riichi_test(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        player = Player(ctx.author.id, ctx.author, discordclient)
        otherplayer = Player('notbob', 1, discordclient)
        game = Game([otherplayer, otherplayer, otherplayer, otherplayer], 1)
        player.hand.add_tiles('1112345678999m')
        discard = await player.riichi(Tile('2','p'), game)
        await ctx.send(str(player) + str(Tile('2','p')))
        await ctx.send(str(discard))
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
            await game.start()
            
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
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
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
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
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
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        await ctx.send(pending_games)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def active_user(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        await ctx.send(active_users)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def active_game(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        await ctx.send(active_games)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def pending_user(ctx):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    if ctx.author.id in whitelist:
        await ctx.send(pending_users)
    else:
        await ctx.send("Administrator command")
        
@discordclient.command()
async def add_pending_user(ctx, arg):
    ''' admin command
    this is a command used for testing functionality and either doesnt work or shouldnt be used
    '''
    global pending_users
    if ctx.author.id in whitelist:
        for user in active_users:
            if int(arg) == user.id:
                pending_users.append(user)
    else:
        await ctx.send("Administrator command")

@discordclient.command()
async def game(ctx):
    ''' Start a game of mahjong
    '''
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
    await ctx.send('https://discord.com/oauth2/authorize?client_id=769708017993121822&permissions=387136&scope=bot')

@discordclient.command()
async def official_server(ctx):
    ''' The invite link for the official server.
    It probably doesn't exist yet.
    '''
    await ctx.send("it doesn't exist yet lol")
    
@discordclient.command()
async def improvements(ctx, arg):
    ''' A (13 - 3n)-tile improvement calculator.
    Prints a list of tiles that can improve your hand (decrease the shanten count)
    Except weird results if you enter the wrong number of tiles.
    '''
    tiles = ukeire(arg)
    tiles = [str(tile) for tile in tiles]
    tiles = ' '.join(tiles)
    await ctx.send(tiles)
    
@discordclient.command()
async def shanten(ctx, arg):
    ''' A (14 - 3n)-tile shanten calculator.
    -2 indicates an invalid hand, -1 indicates a winning hand, 0 indicates tenpai, etc
    '''
    await ctx.send(shanten_calculator(arg))
    
@discordclient.command()
async def waits(ctx, arg):
    ''' A (13 - 3n)-tile tenpai wait calculator.
    Returns the tiles you can win on.
    '''
    agaripai = winning_tiles(arg)
    agaripai = [str(tile) for tile in agaripai]
    agaripai = ' '.join(agaripai)
    await ctx.send(agaripai)

token = os.getenv("DISCORD_TOKEN")
discordclient.run(token)