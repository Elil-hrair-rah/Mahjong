from mahjong.hand_calculating.hand import HandCalculator
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.shanten import Shanten


from tiles import Tiles, OneOfEach, Wall

#computes what tiles would complete a given (13 - 3n)-tile hand.
#returns nothing (empty list) if hand is not in tenpai
#converts tile objects or lists of tiles to the appropriate tenhou/majsoul notation
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

#computes what tiles would improve a given (13 - 3n)-tile hand.
#probably bugs out if you give it the wrong number of tiles 
#converts tile objects or lists of tiles to the appropriate tenhou/majsoul notation
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
    
#brute force search for number of tiles that improve shanten count based on the
#tiles in the pool given, or the entire wall if no pool provided
def efficient_discard(tiles, pool = None):
    base_shanten = shanten_calculator(tiles)
    improvements = {}
    if pool is None:
        pool = Wall()
        pool.remove_tiles(tiles)
    for tile in tiles.tiles:
        count = 0
        temp = Tiles()
        temp.tiles = tiles.tiles[:]
        temp.remove_tiles(tile)
        for sample in pool.tiles:
            temp.add_tiles(sample)
            shanten = shanten_calculator(temp)
            if shanten < base_shanten:
                count += 1
            temp.remove_tiles(sample)
        if count > 0:
            improvements[str(tile)] = count
    return improvements
        
'''
def sidegrade(tiles, pool = None):
    number_of_upgrades = {}
    if pool is None:
        pool = Wall()
        pool.remove_tiles(tiles)
    for tile in tiles.tiles:
        temp = Tiles()
        temp.tiles = tiles.tiles[:]
        temp.remove_tiles(tile)
        for sample in pool.tiles:
            temp.add_tiles(sample)
            if pool is None:
                efficiency = efficient_discard(temp)
            else:
                efficiency = efficient_discard(temp,pool)
            temp.remove_tiles(sample)
        number_of_upgrades[str(tile)] = len(efficiency)
        print(tile, efficiency)
    return number_of_upgrades
'''       

def efficiency_discard(tiles, pool = None):
    if isinstance(tiles,str):
        tiles = tiles.replace(' ','')
        temp = Tiles()
        temp.add_tiles(tiles)
        return winning_tiles(temp)
    elif issubclass(type(tiles),Tiles):
        if pool is None:
            discards = efficient_discard(tiles)
        else:
            discards = efficient_discard(tiles, pool)
        most_efficient = [tile for tile in discards.keys() if discards[tile] == max(discards.values())]
        #return the entire list, and a choice can be made later
        return most_efficient
    elif isinstance(tiles,list):
        temp = Tiles()
        temp.add_tiles(tiles)
        return winning_tiles(str(temp))
    

#computes a rough estimate of the value of a given hand
#ignores conditional yaku such as riichi, ippatsu, haitei, etc
#for a simplified calculation of how much the hand is worth
#see the mahjong library for details regarding the returned object
def hand_calculator(tiles, win_tile, config = HandConfig()):
    calculator = HandCalculator()
    tiles = TilesConverter.one_line_string_to_136_array(str(tiles), has_aka_dora = True)
    win_tile = TilesConverter.one_line_string_to_136_array(str(win_tile), has_aka_dora = True)[0]
    return calculator.estimate_hand_value(tiles, win_tile, config = config)

#computes the shanten of a given (14 - 3n) tile hand
#returns -2 if you give it an invalid hand, i think
#-1 is a winning hand, 0 is tenpai, 1 is iishanten, etc
def shanten_calculator(tiles):
    shanten = Shanten()
    tiles = TilesConverter.one_line_string_to_34_array(str(tiles), has_aka_dora = True)
    result = shanten.calculate_shanten(tiles)
    return result