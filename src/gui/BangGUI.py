import json
from typing import Any

import dearpygui.dearpygui as dpg

from src.agent.UserAgent import UserAgent
from src.emulator.Emulator import GameEmulator
from src.game.Player import Player
from src.game.Utils import GameEncoder


class BangGUI:
    def __init__(self, config_path: str):
        dpg.create_context()
        self.__create_layouts()
        self.emulator = GameEmulator(config_path,
                                     self.current_player_state_render,
                                     self.players_game_state_render,
                                     use_gui=True)
        user_data = {"card_id": "end",
                     "emulator": self.emulator}
        dpg.set_item_user_data("end_turn", user_data)

        self.emulator.gui_game()

        dpg.create_viewport(title="Bang GUI", width=800, height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        dpg.start_dearpygui()
        dpg.destroy_context()

    @staticmethod
    def card_play_callback(sender, app_data, user_data):
        card_id, emulator = user_data.values()
        card = emulator.get_card_for_play(preselect_card_id=card_id)
        result = emulator.play_card(card)
        emulator.draw_state()
        if result["end_of_turn"]:
            emulator.end_of_turn()
            agent = emulator.current_agent
            if isinstance(agent, UserAgent):
                emulator.start_of_turn()
            else:
                emulator.auto_play()

    def current_player_state_render(self, player: Player):
        player = player.get_state_log()
        player_info = json.dumps(({"name": player["name"],
                           "role": player["role"],
                           "max_hp": player["max_hp"],
                           "cur_hp": player["cur_hp"],
                           "weapon": player["weapon"],
                           "weapon_range": player["weapon_range"]}),
                                 indent=4,
                                 ensure_ascii=False,
                                 cls=GameEncoder)
        dpg.delete_item("cur_player_info", children_only=True)
        dpg.add_text("Current player info", parent="cur_player_info")
        dpg.add_text(player_info, parent="cur_player_info")

        player_cards = player["hand"]
        dpg.delete_item("cur_player_cards", children_only=True)
        dpg.add_text("Current player cards", parent="cur_player_cards")
        for card in player_cards:
            with dpg.group(horizontal=False, parent="cur_player_cards"):
                dpg.add_text(str(card))
                dpg.add_button(label="Play",
                               callback=BangGUI.card_play_callback,
                               user_data={"card_id": card.card_id.value,
                                          "emulator": self.emulator})

        player_effects = json.dumps(player["effects"], indent=4, ensure_ascii=False, cls=GameEncoder)
        dpg.delete_item("cur_player_effects", children_only=True)
        dpg.add_text("Current player effects", parent="cur_player_effects")
        dpg.add_text(player_effects, parent="cur_player_effects")

    @staticmethod
    def players_game_state_render(players_data: dict[str, Any]):
        players = players_data["players"]
        dpg.delete_item("players", children_only=True)
        with dpg.tab_bar(parent="players"):
            for name, player_info in players.items():
                player_info = json.dumps(player_info, indent=4, ensure_ascii=False, cls=GameEncoder)
                with dpg.tab(label=name):
                    dpg.add_text(player_info)

    def __create_layouts(self):
        with dpg.window(label="primary_window", tag="primary_window", width=1200, height=800):
            with dpg.table(header_row=False):
                dpg.add_table_column(init_width_or_weight=400, width_fixed=True)
                dpg.add_table_column(init_width_or_weight=1, width_fixed=False)
                dpg.add_table_column(init_width_or_weight=400, width_fixed=True)

                with dpg.table_row():
                    with dpg.child_window(autosize_y=True, tag="agent_log", horizontal_scrollbar=True):
                        dpg.add_text("Agent log")

                    with dpg.child_window(autosize_y=True):
                        with dpg.group(horizontal=False):
                            with dpg.child_window(height=400, tag="players"):
                               pass
                            with dpg.child_window(autosize_y=True):
                                with dpg.group(horizontal=True, tag="cur_player"):
                                    with dpg.table(header_row=False):
                                        dpg.add_table_column(init_width_or_weight=1, width_fixed=False)
                                        dpg.add_table_column(init_width_or_weight=1, width_fixed=False)
                                        dpg.add_table_column(init_width_or_weight=1, width_fixed=False)

                                        with dpg.table_row():
                                            with dpg.child_window(autosize_y=True):
                                                with dpg.group(horizontal=False, tag="cur_player_info"):
                                                    pass
                                            with dpg.child_window(autosize_y=True):
                                                with dpg.group(horizontal=False, tag="cur_player_cards"):
                                                    pass
                                            with dpg.child_window(autosize_y=True):
                                                with dpg.group(horizontal=False):
                                                    with dpg.group(horizontal=False, tag="cur_player_effects"):
                                                        pass
                                                    dpg.add_button(label="End turn",
                                                                   tag="end_turn",
                                                                   callback=BangGUI.card_play_callback)

                    with dpg.child_window(autosize_y=True, tag="game_log", horizontal_scrollbar=True):
                        dpg.add_text("Shared memory")

