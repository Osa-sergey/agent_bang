import json
import os.path

from glob import glob
from pprint import pprint


def read_game(path: str):
    shared_memory_log_path = os.path.join(path, 'shared_memory_log.json')
    agents = glob(os.path.join(path, 'agents', '*', 'local_memory.json'))
    game_log = get_jsonl(shared_memory_log_path)
    for agent in agents:
        game_log.extend(get_jsonl(agent))
    game_log = sorted(game_log, key=lambda x: x["dttm"])
    pprint(game_log)

def get_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

if __name__ == "__main__":
    read_game(os.path.join('save', 'test8', '4a808750-5193-4ba4-9403-07e450ef9ca4'))