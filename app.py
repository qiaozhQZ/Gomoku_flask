import sys
import pickle
import uuid

from flask import Flask
from flask import render_template
from flask import redirect
from flask import request
from flask import session
from flask import send_from_directory

from models import db
from models import Player
from models import Game
from models import Move

sys.path.append('../AlphaZero_Gomoku')

from game import Board  # noqa: E402
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from policy_value_net_numpy import PolicyValueNetNumpy  # noqa: E402

# Setup the Flask app with the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)
app.secret_key = b'asrdf0daf09dasd902j323jkh32jhkd0sdjlksdljn1n120919030923' # change the key to clear cookies


# Create the database if it does not exist.
with app.app_context():
    db.create_all()


def build_board_and_players():
    # Setup the board and MCTS player
    board = Board()
    board.init_board(1)

    width, height = 8, 8
    model_file = '../AlphaZero_Gomoku/best_policy_8_8_5.model'

    try:
        policy_param = pickle.load(open(model_file, 'rb'))
    except Exception:
        policy_param = pickle.load(open(model_file, 'rb'), encoding='bytes')
    best_policy = PolicyValueNetNumpy(width, height, policy_param)
    mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=5,
                             n_playout=400)
    mcts_player.set_player_ind(2)
    mcts_human_hint = MCTSPlayer(best_policy.policy_value_fn, c_puct=5,
                                 n_playout=400)
    mcts_human_hint.set_player_ind(1)
    return board, mcts_player, mcts_human_hint


games = {}
# board, mcts_player, mcts_human_hint = build_board_and_players()


@app.route("/about")
def about():
    """View function for About Page."""
    return render_template("about.html")


def get_player_game():
    if 'player_id' not in session or Player.query.filter_by(id=session['player_id']).first() is None:
        username = str(uuid.uuid1())
        # username = str(hash(request.remote_addr))
        player = Player(username=username)
        db.session.add(player)
        db.session.commit()
        session['player_id'] = player.id
    else:
        player = Player.query.filter_by(id=session['player_id']).first()
        print('PLAYER', player)

    global games
    if 'game_id' not in session or session['game_id'] not in games:
        game = Game(player=player, player_is_white=True, training_game=True)
        db.session.add(game)
        db.session.commit()
        session['game_id'] = game.id
    else:
        game = Game.query.filter_by(id=session['game_id']).first()

    return player, game


@app.route('/')
def get_board():
    global games

    print(session)
    print(games)

    player, game = get_player_game()

    print(game.moves)

    if game.id not in games:
        games[game.id] = build_board_and_players()

    score = request.args.get('score')
    width = games[game.id][0].width
    height = games[game.id][0].height

    # board_state
    state = []

    for i in range(height - 1, -1, -1):
        state.append([])
        for j in range(width):
            loc = i * width + j
            p = games[game.id][0].states.get(loc, -1)
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
    global games

    print(session)
    print(games)
    player, game = get_player_game()

    if game.id not in games:
        games[game.id] = build_board_and_players()
    board, mcts_player, mcts_human_hint = games[game.id]

    hint, move_probs = mcts_human_hint.get_action(board, return_prob=True)

    # print(move_probs)

    move = (board.height - int(i) - 1) * board.width + int(j)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    player_move = Move(game=game, player_move=True, location=move, score=score,
                       hint_location=hint, raw_move_scores=str(move_probs),
                       is_hint=False)
    db.session.add(player_move)
    db.session.commit()

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        print(winner)
        game.player_won = winner
        db.session.add(game)
        db.session.commit()

        del games[game.id]
        session.pop('game_id', None)
        # board = Board()  # reset board
        # board.init_board(1)
        # mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)

    opponent_move = Move(game=game, player_move=False, location=move)
    db.session.add(opponent_move)
    db.session.commit()

    end, winner = board.game_end()
    if end:
        print(winner)
        game.player_won = winner
        db.session.add(game)
        db.session.commit()

        del games[game.id]
        session.pop('game_id', None)
        # board = Board()  # reset board
        # board.init_board(1)
        # mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)


@app.route('/hint')
def hint():
    player, game = get_player_game()

    global games
    if game.id not in games:
        games[game.id] = build_board_and_players()
    board, mcts_player, mcts_human_hint = games[game.id]

    move, move_probs = mcts_human_hint.get_action(board, return_prob=True)
    score = move_probs[move]
    print(board.availables)
    print(move)
    board.do_move(move)

    player_move = Move(game=game, player_move=True, location=move, score=score,
                       hint_location=move, raw_move_scores=str(move_probs),
                       is_hint=True)
    db.session.add(player_move)
    db.session.commit()

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        del games[game.id]
        session.pop('game_id', None)
        # board = Board()  # reset board
        # board.init_board(1)
        # mcts_player.reset_player()
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)

    opponent_move = Move(game=game, player_move=False, location=move)
    db.session.add(opponent_move)
    db.session.commit()

    end, winner = board.game_end()
    if end:
        del games[game.id]
        session.pop('game_id', None)
        # board = Board()  # reset board
        # board.init_board(1)
        # mcts_player.reset_player()
    return redirect("/?score={}".format(score), code=302)


@app.route('/<path:path>')
def send_files(path):
    """Serve up the static files"""
    return send_from_directory('static', path)


if __name__ == "__main__":
    app.run()
