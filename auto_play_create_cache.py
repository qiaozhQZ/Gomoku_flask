from pprint import pprint
from flask import Flask
import os
import sys
import json
import numpy as np
from tqdm import tqdm

sys.path.append('../AlphaZero_Gomoku')

from game import Board, Game
from mcts_alphaZero import MCTSPlayer # noqa: E402
from mcts_alphaZero import softmax  # noqa: E402
from policy_value_net_pytorch import PolicyValueNet

from models import db
from models import MctsCache

# Setup the Flask app with the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

# Create the database if it does not exist.
with app.app_context():
    db.create_all()

# difficulty

def get_mcts_player(model_file, player_index=1, n_playout=400):
    board_width, board_height, n = 8, 8, 5
    board = Board(width=board_width, height=board_height, n_in_row=n)
    board.init_board()
    # make a random move on the board
    # game = Game(board)

    policy = PolicyValueNet(board_width, board_height, model_file=model_file, use_gpu=False)
    mcts_player = MCTSPlayer(policy.policy_value_fn,
          alpha=0.15, epsilon=0.25, c_puct=3.0,
                             n_playout=n_playout, is_selfplay=0)
    mcts_player.set_player_ind(player_index)
    
    return mcts_player

def get_probs_given_visits(visits, temp):
    return softmax(1.0/temp * np.log(np.array(visits) + 1e-10))

def compute_mcts_move(human, board, temp=1, n_playout=400):
    c = MctsCache.query.filter_by(human=human, board=json.dumps(board.states, sort_keys=True)).first()
    if c is not None and c.n_playout < n_playout:
        db.session.delete(c)
        db.session.commit()
        c = None
        
    if c is None:
        mcts_player = get_mcts_player('../AlphaZero_Gomoku/Models/1375_current_policy.model', 1, n_playout=n_playout)
        acts, visits = mcts_player.get_visits(board)
        #print("acts", acts)
        #print("visits", visits)

        c = MctsCache(human=human, board=json.dumps(board.states, sort_keys=True), n_playout=n_playout, acts=json.dumps(acts), visits=json.dumps(visits))
        # save last_move, cur_player
        db.session.add(c)
        db.session.commit()
    
    acts = json.loads(c.acts)
    visits = json.loads(c.visits)
    probs = get_probs_given_visits(np.array(visits), temp=temp)
    move = np.random.choice(acts, p=probs)
    move_probs = np.zeros(8*8)
    move_probs[list(acts)] = probs

    return int(move), move_probs

def play_game(num_game, moves_cnt, n_playout=400):
    board_width, board_height, n = 8, 8, 5
    board = Board(width=board_width, height=board_height, n_in_row=n)
    #game = Game(board)
    #mcts_human = get_mcts_player(model_file_1, 1, difficulty=4)
    #mcts_ai = get_mcts_player(model_file_2, 2, difficulty=4)

# play n games
# make i moves in each game
   
    for i in tqdm(range(num_game)):
        board.init_board()
        for _ in range(moves_cnt):
            #game.start_play(mcts_human, mcts_ai, start_player=1, is_shown=0, cnt_move=moves_cnt)
            human_move, _ = compute_mcts_move(True, board, temp=1, n_playout=n_playout)
            board.do_move(human_move)
            if board.game_end()[0]:
                break
            agent_move, _ = compute_mcts_move(False, board, temp=1, n_playout=n_playout)
            board.do_move(agent_move)
            if board.game_end()[0]:
                break


def load_cache():
    # load json, pass in the board states, compute acts and visits
    pass

def save_to_db():
    pass

if __name__ == "__main__":
    with app.app_context():
        play_game(10, 5, n_playout=500)
    # create_cache(model_file_1, model_file_2, 5)