import argparse

from src.emulator.Emulator import GameEmulator

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Bang emulator")
    parser.add_argument("config", type=str, help="config.yaml")

    args = parser.parse_args()

    print(f"Config name: {args.config}")
    emulator = GameEmulator(f'config/{args.config}')
    emulator.play_game()


# from src.gui.BangGUI import BangGUI
#
# if __name__ == '__main__':
#     gui = BangGUI('config/config.yaml')



