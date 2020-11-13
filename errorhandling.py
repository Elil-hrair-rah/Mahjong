# -*- coding: utf-8 -*-
"""
Created on Thu Nov 12 13:58:54 2020

@author: bobtehnoob
"""

class GameOver(Exception):
    
    def __init__(self, winner_result_dict, draw_discard):
        self.winner_result_dict = winner_result_dict
        self.draw_discard = draw_discard