from driver import Simulator
from strategies import *
import json

sim = Simulator(
    win_chance=50,
    wallet=100,
    bet_amount=0.1,
    auto_vault=0.5,
    over_under="over",
    strategy=astra,
    rape_cpu=True
)

res = sim.get_net_results()
print("", end="\n\n")
print(json.dumps(res, indent=4))
