import json
import os
import random
from collections import defaultdict
from enum import Enum
from typing import Optional, Any, Generator, Never, Union

from omegaconf import OmegaConf

from src.game.Card import Card, CardType, CardID, CardActionRequest
from src.game.Config import Config
from src.game.Deck import Deck
from src.game.Player import Player, PlayerActionResponse
from src.game.Role import Role
from src.game.Utils import check_player_roles, GameEncoder


class GameResult(Enum):
    NO_WINNERS = 0
    RENEGADE_WIN = 3
    BANDIT_WIN = 2
    SHERIFF_WIN = 1


class Game:
    def __init__(self):
        self.config = Config().config
        random.seed(self.config.seed)
        check_player_roles(self.config)

        self.__deck = Deck()
        self.__players = self.__create_players()
        self.__players_order = [name for name in self.__players.keys()]
        self.__current_turn = 0
        self.current_player_state = self.__get_current_player_state()
        self.players_game_state = self.__get_players_game_state()
        self.__save_init_game_state()

    def get_player_names(self):
        return self.__players_order

    def get_player(self, name: str) -> Player:
        return self.__players[name]

    def __get_current_player_state(self):
        return self.__players[self.__players_order[self.__current_turn]]

    def get_game_log(self):
        return {
            "deck_and_discard": self.__deck.get_state_log(),
            "players": [player.get_state_log() for player in self.__players.values()],
            "players_order": self.__players_order
        }

    def __get_players_game_state(self):
        return {
            "players": {player_name: player_state.get_game_state()
                        for player_name, player_state in self.__players.items()},
            "players_order": self.__players_order,
            "current_player": self.current_player_state.name
                }

    def play_card(self, card: Card, options: Optional[dict[str, Any]] = None) -> Generator[dict[str, Any],
                                                                                    dict[str, PlayerActionResponse],
                                                                                    dict[str, Any]]:
        outliers = {}
        if self.current_player_state.has_card(card):
            match card.card_type:
                case CardType.ACTION:
                    action_handler = self.__play_action_card(card, options)
                    outliers = yield from action_handler
                case CardType.EFFECT:
                    self.current_player_state.play_effect_card(card)
                case CardType.WEAPON:
                    self.current_player_state.play_weapon_card(card)
        else:
            raise Exception(f"Card {card} not in hand")
        self.players_game_state = self.__get_players_game_state()
        return {"outliers": outliers, "game_status": self.__check_game_over()}

    def __play_action_card(self, card: Card, options: Optional[dict[str, Any]] = None) -> Generator[dict[str, Any],
                                                                                        dict[str, PlayerActionResponse],
                                                                                        dict[str, Role]]:
        outliers = {}
        match card.card_id:
            case CardID.STAGECOACH:
                self.current_player_state.draw_cards(2)
            case CardID.FARGO:
                self.current_player_state.draw_cards(3)
            case CardID.INDIANS:
                opponents = [player for player in self.__players_order
                             if player != self.__players_order[self.__current_turn]]
                for opponent in opponents:
                    request = {"request": CardActionRequest.RESPONSE_TO_INDIANS, "opponent": opponent}
                    self.current_player_state = self.__players[opponent]
                    response = yield request
                    if (response["action"] == PlayerActionResponse.BANG and
                            self.current_player_state.has_card(Card(CardID.BANG))):
                        self.current_player_state.discard_cards_from_hand(Card(CardID.BANG))
                    else:
                        self.current_player_state.decrease_health()
                        self.__beer_save()
                        outliers = self.__update_live_list()
            case CardID.GATLING:
                opponents = [player for player in self.__players_order
                             if player != self.__players_order[self.__current_turn]]
                for opponent in opponents:
                    request = {"request": CardActionRequest.RESPONSE_TO_GATLING, "opponent": opponent}
                    self.current_player_state = self.__players[opponent]
                    response = yield request
                    if (response["action"] == PlayerActionResponse.MISS and
                            self.current_player_state.has_card(Card(CardID.MISS))):
                        self.current_player_state.discard_cards_from_hand(Card(CardID.MISS))
                    else:
                        self.current_player_state.decrease_health()
                        self.__beer_save()
                        outliers = self.__update_live_list()
            case CardID.PANIC:
                opponent = options.get("opponent", "default")
                action_type = options.get("action_type", "from_hand")

                self.__check_opponent_availability(opponent)

                cur_player_name = self.__players_order[self.__current_turn]
                if self.__distance_to_opponent(cur_player_name, opponent) > 1:
                    raise Exception("The opponent is too far away")

                if action_type == "from_hand":
                    self.current_player_state.add_card_to_hand(self.__players[opponent].get_random_card_from_hand())
                else:
                    try:
                        card_for_steal = Card(CardID(options.get("card")))
                    except:
                        raise Exception(f"Card {options.get('card')} doesn't exist in the game")
                    try:
                        self.current_player_state.add_card_to_hand(
                            self.__players[opponent].get_card_from_game(card_for_steal)
                        )
                    except Exception as e:
                        raise Exception(str(e))
            case CardID.HOTTIE:
                opponent = options.get("opponent", "default")
                action_type = options.get("action_type", "from_hand")

                self.__check_opponent_availability(opponent)

                if action_type == "from_hand":
                    self.__deck.discard(self.__players[opponent].get_random_card_from_hand())
                else:
                    try:
                        card_for_discard = Card(CardID(options.get("card")))
                    except:
                        raise Exception(f"Card {options.get('card')} doesn't exist in the game")
                    try:
                           self.__deck.discard(self.__players[opponent].get_card_from_game(card_for_discard))
                    except Exception as e:
                        raise Exception(str(e))
            case CardID.SALOON:
                for player in self.__players.values():
                    player.increase_health()
            case CardID.BEER:
                if len(self.__players) > 2:
                    if not self.current_player_state.increase_health():
                        raise Exception("The player is at maximum health, the beer has no effect")
            case CardID.BANG:
                opponent = options.get("opponent", "default")
                self.__check_opponent_availability(opponent)

                cur_player_name = self.__players_order[self.__current_turn]
                if (not self.__distance_to_opponent(cur_player_name, opponent)
                        <= self.current_player_state.get_state_log()['weapon_range']):
                    raise Exception("The opponent is too far away")
                if not self.current_player_state.can_use_weapon:
                    raise Exception("You've used up all your shots this turn")

                if self.current_player_state.get_state_log()['weapon'] != Card(CardID.VOLKANIC):
                    self.current_player_state.can_use_weapon = False

                request = {"request": CardActionRequest.RESPONSE_TO_BANG, "opponent": opponent}
                self.current_player_state = self.__players[opponent]
                response = yield request
                if (response["action"] == PlayerActionResponse.MISS and
                        self.current_player_state.has_card(Card(CardID.MISS))):
                    self.current_player_state.discard_cards_from_hand(Card(CardID.MISS))
                else:
                    self.current_player_state.decrease_health()
                    self.__beer_save()
                    outliers = self.__update_live_list()

        self.current_player_state = self.__get_current_player_state()
        self.current_player_state.discard_cards_from_hand(card)
        return outliers

    def __check_opponent_availability(self, opponent: str):
        cur_player_name = self.__players_order[self.__current_turn]
        if opponent not in self.__players_order or opponent == cur_player_name:
            raise Exception("This opponent doesn't exist, or is it just you")

    def __distance_to_opponent(self, cur_player_name: str, opponent: str) -> bool:
        index_1 = self.__players_order.index(cur_player_name)
        index_2 = self.__players_order.index(opponent)
        num_players = len(self.__players_order)
        dist = abs(index_1 - index_2)
        min_dist = min(dist, num_players - dist)
        dist_modifiers = (self.__players[opponent].get_dist_modifiers()["for_save"]
                          - self.__players[cur_player_name].get_dist_modifiers()["for_shoot"])
        return min_dist + dist_modifiers

    def __beer_save(self):
        if self.current_player_state.get_health() < 1 and len(self.__players) > 2:
            beer_card = Card(CardID.BEER)
            if self.current_player_state.has_card(beer_card):
                self.current_player_state.increase_health()
                self.current_player_state.discard_cards_from_hand(beer_card)

    def __update_live_list(self) -> Union[dict[str, Role], dict[Never]]:
        outliers = self.__check_for_update_live_list()
        if outliers:
            self.__make_post_death_events(outliers)
        return outliers

    def __check_for_update_live_list(self) -> Union[dict[str, Role], dict[Never]]:
        outliers = [player_state for player_state in self.__players.values()
                    if player_state.get_state_log()['cur_hp'] <= 0]

        for outlier in outliers:
            key = outlier.get_state_log()['name']
            self.__players[key].death()
            del self.__players[key]
            self.__players_order.remove(key)

        outliers = {player.get_state_log()['name']: Role(player.get_state_log()['role']) for player in outliers}
        return outliers

    def __make_post_death_events(self, outliers: Union[dict[str, Role], dict[Never]]):
        for outlier_role in outliers.values():
            match outlier_role.value:
                case Role.BANDIT:
                    self.__get_current_player_state().draw_cards(3)
                case Role.SHERIFF_ASSISTANT:
                    if Role(self.__get_current_player_state().get_state_log()['role']) == Role.SHERIFF:
                        self.__get_current_player_state().death()

    def __check_game_over(self) -> GameResult:
        alive_roles = defaultdict(int)
        alive_num = 0
        for player in self.__players.values():
            player_info = player.get_state_log()
            alive_roles[Role(player_info['role'])] += 1
            alive_num += 1
        if alive_roles[Role.SHERIFF] == 1 and alive_roles[Role.BANDIT] == 0 and alive_roles[Role.RENEGADE] == 0:
            return GameResult.SHERIFF_WIN
        elif alive_roles[Role.SHERIFF] == 0 and alive_roles[Role.BANDIT] > 0:
            return GameResult.BANDIT_WIN
        elif alive_roles[Role.RENEGADE] == 1 and alive_num == 1:
            return GameResult.RENEGADE_WIN
        else:
            return GameResult.NO_WINNERS

    def start_of_turn(self):
        self.current_player_state.start_of_turn()

    def end_of_turn(self):
        self.current_player_state.end_of_turn()
        if self.__current_turn >= len(self.__players_order) - 1:
            self.__current_turn = 0
        else:
            self.__current_turn += 1
        self.current_player_state = self.__get_current_player_state()
        self.players_game_state = self.__get_players_game_state()

    def __save_init_game_state(self):
        path_to_save = self.config.save_path
        if not path_to_save:
            raise Exception('Fill in the path to save the game')
        if os.path.exists(path_to_save) and os.listdir(path_to_save):
            raise Exception('A save folder with this name already exists')
        os.makedirs(path_to_save, exist_ok=True)

        game_state = {
            "config": OmegaConf.to_container(self.config, resolve=True),
            "deck_and_discard": self.__deck.get_state_log(),
            "players": [player.get_state_log() for player in self.__players.values()],
            "players_order": self.__players_order
        }

        with open(os.path.join(path_to_save, 'game_init.json'), 'w', encoding='utf-8') as f:
            json.dump(game_state, f, indent=4, cls=GameEncoder)

    def __create_players(self) -> dict[str, Player]:
        hands = self.__init_players_hand()
        players = {}
        for player_config in self.config.players:
            name = player_config.name
            players[name] = Player(self.__deck, hands[name], player_config)
        return players

    def __init_players_hand(self) -> defaultdict[str, list[Card]]:
        hands = defaultdict(list)
        max_hand_size = -1
        for player in self.config.players:
            player_hand_size = player.max_hp
            if Role(player.role) == Role.SHERIFF:
                player_hand_size += 1
            if max_hand_size < player_hand_size:
                max_hand_size = player_hand_size

        for i in range(max_hand_size):
            for player in self.config.players:
                player_hand_size = player.max_hp + 1 if Role(player.role) == Role.SHERIFF else player.max_hp
                if len(hands[player.name]) >= player_hand_size:
                    continue
                hands[player.name].append(self.__deck.draw())
        return hands

