import argparse
import json
import os.path
import glob
from collections import defaultdict
from pprint import pprint
import numpy as np


def init_user_config(run: str) -> defaultdict:
    stat = defaultdict(dict)
    game_init_path = os.path.join(os.getcwd(), run, 'game_init.json')
    with open(game_init_path, 'r') as f:
        init_log = json.load(f)
    for player in init_log['config']['players']:
        stat[player['name']]['role'] = player['role']
    for name, agent_info in init_log['config']['agents'].items():
        stat[name]['agent'] = agent_info
    return stat

def get_sorted_game_log(run: str):
    game_log_path = os.path.join(os.getcwd(), run, 'game_log.json')
    game_log = get_jsonl(game_log_path)
    agents_log = glob.glob(os.path.join(run, 'agents', '*', 'local_log.json'))
    for agent_log in agents_log:
        game_log.extend(get_jsonl(agent_log))
    game_log = sorted(game_log, key=lambda x: x["dttm"])
    return game_log

def analyze_exp(exp_name: str) -> dict:
    base_path = os.path.join('save', exp_name)
    runs = glob.glob(os.path.join(base_path, '*'))
    stats = []
    for run in runs:
        if not os.path.isdir(run):
            continue
            
        game_statistic = dict()
        stat = init_user_config(run)
       
        game_log = get_sorted_game_log(run)
        
        game_step = 0
        first_player_in_step = ""
        cur_player = {}
        game_state = {}
        cur_card = ""
        cur_player_name = ""
        end_of_run = False
        for event in game_log:
            if event.get("value"):
                value = event['value']

                match event['type']:
                    case "game_state":
                        first_player_in_step = value['players_order'][0]
                        game_state = value['players']

                    case "turn_player":
                        if cur_player:
                            if not stat[cur_player_name].get('played_cards', []):
                                stat[cur_player_name]['played_cards'] = []
                            stat[cur_player_name]['played_cards'].append(cur_player['played_cards'])

                        cur_player = {"name": value, "played_cards": []}
                        cur_player_name = cur_player["name"]

                        if value == first_player_in_step:
                            game_step += 1

                    case "step_result":
                        outliers = value['outliers']
                        if outliers:
                            for k in outliers.keys():
                                stat[k]['death_step'] = game_step

                    case "game_result":
                        game_statistic['game_result'] = value['name']
                        end_of_run = True
                    case "play_card":
                        if value != 'end':
                            cur_card = value['card']['card_id']
                            cur_player['played_cards'].append(cur_card)

                            if cur_card in ['hottie', 'panic']:
                                if not stat[cur_player_name].get('steel_or_discard', []):
                                    stat[cur_player_name]['steel_or_discard'] = defaultdict(list)

                                stat[cur_player_name]['steel_or_discard'][cur_card].append({'game_step': game_step, 'possibilities': game_state})

                    case "current_player_state_after_draw":
                        if not stat[cur_player_name].get('cards_before_turn', []):
                            stat[cur_player_name]['cards_before_turn'] = []
                        stat[cur_player_name]['cards_before_turn'].append(value['hand'])

                    case "need_to_discard":
                        if not stat[cur_player_name].get('need_to_discard', []):
                            stat[cur_player_name]['need_to_discard'] = []
                        stat[cur_player_name]['need_to_discard'].append({'game_step': game_step, 'num_cards': value})

                    case "discarded_cards":
                        if not stat[cur_player_name].get('step_discarded_cards', []):
                            stat[cur_player_name]['step_discarded_cards'] = []
                        if not stat[cur_player_name].get('discarded_cards', {}):
                            stat[cur_player_name]['discarded_cards'] = defaultdict(int)
                        stat[cur_player_name]['step_discarded_cards'].append({'game_step': game_step, 'discarded_cards': value})
                        for card in value:
                            stat[cur_player_name]['discarded_cards'][card['card_id']] += 1

                    case "draft_play_card_option_fail":
                        if not stat[cur_player_name].get('card_option_fail', []):
                            stat[cur_player_name]['card_option_fail'] = defaultdict(list)
                        stat[cur_player_name]['card_option_fail'][cur_card].append({'game_step': game_step,
                                                                            'fail': value})
                    case "step_error":
                        if not stat[cur_player_name].get('play_card_error', []):
                            stat[cur_player_name]['play_card_error'] = defaultdict(list)
                        stat[cur_player_name]['play_card_error'][cur_card].append({'game_step': game_step,
                                                                            'fail': value})
                    case "response_for_card_fail":
                        if not stat[value['player']].get('response_for_card_fail', []):
                            stat[value['player']]['response_for_card_fail'] = defaultdict(list)
                        stat[value['player']]['response_for_card_fail'][cur_card].append({'game_step': game_step,
                                                                            'request_player': cur_player_name,
                                                                            'fail': value})
                    case "response_for_card":
                        if not stat[value['user']].get('response_for_card', []):
                            stat[value['user']]['response_for_card'] = defaultdict(list)
                        stat[value['user']]['response_for_card'][cur_card].append({'game_step': game_step,
                                                                             'request_player': cur_player_name,
                                                                        'response': value})
            else:
                if event.get("users_role"):
                    users_role = clear_users_role(event["users_role"], stat)

                    if not stat[cur_player_name].get('users_role', []):
                        stat[cur_player_name]['users_role'] = []
                    stat[cur_player_name]['users_role'].append({"game_step": game_step, "users_role": users_role})

            if end_of_run:
                break

        game_statistic['max_game_step'] = game_step + 1
        game_statistic['players'] = stat
        stats.append(game_statistic)
    # pprint(stats)
    return stats

def clear_users_role(users_role_raw, stat):
    names = [name for name in stat.keys()]
    users_role_clear = dict()
    for name in names:
        role = users_role_raw.get(name, "")
        if role:
            role = role.lower()
            if role in ["sherif", "renegade", "bandits", "bandit", "sherif_assistant"]:
                if role == "bandits":
                    role = "bandit"
                users_role_clear[name] = role
            if role == "deputies":
                users_role_clear[name] = "sherif_assistant"
    return users_role_clear

def get_jsonl(path):
    data = []
    with open(path, 'r') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data

def get_metrics(stats: dict) -> dict:
    metrics = defaultdict(dict)
    for name, metric in get_death_metrics(stats).items():
        metrics[name].update(metric)
    for name, metric in get_efficiency_metrics(stats).items():
        metrics[name].update(metric)
    for name, metric in get_cards_fails_metrics(stats).items():
        metrics[name].update(metric)

    print(f"avg_surv_time_percent_of bandit_group {metrics['avg_surv_time_percent_of_bandit_group']}")
    print(f"avg_surv_time_percent_of sherif_group {metrics.get('avg_surv_time_percent_of_sherif_group', "not in exp")}")

    del metrics['avg_surv_time_percent_of_bandit_group']
    del metrics['avg_surv_time_percent_of_sherif_group']

    for player_name, metric in metrics.items():
        print(f"Player: {player_name}")
        print(f"Player role: {metric["player_role"]}")
        print(f"Player agent config: {metric["agent_config"]}")
        print(f"Average percentage of survival time: {metric["avg_perc_of_survival_time"]}")
        print(f"Percentage of survival to the end: {metric["perc_of_survival_to_end"]}")
        print(f"Percentage of victories: {metric["perc_of_victories"]}")
        print(f"Percentage of survival to the end with victory: {metric["perc_of_survival_to_end_with_victory"]}")
        print(f"Card utilization rate: {metric['card_utilization_rate']}")
        print(f"Max num card discarded: {metric['max_num_card_discarded']}")
        print(f"Attack efficiency: {metric['attack_efficiency']}")
        print(f"Defense efficiency: {metric['defense_efficiency']}")
        print(f"Percentage of auto pass: {metric['perc_of_auto_pass']}")
        print(f"Willful refusal defend: {metric['willful_refusal_defend']}")

        print()
        print(f"Percentage of assumption unk attack: {metric['assumption_unk_attack']}")
        print(f"Percentage of assumption correct attack: {metric['assumption_correct_attack']}")
        print(f"Percentage of fact correct attack: {metric['fact_correct_attack']}")

        print()
        print(f"Percentage of correct role assumption: {metric['correct_role_assumption']}")
        print(f"Percentage of correct role assumption bandit: {metric['correct_role_assumption_bandit']}")
        print(f"Percentage of correct role assumption sherif_assistant: {metric['correct_role_assumption_sherif_assistant']}")
        print(f"Percentage of correct role assumption renegade: {metric['correct_role_assumption_renegade']}")

        print()
        print(f"Mean per round response for card fail: {metric['response_for_card_fail']}")
        print(f"Mean per round step play card error: {metric['play_card_error']}")
        print(f"Mean per round step card option fail: {metric['card_option_fail']}")

        print()
        print("===" * 30)

def get_death_metrics(stats: dict) -> dict:
    metrics = defaultdict(dict)
    death_steps = dict()
    for stat in stats:
        game_result = stat['game_result']
        max_game_step = stat['max_game_step']
        for name, player_stat in stat['players'].items():
            who = player_stat['role']
            is_win = False
            match game_result:
                case "SHERIFF_WIN":
                    if who == 'sherif' or who == 'sherif_assistant':
                        is_win = True
                case "RENEGADE_WIN":
                    if who == 'renegade':
                        is_win = True
                case "BANDIT_WIN":
                    if who == 'bandit':
                        is_win = True
            death_step = player_stat.get('death_step', max_game_step)
            if not death_steps.get(name, False):
                death_steps[name] = dict()
                death_steps[name]['death_step'] = []
                death_steps[name]['game_step'] = []
                death_steps[name]['surv_time_percent'] = []
                death_steps[name]['is_win'] = []
            death_steps[name]['death_step'].append(death_step)
            death_steps[name]['game_step'].append(max_game_step)
            death_steps[name]['surv_time_percent'].append(death_step / max_game_step)
            death_steps[name]['is_win'].append(is_win)

    allies_groups = get_allies_groups(stats)

    for group, players in allies_groups.items():
        surv_time_percent = [death_steps[player]["surv_time_percent"] for player in players]
        mins = [min(arr[i] for arr in surv_time_percent) for i in range(len(surv_time_percent[0]))]
        metrics[f"avg_surv_time_percent_of_{group}_group"] = {"res": sum(mins) / len(mins)}

    for player, death_stat in death_steps.items():
        np_death_steps = np.array(death_stat['death_step'])
        np_game_steps = np.array(death_stat['game_step'])
        np_is_wins = np.array(death_stat['is_win'])

        avg_perc_of_survival_time = np.mean(np_death_steps / np_game_steps)
        perc_of_survival_to_end = np.sum(np_death_steps == np_game_steps) / len(np_death_steps)
        perc_of_victories = np.sum(np_is_wins == True) / len(np_is_wins)
        perc_of_survival_to_end_with_victory = np.sum((np_death_steps == np_game_steps) & (np_is_wins == True)) / len(
            np_death_steps)

        player_role = stats[0]['players'][player]["role"]
        agent_config = stats[0]['players'][player]["agent"]

        metrics[player] = {"player_role": player_role,
                                "agent_config": agent_config,
                                "avg_perc_of_survival_time": avg_perc_of_survival_time,
                                "perc_of_survival_to_end": perc_of_survival_to_end,
                                "perc_of_victories": perc_of_victories,
                                "perc_of_survival_to_end_with_victory": perc_of_survival_to_end_with_victory}
    return metrics

def get_allies_groups(stats: dict) -> dict:
    groups = defaultdict(list)
    stat = stats[0]
    for name, player_stat in stat['players'].items():
        who = player_stat['role']
        groups[who].append(name)
    res = dict()
    res["bandit"] = groups["bandit"]
    if groups.get("sherif_assistant"):
        res["sherif"] = groups["sherif_assistant"] + groups["sherif"]
    return res

def get_efficiency_metrics(stats: dict) -> dict:
    metrics = defaultdict(dict)
    played_cards_stat = dict()
    discarded_cards = dict()
    cards_before_turn_stat = dict()
    attacks = defaultdict(lambda: defaultdict(int))
    defenses = defaultdict(lambda: defaultdict(int))

    roles = defaultdict(lambda: defaultdict(int))

    for stat in stats:
        players_role = {name: info["role"] for name, info in stat["players"].items()}

        for name, player_stat in stat['players'].items():
            if not played_cards_stat.get(name):
                played_cards_stat[name] = []
            played_cards_stat[name].extend([len(cards) for cards in player_stat['played_cards']])
            if not cards_before_turn_stat.get(name):
                cards_before_turn_stat[name] = []
            cards_before_turn_stat[name].extend([len(cards) for cards in player_stat['cards_before_turn']])
            if not discarded_cards.get(name):
                discarded_cards[name] = []
            if not player_stat.get('need_to_discard'):
                discarded_cards[name].append(0)
            else:
                discarded_cards[name].extend([cards['num_cards'] for cards in player_stat['need_to_discard']])

            for roles_assumption in player_stat['users_role']:
                users_role = roles_assumption['users_role']
                for player, role in users_role.items():
                    cur_player_role = players_role[player]
                    if cur_player_role != "sherif":
                        if role == cur_player_role:
                            roles[name]["correct"] += 1
                            roles[name][f"{cur_player_role}_correct"] += 1
                        roles[name]["all"] += 1
                        roles[name][cur_player_role] += 1

            for card_type, responses in player_stat['response_for_card'].items():
                for player_response in responses:
                    game_step, request_player, response = player_response.values()
                    fact_correct_attack, assumption_correct_attack, mass_attack = get_attack_info(players_role,
                                                                                                  stat,
                                                                                                  card_type,
                                                                                                  game_step,
                                                                                                  request_player,
                                                                                                  response['user'])
                    if not mass_attack:
                        if fact_correct_attack:
                            attacks[request_player]['fact_correct_attack'] += 1
                        if assumption_correct_attack:
                            attacks[request_player]['assumption_correct_attack'] += 1
                        if assumption_correct_attack == "unk":
                            attacks[request_player]['assumption_unk_attack'] += 1
                        attacks[request_player]['all_target_attack'] += 1

                    if response['reaction'] == 'pass':
                        attacks[request_player]['success'] += 1
                        if response['is_auto_response']:
                            defenses[response['user']]['auto_pass'] += 1
                    else:
                        defenses[response['user']]['success'] += 1
                    attacks[request_player]['all'] += 1
                    defenses[response['user']]['all'] += 1

    player_names = stats[0]['players'].keys()
    for name in player_names:
        metrics[name]['card_utilization_rate'] = sum(played_cards_stat[name]) / sum(cards_before_turn_stat[name])
        metrics[name]['max_num_card_discarded'] = max(discarded_cards[name])
        metrics[name]['attack_efficiency'] = attacks[name]['success'] / attacks[name]['all']
        metrics[name]['defense_efficiency'] = defenses[name]['success'] / defenses[name]['all']
        metrics[name]['willful_refusal_defend'] = (defenses[name]['all'] - defenses[name]['success'] - defenses[name]['auto_pass']) / defenses[name]['all']
        metrics[name]['perc_of_auto_pass'] = defenses[name]['auto_pass'] / defenses[name]['all']

        metrics[name]['fact_correct_attack'] = attacks[name]["fact_correct_attack"] / attacks[name]["all_target_attack"]
        metrics[name]['assumption_correct_attack'] = attacks[name]["assumption_correct_attack"] / attacks[name]["all_target_attack"]
        metrics[name]['assumption_unk_attack'] = attacks[name]["assumption_unk_attack"] / attacks[name]["all_target_attack"]

        metrics[name]['correct_role_assumption'] = roles[name]['correct'] /  roles[name]['all']

        metrics[name]['correct_role_assumption_bandit'] = 0 if roles[name]['bandit'] == 0 else roles[name]['bandit_correct'] / roles[name]['bandit']
        metrics[name]['correct_role_assumption_sherif_assistant'] = 0 if roles[name]['sherif_assistant'] == 0 else roles[name]['sherif_assistant_correct'] / roles[name]['sherif_assistant']
        metrics[name]['correct_role_assumption_renegade'] = 0 if roles[name]['renegade'] == 0 else roles[name]['renegade_correct'] / roles[name]['renegade']
    return metrics

def get_attack_info(players_role, stat, card_type, game_step, attacker, defender):
    attacker_role = players_role[attacker]
    defender_role = players_role[defender]

    fact_correct_attack = check_correct_attack(attacker_role, defender_role)
    assumption_correct_attack = "unk"

    assumptions = stat['players'][attacker]["users_role"]
    for assumption in assumptions:
        if assumption["game_step"] == game_step:
            defender_role = assumption["users_role"].get(defender, "unk")
            if defender_role != "unk":
                assumption_correct_attack = check_correct_attack(attacker_role, defender_role)
            break

    mass_attack = card_type != "bang"

    return fact_correct_attack, assumption_correct_attack, mass_attack

def check_correct_attack(attacker_role, defender_role):
    return (attacker_role == "sherif" and defender_role != "sherif_assistant" or
            attacker_role == "bandit" and defender_role != "bandit" or
            attacker_role == "sherif_assistant" and defender_role != "sherif")

def get_cards_fails_metrics(stats: dict) -> dict:
    metrics = defaultdict(dict)
    response_fails = defaultdict(int)
    play_card_fails = defaultdict(int)
    card_option_fails = defaultdict(int)

    for stat in stats:
        for name, player_stat in stat['players'].items():
            if player_stat.get('response_for_card_fail'):
                for card_type, fails in player_stat['response_for_card_fail'].items():
                    response_fails[name] += len(fails)

            if player_stat.get('play_card_error'):
                for card_type, fails in player_stat['play_card_error'].items():
                    play_card_fails[name] += len(fails)

            if player_stat.get('card_option_fail'):
                for card_type, fails in player_stat['card_option_fail'].items():
                    card_option_fails[name] += len(fails)

    num_rounds = len(stats)
    player_names = stats[0]['players'].keys()
    for name in player_names:
        metrics[name]['response_for_card_fail'] = response_fails[name] / num_rounds
        metrics[name]['play_card_error'] = play_card_fails[name] / num_rounds
        metrics[name]['card_option_fail'] = card_option_fails[name] / num_rounds
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metric analyze")
    parser.add_argument("exp", type=str)
    args = parser.parse_args()

    statistic = analyze_exp(exp_name=args.exp)
    metrics = get_metrics(statistic)
