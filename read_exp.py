import json
import os.path
import argparse

from glob import glob
from pprint import pprint


def read_game(path: str):
    game_log_path = os.path.join(path, 'game_log.json')
    shared_memory_log_path = os.path.join(path, 'shared_memory_log.json')
    agents = glob(os.path.join(path, 'agents', '*', 'local_log.json'))
    game_log = get_game_history(game_log_path)
    game_log += get_communications(shared_memory_log_path)
    for agent in agents:
        game_log.extend(get_player_history(agent))
    game_log = sorted(game_log, key=lambda x: x["dttm"])
    game_state_counter = 0
    final_log = []
    for log_event in game_log:
        del log_event["dttm"]
        event_type = log_event.get("type")
        if event_type:
            if event_type == "game_state":
                game_state_counter += 1
                if game_state_counter == 5:
                    final_log.append(log_event)
                    game_state_counter = 0
            if event_type != "current_player_state":
                final_log.append(log_event)
        else:
            if not ( "Events since the last time you acted" in log_event["content"] or
                "Reply in JSON format of the following structure" in log_event["content"]):
                final_log.append(log_event)
    counter = 0
    for log_event in final_log:
        player_name = log_event.get("name")
        if player_name:
            print("USER REASONING")
            print(player_name, log_event.get("agent", ""))
            print(log_event["content"])
        else:
            print("===" * 30)
            print("GAME EVENT")
            pprint(log_event)
            print("===" * 30)
        counter += 1
        if counter > 5:
            input("Press Enter to continue...")
            print("<<<<<<<<<<NEW DATA!!!>>>>>>>>>>>")
            counter = 0

def get_game_history(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def get_communications(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                log = json.loads(line)
                if log["type"]["name"] == "PLAYER_SAY":
                    data.append(log)
    return data

def get_player_history(path):
    data = []
    name = path.split("\\")[-2].title()
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                log = json.loads(line)
                log["name"] = name
                data.append(log)
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bang viewer")
    parser.add_argument("exp", type=str)
    parser.add_argument("run", type=str)

    args = parser.parse_args()
    read_game(os.path.join('save', args.exp, args.run))