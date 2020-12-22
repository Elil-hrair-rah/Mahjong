import io
import re
from functools import reduce

import random
from PIL import Image

from tiles import Tile, Tiles

''' testing code, probably doesnt work properly given some of the adjustments i've made so far

alsonotbob = Player('anb',3, 1)
bob = Player('bob', 1, 2)
notbob = Player('notbob',2, 3)
bob.hand.add_tiles('11p23s5505m666p777s123z')
tile1 = Tile('1','p')
tile2 = Tile('1','s')
tile3 = Tile('6','p')
tile4 = Tile('7','s')
bob.seat = SOUTH
game = Game([notbob, alsonotbob, alsonotbob, alsonotbob], 1)
await bob.pon(tile1, game)
await bob.chii(tile2, game)
bob.seat = NORTH
await bob.ckan()
bob.okan(tile3, game)
bob.seat = WEST
await bob.pon(tile4, game)
await bob.ckan()

'''

#ok so if you're working with this and wondering why images dont work properly
#keep in mind that the images are streams and so every time you generate an image
#using a stream the image gets "used up" and the pointer ends up at the end of the
#byte string that represents the image (or something like that, i dont really know what im talking about)
#basically if you're using this and the image isnt showing up properly just apply the function
#image.seek(0) and the image should display/send/etc properly again
#this only matters if you try to use the same image multiple times in the same function
#or are using an image in a function then passing it through to another one

#heavily edited version of the image generation from the majsoul generator app
#https://github.com/watterle/majsoul-generator
#generates an image of a player's hand with melds and rotated tiles in appropriate locations
#can display opponents' hands with melds visible, as well as distinguishes between tedashi and tsumogiri
#if the hand doesn't have any melds, it just redirects to the makeImage function

#there's a weird bug here with a part (the rotated part?) of a particular meld
#disappearing from the image sometimes, but only a display issue, not sure where
#it is or how to fix it atm

def player_image(player, hidden, tsumogiri, *args):
#    if not isinstance(player, Player):
#        return False
    
    #if there are melds, do some specific stuff to display the meld accordingly
    #this includes rotating the tile and placing the rotated tile based on who
    #the tile was called from
    
    if player.melds.melds:
        image_list = []
        
        #if the hand is another players', hide the hand by displaying a tileback image
        #distinguish a tsumogiri discard from a tedashi discard by creating a
        #randomly placed break in the undisplayed hand
        #to do this, split up the hand into two chunks, each of which is a series of
        #tileback images
        
        if hidden:
            if tsumogiri:
                parts = ['x' * len(player.hand) + 'z']
            else:
                location = random.randint(1,len(player.hand))
                parts = ['x' * location + 'z']
                parts.append('x' * (len(player.hand) - location) + 'z')
        else:
            parts = [str(player.hand)]
            
        #this creates an array that corresponds with the individual tiles
        #and determines whether or not to display the tile rotated
        #0 indicates upright, while 1 indicates rotated
        #2 is used to indicate an added kan, which is rotated but placed above
        #a previously rotated tile
        #if there is a 2 without a corresponding 1 in this array, it'll probably
        #bug out and have the tiles clip into one another
            
        rotated = []
        
        #the tiles in hand are obviously not rotated
        
        rotated.append([0 for tile in player.hand.tiles])
        
        #and neither are the arguments (which are basically just the discard,
        #but this is flexible enough to allow for other displays)
        
        for arg in args:
            if isinstance(arg, Tiles):
                rotated.append([0 for tile in arg.tiles])
                parts.append(str(arg))
            elif isinstance(arg, Tile):
                rotated.append([0])
                parts.append(str(arg))
            else:
                parts.append(arg)
                tiles = Tiles()
                tiles.add_tiles(arg)
                rotated.append([0 for tile in tiles.tiles])
                
        #figure out who the tile was called from, for all open melds
                
        for meld in player.melds.melds:
            rotation = {'L': [1, 0, 0], 'M': [0, 1, 0], 'R': [0, 0, 1]}
            if meld.who:
                
                rotate = rotation[meld.who][:]
                if meld.shominkan:
                    rotate[rotate.index(1):rotate.index(1)+1] = [1,2]
                elif len(meld) == 4:
                    rotate.insert(2, 0)
                    
                tiles = sorted(meld.tiles, key=lambda tile:tile.true_value)
                remove = [index for index, tile in enumerate(tiles) if tile.suit == meld.called.suit and tile.value == meld.called.value]
                del tiles[remove[0]]                
                string = ''
                zero_counter = 0
                
                for ref in rotate:
                    if ref == 0:
                        string += tiles[zero_counter].value
                        zero_counter += 1
                    elif ref == 1:
                        string += meld.called.value
                    elif ref == 2:
                        string += meld.shominkan_tile.value
                string += meld.called.suit
                    
            #if its a closed kan, then display the tiles without rotation
            #but with flipping
            #the logic exists to display the red 5 in the kan at all times if applicable
            #but realistically this doesn't need to be present
                
            else:
                rotate = [0 for tile in meld.tiles]
                string = str(meld)
                if string[0] == string[3]:
                    string = 'x'.join(string.rsplit(meld.tiles[0].value, 1))
                    string = string.replace(meld.tiles[0].value, 'x', 1)
                elif string[0] == string[1]:
                    string = 'x'.join(string.rsplit(meld.tiles[0].value, 2))
                else:
                    string = string.replace(meld.tiles[-1].value, 'x', 2)
                    
            rotated.append(rotate)
            parts.append(string)
        
        #converts the tile string (11123456789999m) into a list of image links
        #to be pasted together into one long image
        #any breaks (tedashi discarding hands, the discard, and meld blocks)
        #are separated by a short upright transparent rectangle image
        
        image_list = []
        for part in parts:
            results = re.findall(r'([0-9x]+[mpsz])', part)
            if part == parts[0]:
                results = list(
                    reduce(list.__add__,
                           [['{}{}'.format(x, result[-1]) for x in result[:-1]]
                            for result in results]))
            for result in results:
                image_list += [
                    './ui/{}{}.png'.format(x, result[-1]) for x in result[:-1]
                ]
            image_list.append('./ui/0.png')
        
        refs = []
        for block in rotated:
            refs.extend(block)
            refs.append(0)
        del refs[-1]
        
        imagefile = [Image.open(x) for x in image_list]
        
        dim_x = imagefile[0].size[0]
        dim_y = imagefile[0].size[1]
        
        image_length = refs.count(0) * dim_x + refs.count(1) * dim_y
        if refs.count(2): image_height = 2 * dim_x
        else: image_height = dim_y
        
        #create a new image, based on how many images need to be displayed
        #the image generated will always be longer than the space required, due
        #to the transparent separator image being thinner than a normal tile
        #but this issue doesn't seem like a big deal
        
        target = Image.new('RGBA', (image_length, image_height))
        left = 0
        for image, ref in zip(imagefile, refs):
            
            bottom = 0 + image_height - dim_y
            
            if ref:
                image = image.rotate(90, expand = True)
                bottom += dim_y - dim_x
            if ref == 2:
                bottom -= dim_x
                left -= dim_y
                
            target.paste(image, (left, bottom))
            
            left += image.size[0]
            
#        target.save('{}-{}.png'.format(player.disc, player.disc_id), quality=100)
        
        image = io.BytesIO()
        target.save(image, format = 'PNG')
        image.seek(0)
        return image
        
    else:
        tiles = str(player.hand)
        if args:
            args = [str(arg) for arg in args]
            return makeImage(tiles, hidden, tsumogiri, args)
        return makeImage(tiles, hidden, tsumogiri)
        
#the image generation function from the majsoul image generator found at 
#https://github.com/watterle/majsoul-generator
#with some added functionality to be able to display an opponent's hand and discards
#closed, along with the ability to specify whether or not a discard was tedashi or tsumogiri
def makeImage(text, hidden = False, tsumogiri = False, *args):
    if not text:
        raise Exception('Text to generate image not found')
    image_list = []
    if hidden:
        length = len(re.findall(r'([0-9x])', text))
        if tsumogiri:
            parts = ['x' * (length) + 'z']
        else:
            location = random.randint(1,length)
            parts = ['x' * location + 'z']
            parts.append('x' * (length - location) + 'z')
    else:
        parts = text.split(' ')
    if args:
        parts.extend(args[0])
    for part in parts:
        results = re.findall(r'([0-9x]+[mpsz])', part)
        if part == parts[0]:
            results = list(
                reduce(list.__add__,
                       [['{}{}'.format(x, result[-1]) for x in result[:-1]]
                        for result in results]))
#            results = sorted(sorted(results), key=lambda x: x[-1])
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
        
#    target.save('{}.png'.format(text.replace(' ', '_')), quality=100)

    image = io.BytesIO()
    target.save(image, format = 'PNG')
    image.seek(0)
    return image

#largely untouched from the majsoul generator app
#https://github.com/watterle/majsoul-generator
#generates dora images
#unused for now
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
    #target.save('{}.png'.format(text if text else 'Yama'), quality=100)

    image = io.BytesIO()
    target.save(image, format = 'PNG')
    image.seek(0)
    return image