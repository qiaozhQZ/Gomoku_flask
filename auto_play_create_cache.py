from pprint import pprint
import os
import sys
import json
import numpy as np

sys.path.append('../AlphaZero_Gomoku')

from game import Board, Game
from mcts_alphaZero import MCTSPlayer # noqa: E402
from mcts_alphaZero import softmax  # noqa: E402
from policy_value_net_pytorch import PolicyValueNet

from models import db
from models import MctsCache

# difficulty

def get_mcts_player(model_file, player_index=1, difficulty=4):
    board_width, board_height, n = 8, 8, 5
    board = Board(width=board_width, height=board_height, n_in_row=n)
    board.init_board()
    # make a random move on the board
    # game = Game(board)

    policy = PolicyValueNet(board_width, board_height, model_file=model_file, use_gpu=False)
    mcts_player = MCTSPlayer(policy.policy_value_fn,
          alpha=0.15, epsilon=0.25, c_puct=3.0,
                             n_playout=400, is_selfplay=0)
    mcts_player.set_player_ind(player_index)
    
    return mcts_player

def get_probs_given_visits(visits, temp):
    return softmax(1.0/temp * np.log(np.array(visits) + 1e-10))

def compute_mcts_move(human, board, temp=1, difficulty=4):
    c = MctsCache.query.filter_by(human=human, board=json.dumps(board.states, sort_keys=True), difficulty=difficulty).first()
    if c is None:
        # print('computing MCTS move')
        if human:
            mcts_player = get_mcts_player(model_file_1, 1, difficulty=difficulty)
        else:
            mcts_player = get_mcts_player(model_file_2, 2, difficulty=difficulty)
        acts, visits = mcts_player.get_visits(board)

        c = MctsCache(human=human, board=json.dumps(board.states, sort_keys=True), difficulty=difficulty, acts=json.dumps(acts), visits=json.dumps(visits))
        db.session.add(c)
        db.session.commit()
    
    acts = json.loads(c.acts)
    visits = json.loads(c.visits)
    probs = get_probs_given_visits(np.array(visits), temp=temp)
    move = np.random.choice(acts, p=probs)
    move_probs = np.zeros(8*8)
    move_probs[list(acts)] = probs

    return int(move), move_probs

# play n games
# make i moves in each game

    # num_game = 2
   
    # for i in range(num_game):
    #     print("game", i)
    #     game.start_play(mcts_human_1, mcts_AI_2, start_player=1, is_shown=0, cnt_move=moves_cnt)
    #     print(board.states)

    
        
def save_to_db():
    pass

if __name__ == "__main__":
    model_file_1 = '../AlphaZero_Gomoku/Models/1375_current_policy.model'
    model_file_2 = '../AlphaZero_Gomoku/Models/1375_current_policy.model'


    # create_cache(model_file_1, model_file_2, 5)