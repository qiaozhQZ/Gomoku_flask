import sys
import pickle
import uuid
import json
import datetime
import torch
import yaml
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

sys.path.append('../AlphaZero_Gomoku')

from game import Board  # noqa: E402
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from mcts_alphaZero import softmax  # noqa: E402
# from policy_value_net_numpy import PolicyValueNetNumpy  # noqa: E402
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
        test_item_time = data['test_item_time']
        reward_for_correct = data['reward_for_correct']
        ai_move_temp = data['ai_move_temp']
        move_eval_temp = data['move_eval_temp']
        player_hint_temp = data['player_hint_temp']
        random_uuid = data['random_uuid']
else:
    # numbers for launching the experiment
    training_time = 1200
    test_item_time = 60
    reward_for_correct = 0.5
    ai_move_temp = 1.0
    move_eval_temp = 1.0
    player_hint_temp = 0.5
    random_uuid = True
    # write to the yaml file
    with open('config.yaml','w') as fout:
        # save the variables to the yaml file
        fout.write(yaml.dump({'training_time': training_time,
                              'test_item_time': test_item_time,
                              'reward_for_correct': reward_for_correct,
                              'ai_move_temp': ai_move_temp,
                              'move_eval_temp': move_eval_temp,
                              'player_hint_temp': player_hint_temp,
                              'random_uuid': random_uuid}, Dumper=Dumper))


test_items = []
with open("test_items.json", 'r') as fin:
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

            #assign into different conditions to balance
            condition = sorted([(num_imm, random(), 'immediate'), 
                                (num_ctr, random(), 'control'),
                                (num_ctr, random(), 'delayed')])[0][2] 

            condition = "delayed"
            player = Player(username=username, condition=condition)
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
                                     problem=json.dumps(transformed_item),
                                     player_id = player.id,
                                     pretest=True,
                                     flipped=flip,
                                     rotation=rotate)
                db.session.add(test_item)

            print("creating posttest")
            # create posttest
            posttest = [(item_id, item) for item_id, item in enumerate(test_items)]
            shuffle(posttest)

            for item_id, item in posttest:
                flip = choice([True, False])
                rotate = choice(["0", "90", "180", "270"])
                transformed_item = transform_item(item, flip, rotate)

                test_item = TestItem(test_item_id=item_id,
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
            game = Game(player=player, player_is_white=False, training_game=not is_testing, game_difficulty=num_test_games%5)
            
        else:
            game = Game(player=player, player_is_white=False, training_game=not is_testing, game_difficulty=4)
        
        print("game difficulty", game.game_difficulty)

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


def get_mcts_player(player_index=1, difficulty=4):
    """
    Get an mcts player, an index of 1 corresponds to first player (typically
    human) and an index of 2 corresponds to the second player (typically AI
    opponent).
    """
    if difficulty < 0 or difficulty > 4:
        raise ValueError('Difficulty must be between 0 and 4.')

    board = Board()
    board.init_board()

    size = 8
    model_dict = {
            '0':'../AlphaZero_Gomoku/Models/PyTorch_models/best_policy_885_pt_50.model',
            '1':'../AlphaZero_Gomoku/Models/PyTorch_models/best_policy_885_pt_600.model',
            '2':'../AlphaZero_Gomoku/Models/PyTorch_models/best_policy_885_pt_3000.model',
            '3':'../AlphaZero_Gomoku/Models/PyTorch_models/best_policy_885_pt_5200.model',
            '4':'../AlphaZero_Gomoku/Models/PyTorch_models/best_policy_885_pt_10500.model'}
            # '4':'../AlphaZero_Gomoku/testing_only_2023-07-30_213745/current.model'}
    model_file = model_dict[str(difficulty)]
    

    # for numpy
    # try:
    #     policy_param = pickle.load(open(model_file, 'rb'))
    # except Exception:
    #     policy_param = pickle.load(open(model_file, 'rb'), encoding='bytes')

    # best_policy = PolicyValueNetNumpy(size, size, policy_param)

    use_gpu = torch.cuda.is_available()
    # use_gpu = False
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
        p.pretest_start = datetime.datetime.utcnow()
        p.stage = 'pretest_start'
    elif p.stage == 'pretest_start' and request.get_json().get('page') == 'pretest_start':
        p.pretest_result_start = datetime.datetime.utcnow()
        p.stage = 'pretest'
    elif p.stage == 'pretest' and request.get_json().get('page') == 'pretest':
        p.pretest_result_start = datetime.datetime.utcnow()
        p.stage = 'pretest_result'
    elif p.stage == 'pretest_result' and request.get_json().get('page') == 'pretest_result':
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
        return json.dumps({'next_page':'https://gatech.co1.qualtrics.com/jfe/form/SV_6PUWBRnlpQheP6C?participant_id={}'.format(p.id)}), 200, {'ContentType':'application/json'}

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
    test_item_id = data['test_item_id'];
    move = data['move'];
    p = get_player()

    item = TestItem.query.filter_by(player_id=p.id,
                                    test_item_id=test_item_id,
                                    pretest=p.stage=="pretest").first()

    item.move = json.dumps(move)
    item.move_time = datetime.datetime.utcnow();

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
        item.start_time = datetime.datetime.utcnow();

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


# @app.route('/done')
# def done():
#     return render_template('done.html')


######## time the function and log into a file ######
def move_player_and_opponent(i, j): 
    player = get_player()
    game = get_game(player)

    board = get_board(game)

    hint, move_probs = compute_mcts_move(True, board, difficulty=game.game_difficulty) # human is True

    # print(move_probs)

    move = int(i) * board.height + int(j)
    score = move_probs[move]
    score = round(score / move_probs.max())# normalize

    board.do_move(move)

    player_move = Move(game=game, player_move=True, location=move, score=score,
                       hint_location=hint, raw_move_scores=str(move_probs))
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

    move, _ = compute_mcts_move(False, board, difficulty=game.game_difficulty) # do not need probability
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

    hint, move_probs = compute_mcts_move(human, board, temp=move_eval_temp,
                                         difficulty=game.game_difficulty)
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
            'move': move, 'hint': hint}

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

def get_probs_given_visits(visits, temp):
    return softmax(1.0/temp * np.log(np.array(visits) + 1e-10))

def compute_mcts_move(human, board, temp=1, difficulty=4):
    
    c = MctsCache.query.filter_by(human=human, board=json.dumps(board.states, sort_keys=True), difficulty=difficulty).first()
    # c = MctsCache.query.filter_by(human=human, board=str(board.current_state())).first()
    if c is None:
        # print('computing MCTS move')

        if human:
            mcts_player = get_mcts_player(1, difficulty=difficulty)
        else:
            mcts_player = get_mcts_player(2, difficulty=difficulty)

        #TODO SET TEMP
        # temp here set to 1, should return visit count ratios
        # move, scores = mcts_player.get_action(board, return_prob=True, temp=1)
        acts, visits = mcts_player.get_visits(board)
        # print(acts)
        # print(visits)

        c = MctsCache(human=human, board=json.dumps(board.states, sort_keys=True), difficulty=difficulty, acts=json.dumps(acts), visits=json.dumps(visits))
        
        # print('human: ', c.human)
        # print('board: ', c.board)
        # print('move: ', c.visits)
        # print('difficulty: ', c.difficulty)
        
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

    hint_move, _ = compute_mcts_move(human, board, temp=player_hint_temp,
                                        difficulty=game.game_difficulty)

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

    human = False
    if len(game.moves) % 2 == 0:
        human = True

    board = get_board(game)

    ai_move, _ = compute_mcts_move(human, board, temp=ai_move_temp,
                                   difficulty=game.game_difficulty)

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

@app.route('/<path:path>')
def send_files(path):
    """Serve up the static files"""
    return send_from_directory('static', path)


if __name__ == "__main__":
    app.run()
