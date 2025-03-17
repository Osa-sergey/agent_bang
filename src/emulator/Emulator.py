import datetime
import json
import os.path
from collections import defaultdict
from enum import Enum
from pprint import pprint
from typing import Any, Optional, Callable, Union
from zoneinfo import ZoneInfo

from src.agent.Agent import Agent, AgentType
from src.emulator.LoggedList import LoggedList, SavePath
from src.game.Card import Card, CardID, CardActionRequest
from src.game.Config import Config
from src.game.Game import Game, GameResult
from src.game.Player import Player, PlayerActionResponse
from src.game.Utils import GameEncoder
from src.agent.UserAgent import UserAgent


class LogEventType(Enum):
    NEED_DISCARD_CARDS = 10
    STEP_ERROR = 9
    STEP_RESULT = 8
    RESPONSE_FOR_CARD_FAIL = 7
    RESPONSE_FOR_CARD = 6
    DRAFT_PLAY_CARD = 5
    DRAFT_PLAY_CARD_FAIL = 4
    DRAFT_PLAY_CARD_OPTION_FAIL = 3
    PLAY_CARD = 2
    PLAYERS_GAME_STATE = 1
    TURN_PLAYER = 0


class GameEmulator:

    def __init__(self, config_path: str,
                 current_player_state_render: Optional[Callable[[Player], None]] = None,
                 players_game_state_render: Optional[Callable[[dict[str, Any]], None]] = None,
                 use_gui: bool = False):
        self.__config = Config()
        self.__config.init(config_path)
        self.use_gui = use_gui
        Config().config.gui = self.use_gui
        self.__game = Game(current_player_state_render, players_game_state_render)
        self.__shared_memory = LoggedList(self._write_json_log, SavePath.SHARED_MEMORY)
        self.__agents = self.__init_agents(self.__game, self.__shared_memory, config=Config().config)

    @property
    def shared_memory(self):
        return self.__shared_memory

    @property
    def current_agent(self):
        return self.__agents[self.__game.current_player_state.name]

    @staticmethod
    def __init_agents(game: Game, shared_memory: LoggedList, config) -> dict[str, Agent]:
        agents = {}
        for agent_name, agent_config in config.agents.items():
            match AgentType(agent_config["agent_type"]):
                case AgentType.USER_AGENT:
                    player = game.get_player(agent_name)
                    agents[agent_name] = UserAgent(agent_name, config, player, shared_memory)
        return agents

    def draw_state(self):
        _ = self.__game.players_game_state
        _ = self.__game.current_player_state

    def start_of_turn(self):
        _ = self.__game.players_game_state
        player_state = self.__game.current_player_state
        print("===" * 15, f"Turn player: {player_state.name}", "===" * 15)
        self._write_json_log({"turn_player": player_state.name})
        self._write_json_log({"current_player_state": player_state.get_state_log()})
        self.__shared_memory.append({"type": LogEventType.TURN_PLAYER, "value": player_state.name})
        self.__game.start_of_turn()
        self._write_json_log({"current_player_state_after_draw": player_state.get_state_log()})
        self.__print_game_state()

    def gui_game(self):
        agent = self.current_agent
        if not isinstance(agent, UserAgent):
            self.auto_play()
        else:
            self.start_of_turn()

    def __one_player_game_circle(self):
        self.start_of_turn()
        game_result = self.__play_cards()
        if game_result != GameResult.NO_WINNERS:
            print("===" * 15, "END OF GAME", "===" * 15)
            print(game_result.name)
            return
        self.end_of_turn()

    def end_of_turn(self):
        self.__discard_cards()
        self.__game.end_of_turn()

    def auto_play(self):
        while True:
            self.__one_player_game_circle()

            agent = self.current_agent
            if isinstance(agent, UserAgent):
                return

    def play_game(self):
        while True:
            self.__one_player_game_circle()

    def _write_json_log(self, data: dict[str, Any], file_name: str = "game_log.jsonl"):
        log_file = os.path.join(self.__config.config.save_path, file_name)
        with open(log_file, "a", encoding="utf-8") as f:
            data["dttm"] = datetime.datetime.now(ZoneInfo("Europe/Moscow"))
            json.dump(data, f, indent=4, cls=GameEncoder)

    def __print_game_state(self):
        print("===" * 15, "All player", "===" * 15)
        self.__shared_memory.append({"type": LogEventType.PLAYERS_GAME_STATE, "value": self.__game.players_game_state})
        self._write_json_log({"game_state": self.__game.get_game_log()})
        pprint(self.__game.players_game_state)
        print("===" * 15, "Current player", "===" * 15)
        print(self.__game.current_player_state)

    def play_card(self, card:  dict[str, dict[str, Any] | Card] | str) -> dict[str, Union[GameResult, bool]]:
        self.__shared_memory.append({"type": LogEventType.PLAY_CARD, "value": card})
        self._write_json_log({"play_card": card})
        if card != "end":
            card, options = card["card"], card["options"]
            generator_play_card = self.__game.play_card(card, options=options)
            try:
                request = next(generator_play_card)
                while True:
                    response = self.__get_opponent_response_for_card(request)
                    request = generator_play_card.send(response)
            except StopIteration as e:
                print("Step result")
                pprint(e.value)
                self.__shared_memory.append({"type": LogEventType.STEP_RESULT, "value": e.value})
                self._write_json_log({"step_result": e.value})
                if e.value["game_status"] != GameResult.NO_WINNERS:
                    self._write_json_log({"game_result": e.value["game_status"]})
                    return {"game_result": e.value["game_status"], "end_of_turn": True}
            except Exception as e:
                pprint(e)
                self.__shared_memory.append({"type": LogEventType.STEP_ERROR, "value": str(e)})
                self._write_json_log({"step_error": str(e)})
            self.__print_game_state()
            return {"game_result": GameResult.NO_WINNERS, "end_of_turn": False}
        else:
            return {"game_result": GameResult.NO_WINNERS, "end_of_turn": True}

    def __play_cards(self) -> GameResult:
        while True:
            card = self.get_card_for_play()
            card_result = self.play_card(card)
            if card_result["end_of_turn"]:
                return card_result["game_result"]

    def __discard_cards(self):
        player_state = self.__game.current_player_state
        need_to_discard = player_state.need_to_discard()
        if need_to_discard > 0:
            print(f"Need to discard {need_to_discard} cards")
            print(f"Please make a choice")
            print(player_state)
            self.__shared_memory.append({"type": LogEventType.NEED_DISCARD_CARDS,
                               "value": f"Player {player_state.name} need to discard {need_to_discard} cards"})
            self._write_json_log({"need_to_discard": need_to_discard})
            agent = self.__agents[player_state.name]
            while True:
                try:
                    cards_for_discard = self.__get_cards_for_discard(need_to_discard, player_state, agent)
                    break
                except Exception as e:
                    agent.react_to_discard_error(str(e))

            self._write_json_log({"discarded_cards": cards_for_discard})
            player_state.discard_cards_from_hand(cards_for_discard)
            print("===" * 30)
            print(f"Player state after discard cards")
            print(player_state)
        else:
            print(f"Player state")
            print(player_state)

    def get_card_for_play(self, preselect_card_id: str = None) -> dict[str, dict[str, Any] | Card] | str:
        def get_card_options(card: Card, agent: Agent) -> dict[str, Any]:
            def get_opponent(card: Card, agent: Agent) -> str:
                while True:

                    opponent = agent.get_opponent(card)
                    if opponent in self.__game.get_player_names():
                        return opponent
                    else:
                        print(f"That player {opponent} doesn't exist")
                        self.__shared_memory.append(
                            {"type": LogEventType.DRAFT_PLAY_CARD_OPTION_FAIL,
                             "value": f"That player {opponent} doesn't exist"})
                        self._write_json_log({"draft_play_card_option_fail": {"fail": "That player doesn't exist",
                                                                              "value": opponent}})

            def get_action_type(card: Card, agent: Agent) -> str:
                while True:
                    action_type = agent.get_action_type(card)
                    if action_type in ("from_hand", "from_play"):
                        return action_type
                    else:
                        print("Allowable options (from_hand, from_play)")
                        self.__shared_memory.append(
                            {"type": LogEventType.DRAFT_PLAY_CARD_OPTION_FAIL,
                             "value": f"Action_type {action_type} not allowed. Allowable options (from_hand, from_play)"})
                        self._write_json_log({"draft_play_card_option_fail": {"fail": "Action_type not allowed",
                                                                              "value": action_type}})
                                                   

            def get_card_for_steal(card: Card, agent: Agent) -> str:
                while True:
                    card_name = agent.get_card_for_steal(card)
                    try:
                        Card(CardID(card_name))
                        return card_name
                    except:
                        print(f"Card {card_name} doesn't exist in the game")
                        self.__shared_memory.append(
                            {"type": LogEventType.DRAFT_PLAY_CARD_OPTION_FAIL,
                             "value": f"Card {card_name} doesn't exist in the game"})
                        self._write_json_log({"draft_play_card_option_fail": {"fail": "Card doesn't exist in the game",
                                                                              "value": card_name}})

            options = {}
            match card.card_id:
                case CardID.PANIC | CardID.HOTTIE:
                    options["opponent"] = get_opponent(card, agent)
                    options["action_type"] = get_action_type(card, agent)
                    if options["action_type"] == "from_play":
                        options["card"] = get_card_for_steal(card, agent)
                case CardID.BANG:
                    options["opponent"] = get_opponent(card, agent)
            return options

        agent = self.current_agent
        while True:
            card_id = preselect_card_id if preselect_card_id\
                                        else agent.choice_card_for_play()
            try:
                if card_id == "end":
                    return "end"
                card = Card(CardID(card_id))
                options = get_card_options(card, agent)
                return {"card": card, "options": options}
            except ValueError:
                print(f"Card {card_id} doesn't exist in the game")
                self.__shared_memory.append(
                    {"type": LogEventType.DRAFT_PLAY_CARD_FAIL,
                     "value": f"Card {card_id} doesn't exist in the game"})
                self._write_json_log({"draft_play_card_fail": {"fail": "Card doesn't exist in the game",
                                                               "value": card_id}})

    def __get_opponent_response_for_card(self, request: dict[str, Any]) -> dict[str, PlayerActionResponse]:
        def indians_response(agent: Agent) -> PlayerActionResponse:
            while True:
                response = agent.get_indians_response()
                if response in ("bang", "pass"):
                    return PlayerActionResponse(response)
                else:
                    print("Acceptable options (bang, pass)")
                    self.__shared_memory.append(
                        {"type": LogEventType.RESPONSE_FOR_CARD_FAIL,
                         "value": f"The response {response} is not acceptable. Acceptable options (bang, pass)"})
                    self._write_json_log({"response_for_card_fail": {"player": agent.name,
                                                                     "fail": "The response is not acceptable",
                                                                     "value": response}})

        def bang_response(agent: Agent) -> PlayerActionResponse:
            while True:
                response = agent.get_bang_response()
                if response in ("miss", "pass"):
                    return PlayerActionResponse(response)
                else:
                    print("Acceptable options (miss, pass)")
                    self.__shared_memory.append(
                        {"type": LogEventType.RESPONSE_FOR_CARD_FAIL,
                         "value": f"The response {response} is not acceptable. Acceptable options (miss, pass)"})
                    self._write_json_log({"response_for_card_fail": {"player": agent.name,
                                                                     "fail": "The response is not acceptable",
                                                                     "value": response}})

        def gatling_response(agent: Agent) -> PlayerActionResponse:
            while True:
                response = agent.get_gatling_response()
                if response in ("miss", "pass"):
                    return PlayerActionResponse(response)
                else:
                    print("Acceptable options (miss, pass)")
                    self.__shared_memory.append(
                        {"type": LogEventType.RESPONSE_FOR_CARD_FAIL,
                         "value": f"The response {response} is not acceptable. Acceptable options (miss, pass)"})
                    self._write_json_log({"response_for_card_fail": {"player": agent.name,
                                                                     "fail": "The response is not acceptable",
                                                                     "value": response}})

        response = {}
        opponent = request['opponent']
        player_state = self.__game.current_player_state
        assert opponent == player_state.name
        agent = self.__agents[opponent]

        print("===" * 15, f"Reaction for player: {player_state.name}", "===" * 15)
        match request['request']:
            case CardActionRequest.RESPONSE_TO_INDIANS:
                response["action"] = (indians_response(agent)
                                      if player_state.has_card(Card(CardID.BANG))
                                      else PlayerActionResponse.PASS)
            case CardActionRequest.RESPONSE_TO_BANG:
                response["action"] = (bang_response(agent)
                                      if player_state.has_card(Card(CardID.MISS))
                                      else PlayerActionResponse.PASS)
            case CardActionRequest.RESPONSE_TO_GATLING:
                response["action"] = (gatling_response(agent)
                                      if player_state.has_card(Card(CardID.MISS))
                                      else PlayerActionResponse.PASS)
       
        self.__shared_memory.append(
            {"type": LogEventType.RESPONSE_FOR_CARD,
             "value": f"Reaction for player {player_state.name} for {request['request'].value} is {response["action"].value}"})
        self._write_json_log({"response_for_card": {"user": player_state.name,
                                                    "reaction": response["action"].value}})
        return response

    def __get_cards_for_discard(self, num_discard_cards: int, player_state: Player, agent: Agent) -> list[Card]:
        cards_for_discard = []
        hand = player_state.get_state_log()["hand"]
        assert len(hand) > num_discard_cards

        hand_count = defaultdict(int)
        for card in hand:
            hand_count[card] += 1

        player_input = agent.get_card_for_discard(num_discard_cards)

        errors = []
        for card_id in player_input.split():
            try:
                card = Card(CardID(card_id))
                cards_for_discard.append(card)
            except ValueError:
                errors.append(f"Card {card_id} doesn't exist in the game")

        disc_count = defaultdict(int)
        for card in cards_for_discard:
            disc_count[card] += 1
        for k, v in disc_count.items():
            if hand_count[k] < v:
                if hand_count[k] == 0:
                    errors.append(f"Card {k.card_id.value} is not in the player's hand")
                else:
                    errors.append(f"Cards {k.card_id.value} is less than {v}. You can't drop that many cards")

        if errors:
            self._write_json_log({"cards_for_discard_errors": errors})
            raise Exception(errors)
        return cards_for_discard
