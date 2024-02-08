import os

from tqdm import tqdm

from matplotlib import pyplot as plt

file_path = 'prolific_pilot_player_game_move.csv'
file_path = 'cleaned_125.csv'
file_path = '189_player_game_move_ori.csv'

def render_game(game_id, save=False):

    fig, ax = plt.subplots()

    path = "game_images/"
    if not os.path.exists(path):
        os.mkdir(path)

    with open(file_path) as fin:

        player_x_loc = []
        player_y_loc = []
        player_mov_ids = []
        opp_x_loc = []
        opp_y_loc = []
        opp_mov_ids = []
        mov_id = 0
        player_id = None
        is_training = None
        player_won = None
        condition = None

        for line in fin:
            if 'player_id' in line:
                continue 

            line = line.replace('"', '').split(',')

            if len(line) < 2:
                continue

            if int(line[1]) != game_id:
                 continue

            player_id = int(line[0])
            is_training = int(line[5])
            condition = str(line[2])

            try:
                player_won = int(line[4])
            except:
                pass

            location = int(line[11])
            is_player = int(line[9]) == 1

            if is_player:
                player_x_loc.append(location % 8 + 0.5)
                player_y_loc.append(location // 8 + 0.5)
                player_mov_ids.append(mov_id)
            else:
                opp_x_loc.append(location % 8 + 0.5)
                opp_y_loc.append(location // 8 + 0.5)
                opp_mov_ids.append(mov_id)

            mov_id += 1
            
    ax.scatter(player_x_loc, player_y_loc, color='black')
    for x, y, i in zip(player_x_loc, player_y_loc, player_mov_ids):
        ax.text(x, y, str(i), color="black", fontsize=12)

    ax.scatter(opp_x_loc, opp_y_loc, color='red')
    for x, y, i in zip(opp_x_loc, opp_y_loc, opp_mov_ids):
        ax.text(x, y, str(i), color="red", fontsize=12)

    for i in range(9):
        ax.plot([0, 8], [i, i], color="black")
        ax.plot([i, i], [0, 8], color="black")

    if player_won is None:
        ax.title.set_text('Game Unfinished')
    elif player_won:
        ax.title.set_text('Player Won')
    else:
        ax.title.set_text('Player Lost')

    if save:
        if not os.path.exists(path + "{}/".format(player_id)):
            os.mkdir(path + "{}/".format(player_id))
        if is_training:
            fig.savefig(path + "{}/".format(player_id) + condition + "_{}_".format(player_id) + 'training_{}.png'.format(game_id))
        else:
            fig.savefig(path + "{}/".format(player_id) + condition + "_{}_".format(player_id) + 'testing_{}.png'.format(game_id))
    else:
        fig.show()

    plt.close(fig)

def get_game_ids():

    with open(file_path) as fin:
        game_ids = set()
        for line in fin:
            if 'player_id' in line:
                continue 

            line = line.replace('"', '').split(',')

            if len(line) < 2:
                continue
    
            if int(line[1]) == 0:
                 continue

            game_ids.add(int(line[1]))

    return game_ids

if __name__ == "__main__":

    game_ids = get_game_ids()
    for i in tqdm(game_ids):
        render_game(game_id=i, save=True)

