import itertools
import pandas as pd

# ----- Constants -----
a = 0.001
b = 1.05
d = 50.0
m = 1.5
g = 50 / 20
ROUNDS = 120

# ----- Policy table -----
POLICIES = [
    ("Licensing Requirement (Arts 59–63)",                0, 8,  7, -7, 7),
    ("Operational Resilience / Cybersecurity (DORA)",     9, 7,  4, -4, 8),
    ("Outsourcing Controls (Arts 66–67)",                 6, 5,  4, -4, 5),
    ("Capital / Own Funds (Arts 61–63)",                  0, 9,  8, -8, 9),
    ("Segregation of Client Assets (Arts 75–76)",         0, 10,  7, -7, 7),
    ("White Paper / Disclosure (Arts 4–15)",              0, 6,  6, -6, 4),
    ("Ban on Certain Products (Arts 122–124)",            0, 4, -3,  5, 1),
]

df_policies = pd.DataFrame(
    POLICIES,
    columns=["Policy", "Impl_S", "Impl_T", "Impl_C", "Not_C", "K"]
)

TRUST_MEAN = df_policies["Impl_T"].mean()
CAP_MEAN = df_policies["Impl_C"].mean()
COST_MEAN = df_policies["K"].mean()

# ----- Strategy set -----
STRATEGIES = [
    "All-policies",
    "Security-focused",
    "Trust-focused",
    "Cap-focused",
    "Low-cost",
]

N_PLAYERS = 5
TRUST_POWER = 1.5

# ----- Strategy rules -----
def implements(row, strategy):
    if strategy == "All-policies":
        return True
    if strategy == "Security-focused":
        return row["Impl_S"] > 0
    if strategy == "Trust-focused":
        return row["Impl_T"] >= TRUST_MEAN
    if strategy == "Cap-focused":
        return row["Impl_C"] >= CAP_MEAN
    if strategy == "Low-cost":
        return row["K"] <= COST_MEAN
    return False

# ----- Stats per strategy -----
def stats_for_strategy(strategy):
    x = t = C = K = 0.0
    for _, r in df_policies.iterrows():
        if implements(r, strategy):
            x += r["Impl_S"]
            t += r["Impl_T"]
            C += r["Impl_C"]
            K += r["K"]
        else:
            C += r["Not_C"]
    return max(0, x), max(0, t), C, K

# ----- Core functions -----
def compute_V(C):
    return a * (max(1.0, C) ** b)

def compute_s(i, xs, ts):
    products = [xs[j] * (ts[j] ** TRUST_POWER) for j in range(len(xs))]
    own = products[i]
    others = sum(products) - own
    denom = others + d * own
    if denom <= 0 or xs[i] <= 0 or ts[i] <= 0:
        return 0.0
    return (d * own) / denom


def compute_p(x, V):
    return 1.0 / (1.0 + (x / V) ** 0.9) if V > 0 else 0.0

def compute_I(s, V, p, K):
    return s * V * m - V * g * p - K / 41

# ----- Simulation -----
def simulate_profile(profile, rounds=ROUNDS):
    stats = [stats_for_strategy(s) for s in profile]
    xs, ts, Cs, Ks = zip(*stats)

    C_total = 1.0
    profits = [0.0] * N_PLAYERS
    per_round_C = sum(Cs) / N_PLAYERS

    for _ in range(rounds):
        C_total = max(1.0, C_total + per_round_C)
        V = compute_V(C_total)
        for i in range(N_PLAYERS):
            s = compute_s(i, xs, ts)
            p = compute_p(xs[i], V)
            profits[i] += compute_I(s, V, p, Ks[i])

    return profits, C_total

# ----- Nash check -----
def is_nash(profile, tol=1e-6):
    base, _ = simulate_profile(profile)
    for i in range(N_PLAYERS):
        for s in STRATEGIES:
            if s == profile[i]:
                continue
            trial = profile.copy()
            trial[i] = s
            payoff, _ = simulate_profile(trial)
            if payoff[i] > base[i] + tol:
                return False
    return True

# ----- Main execution -----
if __name__ == "__main__":

    equilibria = []
    best_total = -float("inf")
    best_profiles = []
    all_totals = []

    for profile in itertools.product(STRATEGIES, repeat=N_PLAYERS):
        profile = list(profile)
        payoffs, C_final = simulate_profile(profile)
        total = sum(payoffs)
        all_totals.append(total)

        if is_nash(profile):
            equilibria.append((profile, payoffs, C_final))

        if total > best_total:
            best_total = total
            best_profiles = [(profile, payoffs, C_final)]
        elif abs(total - best_total) < 1e-9:
            best_profiles.append((profile, payoffs, C_final))

    # ----- Output -----
    print(f"\nTOTAL NASH EQUILIBRIA FOUND: {len(equilibria)}")
    for i, (p, pay, C) in enumerate(equilibria, 1):
        print(f"\nNASH #{i}: {p}")
        print(f"  Profits: {[round(x,4) for x in pay]}")
        print(f"  Total welfare: {sum(pay):.4f}")
        print(f"  Final market cap: {C:.4f}")

    print("\nSOCIAL OPTIMUM:")
    for p, pay, C in best_profiles:
        print(f"  Profile: {p}")
        print(f"  Total welfare: {sum(pay):.4f}")
        print(f"  Final market cap: {C:.4f}")

    # ----- Efficiency -----
    nash_totals = [sum(p[1]) for p in equilibria]
    offset = -min(all_totals) + 1e-6 if min(all_totals) <= 0 else 0

    PoS = (best_total + offset) / (max(nash_totals) + offset)
    PoA = (best_total + offset) / (min(nash_totals) + offset)

    print("\nEFFICIENCY METRICS")
    print(f"Price of Stability: {PoS:.6f}")
    print(f"Price of Anarchy:   {PoA:.6f}")
