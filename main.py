from pprint import pprint
from collections import defaultdict
from typing import Any

from Card import CardID, Card, CardActionRequest
from Config import Config
from Game import Game, GameResult
from Player import Player, PlayerActionResponse


def print_game_state(game: Game):
    print("===" * 15, "All player", "===" * 15)
    pprint(game.players_game_state)
    print("===" * 15, "Current player", "===" * 15)
    print(game.current_player_state)


def get_cards_for_discard(need_to_discard: int, player_state: Player) -> list[Card]:
    cards_for_discard = []
    hand = player_state.get_state_log()["hand"]
    assert len(hand) > need_to_discard

    hand_count = defaultdict(int)
    for card in hand:
        hand_count[card] += 1

    user_input = input(f"Введите {need_to_discard} названий карт через пробел: ").strip()
    errors = []
    for card_id in user_input.split():
        try:
            card = Card(CardID(card_id))
            cards_for_discard.append(card)
        except ValueError:
            errors.append(f"Карты {card_id} не существует в правилах")

    disc_count = defaultdict(int)
    for card in cards_for_discard:
        disc_count[card] += 1
    for k, v in disc_count.items():
        if hand_count[k] < v:
            if hand_count[k] == 0:
                errors.append(f"карты {k.card_id.value} нет у игрока в руке")
            else:
                errors.append(f"карт {k.card_id.value} меньше чем {v}. Нельзя сбросить столько карт")

    if errors:
        raise Exception(errors)
    return cards_for_discard


def react_to_discard_error(error: str):
    #TODO дописать
    print(error)


def get_card_for_play(game: Game) -> dict[str, dict[str, Any] | Card] | str:
    def get_card_options(card: Card, game: Game) -> dict[str, Any]:
        def get_opponent(game: Game) -> str:
            while True:
                opponent = input(f"Введите имя оппонента: ").strip().lower()
                if opponent in game.get_player_names():
                    return opponent
                else:
                    print("Некорректное имя оппонента")

        def get_action_type() -> str:
            while True:
                action_type = input(f"Введите откуда должна быть карта (from_hand, from_play): ").strip().lower()
                if action_type in ("from_hand", "from_play"):
                    return action_type
                else:
                    print("Допустимые варианты (from_hand, from_play)")

        def get_card_for_steal() -> str:
            while True:
                card_name = input(f"Введите название карты: ").strip().lower()
                try:
                    Card(CardID(card_name))
                    return card_name
                except:
                    raise Exception("такой карты в игре не существует")

        options = {}
        match card.card_id:
            case CardID.PANIC | CardID.HOTTIE:
                options["opponent"] = get_opponent(game)
                options["action_type"] = get_action_type()
                if options["action_type"] == "from_play":
                    options["card"] = get_card_for_steal()
            case CardID.BANG:
                options["opponent"] = get_opponent(game)
        return options

    while True:
        card_id = input(f"Введите название карты чтобы ее сыграть или end для завершения хода: ").strip()
        try:
            if card_id == "end":
                return "end"
            card = Card(CardID(card_id))
            options = get_card_options(card, game)
            return {"card": card, "options": options}
        except ValueError:
            print(f"Карты {card_id} не существует в правилах")


def discard_cards(player_state: Player):
    need_to_discard = player_state.need_to_discard()
    if need_to_discard > 0:
        print(f"Need to discard {need_to_discard} cards")
        print(f"Please make a choice")
        print(player_state)

        while True:
            try:
                cards_for_discard = get_cards_for_discard(need_to_discard, player_state)
                break
            except Exception as e:
                react_to_discard_error(str(e))

        player_state.discard_cards_from_hand(cards_for_discard)
        print("===" * 30)
        print(f"Player state after discard cards")
        print(player_state)
    else:
        print(f"Player state")
        print(player_state)


def make_opponent_response_for_card(request: dict[str, Any], game: Game) -> dict[str, PlayerActionResponse]:
    def indians_response() -> PlayerActionResponse:
        while True:
            response = input(f"Выберите действие в ответ на карту индейцев (bang, pass): ").strip().lower()
            if response in ("bang", "pass"):
                    return PlayerActionResponse(response)
            else:
                print("Допустимые варианты (bang, pass)")

    def bang_response() -> PlayerActionResponse:
        while True:
            response = input(f"Выберите действие в ответ на карту bang (miss, pass): ").strip().lower()
            if response in ("miss", "pass"):
                    return PlayerActionResponse(response)
            else:
                print("Допустимые варианты (miss, pass)")

    def gatling_response() -> PlayerActionResponse:
        while True:
            response = input(f"Выберите действие в ответ на карту гатлинг (miss, pass): ").strip().lower()
            if response in ("miss", "pass"):
                    return PlayerActionResponse(response)
            else:
                print("Допустимые варианты (miss, pass)")

    response = {}
    opponent = request['opponent']
    player_state = game.current_player_state
    assert opponent == player_state.name
    print("===" * 15, f"Reaction for player: {player_state.name}", "===" * 15)
    match request['request']:
        case CardActionRequest.RESPONSE_TO_INDIANS:
            response["action"] = (indians_response()
                                    if player_state.has_card(Card(CardID.BANG))
                                    else PlayerActionResponse.PASS)
        case CardActionRequest.RESPONSE_TO_BANG:
            response["action"] = (bang_response()
                                    if player_state.has_card(Card(CardID.MISS))
                                    else PlayerActionResponse.PASS)
        case CardActionRequest.RESPONSE_TO_GATLING:
            response["action"] = (gatling_response()
                                    if player_state.has_card(Card(CardID.MISS))
                                    else PlayerActionResponse.PASS)
    return response


def play_cards(game: Game) -> GameResult:
    while True:
        card = get_card_for_play(game)
        if card == "end":
            break
        card, options = card["card"], card["options"]
        generator_play_card = game.play_card(card, options=options)
        try:
            request = next(generator_play_card)
            while True:
                response = make_opponent_response_for_card(request, game)
                request = generator_play_card.send(response)
        except StopIteration as e:
            print("Результат хода")
            pprint(e)
            if e.value["game_status"] != GameResult.NO_WINNERS:
                return e["game_status"]
        except Exception as e:
            pprint(e)
        print_game_state(game)
    return GameResult.NO_WINNERS

def play_game(game: Game):
    while True:
        player_state = game.current_player_state
        print("===" * 15, f"Turn player: {player_state.name}", "===" * 15)
        game.start_of_turn()
        print_game_state(game)
        game_result = play_cards(game)
        if game_result != GameResult.NO_WINNERS:
            print("===" * 15, "END OF GAME", "===" * 15)
            print(game_result.name)
        discard_cards(player_state)
        game.end_of_turn()


if __name__ == '__main__':
    config = Config()
    config.init('config.yaml')
    game = Game()

    play_game(game)



