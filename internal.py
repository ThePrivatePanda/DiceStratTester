import itertools
import re

CONDITION_REGEX = re.compile(
    r"(every|every streak of|first streak of|streak greater than|streak lower than) ([0-9]{1,10}) (bets|losses|wins)"
)
ACTION_REGEX_WITH_VALUE = re.compile(
    r"( increase bet amount| decrease bet amouont| add to win chance| subtract from win chance| set win chance) ([0-9]{1,10})"
)
ACTION_REGEX = re.compile(r"( reset bet amount| reset win chance| switch over under| stop autobet)")


class Tester:
    def __init__(
        self,
        results,
        wallet: float,
        betAmount: float,
        winChance: float,
        autoVault: float,
        overunder: str,
        strategy,
    ):
        self.wallet = wallet
        self.bet_amount = betAmount
        self.win_chance = winChance
        self.auto_vault = autoVault
        self.strategy = strategy
        self.results = results
        self.overunder = overunder

        self.games = []
        self.actions = []
        self._max_wallet = self.wallet

        self._over_under = self.overunder
        self._bet_amount = self.bet_amount
        self._win_chance = self.win_chance
        self._wallet = self.wallet

        self.vault = 0
        self._net_wagered = 0

        self._win_streaks_done = []
        self._loss_streaks_done = []
        self.wins = 0
        self.losses = 0

    def is_xth_bet(self, x: int):
        return len(self.games) % x == 0

    def is_xth_win(self, x: int):
        if x == 1:
            return self.games[-1]
        return self.wins % x == 0

    def is_xth_loss(self, x: int):
        if x == 1:
            return not self.games[-1]
        return self.losses % x == 0

    def is_win_streak(self, x: int):
        return all(self.games[-x:])

    def is_loss_streak(self, x: int):
        return not any(self.games[-x:])

    def is_first_bet_streak(self, x: int):
        return len(self.games) == x

    def is_first_win_streak(self, x: int):
        if x in self._win_streaks_done:
            return False

        is_done = "".join(["1" if i else "0" for i in self.games]).count("1" * x) == 1
        if is_done:
            self._win_streaks_done.append(x)
        return True

    def is_first_loss_streak(self, x: int):
        if x in self._loss_streaks_done:
            return False

        is_done = "".join(["1" if i else "0" for i in self.games]).count("0" * x) == 1
        if is_done:
            self._loss_streaks_done.append(x)
        return True

    def get_longest_win_streak(self):
        return max((sum(1 for _ in group) for key, group in itertools.groupby(self.games) if key), default=0)

    def get_longest_loss_streak(self):
        return max((sum(1 for _ in group) for key, group in itertools.groupby(self.games) if not key), default=0)

    def get_win_streak(self):
        streak = 0
        for i in self.games[::-1]:
            if i:
                streak += 1
            else:
                break
        return streak

    def get_loss_streak(self):
        streak = 0
        for i in self.games[::-1]:
            if not i:
                streak += 1
            else:
                break
        return streak

    def latest_streak(self):
        streak = 0
        for i in self.games[::-1]:
            if i == self.games[-1]:
                streak += 1
            else:
                break
        return streak

    def group_frequency(self):
        result = {"True": {}, "False": {}}
        current_value = None
        current_count = 0

        for value in self.games:
            if current_value is None:
                current_value = value
                current_count = 1
            elif current_value == value:
                current_count += 1
            else:
                result[str(current_value)][current_count] = result[str(current_value)].get(current_count, 0) + 1
                current_value = value
                current_count = 1

        if current_value is not None:
            result[str(current_value)][current_count] = result[str(current_value)].get(current_count, 0) + 1

        return result

    def _result(self, win: bool):
        self.games.append(win)
        self._net_wagered += self._bet_amount

        if win:
            x = round((self._bet_amount * ((99 / self._win_chance) - 1)), 8)
            self._wallet += x
            self.actions.append(x)
            self.wins += 1
        else:
            self._wallet -= self._bet_amount
            self.actions.append(-self._bet_amount)
            self.losses += 1

        self._max_wallet = max(self._max_wallet, self._wallet)

        if self.auto_vault:
            profit = self._wallet - self.wallet
            deposit = (profit // self.auto_vault) * self.auto_vault
            if deposit >= 0:
                self._wallet -= deposit
                self.vault += deposit

        for temp in self.strategy:
            condition, action = temp.split(",")
            type, num, check = CONDITION_REGEX.findall(condition)[0]
            num = int(num)
            act = False
            if type == "every":
                if check == "bets" and self.is_xth_bet(num):
                    act = True
                elif check == "wins" and self.is_xth_win(num):
                    act = True
                elif check == "losses" and self.is_xth_loss(num):
                    act = True
            elif type == "every streak of":
                if check == "wins" and self.is_win_streak(num):
                    act = True
                elif check == "losses" and self.is_loss_streak(num):
                    act = True
                elif check == "bets" and self.is_xth_bet(num):
                    act = True
            elif type == "first streak of":
                if check == "wins" and self.is_first_win_streak(num):
                    act = True
                elif check == "losses" and self.is_first_loss_streak(num):
                    act = True
                elif check == "bets" and len(self.games) == num:
                    act = True
            elif type == "streak greater than":
                if check == "wins" and self.get_win_streak() > num:
                    act = True
                elif check == "losses" and self.get_loss_streak() > num:
                    act = True
                elif check == "bets" and len(self.games) > num:
                    act = True
            elif type == "streak lower than":
                if check == "wins" and self.get_win_streak() < num:
                    act = True
                elif check == "losses" and self.get_loss_streak() < num:
                    act = True
                elif check == "bets" and len(self.games) < num:
                    act = True

            if act:
                t = ACTION_REGEX_WITH_VALUE.findall(action)
                if t:
                    action, value = t[0]
                    value = int(value)
                    action = action.strip()
                    if action == "increase bet amount":
                        self._bet_amount *= 1 + (value / 100)
                    elif action == "decrease bet amouont":
                        self._bet_amount *= 1 - (value / 100)
                    elif action == "add to win chance":
                        self._win_chance += value
                    elif action == "subtract from win chance":
                        self._win_chance -= value
                    elif action == "set win chance":
                        self._win_chance = value
                else:
                    t = ACTION_REGEX.findall(action)
                    if not t:
                        raise Exception("Invalid Action")
                    action = action.strip()
                    if action == "reset bet amount":
                        self._bet_amount = self.bet_amount
                    elif action == "reset win chance":
                        self._win_chance = self.win_chance
                    elif action == "switch over under":
                        self._over_under = "over" if self._over_under == "under" else "under"
                    elif action == "stop autobet":
                        return "Stop Autobet"

    def validate_conditions(self):
        if self._wallet <= 0:
            return "Wallet is 0"
        if self._bet_amount >= self._wallet:
            return "Bet Amount is greater than Wallet"
        if self._win_chance > 98:
            # self._win_chance = 98
            return "Win Chance is greater than 98%"
        if self._win_chance < 0.01:
            # self._win_chance = 0.01
            return "Win Chance is less than 0.01%"
        if self._bet_amount < 0.00001:
            # self._bet_amount = 0.00001
            return "Bet Amount is less than 0.00001"

    def main(self):
        for condition, action in [i.split(",") for i in self.strategy]:
            if not CONDITION_REGEX.findall(condition):
                raise Exception(f"Invalid Condition: ```{condition}```")
            if not ACTION_REGEX.findall(action) and not ACTION_REGEX_WITH_VALUE.findall(action):
                raise Exception("Invalid Action")

        cont = False
        for i, num in enumerate(self.results):
            cont = cont or self.validate_conditions()
            if cont:
                break
            if self._over_under == "under":
                if num < self._win_chance:
                    cont = self._result(True)
                else:
                    cont = self._result(False)
            elif self._over_under == "over":
                if num > 100 - self._win_chance:
                    cont = self._result(True)
                else:
                    cont = self._result(False)

            self._wallet = round(self._wallet, 8)
            self._bet_amount = round(self._bet_amount, 8)
            # print(f"{i}/{len(self.results)}", end="\r")

        cont = cont or "All Games Played"
        freqs = self.group_frequency()
        return {
            "starting_wallet": self.wallet,
            "starting_bet": self.bet_amount,
            "starting_win_chance": self.win_chance,
            "starting_over_under": self.overunder,
            "stop_reason": cont,
            "ending_wallet": self._wallet,
            "ending_vault": self.vault,
            "net_profit": self._wallet + self.vault - self.wallet,
            "games": len(self.games),
            "wins": self.games.count(True),
            "losses": self.games.count(False),
            "losses_streak_freq": freqs["False"],
            "wins_streak_freq": freqs["True"],
            "max_balance": self._max_wallet,
            "max_win_streak": self.get_longest_win_streak(),
            "max_loss_streak": self.get_longest_loss_streak(),
            "net_wagered": self._net_wagered,
            "highest_payout": max(self.actions),
            "lowest_payout": min(self.actions),
        }
