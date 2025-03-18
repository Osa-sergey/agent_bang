from src.emulator.Emulator import GameEmulator

if __name__ == '__main__':
    emulator = GameEmulator('config/config.yaml')
    emulator.play_game()


# from src.gui.BangGUI import BangGUI
#
# if __name__ == '__main__':
#     gui = BangGUI('config/config.yaml')
#


