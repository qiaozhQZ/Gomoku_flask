import os
import shutil

source_path = "C:/Users/qzhang490/Desktop/delay/include"
destination_path = "C:/Users/qzhang490/Desktop/delay_print"
    
for foldername in os.listdir(source_path):
    folder_path = os.path.join(source_path, foldername)
    for dirpath, dirnames, filenames in os.walk(folder_path):
        # print(folder_path)
        # print(filenames)
        train = [filename.split('_')[-1] for filename in filenames if filename.split('_')[2] == 'training' ]
        train_sort = sorted([game_id.split('.')[0] for game_id in train])
        train_select = train_sort[:3] + train_sort[-3:]
        # print(train_sort)
        # print(train_select)

        files_to_copy = (['_'.join(filenames[0].split('_')[:2]) + '_training_' + game_id + '.png' for game_id in train_select])
        # print(files_to_copy)
        for file_path in files_to_copy:
            shutil.copy(os.path.join(folder_path, file_path), destination_path)
         