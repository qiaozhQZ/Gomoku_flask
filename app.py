import sys
import pickle
import uuid
import json
import datetime
import torch
import yaml
from yaml import Loader, Dumper
from random import random
from os.path import exists

from flask import Flask
from flask import render_template
from flask import redirect
from flask import session
from flask import send_from_directory
from flask import jsonify
from flask import request

from models import db
from models import Player
from models import Game
from models import Move
from models import Log

sys.path.append('../AlphaZero_Gomoku')

from game import Board  # noqa: E402
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from policy_value_net_numpy import PolicyValueNetNumpy  # noqa: E402
from policy_value_net_pytorch import PolicyValueNet 


# Setup the Flask app with the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)


# change the key to clear cookies
app.secret_key = b'azsrdf0zdaf09dasd902j323xjkh32jhkd0sdjlksdljn1n120919030923'


# Create the database if it does not exist.
with app.app_context():
    db.create_all()


# configuration file
if exists('config.yaml'):
    with open('config.yaml', 'r') as fin:
        # read the file into a file input
        data = yaml.load(fin, Loader=Loader)
        training_time = data['training_time']
        testing_games = data['testing_games']
        random_uuid = data['random_uuid']
else:
    # numbers for launching the experiment
    training_time = 900
    testing_games = 5
    random_uuid = True
    # write to the yaml file
    with open('config.yaml','w') as fout:
        # save the variables to the yaml file
        fout.write(yaml.dump({'training_time':training_time, 
        'testing_games':testing_games, 'random_uuid':random_uuid}, Dumper=Dumper))


def get_player():
    if ('player_id' not in session or
            Player.query.filter_by(id=session['player_id']).first() is None):
        if random_uuid:
            username = str(uuid.uuid1()) # generate a random id
        else:
            username = str(hash(request.remote_addr)) # use the hash of IP address
        
        if Player.query.filter_by(username=username).count() > 0:
            player = Player.query.filter_by(username=username).first() # get the player with a username if existed
        else:
            # query the numer of people in each condition
            num_imm = Player.query.filter_by(condition='immediate').count()
            num_ctr = Player.query.filter_by(condition='control').count()
            num_dly = Player.query.filter_by(condition='delayed').count() # add delayed condition

            condition = sorted([(num_imm, random(), 'immediate'), 
            (num_ctr, random(), 'control'), (num_ctr, random(), 'delayed')])[0][2] #assign into different conditions to balance
            condition = "delayed"
            player = Player(username=username, condition=condition)
            db.session.add(player)
            db.session.commit()
        session['player_id'] = player.id
    else:
        player = Player.query.filter_by(id=session['player_id']).first()
    return player


def redirect_player(player, cur_page):
    if player.stage != cur_page:
        # redirect user to the stage they should be on
        return redirect('/{}'.format(player.stage))
    
    # print(player.stage)
    # print(cur_page)


def get_game(player):
    if ('game_id' not in session or
            Game.query.filter_by(id=session['game_id'],
                                 player_won=None).first() is None):
        is_testing = player.stage == 'testing'
        game = Game(player=player, player_is_white=False, training_game=not is_testing)
        db.session.add(game)
        db.session.commit()
        session['game_id'] = game.id
    else:
        game = Game.query.filter_by(id=session['game_id'],
                                    player_won=None).first()
    return game


def get_board(game):
    board = Board()
    board.init_board(0)

    for move in game.moves:
        board.do_move(move.location)

    return board


def get_mcts_player(player_index=1):
    """
    Get an mcts player, an index of 1 corresponds to first player (typically
    human) and an index of 2 corresponds to the second player (typically AI
    opponent).
    """
    board = Board()
    board.init_board()

    size = 8
    # model_file = '../AlphaZero_Gomoku/PyTorch_models/best_policy_885_pt_50.model'
    # model_file = '../AlphaZero_Gomoku/Batch_5_models/5_current_policy.model'
    model_file = '../AlphaZero_Gomoku/PyTorch_models/best_policy_885_pt_10500.model'
    

    # for numpy
    # try:
    #     policy_param = pickle.load(open(model_file, 'rb'))
    # except Exception:
    #     policy_param = pickle.load(open(model_file, 'rb'), encoding='bytes')

    # best_policy = PolicyValueNetNumpy(size, size, policy_param)

    # use_gpu = torch.cuda.is_available()
    use_gpu = False
    # print('using GPU: ', use_gpu)

    best_policy = PolicyValueNet(size, size, model_file = model_file, use_gpu=use_gpu)
    mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=5,
                             n_playout=200) # modify n_playout to make easier models
    mcts_player.set_player_ind(player_index)

    return mcts_player


@app.route('/new_game', methods = ['POST'])
def new_game():
    session.pop('game_id', None)
    return json.dumps({}), 200, {'ContentType':'application/json'}


@app.route('/advance_stage', methods = ['POST']) #only accepting 'POST'
def advance_stage():
    '''automatically direct to the correct page'''
    # print('advance_stage')

    # print(request.get_json(force=True))
    # print(request.data)
    # print(request.data.decode('UTF-8'))
    # print(json.loads(request.data.decode('UTF-8'), strict=False))
    # print('beep')

    p = get_player()

    if p.stage == 'consent' and request.get_json().get('page') == 'consent':
        p.instructions_start = datetime.datetime.utcnow()
        p.stage = 'instructions'
    elif p.stage == 'instructions' and request.get_json().get('page')== 'instructions':
        p.training_start = datetime.datetime.utcnow()
        p.stage = 'training'
    elif p.stage == 'training' and request.get_json().get('page') == 'training':
        p.testing_start = datetime.datetime.utcnow()
        p.stage = 'testing'
        session.pop('game_id', None) #start a new game for testing
    elif p.stage == 'testing' and request.get_json().get('page') == 'testing':
        p.survey_start = datetime.datetime.utcnow()
        p.stage = 'survey'
    elif p.stage == 'survey' and request.get_json().get('page') == 'survey':
        p.experiment_end = datetime.datetime.utcnow()
        p.stage = 'done'

    # save to the database
    db.session.add(p)
    db.session.commit() 

    if p.stage == 'survey':
        # senf the participant id to Qualtrics
        return json.dumps({'next_page':'https://drexel.qualtrics.com/jfe/form/SV_ewWFeWkDV9uHMtE?participant_id={}'.format(p.id)}), 200, {'ContentType':'application/json'}

    return json.dumps({'next_page':'/{}'.format(p.stage)}), 200, {'ContentType':'application/json'}


@app.route('/training_time_left')
def training_time_left():
    p = get_player()
    delta = datetime.datetime.utcnow() - p.training_start #calculate the period of time
    ############# modify the number for testing #############
    seconds = max(0, training_time - delta.total_seconds()) #take the seconds left from 300 seconds
    return json.dumps({'seconds':seconds}), 200, {'ContentType':'application/json'} #return a dictionary


@app.route('/testing_games_left')
def testing_games_left():
    p = get_player()
    test_games = Game.query.filter_by(player_id=p.id, training_game=False)
    ############# modify the number for testing #############
    games = max(0, testing_games + 1 - test_games.count()) #calculate the number of games left
    return json.dumps({'games':games}), 200, {'ContentType':'application/json'} #return a dictionary


@app.route('/consent')
def consent():
    r = redirect_player(get_player(), 'consent')
    if r is not None:
        return r
    return render_template('consent.html')


@app.route('/instructions')
def tutorial():
    r = redirect_player(get_player(), 'instructions')
    if r is not None:
        return r
    return render_template('instructions.html')


@app.route('/training')
def training():
    player = get_player()
    r = redirect_player(player, 'training')
    if r is not None:
        return r
    game = get_game(player)
    moves = {move.location: "black" if
             (move.player_move and not game.player_is_white) or
             (not move.player_move and game.player_is_white)
             else "white" for move in game.moves}
    move_seq = [(move.location, move.score, move.hint_location, "black" if (move.player_move and not
                 game.player_is_white) or (not move.player_move and
                 game.player_is_white) else "white") for move in game.moves]

    score = None
    if len(game.moves) > 1:
        score = game.moves[-2].score

    if len(moves) % 2 == 0:
        color = 'black'
    else:
        color = 'white'

    page = str(player.condition) + '.html'
    print(moves)
    return render_template(page, moves=moves, move_seq=move_seq, color=color,
                           size=game.size, score=score)


@app.route('/testing')
def testing():
    player = get_player()
    r = redirect_player(player, 'testing')
    if r is not None:
        return r
    game = get_game(player)
    moves = {move.location: "black" if
             (move.player_move and not game.player_is_white) or
             (not move.player_move and game.player_is_white)
             else "white" for move in game.moves}

    score = None
    if len(game.moves) > 1:
        score = game.moves[-2].score

    if len(moves) % 2 == 0:
        color = 'black'
    else:
        color = 'white'

    page = 'testing.html'
    return render_template(page, moves=moves, color=color,
                           size=game.size, score=score)


@app.route('/survey')
def survey():
    r = redirect_player(get_player(), 'survey')
    if r is not None:
        return r
    return render_template('survey.html')


@app.route('/goodbye')
def goodbye():
    return render_template('goodbye.html')


# @app.route('/done')
# def done():
#     return render_template('done.html')


######## time the function and log into a file ######
def move_player_and_opponent(i, j): 
    player = get_player()
    game = get_game(player)

    board = get_board(game)
    mcts_player = get_mcts_player(2)
    mcts_human_hint = get_mcts_player(1)

    hint, move_probs = mcts_human_hint.get_action(board, return_prob=True)

    # print(move_probs)

    move = int(i) * board.height + int(j)
    score = move_probs[move]
    score = round(score / move_probs.max())# normalize

    board.do_move(move)

    player_move = Move(game=game, player_move=True, location=move, score=score,
                       hint_location=hint.item(), raw_move_scores=str(move_probs),
                       is_hint=False)
    db.session.add(player_move)
    db.session.commit()

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        game.player_won = winner == 1
        db.session.add(game)
        db.session.commit()
        session.pop('game_id', None)
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)

    opponent_move = Move(game=game, player_move=False, location=int(move))
    db.session.add(opponent_move)
    db.session.commit()

    end, winner = board.game_end()
    if end:
        game.player_won = winner == 1
        db.session.add(game)
        db.session.commit()
        session.pop('game_id', None)


def add_move(i, j):
    player = get_player()
    game = get_game(player)

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)

    if human:
        mcts_player = get_mcts_player(1)
    else:
        mcts_player = get_mcts_player(2)

    hint, move_probs = mcts_player.get_action(board, return_prob=True)
    # print("hint_location", hint)
    # print("hint_type", type(hint))
    # print("hint_item_type", type(hint.item()))

    # print(move_probs)

    move = int(i) * board.height + int(j)
    score = move_probs[move]
    score = round(score / move_probs.max()) # normalize

    board.do_move(move)

    player_move = Move(game=game, player_move=human, location=move,
                       score=score, hint_location=hint.item(),
                       raw_move_scores=str(move_probs), is_hint=False)

    db.session.add(player_move)
    db.session.commit()

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        game.player_won = winner == 1
        db.session.add(game)
        db.session.commit()
        session.pop('game_id', None)
        # return redirect("/", code=302)

    if player_move.player_move and game.player_is_white:
        color = 'white'
    elif not player_move.player_move and not game.player_is_white:
        color = 'white'
    else:
        color = 'black'

    return {'end': end, 'winner': winner, 'score': score, 'color': color,
            'move': move, 'hint': hint.item()}

@app.route('/log/', methods=['POST'])
def log():
    event = request.get_json()['event']
    player = get_player()
    game = get_game(player)
    logged_event = Log(game_id=game.id, event=event)
    db.session.add(logged_event)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/move/<i>/<j>', methods=['GET', 'POST'])
def make_move(i, j):
    if request.method == 'POST':
        return jsonify(add_move(i, j))
    else:
        move_player_and_opponent(i, j)
        return redirect("/", code=302)


@app.route('/optimal_move', methods=['POST'])
def optimal_move():
    player = get_player()
    game = get_game(player)

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)

    if human:
        mcts_player = get_mcts_player(1)
    else:
        mcts_player = get_mcts_player(2)

    optimal_move, move_probs = mcts_player.get_action(board, return_prob=True)

    score = move_probs[optimal_move]
    score = round(score / move_probs.max()) # normalize

    if human and game.player_is_white:
        color = 'white'
    elif not human and not game.player_is_white:
        color = 'white'
    else:
        color = 'black'

    i = int(optimal_move) // board.height
    j = int(optimal_move) % board.height

    return jsonify({'color': color, 'location': int(optimal_move), 'score':
                    score, 'i': i, 'j': j})


@app.route('/hint')
def hint():
    player = get_player()
    game = get_game(player)

    board = get_board(game)
    mcts_player = get_mcts_player(2)
    mcts_human_hint = get_mcts_player(1)

    move, move_probs = mcts_human_hint.get_action(board, return_prob=True)

    score = move_probs[move]
    score = round(score / move_probs.max()) # normalize

    board.do_move(move)

    player_move = Move(game=game, player_move=True, location=int(move),
                       score=score, hint_location=move,
                       raw_move_scores=str(move_probs), is_hint=True)
    db.session.add(player_move)
    db.session.commit()

    # check if the game has ended
    end, winner = board.game_end()
    if end:
        session.pop('game_id', None)
        return redirect("/", code=302)

    move = mcts_player.get_action(board)
    board.do_move(move)

    opponent_move = Move(game=game, player_move=False, location=int(move))
    db.session.add(opponent_move)
    db.session.commit()

    end, winner = board.game_end()
    if end:
        session.pop('game_id', None)
        return redirect("/", code=302)

    return redirect("/", code=302)


@app.route('/<path:path>')
def send_files(path):
    """Serve up the static files"""
    return send_from_directory('static', path)


if __name__ == "__main__":
    app.run()
