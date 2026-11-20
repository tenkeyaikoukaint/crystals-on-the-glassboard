import random
import time
import copy

# --- Constants ---
FIELD_MIN = 0
FIELD_MAX = 6

ATTR_PHYS = "Physical"
ATTR_MAG = "Magic"

# Priority (Frames: lower numbers act first)
PRIO_SYSTEM = 0   # Fastest (Ultimate attacks / system processes)
PRIO_DEFEND = 1   # Evade, guard, deploy/dispel barrier, knockback/denial moves
PRIO_FAST_ATK = 2 # Poke attacks, rush moves
PRIO_MOVE = 3     # Standard advance, barrier break
PRIO_SLOW_ATK = 4 # Heavy attacks, grand magic, cast completion

# --- Class Definitions ---
class Skill:
    def __init__(self, name, power, range_req, attr, priority, sp_cost, charge=0, is_rush=False, req_barrier=False, desc=""):
        self.name = name
        self.power = power
        self.range_req = range_req
        self.attr = attr
        self.priority = priority
        self.sp_cost = sp_cost
        self.charge = charge
        self.is_rush = is_rush
        self.req_barrier = req_barrier
        self.desc = desc

class Fighter:
    def __init__(self, name, hp, sp, atk, mag, speed, desc):
        self.name = name
        self.max_hp = hp
        self.hp = hp
        self.max_sp = sp
        self.sp = sp
        self.atk = atk
        self.mag = mag
        self.speed = speed
        self.desc = desc
        
        self.pos = 0
        self.barrier_active = False
        self.barrier_life = -1
        self.is_flying = False
        self.is_jumping = False
        self.is_guarding = False
        self.vulnerable = False
        
        self.charge_skill = None
        self.charge_wait = 0
        self.skills = []
        self.can_barrier = False

    def add_skill(self, skill):
        self.skills.append(skill)

    def is_alive(self): return self.hp > 0
    def is_in_barrier_zone(self, dist): return self.barrier_active and self.barrier_life == -1 and dist <= 1

# --- Game System ---
class Game:
    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2
        self.p1.pos = 1
        self.p2.pos = 5
        self.turn_count = 1

    def get_dist(self): return abs(self.p1.pos - self.p2.pos)

    def print_msg(self, text):
        print(text)
        time.sleep(0.35)

    def draw_field(self):
        field = ["_"] * (FIELD_MAX + 1)
        if self.p1.pos == self.p2.pos: field[self.p1.pos] = "X"
        else:
            field[self.p1.pos] = "1"
            field[self.p2.pos] = "2"
        print(f"\n[WALL] {' '.join(field)} [WALL] (Dist: {self.get_dist()})")

    def print_status(self):
        print(f"\n{'='*15} Turn {self.turn_count} {'='*15}")
        self.draw_field()
        for i, p in enumerate([self.p1, self.p2]):
            st = []
            if p.pos == FIELD_MIN or p.pos == FIELD_MAX: st.append("<Cornered>")
            if p.charge_skill: st.append(f"<Chanting:{p.charge_skill.name}>")
            if p.barrier_active:
                if p.barrier_life > 0: st.append(f"[Ice Shield({p.barrier_life}T left)]")
                else: st.append("[Barrier Active (Melee Boost / Instant Cast / Phys Reflect)]")
            if p.is_flying: st.append("<Flying>")
            if p.vulnerable: st.append("<Wide Open!!>")
            if p.name == "Keiko Shirasawa" and self.get_dist() <= 1: st.append("<Close-Range Danger!>")
            
            print(f"P{i+1} {p.name}: HP {int(p.hp):>3}/{p.max_hp} | SP {int(p.sp):>3}/{p.max_sp} " + " ".join(st))
        print("="*42)

    def get_effective_range(self, actor, skill):
        # While a barrier is active, all magic is optimized to range 0-1 (inside the barrier zone)
        if actor.barrier_active and actor.barrier_life == -1 and skill.name != "Desperate Flash":
            return [0, 1]
        return skill.range_req

    def get_valid_actions(self, actor, enemy):
        if actor.charge_skill:
            return [("Continue Chant", PRIO_SLOW_ATK, 0, True, "")]
            
        acts = []
        dist = self.get_dist()
        
        for s in actor.skills:
            usable = True
            reason = ""
            if actor.sp < s.sp_cost:
                usable = False; reason = "Insufficient SP"
            elif getattr(s, 'req_barrier', False) and not (actor.barrier_active and actor.barrier_life == -1):
                usable = False; reason = "Requires Barrier Zone"
            elif actor.barrier_active and actor.barrier_life == -1 and s.name != "Desperate Flash" and dist >= 2:
                usable = False; reason = "Cannot attack outside Barrier (Dist 2+) - must close in"
                
            acts.append((s, s.priority, s.sp_cost, usable, reason))

        acts.append(("Wait & See (Guard / Recover SP)", PRIO_DEFEND, 0, True, ""))

        if actor.barrier_active and actor.barrier_life == -1:
            acts.append(("Dispel Barrier", PRIO_DEFEND, 0, True, "Cancel + Recover 15 SP"))
        elif not actor.barrier_active:
            if actor.can_barrier:
                u_barrier = actor.sp >= 20
                acts.append(("Deploy Barrier", PRIO_DEFEND, 20, u_barrier, "Insufficient SP" if not u_barrier else "Instant Deploy / Melee Instant-Cast"))
            if actor.name == "Masahiro Hayashi":
                u_ice = actor.sp >= 20
                acts.append(("Ice Shield", PRIO_DEFEND, 20, u_ice, "Insufficient SP" if not u_ice else "2T Halve Magic + Phys Counter"))

        # Barrier Break includes a step-in, so it reaches from distance 2
        u_break = enemy.barrier_active and dist <= 2 and actor.sp >= 10
        acts.append(("Shatter Enemy Barrier", PRIO_MOVE, 10, u_break, "Requires Dist <= 2 & Enemy Barrier" if not u_break else "Step 1 Forward + Shatter Barrier"))

        acts.append(("Close Distance", PRIO_MOVE, 5, actor.sp >= 5 and dist > 0, "Already Point-Blank" if dist == 0 else "Insufficient SP"))
        acts.append(("Step Back", PRIO_DEFEND, 15, actor.sp >= 15, "Insufficient SP"))

        if actor.name != "Blau" and not actor.is_jumping:
            acts.append(("Jump", PRIO_DEFEND, 15, actor.sp >= 15, "Insufficient SP"))
        if actor.name == "Blau" and not actor.is_flying:
            acts.append(("Fly", PRIO_DEFEND, 20, actor.sp >= 20, "Insufficient SP"))

        return acts

    def resolve_action(self, actor, target, act_obj):
        if not actor.is_alive(): return
        act, prio, cost, usable, reason = act_obj
        
        if act == "Continue Chant":
            if not actor.charge_skill:
                self.print_msg(f"* {actor.name}'s chant was interrupted and cannot move!")
                return
            actor.charge_wait -= 1
            if actor.charge_wait <= 0:
                s = actor.charge_skill
                actor.charge_skill = None
                self.print_msg(f"\n* {actor.name} finished chanting! Unleashes '{s.name}'!")
                self.fire_skill(actor, target, s)
            else:
                self.print_msg(f"\n* {actor.name} is still chanting... ({actor.charge_wait}T left)")
            return

        self.print_msg(f"\n* {actor.name}'s Action: {act.name if isinstance(act, Skill) else act}")
        actor.sp -= cost
        dist = self.get_dist()

        if act == "Wait & See (Guard / Recover SP)":
            actor.is_guarding = True
            actor.sp = min(actor.max_sp, actor.sp + 35)
            self.print_msg("  Braced for impact! (Halves damage & recovers +35 SP)")
            return

        if act == "Close Distance":
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                # While Barrier is active, pulls/closes distance by 2 spaces like magnetism
                steps = 2 if (actor.barrier_active and actor.barrier_life == -1 and dist >= 2) else 1
                for _ in range(steps):
                    if actor.pos != target.pos:
                        actor.pos += dir
                if steps == 2:
                    self.print_msg(f"  Closed the gap in an instant along with the barrier zone! (Dist: {self.get_dist()})")
                else:
                    self.print_msg(f"  Stepped forward! (Dist: {self.get_dist()})")
            else:
                self.print_msg("  Already at point-blank range!")
            return
            
        if act == "Step Back":
            dir = -1 if target.pos > actor.pos else 1
            new_pos = actor.pos + dir
            if FIELD_MIN <= new_pos <= FIELD_MAX:
                actor.pos = new_pos
                self.print_msg(f"  Quickly stepped backward! (Dist: {self.get_dist()})")
            else:
                self.print_msg("  Backed against the wall! Nowhere to retreat! (Left wide open)")
                actor.vulnerable = True
            return

        if act in ["Jump", "Fly"]:
            if act == "Jump":
                actor.is_jumping = True
                self.print_msg("  Leapt high into the air! (Greatly reduces hit rate this turn)")
            else:
                actor.is_flying = True
                self.print_msg("  Took to the skies! (Evasion UP / Attack Power x1.2)")
            return

        # Instant Barrier Deployment
        if act == "Deploy Barrier":
            actor.barrier_active = True
            actor.barrier_life = -1
            self.print_msg("  [BARRIER ZONE: INSTANT DEPLOYMENT!]")
            self.print_msg("  (Effect: Halves Magic DMG / Reflects Phys DMG / Instant-Cast & x1.4 Power at Dist 0-1)")
            return

        if act == "Dispel Barrier":
            actor.barrier_active = False
            actor.sp = min(actor.max_sp, actor.sp + 15)
            self.print_msg("  Dispelled the barrier and reclaimed magical energy! (+15 SP)")
            return

        if act == "Ice Shield":
            actor.barrier_active = True
            actor.barrier_life = 2
            self.print_msg("  Deployed an Ice Shield! (2T Halves Magic DMG / Chilling Counter on Phys hit)")
            return
            
        if act == "Shatter Enemy Barrier":
            if dist <= 2 and target.barrier_active:
                if dist >= 1:
                    dir = 1 if target.pos > actor.pos else -1
                    actor.pos += dir
                    self.print_msg(f"  Stepped in and interfered with the enemy's barrier! (Dist: {self.get_dist()})")

                if self.get_dist() <= 1:
                    dmg = 15 + max(actor.atk, actor.mag) // 2
                    if target.is_guarding:
                        self.print_msg("  GUARD BREAK! Smashed through both guard and barrier!")
                        dmg = int(dmg * 1.5)
                    target.hp -= dmg
                    target.barrier_active = False
                    target.vulnerable = True
                    self.print_msg(f"  Shattered the enemy's barrier for {dmg} DMG and left them wide open!")
                else:
                    self.print_msg("  [WHIFF] Target was too far to reach! (Left open)")
                    actor.vulnerable = True
            else:
                self.print_msg("  [WHIFF] No barrier active or target too far! (Left open)")
                actor.vulnerable = True
            return

        if isinstance(act, Skill):
            # While Barrier is active, charge skills (charge > 0) fire instantly with zero chant time
            if act.charge > 0:
                if actor.barrier_active and actor.barrier_life == -1:
                    self.print_msg(f"  [BARRIER RESONANCE] Bypassed chanting and unleashed '{act.name}' instantly!!")
                else:
                    actor.charge_skill = act
                    actor.charge_wait = act.charge
                    self.print_msg(f"  Started chanting '{act.name}'! (Fires next turn)")
                    return

            self.fire_skill(actor, target, act)

    def fire_skill(self, actor, target, skill):
        if skill.name == "Desperate Flash":
            actor.barrier_active = False
            actor.pos = target.pos
            self.print_msg(f"\n!!! {actor.name} compressed their barrier to its absolute limit !!!")
            self.print_msg("\"This... finishes it!\"")
            self.print_msg(f"  Detonated the barrier, rushing straight into {target.name} in a blinding flash!!")
            actor.hp = max(1, actor.hp - 20)
            actor.sp = 0
            actor.vulnerable = True

        elif getattr(skill, "is_rush", False):
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                actor.pos += dir
                self.print_msg(f"  Lunged forward sharply!! (Dist: {self.get_dist()})")
        
        current_dist = self.get_dist()
        eff_range = self.get_effective_range(actor, skill)
        
        # --- Whiff / Misfire Check ---
        if skill.name != "Desperate Flash":
            if actor.barrier_active and actor.barrier_life == -1 and current_dist >= 2:
                self.print_msg("  [MISFIRE!!] Target escaped outside the Barrier Zone (Dist 2+)! (Wide open)")
                actor.vulnerable = True
                return
            if not (eff_range[0] <= current_dist <= eff_range[1]):
                self.print_msg("  [WHIFF!!] Out of range—the attack cut through empty air! (Wide open)")
                actor.vulnerable = True
                return

        self.resolve_skill(actor, target, skill, current_dist)

    def calculate_damage(self, attacker, defender, skill, dist):
        base = attacker.atk if skill.attr == ATTR_PHYS else attacker.mag
        dmg = base + skill.power

        if attacker.name == "Keiko Shirasawa" and skill.name == "Whirlwind":
            dmg *= (0.7 + (dist * 0.15))

        if attacker.is_flying: dmg *= 1.2
        
        if skill.name != "Desperate Flash":
            if attacker.is_in_barrier_zone(dist):
                dmg *= 1.4 # Barrier zone buff
                
            if defender.barrier_active:
                if skill.attr == ATTR_PHYS:
                    pass # Physical is not reduced (triggers reflect damage instead)
                else:
                    dmg *= 0.5 # Magic is halved

            if defender.is_guarding: dmg *= 0.5

        if defender.name == "Keiko Shirasawa" and dist <= 1: dmg *= 1.4
        if defender.vulnerable: dmg *= 1.4

        return int(dmg)

    def resolve_skill(self, actor, target, skill, dist=None):
        if dist is None: dist = self.get_dist()
        
        hit_rate = 1.0
        if target.is_jumping: hit_rate = 0.35
        elif target.is_flying: hit_rate = 0.70
        # Attacks inside the Barrier Zone never miss
        if actor.is_in_barrier_zone(dist): hit_rate = 1.0
        
        if random.random() > hit_rate and skill.name != "Desperate Flash":
            self.print_msg(f"  {target.name} gracefully evaded the attack in midair!")
            return

        dmg = self.calculate_damage(actor, target, skill, dist)
        target.hp -= dmg
        
        msg = f"  HIT! Dealt {dmg} damage to {target.name}!"
        
        if skill.name == "Desperate Flash":
            msg += " [FATAL STRIKE — PIERCES BARRIER & GUARD!!]"
            if target.barrier_active:
                target.barrier_active = False
                self.print_msg("  The opponent's barrier shattered into pieces!")
        else:
            if target.barrier_active:
                if skill.attr == ATTR_PHYS:
                    msg += " [PHYSICAL PIERCE!!]"
                else:
                    msg += " (Halved by Barrier)"
                        
            if actor.is_in_barrier_zone(dist):
                msg += " [BARRIER ZONE BUFF (Sure-Hit & x1.4)!!]"

            if target.vulnerable: msg += " [COUNTER HIT (x1.4)!!]"
            elif target.is_guarding: msg += " (Halved by Guard)"
            
        self.print_msg(msg)

        # Magical reflect counter against physical attacks hitting a barrier
        if target.barrier_active and skill.attr == ATTR_PHYS and skill.name != "Desperate Flash":
            thorn_dmg = max(10, target.mag // 2)
            actor.hp -= thorn_dmg
            self.print_msg(f"  ⚡ [BARRIER COUNTER] The magical barrier flared back, dealing {thorn_dmg} reflected damage to {actor.name}!")

        if target.charge_skill and dmg >= 20:
            self.print_msg(f"  !! {target.name}'s chant was interrupted!")
            target.charge_skill = None
            target.charge_wait = 0

        if skill.name == "Wind Push":
            self.print_msg("  Wind pressure blew the opponent back 2 spaces!")
            dir = 1 if target.pos > actor.pos else -1
            for _ in range(2):
                if FIELD_MIN <= target.pos + dir <= FIELD_MAX:
                    target.pos += dir
                else:
                    self.print_msg("  [WALL SLAM] Opponent slammed into the wall! (+15 DMG & Wide Open)")
                    target.hp -= 15
                    target.vulnerable = True
                    break
                
        if skill.name == "Whirlwind" and random.random() < 0.35 and not target.is_guarding:
            self.print_msg("  A sudden gust pushed the opponent back!")
            dir = 1 if target.pos > actor.pos else -1
            if FIELD_MIN <= target.pos + dir <= FIELD_MAX: target.pos += dir
            else:
                self.print_msg("  [WALL SLAM] Opponent slammed into the wall! (+15 DMG & Wide Open)")
                target.hp -= 15; target.vulnerable = True

        if target.is_flying and dmg >= 22:
            self.print_msg("  !! Knocked out of the sky by the heavy impact! (10 Fall DMG & Wide Open)")
            target.is_flying = False; target.hp -= 10; target.vulnerable = True

    def run(self):
        print("[Crystals on the Glassboard - Ver1.6.0 BARRIER REWORK]")
        while self.p1.is_alive() and self.p2.is_alive():
            for p in [self.p1, self.p2]:
                p.is_guarding = False
                p.vulnerable = False
                p.is_jumping = False
                
                # Recover +5 SP per turn when barrier is down; no natural regen while maintaining barrier
                if not p.barrier_active:
                    p.sp = min(p.max_sp, p.sp + 5)
                elif p.barrier_life > 0:
                    p.barrier_life -= 1
                    if p.barrier_life == 0:
                        p.barrier_active = False
                        self.print_msg(f"[{p.name}] Ice Shield dissipated!")

            self.print_status()

            act1 = self.ui_action(self.p1, self.get_valid_actions(self.p1, self.p2))
            act2 = self.cpu_action(self.p2, self.get_valid_actions(self.p2, self.p1))

            speed1 = self.p1.speed + random.randint(0, 3)
            speed2 = self.p2.speed + random.randint(0, 3)
            
            q = [
                (self.p1, self.p2, act1, act1[1], speed1),
                (self.p2, self.p1, act2, act2[1], speed2)
            ]
            q.sort(key=lambda x: (x[3], -x[4]))

            print("\n*** COMMAND OPEN ***")
            self.print_msg(f"P1 {self.p1.name}: {act1[0].name if isinstance(act1[0], Skill) else act1[0]}")
            self.print_msg(f"P2 {self.p2.name}: {act2[0].name if isinstance(act2[0], Skill) else act2[0]}")
            print("*"*23)

            for item in q:
                if item[0].is_alive() and item[1].is_alive():
                    self.resolve_action(item[0], item[1], item[2])

            self.turn_count += 1
        
        print("\n=== K.O. ===")
        winner = self.p1 if self.p1.is_alive() else self.p2
        print(f"Winner: {winner.name} !!")

    def ui_action(self, p, actions):
        if len(actions) == 1 and actions[0][0] == "Continue Chant": return actions[0]
        
        print(f">> Select Action for {p.name}:")
        for i, a in enumerate(actions):
            act_obj, prio, cost, usable, reason = a
            act_name = act_obj.name if isinstance(act_obj, Skill) else act_obj
            
            if usable:
                info = f"[Prio:{prio} | SP:{cost}]"
                if getattr(act_obj, "is_rush", False): info += " >Step 1 Forward First<"
                if isinstance(act_obj, Skill):
                    if act_obj.name == "Desperate Flash":
                        info += f" >{act_obj.desc}<"
                    else:
                        eff_r = self.get_effective_range(p, act_obj)
                        info += f" {act_obj.attr}/Pow:{act_obj.power}/Rng:{eff_r[0]}-{eff_r[1]}"
                        if act_obj.charge > 0:
                            if p.barrier_active and p.barrier_life == -1:
                                info += " [Barrier Resonance: Instant!]"
                            else:
                                info += " (1T Chant)"
                if getattr(act_obj, "desc", "") and act_name != "Desperate Flash":
                    info += f" - {act_obj.desc}"
                print(f"{i+1:>2}. {act_name} {info}")
            else:
                print(f"[{i+1:>2}. {act_name}] --- Unavailable ({reason}) ---")
            
        while True:
            try:
                x = int(input("No: ")) - 1
                if 0 <= x < len(actions):
                    if actions[x][3]: return actions[x]
                    else: print(" !! That action cannot be selected right now !!")
            except ValueError: pass

    def cpu_action(self, cpu, actions):
        valid_actions = [a for a in actions if a[3]]
        if len(valid_actions) == 1 and valid_actions[0][0] == "Continue Chant": return valid_actions[0]
        
        dist = self.get_dist()
        enemy = self.p1 if cpu == self.p2 else self.p2

        # 1. If enemy has a barrier up and is within Dist 2, actively try to shatter it
        if enemy.barrier_active and dist <= 2:
            brk = [a for a in valid_actions if a[0] == "Shatter Enemy Barrier"]
            if brk and random.random() < 0.55:
                return brk[0]

        # 2. Tactical routine for barrier-capable characters
        if cpu.can_barrier:
            # If barrier is not active and SP is sufficient, deploy immediately when enemy approaches or with high probability
            if not cpu.barrier_active and cpu.sp >= 35:
                barriers = [a for a in valid_actions if a[0] == "Deploy Barrier"]
                if barriers and (dist <= 2 or random.random() < 0.65):
                    return barriers[0]

            # While barrier is active and enemy is at Dist 0-1, unleash instant-cast grand magic or x1.4 skills
            if cpu.barrier_active and dist <= 1:
                atks = [a for a in valid_actions if isinstance(a[0], Skill) and a[0].name != "Desperate Flash"]
                if atks:
                    # Prioritize highest power moves (e.g., Greater Magic or Salamander)
                    atks.sort(key=lambda x: x[0].power, reverse=True)
                    return atks[0]

            # Miyuki Fujisawa's ultimate decision (distanced while barrier is active, or lethal threshold)
            if cpu.name == "Miyuki Fujisawa" and cpu.barrier_active:
                sutemi = [a for a in valid_actions if getattr(a[0], "name", "") == "Desperate Flash"]
                if sutemi and (dist >= 3 or enemy.hp <= 85 or cpu.hp <= 45) and random.random() < 0.65:
                    return sutemi[0]

            # While barrier is active and Dist >= 2, advance 2 spaces to drag enemy into the zone
            if cpu.barrier_active and dist >= 2:
                fwd = [a for a in valid_actions if a[0] == "Close Distance"]
                if fwd and random.random() < 0.8:
                    return fwd[0]

        # 3. Keiko Shirasawa's close-range denial logic
        if cpu.name == "Keiko Shirasawa" and dist <= 1:
            push = [a for a in valid_actions if getattr(a[0], "name", "") == "Wind Push"]
            if push: return push[0]
            back = [a for a in valid_actions if a[0] == "Step Back"]
            if back and cpu.pos not in [FIELD_MIN, FIELD_MAX]: return back[0]

        # 4. Guard/recover when low on SP
        if cpu.sp < 20:
            guards = [a for a in valid_actions if "Wait & See" in str(a[0])]
            if guards and random.random() < 0.8: return guards[0]

        # 5. Select a valid attack skill within range
        valid_atks = []
        for a in valid_actions:
            if isinstance(a[0], Skill) and a[0].name != "Desperate Flash":
                eff_dist = max(0, dist - 1) if getattr(a[0], "is_rush", False) else dist
                eff_r = self.get_effective_range(cpu, a[0])
                if eff_r[0] <= eff_dist <= eff_r[1]:
                    valid_atks.append(a)

        if valid_atks and random.random() < 0.75:
            return random.choice(valid_atks)
            
        if cpu.name != "Keiko Shirasawa" and dist > 1:
            fwds = [a for a in valid_actions if a[0] == "Close Distance"]
            if fwds: return fwds[0]

        safe_acts = [a for a in valid_actions if not isinstance(a[0], Skill)]
        return random.choice(safe_acts if safe_acts else valid_actions)

def create_characters():
    chars = []
    
    c = Fighter("Miyuki Fujisawa", hp=105, sp=100, atk=12, mag=22, speed=12, desc="Protagonist / Barrier rush-in & ultimate finisher")
    c.can_barrier = True
    c.add_skill(Skill("Magic Arrow", 20, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15, desc="Sure-hit & x1.4 at Dist 0-1 in Barrier"))
    c.add_skill(Skill("Desperate Flash", 75, [0,6], ATTR_MAG, PRIO_SYSTEM, 0, req_barrier=True, desc="Unavoidable homing / Pierces guard / Self-DMG 20, SP->0"))
    chars.append(c)
    
    c = Fighter("Rei", hp=105, sp=120, atk=10, mag=28, speed=11, desc="Mage / Instant-cast Greater Magic in Barrier is lethal")
    c.can_barrier = True
    c.add_skill(Skill("Magic Arrow", 20, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15))
    c.add_skill(Skill("Greater Magic", 45, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 35, charge=1, desc="Grand magic (Instant-cast & Dist 0-1 in Barrier)"))
    chars.append(c)

    c = Fighter("Toshikazu Azuchi", hp=115, sp=95, atk=16, mag=25, speed=11, desc="Pyromancer / No-chant mid-to-close range attacker")
    c.add_skill(Skill("Fireball", 28, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="Reliable instant-cast flame shot"))
    c.add_skill(Skill("Flame Burst", 35, [0,1], ATTR_MAG, PRIO_FAST_ATK, 25, desc="Close-range defensive blast"))
    chars.append(c)

    c = Fighter("Masahiro Hayashi", hp=120, sp=85, atk=26, mag=14, speed=13, desc="Ice Brawler / Ice Shield & high-speed rush")
    c.add_skill(Skill("Ice Knuckle", 26, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="Physical (Pierces Barrier)"))
    c.add_skill(Skill("Ice Slide (Rush)", 18, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="Rush strike with effective range 1-2"))
    chars.append(c)

    c = Fighter("Haruka Yamaguchi", hp=95, sp=110, atk=10, mag=27, speed=13, desc="Spirit Summoner / Instant-cast Salamander in Barrier")
    c.can_barrier = True
    c.add_skill(Skill("Spirit Dart", 16, [1,3], ATTR_MAG, PRIO_FAST_ATK, 12, desc="Spirit shot for poking"))
    c.add_skill(Skill("Salamander", 50, [0,4], ATTR_MAG, PRIO_SLOW_ATK, 30, charge=1, desc="High-power summon (Instant-cast in Barrier)"))
    chars.append(c)

    c = Fighter("Silreim", hp=135, sp=85, atk=28, mag=5, speed=11, desc="Heavy Swordsman / High durability & steady physical")
    c.add_skill(Skill("Broadsword", 30, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="Physical (Pierces Barrier)"))
    c.add_skill(Skill("Step-In", 20, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="Advancing slash with effective range 1-2"))
    chars.append(c)

    c = Fighter("Kenji Hayashi", hp=120, sp=80, atk=35, mag=5, speed=12, desc="Greatsword Master / Massive power, wide swings")
    c.add_skill(Skill("Flamberge", 38, [0,1], ATTR_PHYS, PRIO_SLOW_ATK, 20, desc="Slow but devastating greatsword slash"))
    c.add_skill(Skill("Fierce Pursuit", 22, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 25, is_rush=True, desc="High-speed rushing slash with effective range 1-2"))
    chars.append(c)

    c = Fighter("Keiko Shirasawa", hp=95, sp=105, atk=8, mag=30, speed=13, desc="Wind Mage / Long-range specialist (Takes x1.4 melee DMG)")
    c.add_skill(Skill("Whirlwind", 26, [2,6], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="Higher power at long range + Knockback"))
    c.add_skill(Skill("Wind Push", 12, [0,1], ATTR_MAG, PRIO_DEFEND, 15, desc="Fastest startup / Pushes enemy back 2 spaces"))
    chars.append(c)
    
    c = Fighter("Blau", hp=130, sp=95, atk=24, mag=22, speed=9, desc="Wyvern / Aerial evasion, breath & claw attacks")
    c.add_skill(Skill("Fire Breath", 32, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="Mid-range breath attack"))
    c.add_skill(Skill("Dragon Claw", 26, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="Close-range physical (Pierces Barrier)"))
    c.is_flying = True
    chars.append(c)
    
    return chars

def main():
    chars = create_characters()
    print("Select your character:")
    for i, c in enumerate(chars):
        print(f"{i+1}. {c.name:<18} (HP:{c.max_hp:>3} SP:{c.max_sp:>3} ATK:{c.atk:>2} MAG:{c.mag:>2} SPD:{c.speed:>2}) - {c.desc}")
    try: player = chars[int(input("No: ")) - 1]
    except: player = chars[0]
        
    enemy = copy.deepcopy(random.choice([c for c in chars if c.name != player.name]))
    Game(player, enemy).run()

if __name__ == "__main__":
    main()
    inp = input("Hit ENTER key to exit : ")
