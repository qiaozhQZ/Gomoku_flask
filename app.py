import sys
import pickle

from flask import Flask
from flask import render_template
from flask import redirect
from flask import request
from flask import send_from_directory

from models import db

sys.path.append('../AlphaZero_Gomoku')

from game import Board  # noqa: E402
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from policy_value_net_numpy import PolicyValueNetNumpy  # noqa: E402

# Setup the Flask app with the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

# Create the database if it does not exist.
with app.app_context():
    db.create_all()

# Setup the board and MCTS player
board = Board()
board.init_board(1)

n = 5
width, height = 8, 8
model_file = '../AlphaZero_Gomoku/best_policy_8_8_5.model'
try:
    policy_param = pickle.load(open(model_file, 'rb'))
except Exception:
    policy_param = pickle.load(open(model_file, 'rb'), encoding='bytes')
best_policy = PolicyValueNetNumpy(width, height, policy_param)
mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=5, n_playout=400)
mcts_player.set_player_ind(2)
mcts_human_hint = MCTSPlayer(best_policy.policy_value_fn, c_puct=5,
                             n_playout=400)
mcts_human_hint.set_player_ind(1)

print("I'm ready.")


@app.route("/about")
def about():
    """View function for About Page."""
    return render_template("about.html")


@app.route('/')
def get_board():
    score = request.args.get('score')
    width = board.width
    height = board.height

    # board_state
    state = []

    for i in range(height - 1, -1, -1):
        state.append([])
        for j in range(width):
            loc = i * width + j
            p = board.states.get(loc, -1)
            if p == 1:
                state[-1].append('X')
            elif p == 2:
                state[-1].append('O')
            else:
                state[-1].append('-')
    return render_template('home.html', state=state, size=len(state),
                           width=width, height=height, score=score)


@app.route('/move/<i>/<j>')
def move(i, j):
    global board
    _, move_probs = mcts_human_hint.get_action(board, return_prob=True)
    print(move_probs)

    move = (board.height - int(i) - 1) * board.width + int(j)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        board = Board()  # reset board
        board.init_board(1)
        mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)
    end, winner = board.game_end()
    if end:
        board = Board()  # reset board
        board.init_board(1)
        mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)


@app.route('/hint')
def hint():
    global board
    move, move_probs = mcts_human_hint.get_action(board, return_prob=True)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        board = Board()  # reset board
        board.init_board(1)
        mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)
    end, winner = board.game_end()
    if end:
        board = Board()  # reset board
        board.init_board(1)
        mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)


@app.route('/<path:path>')
def send_files(path):
    """Serve up the static files"""
    return send_from_directory('static', path)


if __name__ == "__main__":
    app.run()
