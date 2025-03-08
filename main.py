from Card import CardID, Card
from Config import Config
from Game import Game

if __name__ == '__main__':
    config = Config()
    config.init('config.yaml')
    game = Game()

    generator_play_card = game.play_card(Card(CardID.INDIANS))
    try:
        request = next(generator_play_card)
        response = {"action": "play_bang"}
        request = generator_play_card.send(response)
        response = {"action": "play_bang1"}
        request = generator_play_card.send(response)
        response = {"action": "play_bang"}
        request = generator_play_card.send(response)
    except StopIteration as e:
        pass

