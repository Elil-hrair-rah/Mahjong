import re
import numpy as np
import random

#dumb luck parameters pls ignore
luck_min = -100
luck_max = 100

class Tile:
    
    #value vs true value is only because of red fives
    #having some things be strings and some things be ints is partially laziness
    #but also because it minimizes the amount of conversions required as well as
    #makes the whole chii check easier
    def __init__(self, value, suit):
        self.value = value
        self.suit = suit
        self.true_value = int(value)
        if self.value == '0':
            self.true_value = 5
        
    def __str__(self):
        return self.value + self.suit
    
    #this kind of fucks with certain things because it makes red 5s functionally
    #equivalent to regular 5s in most of the code, so anything that checks equivalence
    #(for example, removing tiles from hand) would treat them as the same object
    #so special precautions need to be taken as to not have that happen
    #that being said, it also means that sorting the hand automatically groups 
    #regular 5s with red 5s so i'd consider that worth going through the trouble for
    def __eq__(self, other):
        return self.true_value == other.true_value and self.suit == other.suit
    
    #see the Wall object's draw_tiles function for an explanation what this is for
    #tl;dr luck stat influencing draws, isnt implemented anywhere yet
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
    
    #no real safety check to prevent you from getting like 1000 copies of the same tile
    #dont really think it matters though
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
                
    #removing a 5 keeps the red 5 in the hand
    #probably bugs out if you try to remove a tile not in the hand already
    #but theoretically other parts of the code prevent this from happening
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
                
    #tenhou/majsoul standard tile notation
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
        
    #the luck variable is a stupid meme i decided to add and will probably be implemented
    #as a fun game mode later on
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
        
#useful for brute-force functions like ukeire and winning_tiles
#probably also useful for brute force AI algorithms as well
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
    
#there is another meld object in the mahjong library, but having this one be a subclass
#of tiles maintains some level of consistency as well as functionality with some
#of the other code i've written
class Meld(Tiles):
    
    def __init__(self, tiles, called = None, who = None, opened = False):
        Tiles.__init__(self)
        self.add_tiles(tiles)
        self.called = called
        self.who = who
        self.opened = opened
        self.shominkan = False
        self.shominkan_tile = None
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