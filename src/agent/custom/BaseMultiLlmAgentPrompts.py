class BaseMultiLlmAgentPrompts:
    player_prompt = """
**Task**
Analyze the game "Bang!" to understand its rules, player roles, card effects, and victory conditions.

---

**Game Overview**

"Bang!" is a Western-style card game designed for 4-7 players.
Players are assigned roles with unique objectives:
**Sheriff**: Eliminate all Bandits and the Renegade.
**Bandits**: Kill the Sheriff.
**Helpers** (Deputies): Protect the Sheriff.
**Renegade**: Be the last player alive.

For a 4-player game, the roles are: Sheriff, Renegade, Bandit, Bandit.
For a 5-player game, the roles are: Sheriff, Helper, Renegade, Bandit, Bandit.

---

**Preparation**

Players receive roles (hidden, except for the Sheriff) and character cards.
Each player starts with health (ammo) equal to their character’s health and draws starting cards based on that health value.

---

**Game Progression**

The game proceeds clockwise, starting with the Sheriff.
Each turn consists of three phases:
1. **Set**: Draw 2 cards from the deck.
2. **Draw**: Play cards from your hand (limit: one "BANG!" card per turn unless modified by a weapon like VOLKANIC).
3. **Discard**: Discard excess cards if your hand size exceeds your current health.

---

**Card Effects**
- **MUSTANG**: Increases your distance from other players by 1.
- **SCOPE**: Reduces your distance to other players by 1.

**Card Actions**
- **BANG**: Deals 1 damage to a player within firing range.
- **MISS**: Cancels a "**BANG**" or similar attack.
- **BEER**: Restores 1 health (ineffective when only 2 players remain).
- **SALOON**: Restores 1 health to all players.
- **GATLING**: Deals 1 damage to all opponents.
- **INDIANS**: All opponents must play a "BANG!" or lose 1 health.
- **STAGECOACH**: Draw 2 cards.
- **FARGO**: Draw 3 cards.
- **PANIC**: Take a card from a player at distance 1 (random or chosen).
- **HOTTIE**: Force any player to discard a card (random or chosen), regardless of distance.

**Weapons**
- **VOLKANIC**: Allows multiple "BANG!" cards to be played per turn.
- **SCOFIELD**: Firing range of 2.
- **REMINGTON**: Firing range of 3.
- **CARBINE**: Firing range of 4.
- **WINCHESTER**: Firing range of 5.

---

Note: Weapons affect firing range, not the distance between players, which is modified by cards like **MUSTANG** and **SCOPE**.

---

**Elimination and Completion**
- A player is eliminated when they lose all health.
- If the Sheriff accidentally kills a Deputy, the Sheriff discards all their cards.
- Killing a Bandit rewards the killer with 3 cards from the deck.

---

**Victory Conditions**

**Sheriff and Helpers**: Win if all Bandits and the Renegade are eliminated.
**Bandits**: Win if the Sheriff is killed.
**Renegade**: Wins by being the last player alive.

---

**Important Rules**
- Only one "BANG!" card can be played per turn (except with VOLKANIC).
- Weapons modify firing range, not player distance.
- "BEER" has no effect in a two-player scenario.

**Analysis Guidelines**

**Examine** how role objectives shape player strategies and interactions.
**Track card plays** and their impact on health, distance, and game state.
**Monitor eliminations** to assess progress toward victory conditions.
**Evaluate** how card combinations and roles drive the game’s outcome.

---

**Your Task**

- Summarize the rules and mechanics of "Bang!".
- Explain key interactions between cards, weapons, and roles.
- Analyze how the game progresses toward victory based on player actions and eliminations.

---

**Response Format**

- Provide a concise summary of the game’s rules and mechanics.
- Detail critical card effects, weapon impacts, and role-based strategies.
- Describe potential game outcomes based on the interplay of rules and player decisions.
"""
    log_analyzer_prompt = """
**Task**
Analyze a game log provided in JSON format to understand the sequence of events, player actions, and game outcomes.

--- 

**Log Structure**
- Each log entry is a JSON object with:
  - 'type': An object containing 'name' (event name) and 'value' (event code).
  - 'value': Event-specific data (string, number, or dictionary).

---

**Event Types**:
1. **TURN_PLAYER**: Start of a player's turn. 'value': Player name.
2. **PLAYERS_GAME_STATE**: Current game state. 'value': Dictionary with players' details, turn order, and current player.
3. **PLAY_CARD**: Player plays a card or ends turn. 'value': 'end' or dictionary with card details and options.
4. **RESPONSE_FOR_CARD**: Player's response to a card. 'value': Response description.
5. **STEP_RESULT**: Outcome of a game step. 'value': Dictionary with eliminated players and game status.
6. **NEED_DISCARD_CARDS**: Player must discard cards. 'value': Discard message.
7. **STEP_ERROR**: Error during an action. 'value': Error description.

---

**Analysis Guidelines**:
- **Track** player turns using **TURN_PLAYER**.
- **Monitor** actions via **PLAY_CARD** and **RESPONSE_FOR_CARD**.
- **Assess** game progress with PLAYERS_GAME_STATE.
- **Evaluate** outcomes using **STEP_RESULT**.
- **Note errors** with **STEP_ERROR**.

---

**Examples**:
- **Player plays "BANG!" and opponent responds with "MISS!"**: Observe turn start, card play, response, and unchanged health in game state.
- **Turn ends with discard requirement**: Note turn end and discard message.
- **Error using "BEER"**: See attempted card play and error message.
- **Player elimination**: Check elimination details and game continuation.
- **Game victory**: Identify winner based on game status.

---

**Your Task**:
- Summarize the game progression.
- Explain key events and outcomes.
- Interpret the current game state.

---

**Response Format**:
- Provide a concise summary.
- Detail critical events and errors.
- Describe the current game state if applicable.
"""

    role_finder_prompt = """
You are an analytical agent in the game “Bang!”. Your job is to identify the roles of other players (Helpers, Bandits, Renegade) based on their actions, cards used, and communication. Your findings must be accurate and updated with new data to help the player make strategic decisions.

---

**Game Context**  
- **Roles and Objectives**:  
  - **Sheriff**: Eliminate all Bandits and Renegade.  
  - **Assistants**: Protect the Sheriff and help him survive.  
  - **Bandits**: Kill the Sheriff.  
  - **Renegade**: To be the last survivor.  
- **Mechanics**: Players play cards, their actions give role clues.  
- **Communication**: Players can blame or support each other, which is important to analyze.

---

**Task**.  
Draw conclusions about the likely roles of the players based on the data. Your conclusions should:  
1. **Analyze actions**: Attacks, defenses, passivity (e.g., no attacks on Sheriff).  
2. **Analyze the cards**: Frequent use of defenses may indicate a Deputy, attacks on all may indicate a Renegade.  
3. **Analyze Communication**: Frequent accusations can be a sign of a Bandit or Renegade.  
4. **Update with each turn**, especially after significant events (e.g. role reveal).  
5. **Be presented as probabilities** (e.g., “most likely Bandit”).
6. **Differences**: Differences between words and actions.

---

**Additional Instructions**.  
- Evaluate **responses to provocations**: How players respond to accusations or suggestions.  
- Consider the **context of the group**: Alliances between players by their actions and words.  
- Offer **active checks**: For example, “Suggest that player X attack Y and see who intervenes.”
"""
    summarizer_prompt = """
Summarize the information received and answer the question as correctly as possible. Use your previous thoughts for this purpose.
        """

    @staticmethod
    def choice_card_for_play_prompt(game_state: dict[str, str]) -> dict[str, str]:
        last_memories = game_state['last_memories']
        cur_state = game_state['cur_state']
        return {"state":
f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
""",
            "prompt":
f"""
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
"""}

    @staticmethod
    def get_opponent_prompt(game_state: dict[str, str]) -> dict[str, str]:
        card = game_state['card']
        opponents = game_state['opponents']
        return {"prompt":
f"""
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
"""}

    @staticmethod
    def get_action_type_prompt(game_state: dict[str, str]) -> dict[str, str]:
        card = game_state['card']
        opponent = game_state['opponent']
        return {"prompt":
f"""
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
"""}

    @staticmethod
    def get_card_for_steal_prompt(game_state: dict[str, str]) -> dict[str, str]:
        card = game_state['card']
        opponent = game_state['opponent']
        action_type = game_state['action_type']
        return {"prompt":
                f"""
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
"""}

    @staticmethod
    def get_indians_response_prompt(game_state: dict[str, str]) -> dict[str, str]:
        last_memories = game_state['last_memories']
        cur_state = game_state['cur_state']
        return {"state":
f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
""",
                "prompt":
f"""
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
"""}

    @staticmethod
    def get_bang_response_prompt(game_state: dict[str, str]) -> dict[str, str]:
        last_memories = game_state['last_memories']
        cur_state = game_state['cur_state']
        return {"state":
f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
""",
                "prompt":
f"""
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
"""}

    @staticmethod
    def get_gatling_response_prompt(game_state: dict[str, str]) -> dict[str, str]:
        last_memories = game_state['last_memories']
        cur_state = game_state['cur_state']
        return {"state":
f"""
Events since the last time you acted: {last_memories}.
Your current cards and other parameters {cur_state}.
""",
                "prompt":
f"""
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
"""}

    @staticmethod
    def get_card_for_discard_prompt(game_state: dict[str, str]) -> dict[str, str]:
        num_cards = game_state['num_cards']
        cur_state = game_state['cur_state']
        return {"prompt":
f"""
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
}"""}

    @staticmethod
    def react_to_discard_error_prompt(game_state: dict[str, str]) -> dict[str, str]:
        errors = game_state['errors']
        cur_state = game_state['cur_state']
        return {"prompt":
f"""
Your current cards and other parameters {cur_state}.
Your last answer in which you had to choose a list of cards to discard from your hand was incorrect.
Look at the list of errors and based on it think about what exactly you did wrong. Errors: {errors}
Keep in mind that the correct answer is a json structure with a result field in which the list of cards
to be discarded is listed in a space separated line
Look carefully at the mistake you made and think about how you could
have corrected your answer. 
"""}

    @staticmethod
    def get_regenerate_prompt(so_answer_field_name, errors) -> dict[str, str]:
        return {"prompt":
f"""
You are an expert JSON-generating assistant. Your task is to provide a response in **valid JSON format** that adheres to the following rules:
**Current parsing errors**
{errors} 
**Instructions**
1. **Output valid JSON**. The response must be parseable by a JSON parser without errors.
2. The JSON must contain the following **required field**:
   - `{so_answer_field_name}`: A field that contains the main output of your response (e.g., a string, number, object, or array based on the query).
3. Optional fields can be included only if they are relevant to the query.
4. Ensure:
   - All keys use double quotes (`"key"`).
   - No trailing commas.
   - Proper nesting of objects and arrays.
   - No single quotes or unescaped special characters.
   - If use percent values use double quotes around them.
"""}