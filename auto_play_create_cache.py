from pprint import pprint
import os
import sys
import numpy as np

sys.path.append('../AlphaZero_Gomoku')

from game import Board, Game
from mcts_alphaZero import MCTSPlayer # noqa: E402
from policy_value_net_pytorch import PolicyValueNet


def create_cache(model_file_1, model_file_2, moves_cnt):
    board_width, board_height, n = 8, 8, 5
    board = Board(width=board_width, height=board_height, n_in_row=n)
    game = Game(board)


    best_policy_1 = PolicyValueNet(board_width, board_height, model_file=model_file_1, use_gpu=True)
    mcts_player_1 = MCTSPlayer(best_policy_1.policy_value_fn,
          alpha=0.15, epsilon=0.25, c_puct=3.0,
                             n_playout=400, is_selfplay=0) 
    
    best_policy_2 = PolicyValueNet(board_width, board_height, model_file=model_file_2, use_gpu=True)
    mcts_player_2 = MCTSPlayer(best_policy_2.policy_value_fn,
          alpha=0.15, epsilon=0.25, c_puct=3.0,
                             n_playout=400, is_selfplay=0)
    
    #TODO count the moves and start new games  repetitively
    try:
        i= 0
        while i < moves_cnt:
        #TODO output of start_play()
            game.start_play(mcts_player_1, mcts_player_2, start_player=1, is_shown=1)
            i += 1

    except KeyboardInterrupt:
        print('\n\rquit')

    # pprint(game)

def save_to_db():
    pass

if __name__ == "__main__":
    moves_cnt = 2
    model_file_1 = '../AlphaZero_Gomoku/Models/1375_current_policy.model'
    model_file_2 = '../AlphaZero_Gomoku/Models/1375_current_policy.model'
    create_cache(model_file_1, model_file_2, moves_cnt)