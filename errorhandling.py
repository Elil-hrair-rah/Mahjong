class GameOver(Exception):
    
    def __init__(self, winner_result_dict, draw_discard):
        self.winner_result_dict = winner_result_dict
        self.draw_discard = draw_discard
        
class EndGame(Exception):
    def __init__(self):
        pass