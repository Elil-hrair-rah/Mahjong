from mahjong.hand_calculating.hand import HandCalculator
from mahjong.tile import TilesConverter
from mahjong.hand_calculating.hand_config import HandConfig
from mahjong.shanten import Shanten


from tiles import Tiles, OneOfEach

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

#computes a rough estimate of the value of a given hand
#ignores conditional yaku such as riichi, ippatsu, haitei, etc
#for a simplified calculation of how much the hand is worth
#see the mahjong library for details regarding the returned object
def hand_calculator(tiles, win_tile, config = HandConfig()):
    calculator = HandCalculator()
    tiles = TilesConverter.one_line_string_to_136_array(str(tiles))
    win_tile = TilesConverter.one_line_string_to_136_array(str(win_tile))[0]
    return calculator.estimate_hand_value(tiles, win_tile, config = config)

#computes the shanten of a given (14 - 3n) tile hand
#returns -2 if you give it an invalid hand, i think
#-1 is a winning hand, 0 is tenpai, 1 is iishanten, etc
def shanten_calculator(tiles):
    shanten = Shanten()
    tiles = TilesConverter.one_line_string_to_34_array(str(tiles))
    result = shanten.calculate_shanten(tiles)
    return result