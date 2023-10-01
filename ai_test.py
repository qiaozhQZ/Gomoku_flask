from pprint import pprint
import json
import sys
import os
import numpy as np
from matplotlib import pyplot as plt

sys.path.append('../AlphaZero_Gomoku')

from game import Board
from mcts_alphaZero import MCTSPlayer  # noqa: E402
from policy_value_net_pytorch import PolicyValueNet


def render_probs(problem, save=False):
    pprint(problem)

    path = 'test_ai_heatmaps'
    if not os.path.exists(path):
        os.mkdir(path)

    board_width = 8
    board_height = 8

    board = Board(width=board_width, height=board_height, n_in_row=5)
    board.init_board(0)

    black_x = []
    black_y = []
    white_x = []
    white_y = []
    correct_x = [move['x'] for move in problem['correct_move']]
    correct_y = [move['y'] for move in problem['correct_move']]

    for move in problem['moves']:
        move_loc = int(move['y']) * board.height + int(move['x'])
        board.do_move(move_loc)
        if move['color'] == 'black':
            black_x.append(move['x'])
            black_y.append(move['y'])
        else:
            white_x.append(move['x'])
            white_y.append(move['y'])

    policy = PolicyValueNet(board_width, board_height,
                            model_file='../AlphaZero_Gomoku/Models/1375_current_policy.model',
                            use_gpu=False)

    mcts_player = MCTSPlayer(policy.policy_value_fn,
                             alpha=0.15, epsilon=0.25, c_puct=3.0,
                             n_playout=400, is_selfplay=0)

    move_probs = None
    for _ in range(1):
        acts, mp = mcts_player.get_action(board, temp=1.0, return_prob=1)
        if move_probs is None:
            move_probs = mp.copy()
        else:
            move_probs += mp

    fig, ax1 = plt.subplots(1, 1, figsize=(8, 8))

    im1 = ax1.imshow(move_probs.reshape((8,8)))
    ax1.scatter(x=black_x, y=black_y, c="black", s=1000)
    ax1.scatter(x=white_x, y=white_y, c="white", s=1000)
    ax1.scatter(x=correct_x, y=correct_y, c="red", s=1000)
    # , c='black', s=40)
    # im2 = ax2.imshow(move_probs2.reshape((8,8)))

    # row_label = [0 + i*8 for i in range(8)]
    # col_label = [56 + i for i in range(8)]
    # ax1.set_yticks(np.arange(len(row_label)), labels=row_label)
    # ax1.set_xticks(np.arange(len(col_label)), labels=col_label)
    # ax2.set_yticks(np.arange(len(row_label)), labels=row_label)
    # ax2.set_xticks(np.arange(len(col_label)), labels=col_label)

    # Minor ticks
    ax1.set_xticks(np.arange(-.5, 8, 1), minor=True)
    ax1.set_yticks(np.arange(-.5, 8, 1), minor=True)

    # Gridlines based on minor ticks
    ax1.grid(which='minor', color='black', linestyle='-', linewidth=2)


    for row in range(8):
        for col in range(8):
            text1 = ax1.text(col, row, round(move_probs.reshape((8,8))[row, col], 3),
                             ha="center", va="center", color="w")

            # text2 = ax2.text(col, row, round(move_probs2.reshape((8,8))[row, col], 3),
            #                  ha="center", va="center", color="w")

    ax1.set_title("{} (net probs)".format(problem['item_name']))
    # ax2.set_title("{} (mcts counts)".format(problem['item_name']))

    fig.tight_layout()
    # print("Move Probs Shape:", move_probs.shape)
    # print(move_probs.reshape((8,8)))

    if path:
        # print("current_batch", i)
        fig.savefig(path + "/{}".format(problem['item_name']) + ".png")
    else:
        fig.show()
    plt.close(fig)

if __name__ == "__main__":
    with open('test_items.json', 'r') as fin:
        data = json.load(fin)

    # pprint(data)

    for p in data:
        render_probs(p)

