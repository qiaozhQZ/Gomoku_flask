import sys
import pickle
import uuid
import json
import datetime
import torch
import yaml
import os
from sympy.integrals.risch import NonElementaryIntegral
from yaml import Loader, Dumper
from random import random
from random import choice
from random import shuffle
from os.path import exists
from functools import cache

import numpy as np
from flask import Flask
from flask import render_template
from flask import redirect
from flask import session
from flask import send_from_directory
from flask import jsonify
from flask import request
import numpy as np

from models import db
from models import Player
from models import Game
from models import Move
from models import Log
from models import MctsCache
from models import TestItem

from google import genai
from google.genai import types

sys.path.append('../AlphaZero_Gomoku')

from game import Board  # noqa: E402
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from mcts_alphaZero import softmax  # noqa: E402
# from policy_value_net_numpy import PolicyValueNetNumpy  # noqa: E402
from policy_value_net_pytorch import PolicyValueNet 

print("Checking GEMINI_API_KEY environment variable...")
api_key = os.getenv('GEMINI_API_KEY')
print(f"   API key value: {api_key[:10] if api_key else 'None'}...")

if not api_key:
    print("✗ GEMINI_API_KEY environment variable is not set")
    GEMINI_AVAILABLE = False
    print("Warning: GEMINI_API_KEY not set. LLM features will be disabled.")
else:
    print("✓ API key found - LLM features will be available")
    GEMINI_AVAILABLE = True

print(f"Final GEMINI_AVAILABLE status: {GEMINI_AVAILABLE}")

# Setup the Flask app with the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db.init_app(app)

# Add ord and chr functions to Jinja2 environment for coordinate labels
app.jinja_env.globals.update(ord=ord, chr=chr)


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
        test_item_time = data['test_item_time']
        reward_for_correct = data['reward_for_correct']
        ai_move_temp = data['ai_move_temp']
        move_eval_temp = data['move_eval_temp']
        n_playout = data['n_playout']
        random_uuid = data['random_uuid']
else:
    # numbers for launching the experiment
    training_time = 2100
    test_item_time = 60
    reward_for_correct = 0.1
    ai_move_temp = 1.0
    n_playout = 400
    move_eval_temp = 1.0
    random_uuid = True
    # write to the yaml file
    with open('config.yaml','w') as fout:
        # save the variables to the yaml file
        fout.write(yaml.dump({'training_time': training_time,
                              'test_item_time': test_item_time,
                              'reward_for_correct': reward_for_correct,
                              'ai_move_temp': ai_move_temp,
                              'move_eval_temp': move_eval_temp,
                              'n_playout': n_playout,
                              'random_uuid': random_uuid}, Dumper=Dumper))


test_items = []
with open("test_items.json", 'r') as fin:
# with open("test_items_testing.json", 'r') as fin:
    test_items = json.loads(fin.read())

def transform_item(item, flip, rotate):

    answer = np.zeros((8,8), dtype=int)
    board = np.zeros((8,8), dtype=int)

    for move in item['correct_move']:
        answer[move['x']][move['y']] = 1

    for move in item['moves']:
        if move['color'] == "white":
            board[move['x']][move['y']] = -1
        else:
            board[move['x']][move['y']] = 1

    # print('original')
    # print(answer)
    # print(board)
    # print("---------------")

    if flip:
        answer = np.flip(answer, axis=1)
        board = np.flip(board, axis=1)

    if rotate in ["90", "180", "270"]:
        answer = np.rot90(answer)
        board = np.rot90(board)

    if rotate in ["180", "270"]:
        answer = np.rot90(answer)
        board = np.rot90(board)

    if rotate in ["270"]:
        answer = np.rot90(answer)
        board = np.rot90(board)

    # print('transformed')
    # print('flip', flip)
    # print('rotate', rotate)
    # print(answer)
    # print(board)
    # print("---------------")

    correct = np.where(answer == 1)
    transformed = {'correct_move': [], 'moves': []}
    for i in range(correct[0].shape[0]):
        transformed['correct_move'].append({'x': int(correct[0][i]), 'y': int(correct[1][i]), 'color': 'black'})

    black_moves = np.where(board == 1)
    for i in range(black_moves[0].shape[0]):
        transformed['moves'].append({'x': int(black_moves[0][i]), 'y': int(black_moves[1][i]), 'color': 'black'})

    white_moves = np.where(board == -1)
    for i in range(white_moves[0].shape[0]):
        transformed['moves'].append({'x': int(white_moves[0][i]), 'y': int(white_moves[1][i]), 'color': 'white'})

    print(transformed)

    return transformed

def get_player(external_vars=""):
    if ('player_id' not in session or
            Player.query.filter_by(id=session['player_id']).first() is None):
        if random_uuid:
            username = str(uuid.uuid1()) # generate a random id
        else:
            username = str(hash(request.remote_addr)) # use the hash of IP address
        
        if Player.query.filter_by(username=username).count() > 0:
            player = Player.query.filter_by(username=username).first() # get the player with a username if existed
        else:
            # Always assign to immediate feedback condition
            condition = 'immediate' 

            #condition = "delayed"
            external_vars = request.query_string.decode()
            player = Player(username=username, condition=condition,
                            external_vars=external_vars)
            db.session.add(player)
            db.session.commit()

            print("creating pretest")
            # create pretest
            pretest = [(item_id, item) for item_id, item in enumerate(test_items)]
            shuffle(pretest)

            for item_id, item in pretest:
                flip = choice([True, False])
                rotate = choice(["0", "90", "180", "270"])
                transformed_item = transform_item(item, flip, rotate)

                test_item = TestItem(test_item_id=item_id,
                                     test_item_name=item['item_name'],
                                     problem=json.dumps(transformed_item),
                                     player_id = player.id,
                                     pretest=True,
                                     flipped=flip,
                                     rotation=rotate)
                db.session.add(test_item)

            # print("creating posttest")
            # create posttest
            posttest = [(item_id, item) for item_id, item in enumerate(test_items)]
            shuffle(posttest)

            for item_id, item in posttest:
                flip = choice([True, False])
                rotate = choice(["0", "90", "180", "270"])
                transformed_item = transform_item(item, flip, rotate)

                test_item = TestItem(test_item_id=item_id,
                                     test_item_name=item['item_name'],
                                     problem=json.dumps(transformed_item),
                                     player_id = player.id,
                                     pretest=False,
                                     flipped=flip,
                                     rotation=rotate)
                db.session.add(test_item)

            db.session.commit()

        session['player_id'] = player.id
    else:
        player = Player.query.filter_by(id=session['player_id']).first()
    return player


def redirect_player(player, cur_page):
    print('redirect', player, cur_page)
    if player.stage != cur_page:
        # redirect user to the stage they should be on
        return redirect('/{}'.format(player.stage))
    
    print('stage', player.stage)
    print('page', cur_page)
    print()


def get_game(player):
    if ('game_id' not in session or
            Game.query.filter_by(id=session['game_id'],
                                 player_won=None).first() is None):
        is_testing = player.stage == 'testing'

        if is_testing:
            num_test_games = Game.query.filter_by(player=player, training_game=False).count()
            game = Game(player=player, player_is_white=False, training_game=not is_testing)
            
        else:
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


def get_mcts_player(player_index=1, n_playout=400):
    """
    Get an mcts player, an index of 1 corresponds to first player (typically
    human) and an index of 2 corresponds to the second player (typically AI
    opponent).
    """
    board = Board()
    board.init_board()

    size = 8
    model_file = '../AlphaZero_Gomoku/Models/1375_current_policy.model'

    # for numpy
    # try:
    #     policy_param = pickle.load(open(model_file, 'rb'))
    # except Exception:
    #     policy_param = pickle.load(open(model_file, 'rb'), encoding='bytes')

    # best_policy = PolicyValueNetNumpy(size, size, policy_param)

    use_gpu = torch.cuda.is_available()
    gpu_id = 2
    if use_gpu:
        torch.cuda.set_device(gpu_id)
    # use_gpu = False
    # print('using GPU: ', use_gpu)

    best_policy = PolicyValueNet(size, size, model_file = model_file, use_gpu=use_gpu)
    mcts_player = MCTSPlayer(best_policy.policy_value_fn, c_puct=8,
                             n_playout=n_playout) # modify n_playout to make easier models
    mcts_player.set_player_ind(player_index)

    return mcts_player


@app.route('/new_game', methods = ['POST'])
def new_game():
    # session.pop('game_id', None)
    # return json.dumps({}), 200, {'ContentType':'application/json'}

    try:
        # Get current game if exists
        current_game = None
        if 'game_id' in session:
            current_game = Game.query.get(session['game_id'])

        # End current game properly
        if current_game and current_game.player_won is None:
            current_game.player_won = False  # Mark as ended
            db.session.commit()

        # Clear session and start fresh
        session.pop('game_id', None)
        return json.dumps({"success": True}), 200, {'ContentType': 'application/json'}

    except Exception as e:
        db.session.rollback()
        return json.dumps({"success": False, "error": str(e)}), 500, {'ContentType': 'application/json'}


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
        # Skip pretest and go directly to training
        p.training_start = datetime.datetime.utcnow()
        p.stage = 'training'
    elif p.stage == 'training' and request.get_json().get('page') == 'training':
        p.posttest_start = datetime.datetime.utcnow()
        p.stage = 'posttest_start'
    elif p.stage == 'posttest_start' and request.get_json().get('page') == 'posttest_start':
        p.posttest_start = datetime.datetime.utcnow()
        p.stage = 'posttest'
    elif p.stage == 'posttest' and request.get_json().get('page') == 'posttest':
        p.posttest_result_start = datetime.datetime.utcnow()
        p.stage = 'posttest_result'
    elif p.stage == 'posttest_result' and request.get_json().get('page') == 'posttest_result':
        p.survey_start = datetime.datetime.utcnow()
        p.stage = 'survey'
    elif p.stage == 'survey' and request.get_json().get('page') == 'survey':
        p.experiment_end = datetime.datetime.utcnow()
        p.stage = 'done'

    # save to the database
    db.session.add(p)
    db.session.commit() 

    if p.stage == 'survey':
        # send the participant id to Qualtrics
        return json.dumps({'next_page':'https://gatech.co1.qualtrics.com/jfe/form/SV_56BedMBZm7q1TUO?participant_id={}'.format(p.id)}), 200, {'ContentType':'application/json'}

    return json.dumps({'next_page':'/{}'.format(p.stage)}), 200, {'ContentType':'application/json'}

@app.route('/training_time_left')
def training_time_left():
    p = get_player()
    delta = datetime.datetime.utcnow() - p.training_start #calculate the period of time
    ############# modify the number for testing #############
    seconds = max(0, training_time - delta.total_seconds()) #take the seconds left from 300 seconds
    return json.dumps({'seconds':seconds}), 200, {'ContentType':'application/json'} #return a dictionary

@app.route('/answer_test_item', methods=['POST'])
def get_test_item():
    data = request.get_json()
    p = get_player()
    print("/answer_test_item call with player {} and data {}".format(p, data))
    test_item_id = data['test_item_id']
    move = data['move']


    item = TestItem.query.filter_by(player_id=p.id,
                                    test_item_id=test_item_id,
                                    pretest=p.stage=="pretest").first()

    item.move = json.dumps(move)
    item.move_time = datetime.datetime.utcnow()

    db.session.add(item)
    db.session.commit() 

    return current_test_item_info()


@app.route('/current_test_item_info', methods=['POST'])
def current_test_item_info():
    p = get_player()

    total_probs = len(test_items)
    items = TestItem.query.filter_by(player_id=p.id,
                                     pretest=p.stage=="pretest",
                                     move=None)
    completed_probs = (total_probs - items.count())

    if items.count() == 0:
        return json.dumps({}), 200, {'ContentType': 'application/json'}

    item = items.order_by(TestItem.id).first()

    if item.start_time is None:
        item.start_time = datetime.datetime.utcnow()

    db.session.add(item)
    db.session.commit() 

    # delta = datetime.datetime.utcnow() - p.training_start #calculate the period of time
    time_left = max(test_item_time -
                    (datetime.datetime.utcnow() - item.start_time).total_seconds(), 0)

    data = {'item_id': item.test_item_id,
            'moves': json.loads(item.problem)['moves'],
            'completed_probs': completed_probs+1,
            'total_probs': total_probs,
            'seconds': time_left} 

    return json.dumps(data), 200, {'ContentType':'application/json'}

    # get current item
    # get number of seconds left
    # get the number of problems solved so far and the total number
    data = {'item_id': items.test_item_id,
            'moves': items.problem.moves,
            }

    return json.dumps({'seconds': 20}), 200, {'ContentType':'application/json'} #return a dictionary


@app.route('/testing_games_left')
def testing_games_left():
    p = get_player()
    test_games = Game.query.filter_by(player_id=p.id, training_game=False)
    ############# modify the number for testing #############
    games = max(0, testing_games + 1 - test_games.count()) #calculate the number of games left
    return json.dumps({'games':games}), 200, {'ContentType':'application/json'} #return a dictionary


@app.route('/')
def start():
    r = redirect_player(get_player(), 'start')
    if r is not None:
        return r

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


@app.route('/pretest_start')
def pretest_start():
    r = redirect_player(get_player(), 'pretest_start')
    if r is not None:
        return r

    return render_template('preposttest_start.html',
                           reward_per_prob=reward_for_correct,
                           test_item_time=test_item_time)

@app.route('/pretest')
def pretest():
    r = redirect_player(get_player(), 'pretest')
    if r is not None:
        return r

    return render_template('preposttest.html', size=8)


@app.route('/pretest_result')
def pretest_result():
    print('pretest result')
    p = get_player()
    r = redirect_player(p, 'pretest_result')
    if r is not None:
        return r

    return render_test_result(p)


@app.route('/posttest_start')
def posttest_start():
    r = redirect_player(get_player(), 'posttest_start')
    if r is not None:
        return r

    return render_template('preposttest_start.html',
                           reward_per_prob=reward_for_correct,
                           test_item_time=test_item_time)

@app.route('/posttest')
def posttest():
    r = redirect_player(get_player(), 'posttest')
    if r is not None:
        return r
    return render_template('preposttest.html', size=8)

def render_test_result(p):
    items = TestItem.query.filter_by(player_id=p.id,
                                     pretest=p.stage=="pretest_result")

    total_probs = items.count()
    correct_probs = 0
    for item in items:
        user_move = json.loads(item.move)
        if user_move == 'timeout':
            continue

        correct_moves = json.loads(item.problem)['correct_move']
        # if item.is_correct:
        #     correct_probs += 1
        # TODO move up intest_items 
        print(correct_moves)
        for correct_move in correct_moves:
            print(user_move)
            print(correct_move)
            print()
            if user_move['x'] == correct_move['x'] and user_move['y'] == correct_move['y']:
                correct_probs += 1
                break

    reward = correct_probs * reward_for_correct

    return render_template('preposttest_result.html',
                           correct_probs=correct_probs,
                           total_probs=total_probs,
                           reward=reward)


@app.route('/posttest_result')
def posttest_result():
    p = get_player()
    r = redirect_player(p, 'posttest_result')
    if r is not None:
        return r

    return render_test_result(p)


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

@app.route('/viz/<game_id>')
def viz(game_id):

    print(game_id)
    game = Game.query.filter_by(id=int(game_id)).first()
    print("GAME")
    print(game)
    print("END")
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

    page = 'viz.html'
    print(moves)
    return render_template(page, moves=moves, move_seq=move_seq, color=color,
                           size=game.size, score=score)

@app.route('/survey')
def survey():
    r = redirect_player(get_player(), 'survey')
    if r is not None:
        return r
    p = get_player()
    # sent the participant id to Qualtrics
    return redirect('https://gatech.co1.qualtrics.com/jfe/form/SV_6PUWBRnlpQheP6C?participant_id={}'.format(p.id))

@app.route('/goodbye')
def goodbye():
    return render_template('goodbye.html')

def add_move(i, j):
    player = get_player()
    game = get_game(player)

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)
    def is_client_connected():
        return not request.environ.get('werkzeug.server.shutdown')

    # Final check before committing
    if not is_client_connected() or game.player_won is not None:
        return jsonify({'status': 'aborted'}), 499

        # Check if game is still active
    if not game or game.player_won is not None:
        return jsonify({'error': 'Game no longer active'}), 410

        # Check client connection before processing
    if request.environ.get('werkzeug.server.shutdown'):
        return jsonify({'status': 'aborted'}), 499

    _, move_probs = compute_mcts_move(human, board, temp=move_eval_temp,
                                      n_playout=n_playout)

    game2 = get_game(player)
    board2 = get_board(game2)

    print('board1', board.states.items())
    print('board2', board2.states.items())

    if game2 is None or game2.player_won is not None:
        return jsonify({'end': True, 'winner': None})

    if len(set(board.states.items()) - set(board2.states.items())) != 0 and game2 is not None:
        print("boards out of sync")
        # return a json error that boards are out sync
        return jsonify({'error': 'boards are out of sync'}), 500

    # this breaks ties by always choosing the first.
    hint = int(np.argmax(move_probs))

    # print("hint_location", hint)
    # print("hint_type", type(hint))
    # print("hint_item_type", type(hint.item()))

    # print(move_probs)

    move = int(i) * board.height + int(j)
    score = move_probs[move]
    score = round(score / move_probs.max(), 2) # normalize

    board.do_move(move)

    player_move = Move(game=game, player_move=human, location=move,
                       score=score, hint_location=hint,
                       raw_move_scores=str(move_probs))

    def is_client_connected():
        return not request.environ.get('werkzeug.server.shutdown')

    # Final check before committing
    if not is_client_connected() or game2.player_won is not None:
        return jsonify({'status': 'aborted'}), 499

        # Check if game is still active
    if not game2 or game2.player_won is not None:
        return jsonify({'error': 'Game no longer active'}), 410

        # Check client connection before processing
    if request.environ.get('werkzeug.server.shutdown'):
        return jsonify({'status': 'aborted'}), 499

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

    return jsonify({'end': end, 'winner': winner, 'score': score, 'color': color,
            'move': move, 'hint': hint})

@app.route('/log/', methods=['POST'])
def log():
    event = request.get_json()['event']
    player = get_player()
    game = get_game(player)
    logged_event = Log(game_id=game.id, event=event)
    db.session.add(logged_event)
    db.session.commit()

    return jsonify({'success': True})

@app.route('/move/<i>/<j>', methods=['POST'])
def make_move(i, j):
    return add_move(i, j)

def get_probs_given_visits(visits, temp):
    return softmax(1.0/temp * np.log(np.array(visits) + 1e-10))

def compute_mcts_move(human, board, temp=1, n_playout=400):
    
    c = MctsCache.query.filter_by(human=human, board=json.dumps(board.states, sort_keys=True)).first()
    # c = MctsCache.query.filter_by(human=human, board=str(board.current_state())).first()
    if c is not None and c.n_playout < n_playout:
        db.session.delete(c)
        db.session.commit()
        c = None

    if c is None:
        # print('computing MCTS move')
        mcts_player = get_mcts_player(1, n_playout=n_playout)

        # move, scores = mcts_player.get_action(board, return_prob=True, temp=1)
        acts, visits = mcts_player.get_visits(board)

        c = MctsCache(human=human, board=json.dumps(board.states, sort_keys=True), n_playout=n_playout, acts=json.dumps(acts), visits=json.dumps(visits))
        
        # print('human: ', c.human)
        # print('board: ', c.board)
        # print('move: ', c.visits)
        
        db.session.add(c) # save to the database
        db.session.commit()

    acts = json.loads(c.acts)
    visits = json.loads(c.visits)
    probs = get_probs_given_visits(np.array(visits), temp=temp)
    move = np.random.choice(acts, p=probs)

    move_probs = np.zeros(8*8)
    move_probs[list(acts)] = probs

    # print('moves and probs')
    # print(move)
    # print(probs)
    return int(move), move_probs


@app.route('/get_hint', methods=['POST'])
def get_hint():
    """
    This is the AI move?
    """
    player = get_player()
    game = get_game(player)

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)

    _, move_probs = compute_mcts_move(human, board, temp=1e-5,
                                      n_playout=n_playout)

    # this breaks ties by always choosing the first.
    hint_move = np.argmax(move_probs)

    if human and game.player_is_white:
        color = 'white'
    elif not human and not game.player_is_white:
        color = 'white'
    else:
        color = 'black'

    i = int(hint_move) // board.height
    j = int(hint_move) % board.height

    return jsonify({'color': color, 'location': int(hint_move), 
                    'i': i, 'j': j})
    

@app.route('/get_ai_move', methods=['POST'])
def get_ai_move():
    player = get_player()
    game = get_game(player)

    # Validate game state before processing
    if not game or game.player_won is not None:
        db.session.rollback()
        return jsonify({'error': 'Game has ended'}), 410  # 410 Gone status

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)

    if game is None or game.player_won is not None:
        return jsonify({'end': True, 'winner': None})

    ai_move, _ = compute_mcts_move(human, board, temp=ai_move_temp,
                                   n_playout=n_playout)

    game2 = get_game(player)
    board2 = get_board(game2)

    print('board1', board.states.items())
    print('board2', board2.states.items())

    if game2 is None or game2.player_won is not None:
        return jsonify({'end': True, 'winner': None})

    if len(set(board.states.items()) - set(board2.states.items())) != 0 and game2 is not None:
        print("boards out of sync")
        # return a json error that boards are out sync
        return jsonify({'error': 'boards are out of sync'}), 500

    if human and game.player_is_white:
        color = 'white'
    elif not human and not game.player_is_white:
        color = 'white'
    else:
        color = 'black'

    i = int(ai_move) // board.height
    j = int(ai_move) % board.height

    return jsonify({'color': color, 'location': int(ai_move),
                    'i': i, 'j': j})


@app.route('/get_moves', methods=['GET'])
def get_moves():
    game = get_game(get_player())
    num_moves = len(game.moves)

    return jsonify({
        'moves': num_moves
    }), 200


@app.route('/rollback_transaction', methods=['POST'])
def rollback_transaction():
    try:
        db.session.rollback()
        return jsonify({'success': True})
    except:
        return jsonify({'success': False}), 500


@app.route('/analyze_move', methods=['POST'])
def analyze_move():
    """Analyze the last move with LLM"""
    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'LLM features not available'}), 503
    
    try:
        # Get current game and move data
        print("Getting player...")
        player = get_player()
        print(f"Player: {player}")
        
        print("Getting game...")
        game = get_game(player)
        print(f"Game: {game}")
        print(f"Game moves count: {len(game.moves) if game.moves else 0}")
        
        if not game.moves:
            print("ERROR: No moves in game")
            return jsonify({'error': 'No moves to analyze'}), 400
        
        # Print all moves for debugging
        print("All moves in game:")
        for i, move in enumerate(game.moves):
            print(f"  Move {i}: player_move={move.player_move}, location={move.location}, score={move.score}")
        
        # Find the last human move (before AI response)
        print("Looking for last human move...")
        last_human_move = None
        for move in reversed(game.moves):
            if move.player_move:  # This is a human move
                last_human_move = move
                print(f"Found last human move: location={move.location}, score={move.score}")
                break
        
        if not last_human_move:
            print("ERROR: No human move found")
            return jsonify({'error': 'No human move to analyze'}), 400
        
        # Create board state BEFORE the AI moved (after human's move)
        print("Creating board state...")
        moves_before_ai = [move for move in game.moves if move.id <= last_human_move.id]
        print(f"  Including {len(moves_before_ai)} moves (up to and including human's move)")
        
        # Convert to text with explicit position mapping
        print("Converting board to text...")
        board_text = convert_moves_to_board_text(moves_before_ai, current_move=last_human_move)
        # print("=" * 80)
        # print("BOARD STATE BEING SENT TO LLM:")
        # print("=" * 80)
        # print(board_text)
        # print("=" * 80)
        
        # Generate LLM analysis
        print("Calling LLM analysis...")
        llm_response = analyze_move_with_gemini(board_text, last_human_move, game)
        print(f"LLM response length: {len(llm_response) if llm_response else 0}")
        
        return jsonify({
            'analysis': llm_response,
            'score': last_human_move.score,
            'move_position': last_human_move.location
        })
    except Exception as e:
        print(f"Error in analyze_move: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/chat_with_llm', methods=['POST'])
def chat_with_llm():
    """Chat with LLM about the current game"""
    if not GEMINI_AVAILABLE:
        return jsonify({'error': 'LLM features not available'}), 503
    
    try:
        data = request.get_json()
        user_message = data['message']
        conversation_history = data.get('conversation', [])
        
        # Get current game context
        player = get_player()
        game = get_game(player)
        board_text = convert_board_to_text(game)
        
        # print("=" * 80)
        # print("BOARD STATE BEING SENT TO LLM (for chat):")
        # print("=" * 80)
        # print(board_text)
        # print("=" * 80)
        
        # Generate response with context
        llm_response = chat_with_gemini(board_text, user_message, conversation_history)
        
        return jsonify({'response': llm_response})
    except Exception as e:
        print(f"Error in chat_with_llm: {e}")
        return jsonify({'error': str(e)}), 500


def convert_board_to_text(game, current_move=None):
    """Convert game board to text representation with explicit position mapping"""
    return convert_moves_to_board_text(game.moves, current_move=current_move)


def convert_moves_to_board_text(moves, current_move=None):
    """Convert a list of moves to board text representation with explicit position mapping"""
    board = [['.' for _ in range(8)] for _ in range(8)]
    occupied_positions = []
    
    for move in moves:
        row = move.location // 8
        col = move.location % 8
        col_letter = chr(ord('A') + col)
        position = f"{col_letter}{row + 1}"
        
        if move.player_move:
            board[row][col] = 'B'  # Black (human)
            color = 'Black (Human)'
        else:
            board[row][col] = 'W'  # White (AI)
            color = 'White (AI)'
        
        # Mark current move if specified
        if current_move and move.id == current_move.id:
            occupied_positions.append(f"  {position} = {color} ← This is the move being analyzed")
        else:
            occupied_positions.append(f"  {position} = {color}")
    
    # Build result with explicit position mapping
    result = []
    result.append("Board State (8x8 grid):")
    result.append("")
    
    if occupied_positions:
        result.append("Occupied Positions:")
        result.extend(occupied_positions)
        result.append("")
    
    result.append("Visual Grid (for reference):")
    result.append("   A B C D E F G H")  # Column headers
    for i, row in enumerate(board):
        result.append(f"{i+1}  {' '.join(row)}")  # Row number + board row
    
    return '\n'.join(result)


def analyze_move_with_gemini(board_text, move, game):
    """Analyze move with Gemini"""
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    
    # Convert position to chess-like notation
    row = move.location // 8
    col = move.location % 8
    position_notation = f"{chr(ord('A') + col)}{row + 1}"
    
    prompt = f"""
    You are a Gomoku expert tutor. Analyze this human player's move and explain why it received its specific score. Note that the board is 8x8, which is much smaller than a traditional board. Please keep this in mind when analyzing the move.
    
    CRITICAL: Use the "Occupied Positions" list to verify exact positions. This list provides explicit coordinates (e.g., "D3 = White") with no ambiguity. Do NOT rely solely on the visual grid - always cross-reference with the explicit position list to avoid errors.
    
    {board_text}
    
    Move Details:
    - Position: {position_notation} (row {row + 1}, column {chr(ord('A') + col)})
    - Player: Black (Human)
    - Move Number: {len([m for m in game.moves if m.player_move])}
    - Score: {move.score}/1.0
    
    Please provide a concise analysis focusing on:
    1. **Why this move received a score of {move.score}/1.0** - explain the specific reasoning behind this numerical rating
    2. **Strategic assessment** - what this move accomplishes or fails to accomplish
    3. **Tactical patterns** - any threats, opportunities, or defensive moves involved.
    
    Be specific about the scoring rationale and educational for someone learning Gomoku strategy.
    Keep your response concise and to the point.
    When referring to positions, use the exact notation from the "Occupied Positions" list (e.g., "D3", "E4") and verify the color of stones using that list.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disables thinking
        ),
    )
    return response.text


def chat_with_gemini(board_text, user_message, conversation_history):
    """Chat with Gemini about the current game"""
    api_key = os.getenv('GEMINI_API_KEY')
    client = genai.Client(api_key=api_key)
    
    # Build conversation context
    conversation_text = "\n".join([
        f"User: {msg['user']}\nAssistant: {msg['assistant']}"
        for msg in conversation_history
    ])
    
    prompt = f"""
    You are a Gomoku expert tutor having a conversation about a specific move. Note that the board is 8x8, which is much smaller than a traditional board. Please keep this in mind when analyzing the move.
    
    Current Board State (A-H columns, 1-8 rows, B=Black, W=White, .=Empty):
    {board_text}
    
    Previous Conversation:
    {conversation_text}
    
    Current User Question: {user_message}
    
    Respond naturally and helpfully, maintaining context of the specific move being discussed. Use the A-H, 1-8 coordinate system when referring to positions.
    Keep your response concise and to the point.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disables thinking
        ),
    )
    return response.text


@app.route('/<path:path>')
def send_files(path):
    """Serve up the static files"""
    return send_from_directory('static', path)


if __name__ == "__main__":
    app.run()
