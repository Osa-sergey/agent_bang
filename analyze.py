import json
import os.path
import glob
from collections import defaultdict
from pprint import pprint


def analyze_exp(exp_name: str) -> dict:
    base_path = os.path.join('save', exp_name)
    runs = glob.glob(os.path.join(base_path, '*'))
    stats = []
    for run in runs:
        game_stat = dict()
        stat = defaultdict(dict)
        if not os.path.isdir(run):
            continue
        game_init_path = os.path.join(os.getcwd(), run, 'game_init.json')
        with open(game_init_path, 'r') as f:
            init_log = json.load(f)
        for player in init_log['config']['players']:
            stat[player['name']]['role'] = player['role']
        for name, agent_info in init_log['config']['agents'].items():
            stat[name]['agent'] = agent_info

        game_log_path = os.path.join(os.getcwd(), run, 'game_log.json')
        game_log = get_jsonl(game_log_path)
        game_log = sorted(game_log, key=lambda x: x["dttm"])

        game_step = 0
        first_player_in_step = ""
        remaining_players = []
        cur_player = {}
        game_state = {}
        cur_card = ""
        for event in game_log:
            value = event['value']

            match event['type']:
                case "game_state":
                    first_player_in_step = value['players_order'][0]
                    remaining_players = value['players_order']
                    game_state = value['players']

                case "turn_player":
                    if cur_player:
                        if not stat[cur_player['name']].get('played_cards', []):
                            stat[cur_player['name']]['played_cards'] = []
                        stat[cur_player['name']]['played_cards'].append(cur_player['played_cards'])

                    cur_player = {"name": value, "played_cards": []}

                    if value == first_player_in_step:
                        game_step += 1

                case "step_result":
                    outliers = value['outliers']
                    if outliers:
                        for k in outliers.keys():
                            stat[k]['death_step'] = game_step

                case "game_result":
                    game_stat['game_result'] = value['name']

                case "play_card":
                    if value != 'end':
                        cur_card = value['card']['card_id']
                        cur_player['played_cards'].append(cur_card)

                        if cur_card in ['hottie', 'panic']:
                            if not stat[cur_player['name']].get('steel_or_discard', []):
                                stat[cur_player['name']]['steel_or_discard'] = defaultdict(list)

                            stat[cur_player['name']]['steel_or_discard'][cur_card].append({'move': value, 'possibilities': game_state})

                case "current_player_state_after_draw":
                    if not stat[cur_player['name']].get('cards_before_turn', []):
                        stat[cur_player['name']]['cards_before_turn'] = []
                    stat[cur_player['name']]['cards_before_turn'].append(value['hand'])

                case "need_to_discard":
                    if not stat[cur_player['name']].get('need_to_discard', []):
                        stat[cur_player['name']]['need_to_discard'] = []
                    stat[cur_player['name']]['need_to_discard'].append({'game_step': game_step, 'num_cards': value})

                case "discarded_cards":
                    if not stat[cur_player['name']].get('discarded_cards', {}):
                        stat[cur_player['name']]['discarded_cards'] = defaultdict(int)
                    for card in value:
                        stat[cur_player['name']]['discarded_cards'][card['card_id']] += 1

                case "draft_play_card_option_fail":
                    if not stat[cur_player['name']].get('card_option_fail', []):
                        stat[cur_player['name']]['card_option_fail'] = defaultdict(list)
                    stat[cur_player['name']]['card_option_fail'][cur_card].append({'game_step': game_step,
                                                                        'fail': value})
                case "step_error":
                    if not stat[cur_player['name']].get('play_card_error', []):
                        stat[cur_player['name']]['play_card_error'] = defaultdict(list)
                    stat[cur_player['name']]['play_card_error'][cur_card].append({'game_step': game_step,
                                                                        'fail': value})
                case "response_for_card_fail":
                    if not stat[value['player']].get('response_for_card_fail', []):
                        stat[value['player']]['response_for_card_fail'] = defaultdict(list)
                    stat[value['player']]['response_for_card_fail'][cur_card].append({'game_step': game_step,
                                                                        'request_player': cur_player['name'],
                                                                        'fail': value})
                case "response_for_card":
                    if not stat[value['user']].get('response_for_card', []):
                        stat[value['user']]['response_for_card'] = defaultdict(list)
                    stat[value['user']]['response_for_card'][cur_card].append({'game_step': game_step,
                                                                         'request_player': cur_player['name'],
                                                                         'response': value})

        game_stat['max_game_step'] = game_step
        game_stat['players'] = stat
        stats.append(game_stat)
    pprint(stats)
    return stats


def get_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def get_metrics(stats: dict) -> dict:
    metrics = {}
    death_steps = dict()
    for stat in stats:
        game_result = stat['game_result']
        max_game_step = stat['max_game_step'] + 1
        for name, player_stat in stat['players'].items():
            who = player_stat['role']
            match game_result:
                case "SHERIFF_WIN":
                    is_win = True if who == 'sherif' or who == 'sherif_assistant' else False
                case "RENEGADE_WIN":
                    is_win = True if who == 'renegade' else False
                case "BANDIT_WIN":
                    is_win = True if who == 'bandit' else False
            death_step = player_stat.get('death_step', max_game_step)
            if not death_steps.get(name, False):
                death_steps[name] = dict()
                death_steps[name]['death_step'] = []
                death_steps[name]['game_step'] = []
                death_steps[name]['is_win'] = []
            death_steps[name]['death_step'].append(death_step)
            death_steps[name]['game_step'].append(max_game_step)
            death_steps[name]['is_win'].append(is_win)

    print(death_steps)



if __name__ == "__main__":
    stats = analyze_exp(exp_name='test')
    metrics = get_metrics(stats)
