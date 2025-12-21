import math
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

# ----- Implementation rules -----
def implements(row, strategy_name: str) -> bool:
    if strategy_name == "All-policies":
        return True
    if strategy_name == "Security-focused":
        return row["Impl_S"] > 0
    if strategy_name == "Trust-focused":
        return row["Impl_T"] >= TRUST_MEAN
    if strategy_name == "Cap-focused":
        return row["Impl_C"] >= CAP_MEAN
    if strategy_name == "Low-cost":
        return row["K"] <= COST_MEAN
    return False

# ----- Stats per strategy -----
def stats_for_strategy(strategy):
    x = 0.0
    t = 0.0
    C_ex = 0.0
    K_ex = 0.0
    count = 0

    for _, r in df_policies.iterrows():
        if implements(r, strategy):
            x += r["Impl_S"]
            t += r["Impl_T"]
            C_ex += r["Impl_C"]
            K_ex += r["K"]
            count += 1
        else:
            C_ex += r["Not_C"]

    return max(0, x), max(0, t), C_ex, K_ex, count

# ----- Volume function -----
def compute_V(C_total: float) -> float:
    return a * (max(1.0, C_total) ** b)

TRUST_POWER = 1.5

# ----- Trust function -----
def compute_s_for_exchange(i, xs, ts):
    products = [xs[j] * (ts[j] ** TRUST_POWER) for j in range(len(xs))]
    own = products[i]
    others = sum(products) - own
    denom = others + d * own
    if denom <= 0 or xs[i] <= 0 or ts[i] <= 0:
        return 0.0
    return (d * own) / denom

# ----- Breach function -----
def compute_p(x, V):
    if V <= 0:
        return 0.0
    return 1.0 / (1.0 + ((x / V) ** 0.9))

# ----- Utility function -----
def compute_I(s, V, p, K):
    return s * V * m - (V * g * p) - (K / 41)

# ----- Simulation for a strategy profile (returns profits + final market cap) -----
def simulate_profile(profile, rounds=ROUNDS):
    stats = [stats_for_strategy(s) for s in profile]

    x_list = [st[0] for st in stats]
    t_list = [st[1] for st in stats]
    C_list = [st[2] for st in stats]
    K_list = [st[3] for st in stats]

    per_round_C = sum(C_list) / N_PLAYERS

    C_total = 1.0
    cumulative_profits = [0.0] * N_PLAYERS

    for _ in range(rounds):
        C_total = max(1.0, C_total + per_round_C)
        V = compute_V(C_total)

        for i in range(N_PLAYERS):
            s = compute_s_for_exchange(i, x_list, t_list)
            p = compute_p(x_list[i], V)
            I = compute_I(s, V, p, K_list[i])
            cumulative_profits[i] += I

    return cumulative_profits, C_total

# ----- FULL VERBOSE 120-ROUND SIMULATION (round-by-round printout) -----
def simulate_profile_verbose(profile, rounds=ROUNDS):
    stats = [stats_for_strategy(s) for s in profile]

    x_list = [st[0] for st in stats]
    t_list = [st[1] for st in stats]
    C_list = [st[2] for st in stats]
    K_list = [st[3] for st in stats]

    per_round_C = sum(C_list) / N_PLAYERS

    C_total = 1.0
    cumulative_profits = [0.0] * N_PLAYERS

    print("\n" + "=" * 80)
    print("VERBOSE 120-ROUND SIMULATION")
    print("=" * 80)
    print(f"Profile: {profile}")
    print("-" * 80)
    print(f"per_round_C (avg C increment per round) = {per_round_C:.6f}")
    print("-" * 80)

    for r in range(1, rounds + 1):
        C_total = max(1.0, C_total + per_round_C)
        V = compute_V(C_total)

        round_I = [0.0] * N_PLAYERS
        round_s = [0.0] * N_PLAYERS
        round_p = [0.0] * N_PLAYERS

        for i in range(N_PLAYERS):
            s = compute_s_for_exchange(i, x_list, t_list)
            p = compute_p(x_list[i], V)
            I = compute_I(s, V, p, K_list[i])

            round_s[i] = s
            round_p[i] = p
            round_I[i] = I
            cumulative_profits[i] += I

        print(f"Round {r:3d} | C_total={C_total:12.6f} | V={V:12.6f}")
        for i in range(N_PLAYERS):
            print(
                f"  Ex {i+1}: s={round_s[i]:.6f}  p={round_p[i]:.6f}  "
                f"I={round_I[i]:.6f}  CumProfit={cumulative_profits[i]:.6f}"
            )

    print("-" * 80)
    print("FINAL RESULTS AFTER ALL ROUNDS")
    for i in range(N_PLAYERS):
        print(f"  Exchange {i+1}: Total Profit = {cumulative_profits[i]:.6f}")
    print(f"  TOTAL (social welfare) = {sum(cumulative_profits):.6f}")
    print(f"  FINAL market capitalisation (C_total) = {C_total:.6f}")
    print("=" * 80)

    return cumulative_profits, C_total

# ----- Best-response dynamics -----
def best_response_dynamics(initial_profile, max_iters=50, tol=1e-6):
    profile = list(initial_profile)

    for it in range(max_iters):
        improved = False

        for i in range(N_PLAYERS):
            base_payoffs, _ = simulate_profile(profile)
            base_payoff = base_payoffs[i]

            best_strategy = profile[i]
            best_value = base_payoff

            for s in STRATEGIES:
                if s == profile[i]:
                    continue

                trial = profile.copy()
                trial[i] = s
                trial_payoffs, _ = simulate_profile(trial)
                trial_value = trial_payoffs[i]

                if trial_value > best_value + tol:
                    best_value = trial_value
                    best_strategy = s

            if best_strategy != profile[i]:
                print(
                    f"[BR] Iter {it}, Exchange {i+1}: "
                    f"{profile[i]} → {best_strategy} | "
                    f"{base_payoff:.2f} → {best_value:.2f}"
                )
                profile[i] = best_strategy
                improved = True

        if not improved:
            break

    final_payoffs, final_C = simulate_profile(profile)
    return profile, final_payoffs, final_C

# ----- Nash check -----
def is_nash(profile, tol=1e-6):
    base, _ = simulate_profile(profile)
    for i in range(N_PLAYERS):
        current_strategy = profile[i]
        current_payoff = base[i]

        for s in STRATEGIES:
            if s == current_strategy:
                continue
            trial = profile.copy()
            trial[i] = s
            trial_payoffs, _ = simulate_profile(trial)
            trial_payoff_i = trial_payoffs[i]
            if trial_payoff_i > current_payoff + tol:
                return False
    return True

# ----- Verbose Nash check -----
def is_nash_verbose(profile, tol=1e-6):
    base, final_C = simulate_profile(profile)

    print("\nChecking profile:")
    for i in range(N_PLAYERS):
        print(f"  Exchange {i+1}: {profile[i]} | Payoff = {base[i]:.4f}")
    print(f"  Final market capitalisation (C_total) = {final_C:.4f}")

    for i in range(N_PLAYERS):
        current_strategy = profile[i]
        current_payoff = base[i]

        for s in STRATEGIES:
            if s == current_strategy:
                continue

            trial = profile.copy()
            trial[i] = s
            trial_payoffs, _ = simulate_profile(trial)
            trial_payoff_i = trial_payoffs[i]

            print(
                f"    Deviation test: Exchange {i+1} "
                f"{current_strategy} → {s} | "
                f"{current_payoff:.4f} → {trial_payoff_i:.4f}"
            )

            if trial_payoff_i > current_payoff + tol:
                print("    PROFITABLE DEVIATION FOUND → Not Nash")
                return False

    print("    NO PROFITABLE DEVIATIONS → NASH EQUILIBRIUM")
    return True

# ----- brute force -----
def brute_force_nash_verbose_with_social(verbose_social=True, tol=1e-6, social_tol=1e-9):
    equilibria = []
    best_total = -float("inf")
    best_profiles = []
    all_totals = []

    total = len(STRATEGIES) ** N_PLAYERS
    counter = 0

    for profile_tuple in itertools.product(STRATEGIES, repeat=N_PLAYERS):
        counter += 1
        profile = list(profile_tuple)

        print("\n" + "=" * 80)
        print(f"PROFILE {counter} / {total}: {profile}")

        # --- Social welfare computation and comparison ---
        payoffs, final_C = simulate_profile(profile)
        total_welfare = sum(payoffs)
        all_totals.append(total_welfare)

        if verbose_social:
            if total_welfare > best_total + social_tol:
                print(f"[SOCIAL] Total welfare = {total_welfare:.4f}  (NEW BEST )")
            elif abs(total_welfare - best_total) <= social_tol:
                print(f"[SOCIAL] Total welfare = {total_welfare:.4f}  (TIED BEST )")
            else:
                gap = best_total - total_welfare if best_total != -float("inf") else float("nan")
                print(f"[SOCIAL] Total welfare = {total_welfare:.4f}  (Best so far = {best_total:.4f}, Gap = {gap:.4f})")

        # update best trackers (store final_C too)
        if total_welfare > best_total + social_tol:
            best_total = total_welfare
            best_profiles = [(profile, payoffs, final_C)]
        elif abs(total_welfare - best_total) <= social_tol:
            best_profiles.append((profile, payoffs, final_C))

        # --- Every deviation ---
        if is_nash_verbose(profile, tol):
            equilibria.append((profile, payoffs, final_C))

            print("\nCONFIRMED PURE-STRATEGY NASH EQUILIBRIUM ")
            for i in range(N_PLAYERS):
                print(f"  Exchange {i+1}: {profile[i]} | Profit = {payoffs[i]:.4f}")
            print(f"  TOTAL (social welfare) = {total_welfare:.4f}")
            print(f"  FINAL market capitalisation (C_total) = {final_C:.4f}")
        else:
            print(" Rejected profile\n")

    return equilibria, best_total, best_profiles, all_totals

if __name__ == "__main__":
    # starting point
    initial_profile = [
        "All-policies",
        "Security-focused",
        "Trust-focused",
        "Cap-focused",
        "Low-cost",
    ]

    print("=== BEST-RESPONSE DYNAMICS (LOCAL SEARCH) ===")
    eq_profile_local, eq_payoffs_local, eq_final_C_local = best_response_dynamics(initial_profile)

    print("\nLocal equilibrium candidate:")
    for i in range(N_PLAYERS):
        print(f"  Exchange {i+1}: {eq_profile_local[i]} | Profit = {eq_payoffs_local[i]:.4f}")
    print(f"  FINAL market capitalisation (C_total) = {eq_final_C_local:.4f}")
    print("Is Nash (fast check)?", is_nash(eq_profile_local))

    # Global brute-force scan
    print("\n=== VERBOSE GLOBAL BRUTE-FORCE NASH SCAN (3125 PROFILES) + VERBOSE SOCIAL TRACKING ===")
    all_eq, best_total, best_profiles, all_totals = brute_force_nash_verbose_with_social(
        verbose_social=True,
        tol=1e-6,
        social_tol=1e-9
    )

    # Nash summary
    print("\n" + "=" * 80)
    print(f"TOTAL PURE-STRATEGY NASH EQUILIBRIA FOUND: {len(all_eq)}")
    print("=" * 80)

    for idx, (prof, pays, final_C) in enumerate(all_eq, start=1):
        print(f"\n--- FINAL EQUILIBRIUM #{idx} ---")
        for i in range(N_PLAYERS):
            print(f"Exchange {i+1}: {prof[i]} | Profit = {pays[i]:.4f}")
        print(f"TOTAL (social welfare) = {sum(pays):.4f}")
        print(f"FINAL market capitalisation (C_total) = {final_C:.4f}")

    # Social optimum summary
    print("\n" + "#" * 80)
    print("SOCIAL OPTIMUM (HIGHEST TOTAL PROFIT) — FINAL SUMMARY")
    print("#" * 80)
    print(f"Max total profit (social welfare) = {best_total:.4f}")
    print(f"Number of social-optimal profiles (ties) = {len(best_profiles)}")

    for idx, (prof, pays, final_C) in enumerate(best_profiles, start=1):
        print(f"\n--- SOCIAL OPTIMUM #{idx} ---")
        for i in range(N_PLAYERS):
            print(f"Exchange {i+1}: {prof[i]} | Profit = {pays[i]:.4f}")
        print(f"TOTAL (social welfare) = {sum(pays):.4f}")
        print(f"FINAL market capitalisation (C_total) = {final_C:.4f}")

    # ----- Price of Anarchy / Price of Stability -----
    if all_eq:
        nash_totals = [sum(pays) for _, pays, _ in all_eq]
        best_nash_total = max(nash_totals)
        worst_nash_total = min(nash_totals)

        global_min_welfare = min(all_totals)
        epsilon = 1e-6
        offset = (-global_min_welfare + epsilon) if global_min_welfare <= 0 else 0.0

        W_opt = best_total + offset
        W_best_NE = best_nash_total + offset
        W_worst_NE = worst_nash_total + offset

        PoS = W_opt / W_best_NE
        PoA = W_opt / W_worst_NE

        print("\n" + "=" * 80)
        print("EFFICIENCY METRICS (OFFSET-CORRECTED TOTAL WELFARE)")
        print("=" * 80)
        print(f"Minimum welfare across ALL profiles = {global_min_welfare:.6f}")
        print(f"Offset applied Δ                    = {offset:.6f}")
        print("-" * 80)
        print(f"Raw social optimum welfare (W*)     = {best_total:.6f}")
        print(f"Raw best Nash welfare               = {best_nash_total:.6f}")
        print(f"Raw worst Nash welfare              = {worst_nash_total:.6f}")
        print("-" * 80)
        print(f"Shifted social optimum welfare      = {W_opt:.6f}")
        print(f"Shifted best Nash welfare           = {W_best_NE:.6f}")
        print(f"Shifted worst Nash welfare          = {W_worst_NE:.6f}")
        print("-" * 80)
        print(f"Price of Stability (PoS)            = {PoS:.6f}")
        print(f"Price of Anarchy (PoA)              = {PoA:.6f}")

        if abs(PoS - 1.0) < 1e-6:
            print("Interpretation: At least one Nash equilibrium achieves the social optimum (PoS ≈ 1).")
        else:
            print("Interpretation: No Nash equilibrium achieves the social optimum (PoS > 1).")

        if abs(PoA - 1.0) < 1e-6:
            print("Interpretation: All Nash equilibria are socially optimal (PoA ≈ 1).")
        else:
            print("Interpretation: Some Nash equilibria are inefficient (PoA > 1).")
    else:
        print("\nNo Nash equilibria found; PoA/PoS are undefined.")

    # Simulate all 120 rounds with the social optimum/nash eq strategy set
    if best_profiles:
        opt_profile = best_profiles[0][0]  
        print("\n\n" + "#" * 80)
        print("RUNNING 120-ROUND VERBOSE SIMULATION — SOCIAL OPTIMUM PROFILE")
        print("#" * 80)
        simulate_profile_verbose(opt_profile, rounds=ROUNDS)
    else:
        print("\nNo social-optimal profile stored (unexpected).")

    if all_eq:
        best_nash = max(all_eq, key=lambda x: sum(x[1]))
        nash_profile = best_nash[0]

        print("\n\n" + "#" * 80)
        print("RUNNING 120-ROUND VERBOSE SIMULATION — BEST NASH EQUILIBRIUM PROFILE")
        print("#" * 80)
        simulate_profile_verbose(nash_profile, rounds=ROUNDS)
    else:
        print("\nNo Nash equilibria found; cannot run Nash verbose simulation.")
