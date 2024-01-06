import json
import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

tables = ['game', 'log', 'mcts_cache', 'move', 'player', 'test_item']
data = {}

con = sqlite3.connect('/content/art.db')
con.row_factory = dict_factory
cursor = con.cursor()

for table in tables:
    cursor.execute(f'''SELECT * FROM {table}''')
    rows = cursor.fetchall()
    data[table] = rows

with open('final_data.json', 'w') as fp:
    json.dump(data, fp, indent=4)

def count_corrects():
    pass

if __name__ == "__main__":
    count_corrects()