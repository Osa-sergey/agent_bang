import json
from typing import Any, Union, Dict, Sequence
import re

from openai import OpenAI

from src.agent.Agent import Agent
from src.emulator.Emulator import LogEventType
from src.emulator.LoggedList import LoggedList
from src.game.Card import Card
from src.game.Game import Game
from src.game.Player import Player
from src.game.Utils import GameEncoder


class BaseMultiLlmAgent(Agent):
    def __init__(self, agent_name: str,
                 config: dict[str, Any],
                 player: Player,
                 game: Game,
                 shared_memory: LoggedList):
        self.sleep_delay = 0
        self.client = OpenAI(
            api_key="",
            base_url="https://api.deepseek.com"
        )
        player_prompt = """
You're a player of the board game beng.
Bang! is a Western-style card game for 4-7 players. Players are assigned roles with unique objectives:
Role win strategy:
Sheriff: destroy all Bandits and the Renegade.
Bandits: kill the Sheriff.
Helpers: protect the Sheriff.
Renegade: to be the last survivor. Firstly kill all bandits and next kill sheriff and helpers.
For 4 players roles [Sheriff, Renegade, Bandits, Bandits]
For 5 players roles [Sheriff, Renegade, Bandits, Bandits, Helper]
For 6 players roles [Sheriff, Renegade, Bandits, Bandits, Bandits, Helper]
For 7 players roles [Sheriff, Renegade, Bandits, Bandits, Bandits, Helper, Helper]
Preparation
Players get roles (hidden, except for the Sheriff).
Each player receives an amount of health (ammo) equal to the character's health and starting cards (based on the number of health).
Game progress
The game proceeds clockwise, starting with the Sheriff. The turn is divided into three phases:

Set: The player draws 2 cards from the deck.
Draw: The player draws cards. Limit: No more than one “BANG!” card per turn.
Discard: If there are more cards in hand than your current health, the player discards the extra cards.

Cards and their effects
BANG: Deals 1 damage to the selected player within firing range.
MISS: Cancels the effect of “BANG!” or another attack.
BEER: Restores 1 health (does not work if there are 2 players left).
MUSTANG: Increases the distance to a player by 1.
SCOPE: Reduces the distance to other players by 1.
SALOON: Restores 1 health to all players.
GATLING: Deals 1 damage to all opponents.
INDIANS: All opponents must play “BANG!” or lose 1 health.
STAGECOACH: Player draws 2 cards.
FARGO: Player draws 3 cards.
PANIC: Pick up a card in your hand from a player at a distance of 1 (it can be a random card from opponent hand or a card of your choice from the game).
Do not forget that scope and mustang change the distance between players, but weapons do not.
HOTTIE: Force any player regardless of distance to discard a card. (it can be a random card from opponent hand or a card of your choice from the game).
Weapons:
VOLKANIC: Allows for multiple “BANG!” plays per turn.
SCOFIELD: Firing range is 2.
REMINGTON: Firing range - 3.
CARBINE: Firing range - 4.
WINCHESTER: Range - 5.
Elimination and Completion
A player is eliminated if he loses all his health.
A Sheriff who accidentally kills a Helper discards all cards.
The Bandit's killer gets 3 cards as a reward.
Victory Conditions:
Sheriff and Helpers win if all Bandits and Renegade are destroyed.
The Bandits win if the Sheriff is dead.
Renegade wins if he is the last one left.
Important rules
Only one “BANG!” card per turn (except VOLKANIC).
Weapons change the range of fire, but not the distance between players.
“BEER is useless in a two player game.
        """
        log_analyzer_prompt = """
You're a log analyzer. You help in figuring out the events that happen in the game. Take note of important events and summarize them.
Log structure
The log is presented in JSON format. Each record contains:
'type': Object with fields:
'name': Event name (string).
'value': Numeric code of the event.
'value': Event data (string, number or dictionary).
Types of log entries
TURN_PLAYER
Description: Start of the player's turn.
'value': Player name (string).
Example: {“type”: {“name”: “TURN_PLAYER”, “value”: “1}, ‘value’: ‘serg’}
PLAYERS_GAME_STATE
Description: Current game state.
'value': A dictionary with fields:
'players': List of players with their roles, health and cards.
'players_order': The order of the turn.
'current_player': The current player.
Example: { 'type': { “name”: “PLAYERS_GAME_STATE”, “value”: 2}, “value”: { “players”: { “serg”: { “health”: 4}, “igor”: { “health”: 3}}, “players_order”: [ “serg”, “igor” ], “current_player”: “serg"}}
PLAY_CARD
Description: The player has played a card or completed a turn.
'value' value:
'end' - end of turn.
Dictionary with 'card' (card ID and type) and 'options' (target or parameters).
Example: {“type”: { “name”: “PLAY_CARD”, “value”: 3}, “value”: { “card”: { “card_id”: “bang”, “card_type”: 0}, “options”: { “opponent”: “igor"}}}
RESPONSE_FOR_CARD
Description: Player's response to the card (e.g. “MISS!” to “BANG!”).
'value': A string describing the response.
Example: {“type”: { “name”: “RESPONSE_FOR_CARD”, “value”: 4}, “value”: “Reaction for player igor for response to bang is miss”}
STEP_RESULT
Description: Result of an action or game step.
'value': Dictionary with:
'outliers': The eliminated players and their roles.
'game_status': The status of the game (win or continue).
Example: { “type”: { “name”: “STEP_RESULT”, “value”: 5}, “value”: { “outliers”: { “anna”: { “name”: “BANDIT”, “value”: “bandit”}}, “game_status”: { “name”: “NO_WINNERS”, “value”: 0}}}}
NEED_DISCARD_CARDS
Description: The player needs to discard extra cards.
'value': A message about the number of cards to discard.
Example: {“type”: { “name”: “NEED_DISCARD_CARDS”, “value”: 6}, “value”: “Player serg need to discard 1 cards”}
STEP_ERROR
Description: Error during action.
'value': The cause of the error (string).
Example: { “type”: {“name”: “STEP_ERROR”, “value”: 7}, “value”: “The player is at maximum health, the beer has no effect”}

Log Analysis
Moves: Track via TURN_PLAYER.
Actions: Analyze via PLAY_CARD and RESPONSE_FOR_CARD.
Status: Analyze via PLAYERS_GAME_STATE.
Results: Take into account via STEP_RESULT.
Errors: Pay attention to STEP_ERROR.

Examples of log analysis with explanations
Example 1: A player played “BANG!” and received a “MISS!”
Log:
{ “type”: { “name”: “TURN_PLAYER”, “value”: 1}, “value”: “serg”}
{ “type”: { “name”: “PLAY_CARD”, “value”: 3}, “value”: { “card”: { “card_id”: “bang”, “card_type”: 0}, “options”: { “opponent”: “igor"}}}
{ “type”: { “name”: “RESPONSE_FOR_CARD”, “value”: 4}, “value”: “Reaction for player igor for response to bang is miss”}}
{ “type”: { “name”: “PLAYERS_GAME_STATE”, “value”: 2}, “value”: { “players”: { “serg”: { “health”: 4}, “igor”: { “health”: 3}}}}
Explanation: Serg started a move and played “BANG!” against Igor. Igor responded with “MISS!”, preventing damage. The game state shows that Igor's health has not changed (3 health left).
Example 2: Ending a turn with the need to reset
Log:
{ “type”: { “name”: “PLAY_CARD”, “value”: 3}, “value”: “end”}
{ “type”: { “name”: “NEED_DISCARD_CARDS”, “value”: 6}, “value”: “Player serg needs to discard 1 cards”}
Explanation: Serg has completed his turn (“end”), but he has more cards in hand than health. He needs to discard 1 card.
Example 3: Error when using “BEER”
Log:
{ “type”: { “name”: “PLAY_CARD”, “value”: 3}, “value”: { “card”: { “card_id”: “beer”, “card_type”: 1}, “options”: {}}}
{ “type”: {“name”: “STEP_ERROR”, “value”: 7}, “value”: “The player is at maximum health, the beer has no effect”}
Explanation: The player attempted to play “BEER”, but his health is at maximum health. The game rejected the action with an error.
Example 4: Dropping a player
Log:
{ “type”: { “name”: “STEP_RESULT”, “value”: 5}, “value”: { “outliers”: { “anna”: { “name”: “BANDIT”, “value”: “bandit”}}, “game_status”: { “name”: “NO_WINNERS”, “value”: 0}}}}
Clarification: Anna (Bandit) has lost her last health and is eliminated. The game continues as the winner has not yet been determined.
Example 5: Sheriff's Victory
Log:
{ “type”: { “name”: “STEP_RESULT”, “value”: 5}, “value”: { “outliers”: { “andy”: { “name”: “RENEGADE”, “value”: “renegade”}}, “game_status”: {“name”: “SHERIFF_WIN”, “value”: “1” }}}}
Clarification: Andy (Renegade) is out. Since all Bandits and Renegade are eliminated, the Sheriff and Helpers win.
              """
        cooperator_prompt = """
You are the communication agent.
Your job is to manage communication between players to either promote cooperation if it benefits your role, or to confuse other players so they don't understand your role. 
Your communication should be strategic, concise, and tailored to the current situation in the game.
Game Context
Roles and Goals:
Sheriff: eliminate all Bandits and the Renegade.
Helpers: protect the Sheriff and assist him.
Bandits: kill the Sheriff.
Renegade: to be the last survivor.
Mechanics:
Players play cards (attacks, defenses, health regeneration) on their turns.
Role stealth is a key advantage, especially for Bandits and Renegade.
Communication: Players can exchange messages to coordinate actions or to mislead.

Task
Based on the input, generate a message to other players that:

Promotes cooperation if it benefits your role (e.g., coordinating attacks or defense with allies).
Confuses other players to hide your role, if necessary.
Takes into account the players' current situation and psychology (e.g. their possible suspicions or goals).
Is concise but informative, and does not reveal your role directly (if not desired).

Additional guidelines
If your role requires cooperation (e.g., Helper or Bandit), suggest cooperative actions that will strengthen your team.
If your role requires stealth (e.g. Renegade or Bandit), use messages to distract or create false suspicion.
Consider your action history: if a player frequently attacks the Sheriff, he can be accused of being a Bandit.
Avoid making direct statements about your role if it could hurt you.
Adapt to changes: if the situation changes (e.g. a player reveals his role), adjust messages.

Examples
If you are a Helper:
Message: “Player C has attacked the Sheriff, let's focus our attacks on him.”
Goal: Promote cooperation with the Sheriff and other Helpers to eliminate the threat.
If you are a Bandit:
Message: “Player D looks suspicious, he may be a Renegade.”
Goal: Confuse players, divert attention away from yourself and direct attacks at another.
If you are a Renegade:
Message: “I'll help the Sheriff if he protects me from attacks.”
Purpose: To mislead to temporarily cooperate with the Sheriff by hiding your intentions.
        """
        role_finder_prompt = """
Your job is to identify the roles of other players (Helpers, Bandits, Renegade) based on their actions, cards used, and interactions.
The roles, except for the Sheriff, are hidden, and your goal is to identify them as accurately as possible to help the player make strategic decisions.

Task:

Based on the data provided, draw conclusions about the likely roles of the players. Your conclusions should:

Be based on an analysis of actions (e.g., attacking or defending the Sheriff).
Take into account the use of cards and their strategic importance.
Take into account player communication (e.g., who is blaming or supporting whom).
Be presented as probabilities or assumptions (e.g. “most likely Bandit”, “possibly Deputy”).
Be updated as new data becomes available.

Additional Guidelines:
Players may act unconventionally to mislead others (e.g., a Bandit may temporarily not attack the Sheriff).
Pay attention to passive actions (e.g., not attacking the Sheriff may indicate a Helper).
Frequent defense of the Sheriff is a sign of a Helper, attacking everyone is a hint of a Renegade.
Update your conclusions with each new turn, taking into account changes in player behavior.
Purpose: 
To provide the player with accurate and educated guesses about the roles of opponents so that he can effectively choose targets for attack, defense, or cooperation.
                """
        summarizer_prompt = """
Summarize the information received and answer the question as correctly as possible. Use your previous thoughts for this purpose.
        """
        self.agents = {"player": {"system_prompt": player_prompt},
                       "cooperator": {"system_prompt": cooperator_prompt},
                       "role_finder": {"system_prompt": role_finder_prompt},
                       "log_analyzer": {"system_prompt": log_analyzer_prompt},
                       "summarizer": {"system_prompt": summarizer_prompt},}

        self.chat_context = []
        self.errors = 0
        super().__init__(agent_name, config, player, game, shared_memory)



    def __get_player_current_state(self) -> str:
        state = self.player.get_state_log()
        text_state = json.dumps(state, cls=GameEncoder)
        return text_state

    def get_last_memories(self) -> str:
        last_memories = json.dumps(self.shared_memory[self.last_shared_memory_index: ], cls=GameEncoder)
        self.last_shared_memory_index = len(self.shared_memory)
        return last_memories

    def ask_llm(self, prompt: str, agents: list, state: Union[str, None] = None) -> Union[Dict[str, Any], str]:
        print("State: ", state, "Prompt:", prompt)
        if state:
            self.local_memory.append({"content": state})
            self.chat_context.append({"role": "user", "content": state})
        else:
            self.local_memory.append({"content": prompt})
            self.chat_context.append({"role": "user", "content": prompt})
        answer = ""
        for i, agent in enumerate(agents):
            system_prompt = [{"role": "system", "content": self.agents[agent]['system_prompt']}]
            if len(self.chat_context) > 40:
                self.chat_context = self.chat_context[-20:]

            if state and i == len(agents) - 1:
                self.local_memory.append({"content": prompt})
                self.chat_context.append({"role": "user", "content": prompt})
            response = self.client.chat.completions.create(
                model="deepseek-chat",  # deepseek-reasoner или deepseek-chat
                messages=system_prompt + self.chat_context,
                temperature=0.7,
                max_tokens=700,
                stream=False
            )

            answer = response.choices[0].message.content
            print(f"Agent name: {agent}")
            print("Raw answer:", answer)

            if i != len(agents) - 1:
                self.local_memory.append({"content": answer, "agent": agent})
            self.chat_context.append({"role": "assistant", "content": answer})

        json_pattern = r'\{(?:[^{}]|\{[^{}]*\})*\}'
        match = re.search(json_pattern, answer)

        if match:
            json_str = match.group(0)
            try:
                json_object = json.loads(json_str)
                print("Extracted JSON object:", json_object)
                if  json_object.get("users_role"):
                    self.local_memory.append({"content": answer, "users_role": json_object.get("users_role")})
                else:
                    self.local_memory.append({"content": answer})
                if json_object.get("say_to_all"):
                    self.shared_memory.append({"type": LogEventType.PLAYER_SAY,
                                               "value": {"player": self.name, "say": json_object.get("say_to_all")}})
                return json_object
            except json.JSONDecodeError as e:
                self.local_memory.append({"content": answer})
                print(f"JSON parsing error: {e}")
                return answer
        else:
            self.local_memory.append({"content": answer})
            print("No JSON object found in the response")
            return answer


    def choice_card_for_play(self) -> str:
        last_memories = self.get_last_memories()
        cur_state = self.__get_player_current_state()
        state = f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
"""
        prompt = f"""
If you can cooperate with somthing, do this for your win. Use your knowledge of other players' roles to do this.
Carefully analyze what your opponents say in order to coordinate your actions with your friends, or on the contrary,
to prevent your opponents from achieving their goals. Also to do this, analyze the state of your friends and help them if possible,
for example, by removing effect cards from a common enemy or supporting an friend's attack.
Be careful, your assumptions about your friends may be false. Take special care to keep your role a secret from your enemies for as long as possible  

Choose name of a card to play or end to end a turn.
To do this, consider the distance to the player, the effect of the card,
and your assumptions about the player's role and how it relates to your win condition.  
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which card to play now>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the name of a card in lowercase to play or end to end a turn>
  "users_role": <Based on your reasoning, generate a list of assumed role for each opponent. 
  Give the answer in the form of a dictionary in which the key is the opponent's name and the value is the expected role.
  Try to understand what each opponent's role is. Valid options [Sheriff, Renegade, Bandits, Helper]>
}
                """
        return self.ask_llm(prompt, ["log_analyzer", "role_finder", "player", "cooperator", "summarizer"], state)['result']

    def get_opponent(self, card: Card) -> str:
        opponents = [player for player in self.game.get_player_names() if player != self.name]
        prompt = f"""
For card: {card}
and opponents: {opponents}
Choose the best opponent to apply this card to. To do this,
consider the distance to the player, the effect of the card,
and your assumptions about the player's role and how it relates to your win condition  
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which opponent to choose now>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the name of opponent>
}
                """
        return self.ask_llm(prompt, ["player", "summarizer"])['result']

    def get_action_type(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        prompt = f"""
For card: {card}
and opponent: {opponent}
Choose the best action_type from to options (from_hand, from_play) to apply this card to. 
Note that in case from_hand you can take a random card from your opponent's hand,
and in case from_play you take away a strong card from the opponent game, such as a long-range weapon or the effect of a Mustang or scope. 
Use your assumptions about the player's role and how it relates to your win condition  
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which action_type to choose now>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the name of action_type from to options (from_hand, from_play)>
}
                """
        return self.ask_llm(prompt, ["player", "summarizer"])['result']

    def get_card_for_steal(self, card: Card, options: dict) -> str:
        opponent = options["opponent"]
        action_type = options["action_type"]
        prompt = f"""
For card: {card}
and opponent: {opponent}
and action_type: {action_type}
Choose the best card to take it away from your opponent from the game. 
Pay special attention to weapons, if they have a high firing radius,
or to effect cards such as Mustang and Sight to weaken your opponent as much as possible
and deprive him of the ability to attack or defend himself.
Reply in JSON format of the following structure:
""" + """
{
 “your_reflection": <Your thoughts on which card to get from opponent>,
 "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
 “result": <Enter the name of card in lowercase to get from opponent>
}
               """
        return self.ask_llm(prompt, ["player", "summarizer"])['result']

    def get_indians_response(self) -> str:
        last_memories = self.get_last_memories()
        cur_state = self.__get_player_current_state()
        state = f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
            """
        prompt = f"""
Now you need to respond to the Indian card played by your opponent. 
You have two options (bang, pass) In the first case you won't take damage, but you will drop a card bang,
in the second case you will lose a unit of health. Make your choice based on your current health. 
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which option to choose>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the respond from to options (bang, pass)>
}
                """
        return self.ask_llm(prompt, ["log_analyzer", "player", "cooperator", "summarizer"], state)['result']

    def get_bang_response(self) -> str:
        last_memories = self.get_last_memories()
        cur_state = self.__get_player_current_state()
        state = f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
        """
        prompt = f"""
Now you need to respond to the bang card played by your opponent. 
You have two options (miss, pass) In the first case you won't take damage, but you will drop a card miss,
in the second case you will lose a unit of health. Make your choice based on your current health. 
Make sure you take into account who's shooting at you. 
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which option to choose>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the respond from to options (miss, pass)>
}
                """
        return self.ask_llm(prompt, ["log_analyzer", "player", "cooperator", "summarizer"], state)['result']

    def get_gatling_response(self) -> str:
        last_memories = self.get_last_memories()
        cur_state = self.__get_player_current_state()
        state = f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
        """
        prompt = f"""
Now you need to respond to the gatling card played by your opponent. 
You have two options (miss, pass) In the first case you won't take damage, but you will drop a card miss,
in the second case you will lose a unit of health. Make your choice based on your current health. 
Make sure you take into account who's shooting at you. 
Reply in JSON format of the following structure:
""" + """
{
  “your_reflection": <Your thoughts on which option to choose>,
  "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
   team up with someone to win the game. If there is nothing to say, do not add this field>
  “result": <Enter the respond from to options (miss, pass)>
}
                """
        return self.ask_llm(prompt, ["player", "summarizer"], state)['result']

    def get_card_for_discard(self, num_cards: int) -> str:
        if self.errors < 3:
            cur_state = self.__get_player_current_state()
            prompt = f"""
    Your current cards and other parameters {cur_state}.
    Now you need to choose which cards from your hand to discard.
    The total number of cards to be discarded is {num_cards}.
    Choose cards according to their value, cards of effects, weapons, and extra cards are better left
    and not sent to discarding.
    Your answer should consist of a string of card names separated by a space. 
    Make sure that you actually have such cards in the right number and that the total number of cards
    to be discarded corresponds to {num_cards}.  
    Reply in JSON format of the following structure:
    """ + """
    {
      “your_reflection": <Your thoughts on which cards to choose for discard>,
      "say_to_all": <What you have to say for all players. You can use this text to confuse other players or to
        team up with someone to win the game. If there is nothing to say, do not add this field>
      “result": <Enter """ + str(num_cards) + """ of the card names, separated by spaces>
    }
    example of output:
    {
        "your_reflection": "If I need to discard 2 cards and in my hand [bang, miss, fargo, panic] I need to chose less useful for me"
        “result": "bang miss"
    }
                    """
            return self.ask_llm(prompt, ["player", "summarizer"])['result']
        else:
            discarded = []
            for i in range(num_cards):
                discarded.append(self.player_hand[i].card_id.value)
            return " ".join(discarded)

    def react_to_discard_error(self, errors: str):
        cur_state = self.__get_player_current_state()
        prompt = f"""
Your current cards and other parameters {cur_state}.
Your last answer in which you had to choose a list of cards to discard from your hand was incorrect.
Look at the list of errors and based on it think about what exactly you did wrong. Errors: {errors}
Keep in mind that the correct answer is a json structure with a result field in which the list of cards
to be discarded is listed in a space separated line
Look carefully at the mistake you made and think about how you could
have corrected your answer. 
               """
        self.ask_llm(prompt, ["player", "summarizer"])
        print("ERROR ON DISCARD")
        self.errors += 1
