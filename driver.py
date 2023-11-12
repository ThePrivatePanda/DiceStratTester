from internal import Tester
from strategies import *
import sqlite3
import threading
import time
import json

db = sqlite3.connect("results.db")
games = db.cursor().execute("SELECT results FROM results").fetchall()
db.close()


class Simulator:
    def __init__(
        self,
        win_chance,
        wallet,
        bet_amount,
        auto_vault,
        over_under,
        strategy,
        rape_cpu=False,
    ) -> None:
        self.results = []
        if rape_cpu:
            self.thready(win_chance, wallet, bet_amount, auto_vault, over_under, strategy)
        else:
            threading.Thread(
                target=self.nothready,
                args=(win_chance, wallet, bet_amount, auto_vault, over_under, strategy),
            ).start()

    def thready(
        self,
        win_chance,
        wallet,
        bet_amount,
        auto_vault,
        over_under,
        strategy,
    ):
        for ind, game in enumerate(games):
            game = json.loads(game[0])
            tester = Tester(
                results=game,
                wallet=wallet,
                betAmount=bet_amount,
                winChance=win_chance,
                autoVault=auto_vault,
                overunder=over_under,
                strategy=strategy,
            )
            threading.Thread(target=self.main, args=(tester,)).start()
            print(f"Started thread {ind}/{len(games)}", end="\r")

    def main(self, tester):
        self.results.append(tester.main())

    def nothready(
        self,
        win_chance,
        wallet,
        bet_amount,
        auto_vault,
        over_under,
        strategy,
    ):
        for game in games:
            game = json.loads(game[0])
            tester = Tester(
                results=game,
                wallet=wallet,
                betAmount=bet_amount,
                winChance=win_chance,
                autoVault=auto_vault,
                overunder=over_under,
                strategy=strategy,
            )
            self.results.append(tester.main())

    def get_net_results(self):
        while True:
            print(f"Finished {len(self.results)}/{len(games)}", end="\r")
            if len(self.results) == len(games):
                break
            time.sleep(0.01)

        stop_reason_freq = {
            "All Games Played": 0,
            "Wallet is 0": 0,
            "Bet Amount is greater than Wallet": 0,
            "Win Chance is greater than 98%": 0,
            "Win Chance is less than 0.01%": 0,
            "Bet Amount is less than 0.00001": 0,
            "Stop Autobet": 0,
        }

        for result in self.results:
            stop_reason_freq[result["stop_reason"]] += 1

        return {
            "ending_wallet": round((sum([result["ending_wallet"] for result in self.results]) / len(self.results)), 5),
            "ending_vault": round((sum([result["ending_vault"] for result in self.results]) / len(self.results)), 5),
            "net_profit": round((sum([result["net_profit"] for result in self.results]) / len(self.results)), 5),
            "games": round((sum([result["games"] for result in self.results]) / len(self.results)), 5),
            "wins": round((sum([result["wins"] for result in self.results]) / len(self.results)), 5),
            "losses": round((sum([result["losses"] for result in self.results]) / len(self.results)), 5),
            "max_balance": round((sum([result["max_balance"] for result in self.results]) / len(self.results)), 5),
            "max_win_streak": round((sum([result["max_win_streak"] for result in self.results]) / len(self.results)), 5),
            "max_loss_streak": round((sum([result["max_loss_streak"] for result in self.results]) / len(self.results)), 5),
            "net_wagered": round((sum([result["net_wagered"] for result in self.results]) / len(self.results)), 5),
            "highest_payout": round((sum([result["highest_payout"] for result in self.results]) / len(self.results)), 5),
            "lowest_payout": round((sum([result["lowest_payout"] for result in self.results]) / len(self.results)), 5),
            "stop_reason_frequency": stop_reason_freq,
        }
