import random
import time
from aio_timers import Timer

from mahjong.hand_calculating.hand import HandCalculator
from mahjong.hand_calculating.hand_config import HandConfig

from mahjong.constants import EAST, SOUTH, WEST, NORTH

from player import Player, TsumoBot
from tiles import Tile, Wall, Dora, Hand, Melds, Discards
from graphics import makeImage, makeYamaImage, discard_image
from functions import winning_tiles, ukeire, shanten_calculator
from errorhandling import GameOver

import os
from dotenv import load_dotenv

import discord
from discord.ext import commands

import asyncio

intents = discord.Intents(messages = True, guilds = True, members = True, reactions = True)
discordclient = commands.Bot(command_prefix = 'm!', intents = intents)

load_dotenv()

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
    
    async def begin_game(self):
        game_cont = 1
        global active_users
        while game_cont == True:
            game = Game(self.player_order, self.match_id, self.aka, self.round_wind)
            active_games.append(game)
            await game.start()
            
            
            #end game if west 4
            if self.round_number == 4 and self.round_wind == WEST:
                game_cont = False
            
            #end game if south 4 and someone has more than 30000 points
            if self.round_number == 4 and self.round_wind == SOUTH:
                for player in self.players:
                    if player.points >= 30000:
                        game_cont = False
            
            #repeat if dealer was tenpai or won, unless dealer is tenpai and
            #has the most points and one of the above conditions is fulfilled
            if game.winner is not None and game.east in game.winner:
                tot_points = [player.points for player in self.players]
                if game.east.points != max(tot_points):
                    game_cont = True
            else:
                self.round_progression()
                
            #end game if bust
            for player in self.players:
                if player.points < 0:
                    game_cont = False
        
        points_string = ''
        for player in self.players:
            points_string += str(player.disc) + ': ' + str(player.points) + '\n'
        for player in self.players:
            dm = player.disc.dm_channel
            if not dm:
                dm = await player.disc.create_dm()
            await dm.send(points_string)
            if player.disc in active_users:
                active_users.pop(player.disc)
            

class Game:
    
    def __init__(self, players, match_id, aka = 3, wind = EAST):
        self.players = players
        self.match_id = match_id
        
        #temporary
        self.round_wind = wind
        
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
        
        self.winner = None
        
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
                seat = {EAST: "East", SOUTH: "South", WEST: "West", NORTH: "North"}
                await player.show_hand(message = ("You are " + seat[player.seat]))
            
        while self.wall.remaining > 0:
            try:                
                discard, hidden_hand = await self.active_player.draw_discard(self)
                
                other_players = [player for player in self.players if player is not self.active_player]
                
                for player in other_players:
                    dm = player.disc.dm_channel
                    if not dm:
                        dm = await player.disc.create_dm()
                    hidden_hand.seek(0)
                    hidden = discord.File(hidden_hand, filename = str(self.active_player.disc) + "'s hand.png")
                    
                    await dm.send(str(self.active_player.disc) + "'s hand", file = hidden)
                    if self.active_player.in_riichi:
                        await dm.send(str(self.active_player.disc) + ' is in riichi!')
                        
                    discard_pile = discard_image(self.active_player, discard)
                    discard_img = discord.File(discard_pile, filename = str(self.active_player.disc) + "'s discards.png")
                    await dm.send(str(self.active_player.disc) + "'s discards", file = discard_img)
                    
                await self.process_discard(discard)     
                self.turn_progress()
            except GameOver as result:
                win_string = ''
                for winner, score in result.winner_result_dict.items():
                    print("winner", winner)
                    print('score', score)
                    #TODO: check and implement headbump for riichi sticks and honba
                    
                    #ron
                    
                    #should now return riichi sticks to players and take honba
                    #into consideration, not that honba works yet
                    
                    #TODO: riichi sticks not working?
                    
                    if score.cost['additional'] is None or score.cost['additional'] == 0:
                        #calculate headbump player, if applicable
                        #this might not actually be necessary, depending on how
                        #players get added to the game over result, but just in case
                        if len(result.winner_result_dict) > 1:
                            rotation = [self.east, self.south, self.west, self.north]
                            distances = [(rotation.index(player) - rotation.index(self.active_player) % 4)\
                                         for player in result.winner_result_dict.keys()]
                            my_distance = (rotation.index(winner) - rotation.index(self.active_player)) % 4
                            
                            if my_distance == min(distances):
                                self.honba = 0
                                self.riichi = 0
                        else:
                            honba = self.honba * 300
                            riichi = self.riichi * 1000
                            self.honba = 0
                            self.riichi = 0
                                
                        
                        self.active_player.points -= (score.cost['main'] + honba)
                        winner.points += (score.cost['main'] + honba + riichi)
                        win_string += str(winner.disc) + ' has won by ron off ' + str(self.active_player.disc) +\
                                          ' and won ' + str(score.cost['main']) + ' points.\n'
                    #tsumo
                                          
                    #should now return riichi sticks to players and take honba
                    #into consideration, not that honba works yet
                    else:
                        other_players = [player for player in self.players if player is not self.active_player]
                        score_change = 0
                        for player in other_players:
                            if player.seat == EAST:
                                player.points -= (score.cost['main'] + self.honba * 100)
                                winner.points += (score.cost['main'] + self.honba * 100)
                                score_change += (score.cost['main'] + self.honba * 100)
                            else:
                                player.points -= (score.cost['additional'] + self.honba * 100)
                                winner.points += (score.cost['additional'] + self.honba * 100)
                                score_change += (score.cost['additional'])
                        player.points += self.riichi * 1000
                        win_string += str(winner.disc) + ' has won by tsumo and won ' + str(score_change) + ' points.\n'
                        self.riichi = 0
                        self.honba = 0

                details = str(score) + '\nYaku:\n' + str(score.yaku) + '\nFu:\n' + str(score.fu_details)
                    
                scores = 'Scores:\n'
                for player in self.players:
                    scores += str(player.disc) + ': ' + str(player.points) + '\n'
                    
                global active_games            
                
                is_riichi = False
                for player in result.winner_result_dict.keys():
                    if player.in_riichi:
                        is_riichi = True
                
                if is_riichi:
                    for player in self.players:
                        dora_img = makeYamaImage(str(self.ura_dora))
                        dora_img.seek(0)
                        dora = discord.File(dora_img, filename = "uradora.png")
                        dm = player.disc.dm_channel
                        if not dm:
                            dm = await player.disc.create_dm()
                        await dm.send("Uradora indicator:", file = dora)
                
                #might need to compact this part due to discord's ratelimits
                for player in self.players:
                    dm = player.disc.dm_channel
                    if not dm:
                        dm = await player.disc.create_dm()
                    final_string = win_string + '\n\n' + details + '\n\n' + scores
                    for winner in result.winner_result_dict.keys():
                        await winner.show_hand(dm = dm, message = final_string)
                active_games.remove(self)
                self.wall.remaining = -1
                
                self.winner = result.winner_result_dict.keys()
                
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
                            
            self.winner = []                    

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
                            new_discard, hidden_hand = await self.active_player.draw_discard(self.wall)
                            await self.add_dora()
                        
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
                            new_discard, hidden_hand = await self.active_player.discard_tile()
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
                        new_discard, hidden_hand = await self.active_player.discard_tile()
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
                
                discard_pile = discard_image(self.active_player, new_discard)
                discard_img = discord.File(discard_pile, filename = str(self.active_player.disc) + "'s discards.png")
                await dm.send(str(self.active_player.disc) + "'s discards", file = discard_img)
            await self.process_discard(new_discard)
            
        #adds discards to the discard pile, which can then be checked for furiten
        #and referenced to display discard piles
        else:
            if self.active_player.discards.riichi_index is None and self.active_player.in_riichi:
                self.active_player.discards.declare_riichi(discard)
            else:
                self.active_player.discards.add_tiles(discard)
        self.active_player.total_discards.add_tiles(discard)



calculator = HandCalculator()
config = HandConfig()

#test discord ids xd
whitelist = os.getenv("WHITELIST").split(' ')
whitelist = [int(disc_id) for disc_id in whitelist]

pending_games = dict()
pending_bot_games = dict()
active_users = dict()
pending_users = []
active_games = []
active_bot_games = []
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
async def print_hand(ctx, arg):
    if ctx.author.id in whitelist:
        hand_picture = makeImage(arg)
        hand = discord.File(hand_picture, filename = arg + ".png")
        await ctx.send('hand', file = hand)
    else:
        await ctx.send("Administrator command")

    
@discordclient.command()
async def player_hand(ctx):
    """ Display hand
    Displays the tiles in a players hand in DM
    """
    if ctx.author in active_users:
        game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
        player = [player for player in game.players if player.disc == ctx.author]
        await player[0].show_hand()
        await ctx.send('Hand Shown')
    else:
        await ctx.send('You are not in a game')
        
@discordclient.command()
async def game_dora(ctx):
    """ Display dora
    Displays the dora tiles in an active game in DM
    """
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
    global pending_bot_games
    global active_users
    
    
    user = reaction.member
    message_id = reaction.message_id
    
    channel = discordclient.get_channel(reaction.channel_id)
    message = await channel.fetch_message(message_id)
    active = False
    for reaction in message.reactions:
        if reaction.me:
            active = True
    
    if message_id in pending_games and str(reaction.emoji) == '✅' and active:
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
#            game = Game(players, message_id)
#            active_games.append(game)
#            await game.start()
            match = Match(players, message_id)
            active_matches.append(match)
            await message.add_reaction('❌')
            await match.begin_game()
            
    if message_id in pending_bot_games and str(reaction.emoji) == '✅' and active:
        if user not in active_users and user.id != discordclient.user.id:
            pending_bot_games[message_id].append(user)
        if len(pending_bot_games[message_id]) == 1:
            user = pending_bot_games[message_id][0]
            del pending_bot_games[message_id]
            active_users[user] = message_id
            players = []
            players.append(Player(user.id, user, discordclient))
            for _ in range(3):
                players.append(TsumoBot(user.id, user, discordclient))
            match = Match(players, message_id)
            active_matches.append(match)
            await message.add_reaction('❌')
            await match.begin_game()
        
@discordclient.event
async def on_raw_reaction_remove(reaction):
    global pending_games
    message_id = reaction.message_id
    user = [user for user in pending_games[message_id] if user.id == reaction.user_id]
    if message_id in pending_games and str(reaction.emoji) == '✅':
        if user:
            pending_games[message_id].remove(user[0])
  
async def remove_react(msg):
    await msg.remove_reaction('✅', discordclient.user)
    await msg.add_reaction('❌')

@discordclient.command()
async def game(ctx):
    ''' Start a game of mahjong
    '''
    if str(ctx.message.channel.type) == "private":
        await ctx.send("This command does not work in DMs")
    else:
        global pending_games
        msg = await ctx.send("React to this message with ✅ to join the game. You cannot join a game while participating in another one.")
        pending_games[msg.id] = []
        await msg.add_reaction('✅')
        timer = Timer(1800, remove_react, callback_args = (msg,))
    
@discordclient.command()    
async def bot_game(ctx):
    ''' Start a bot game of mahjong
    '''
    global pending_bot_games
    
    if str(ctx.message.channel.type) == "private":
        await ctx.send("This command does not work in DMs")
    else:
        msg = await ctx.send("React to this message with ✅ to join the game. You cannot join a game while participating in another one.")
        pending_bot_games[msg.id] = []
        await msg.add_reaction('✅')
        timer = Timer(1800, remove_react, callback_args = (msg,))
        
@discordclient.command()
async def invite(ctx):
    ''' The invite link for this bot.
    If the link doesn't work, it's probably because the bot is in 100 servers and I haven't verified it.
    '''
    await ctx.send('https://discord.com/oauth2/authorize?client_id=769708017993121822&permissions=387136&scope=bot')
    
@discordclient.command()
async def github(ctx):
    ''' My github.
    '''
    await ctx.send('https://github.com/Elil-hrair-rah/Mahjong')

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

@discordclient.command()
async def leave_game(ctx):
    """Leave the current game.
    Leave the game you are in. You will be replaced with a tsumogiri bot.
    Do not use this function while you are prompted to do something else.
    """
    global active_users
    if ctx.author in active_users:
        game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
        match = [match for match in active_matches if match.match_id == active_users[ctx.author]][0]
        hand = [player for player in game.players if player.disc == ctx.author][0].hand
        replacement = TsumoBot(ctx.author.id, ctx.author, discordclient)
        replacement.hand.add_tiles(str(hand))
        game.players = [replacement if player.disc == ctx.author else player for player in game.players]
        
        if game.east.disc == ctx.author:
            game.east = replacement
            replacement.seat = EAST
            game.active_player = game.east
        elif game.south.disc == ctx.author:
            game.south = replacement
            replacement.seat = SOUTH
        elif game.west.disc == ctx.author:
            game.west = replacement
            replacement.seat = WEST
        elif game.north.disc == ctx.author:
            game.north = replacement
            replacement.seat = NORTH
        
        match.player_order = [TsumoBot(ctx.author.id, ctx.author, discordclient) if player.disc == ctx.author else player for player in match.player_order]
        
        if ctx.author in active_users:
            active_users.pop(ctx.author)
        await ctx.send('Game abandoned successfully')
    else:
        await ctx.send('You are not in a game')
        
@discordclient.command()
async def visible(ctx):
    """Displays a list of all tiles visible to you at the current moment.
    Might not display the most recently drawn tile if you use this command
    while being prompted to discard.
    """
    
    if ctx.author in active_users:
        game = [game for game in active_games if game.match_id == active_users[ctx.author]][0]
        user = [player for player in game.players if ctx.author == player.disc][0]
        tiles = user.visible_tiles(game)
        await ctx.send(str(tiles))
    else:
        await ctx.send('You are not in a game')
    
@discordclient.command()
async def changelog(ctx):
    ''' A list of changes since the last update.
    Current version: 1.0.2
    '''
    await ctx.send('Added 30 minute window to start a game.\
                    Added the option to leave a game, and have a tsumogiri bot replace you.\
                    Added the option to play a solo game against 3 tsumogiri bots.')
                    
token = os.getenv("DISCORD_TOKEN")
discordclient.run(token)