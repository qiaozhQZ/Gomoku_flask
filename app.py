import sys
sys.path.append('E:\GitHub\AlphaZero_Gomoku')
from flask import Flask, render_template, redirect, request, send_from_directory
from game import Board, Game
from mcts_alphaZero import MCTSPlayer
from policy_value_net_numpy import PolicyValueNetNumpy
import pickle

app = Flask(__name__)
board = Board()
board.init_board(1)

@app.route("/about")
def about():
    """View function for About Page."""
    return render_template("about.html")

# @app.route('/')
# def start_game():
#     """start a new game at any time"""

# @app.route('/')
# def end_game():
#     """end the current game at any time"""


# MCTS player
n = 5
width, height = 8, 8
model_file = 'E:/GitHub/AlphaZero_Gomoku/best_policy_8_8_5.model'
try:
    policy_param = pickle.load(open(model_file, 'rb'))
except:
    policy_param = pickle.load(open(model_file, 'rb'),
                                encoding='bytes')  # To support python3
best_policy = PolicyValueNetNumpy(width, height, policy_param)
mcts_player = MCTSPlayer(best_policy.policy_value_fn,
                            c_puct=5,
                            n_playout=400)
mcts_player.set_player_ind(2)
mcts_human_hint = MCTSPlayer(best_policy.policy_value_fn,
                            c_puct=5,
                            n_playout=400)
mcts_human_hint.set_player_ind(1)

print("I'm ready.")

@app.route('/')
def get_board():
    score = request.args.get('score')
    print("SCORE", score)
    width = board.width
    height = board.height

    return_value = ''

    # for x in range(width):
    #     return_value += "{0:8}".format(x)
    # return_value += '\r\n'
    state = [] # board_state

    for i in range(height - 1, -1, -1):
        state.append([])
        # return_value += "{0:4d}".format(i)
        for j in range(width):
            loc = i * width + j
            p = board.states.get(loc, -1)
            if p == 1:
                # return_value +='X'.center(8)
                state[-1].append('X')
            elif p == 2:
                # return_value += 'O'.center(8)
                state[-1].append('O')
            else:
                # return_value += '_'.center(8)
                state[-1].append('-')
        # return_value += '\r\n\r\n'
    return render_template('home.html', state = state, size = len(state), width = width, height = height, score = score)

@app.route('/move/<i>/<j>')
def move(i, j):
    global board
    _, move_probs = mcts_human_hint.get_action(board, return_prob = True)
    print(move_probs)

    move = (board.height - int(i) - 1) * board.width + int(j)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        board = Board() # reset board
        board.init_board(1)
        mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)
    end, winner = board.game_end()
    if end:
        board = Board() # reset board
        board.init_board(1)
        mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)

@app.route('/hint')
def hint():
    global board
    move, move_probs = mcts_human_hint.get_action(board, return_prob = True)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        board = Board() # reset board
        board.init_board(1)
        mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)
    end, winner = board.game_end()
    if end:
        board = Board() # reset board
        board.init_board(1)
        mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)

@app.route('/<path:path>')
def send_files(path):
    """link to the css file"""
    return send_from_directory('static', path)

if __name__ == "__main__":
    app.run()