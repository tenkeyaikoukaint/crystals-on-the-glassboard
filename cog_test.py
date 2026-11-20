import random
import time
import copy

# --- 定数定義 ---
FIELD_MIN = 0
FIELD_MAX = 6

ATTR_PHYS = "物理"
ATTR_MAG = "魔法"

# 優先度（フレーム：数字が小さいほど先に動く）
PRIO_SYSTEM = 0   # 最速（超必殺技・システム処理）
PRIO_DEFEND = 1   # 回避、防御、結界構築・解除、拒否技
PRIO_FAST_ATK = 2 # 牽制攻撃、突進技
PRIO_MOVE = 3     # 通常の前進、結界削り
PRIO_SLOW_ATK = 4 # 大技、大魔法、詠唱完了発動

# --- クラス定義 ---
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

        # シミュレーション統計用フラグ
        self.used_barrier = False

    def add_skill(self, skill):
        self.skills.append(skill)

    def is_alive(self): return self.hp > 0
    def is_in_barrier_zone(self, dist): return self.barrier_active and self.barrier_life == -1 and dist <= 1

# --- ゲームシステム ---
class Game:
    def __init__(self, p1, p2, silent=False):
        self.p1 = p1
        self.p2 = p2
        self.p1.pos = 1
        self.p2.pos = 5
        self.turn_count = 1
        self.silent = silent

    def get_dist(self): return abs(self.p1.pos - self.p2.pos)

    def print_msg(self, text):
        if not self.silent:
            print(text)
            time.sleep(0.35)

    def draw_field(self):
        if self.silent: return
        field = ["＿"] * (FIELD_MAX + 1)
        if self.p1.pos == self.p2.pos: field[self.p1.pos] = "激" 
        else:
            field[self.p1.pos] = "①"
            field[self.p2.pos] = "②"
        print(f"\n【壁】 {' '.join(field)} 【壁】 (間合い: {self.get_dist()})")

    def print_status(self):
        if self.silent: return
        print(f"\n{'='*15} Turn {self.turn_count} {'='*15}")
        self.draw_field()
        for i, p in enumerate([self.p1, self.p2]):
            st = []
            if p.pos == FIELD_MIN or p.pos == FIELD_MAX: st.append("<壁際>")
            if p.charge_skill: st.append(f"<詠唱中:{p.charge_skill.name}>")
            if p.barrier_active:
                if p.barrier_life > 0: st.append(f"[氷盾(残{p.barrier_life})]")
                else: st.append("【結界展開中(近接強化/無詠唱/物理反射)】") 
            if p.is_flying: st.append("<飛行中>")
            if p.vulnerable: st.append("<大隙!!>")
            if p.name == "白沢恵子" and self.get_dist() <= 1: st.append("<近接危険!>")
            
            print(f"P{i+1} {p.name}: HP {int(p.hp):>3}/{p.max_hp} | SP {int(p.sp):>3}/{p.max_sp} " + " ".join(st))
        print("="*42)

    def get_effective_range(self, actor, skill):
        if actor.barrier_active and actor.barrier_life == -1 and skill.name != "捨て身のフラッシュ":
            return [0, 1]
        return skill.range_req

    def get_valid_actions(self, actor, enemy):
        if actor.charge_skill:
            return [("詠唱継続", PRIO_SLOW_ATK, 0, True, "")]
            
        acts = []
        dist = self.get_dist()
        
        for s in actor.skills:
            usable = True
            reason = ""
            if actor.sp < s.sp_cost: 
                usable = False; reason = "SP不足"
            elif getattr(s, 'req_barrier', False) and not (actor.barrier_active and actor.barrier_life == -1): 
                usable = False; reason = "結界領域が必要"
            elif actor.barrier_active and actor.barrier_life == -1 and s.name != "捨て身のフラッシュ" and dist >= 2:
                usable = False; reason = "結界外(距離2以上)へは攻撃不可・接近が必要"
                
            acts.append((s, s.priority, s.sp_cost, usable, reason))

        acts.append(("様子見（防御・SP回復）", PRIO_DEFEND, 0, True, ""))

        if actor.barrier_active and actor.barrier_life == -1:
            acts.append(("結界を解く", PRIO_DEFEND, 0, True, "解除＋SP15回収"))
        elif not actor.barrier_active:
            if actor.can_barrier:
                u_barrier = actor.sp >= 20
                acts.append(("結界構築", PRIO_DEFEND, 20, u_barrier, "SP不足" if not u_barrier else "即時展開・近接無詠唱化"))
            if actor.name == "林正洋":
                u_ice = actor.sp >= 20
                acts.append(("アイスシールド", PRIO_DEFEND, 20, u_ice, "SP不足" if not u_ice else "2T魔法半減＋物理反撃"))

        u_break = enemy.barrier_active and dist <= 2 and actor.sp >= 10
        acts.append(("相手の結界をけずる", PRIO_MOVE, 10, u_break, "距離2以内＆相手結界時のみ" if not u_break else "1マス前進＋結界粉砕"))

        acts.append(("間合いを詰める", PRIO_MOVE, 5, actor.sp >= 5 and dist > 0, "密着中" if dist == 0 else "SP不足"))
        acts.append(("ステップバック", PRIO_DEFEND, 15, actor.sp >= 15, "SP不足"))

        if actor.name != "ブラウ" and not actor.is_jumping:
            acts.append(("ジャンプ", PRIO_DEFEND, 15, actor.sp >= 15, "SP不足"))
        if actor.name == "ブラウ" and not actor.is_flying:
            acts.append(("飛行", PRIO_DEFEND, 20, actor.sp >= 20, "SP不足"))

        return acts

    def resolve_action(self, actor, target, act_obj):
        if not actor.is_alive(): return
        act, prio, cost, usable, reason = act_obj
        
        if act == "詠唱継続":
            if not actor.charge_skill:
                self.print_msg(f"★ {actor.name}は詠唱を中断されており動けない！")
                return
            actor.charge_wait -= 1
            if actor.charge_wait <= 0:
                s = actor.charge_skill
                actor.charge_skill = None
                self.print_msg(f"\n★ {actor.name}の詠唱完了！ 「{s.name}」発動！")
                self.fire_skill(actor, target, s)
            else:
                self.print_msg(f"\n★ {actor.name}は詠唱継続中... (あと{actor.charge_wait})")
            return

        self.print_msg(f"\n★ {actor.name}のアクション: {act.name if isinstance(act, Skill) else act}")
        actor.sp -= cost
        dist = self.get_dist()

        if act == "様子見（防御・SP回復）":
            actor.is_guarding = True
            actor.sp = min(actor.max_sp, actor.sp + 35)
            self.print_msg("  防御を固めた！(ダメージ半減＆SP+35回復)")
            return

        if act == "間合いを詰める":
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                steps = 2 if (actor.barrier_active and actor.barrier_life == -1 and dist >= 2) else 1
                for _ in range(steps):
                    if actor.pos != target.pos:
                        actor.pos += dir
                if steps == 2:
                    self.print_msg(f"  結界領域ごと一気に間合いを詰めた！ (間合い: {self.get_dist()})")
                else:
                    self.print_msg(f"  前に出た！ (間合い: {self.get_dist()})")
            else:
                self.print_msg("  すでに密着している！")
            return
            
        if act == "ステップバック":
            dir = -1 if target.pos > actor.pos else 1
            new_pos = actor.pos + dir
            if FIELD_MIN <= new_pos <= FIELD_MAX:
                actor.pos = new_pos
                self.print_msg(f"  素早く後ろへ下がった！ (間合い: {self.get_dist()})")
            else:
                self.print_msg("  しかし背後は壁だ！ 下がれない！(大きな隙が発生)")
                actor.vulnerable = True
            return

        if act in ["ジャンプ", "飛行"]:
            if act == "ジャンプ":
                actor.is_jumping = True
                self.print_msg("  高く跳躍した！(このターンの被弾率大幅減)")
            else:
                actor.is_flying = True
                self.print_msg("  空中に舞い上がった！(回避率UP・攻撃力1.2倍)")
            return

        if act == "結界構築":
            actor.barrier_active = True
            actor.barrier_life = -1
            actor.used_barrier = True
            self.print_msg("  【結界領域・即時展開！】")
            self.print_msg("  (効果: 被魔法半減 / 物理被弾時に反射ダメージ / 距離0-1で全スキル無詠唱＆威力1.4倍)")
            return

        if act == "結界を解く":
            actor.barrier_active = False
            actor.sp = min(actor.max_sp, actor.sp + 15)
            self.print_msg("  結界を自ら解除し、魔力を回収した！(SP+15)")
            return

        if act == "アイスシールド":
            actor.barrier_active = True
            actor.barrier_life = 2
            actor.used_barrier = True
            self.print_msg("  氷の盾を展開した！(2ターン魔法半減・物理被弾時に冷気反撃)")
            return
            
        if act == "相手の結界をけずる":
            if dist <= 2 and target.barrier_active:
                if dist >= 1:
                    dir = 1 if target.pos > actor.pos else -1
                    actor.pos += dir
                    self.print_msg(f"  踏み込みながら相手の結界に干渉！ (間合い: {self.get_dist()})")

                if self.get_dist() <= 1:
                    dmg = 15 + max(actor.atk, actor.mag) // 2
                    if target.is_guarding:
                        self.print_msg("  ガードブレイク！ 防御ごと結界を砕く！")
                        dmg = int(dmg * 1.5)
                    target.hp -= dmg
                    target.barrier_active = False
                    target.vulnerable = True
                    self.print_msg(f"  相手の結界を粉砕し、{dmg}ダメージ＆大隙を与えた！")
                else:
                    self.print_msg("  【空振り】 相手が遠すぎて届かなかった！(隙が発生)")
                    actor.vulnerable = True
            else:
                self.print_msg("  【空振り】 すでに結界がないか遠すぎる！(隙が発生)")
                actor.vulnerable = True
            return

        if isinstance(act, Skill):
            if act.charge > 0:
                if actor.barrier_active and actor.barrier_life == -1:
                    self.print_msg(f"  【結界共鳴】 詠唱を省略し、「{act.name}」を即時発動！！")
                else:
                    actor.charge_skill = act
                    actor.charge_wait = act.charge
                    self.print_msg(f"  「{act.name}」の詠唱を開始した！(次ターン発動)")
                    return

            self.fire_skill(actor, target, act)

    def fire_skill(self, actor, target, skill):
        if skill.name == "捨て身のフラッシュ":
            actor.barrier_active = False
            actor.pos = target.pos
            self.print_msg(f"\n！！！ {actor.name}は自らの結界を限界まで圧縮した ！！！")
            self.print_msg("「これで……決めるッ！」")
            self.print_msg(f"  結界を大爆発させ、閃光となって{target.name}の懐へ超突進！！")
            actor.hp = max(1, actor.hp - 20)
            actor.sp = 0
            actor.vulnerable = True

        elif getattr(skill, "is_rush", False):
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                actor.pos += dir
                self.print_msg(f"  鋭く踏み込んだ！！ (間合い: {self.get_dist()})")
        
        current_dist = self.get_dist()
        eff_range = self.get_effective_range(actor, skill)
        
        if skill.name != "捨て身のフラッシュ":
            if actor.barrier_active and actor.barrier_life == -1 and current_dist >= 2:
                self.print_msg("  【不発!!】 相手が結界領域の外(距離2以上)に離れたため届かない！(大隙)")
                actor.vulnerable = True
                return
            if not (eff_range[0] <= current_dist <= eff_range[1]):
                self.print_msg("  【空振り!!】 間合いが合わず、攻撃は空を切った！(大隙)")
                actor.vulnerable = True
                return

        self.resolve_skill(actor, target, skill, current_dist)

    def calculate_damage(self, attacker, defender, skill, dist):
        base = attacker.atk if skill.attr == ATTR_PHYS else attacker.mag
        dmg = base + skill.power

        if attacker.name == "白沢恵子" and skill.name == "ワールウィンド":
            dmg *= (0.7 + (dist * 0.15)) 

        if attacker.is_flying: dmg *= 1.2
        
        if skill.name != "捨て身のフラッシュ":
            if attacker.is_in_barrier_zone(dist): 
                dmg *= 1.4 
                
            if defender.barrier_active:
                if skill.attr == ATTR_PHYS:
                    pass
                else:
                    dmg *= 0.5

            if defender.is_guarding: dmg *= 0.5

        if defender.name == "白沢恵子" and dist <= 1: dmg *= 1.4 
        if defender.vulnerable: dmg *= 1.4

        return int(dmg)

    def resolve_skill(self, actor, target, skill, dist=None):
        if dist is None: dist = self.get_dist()
        
        hit_rate = 1.0
        if target.is_jumping: hit_rate = 0.35
        elif target.is_flying: hit_rate = 0.70
        if actor.is_in_barrier_zone(dist): hit_rate = 1.0
        
        if random.random() > hit_rate and skill.name != "捨て身のフラッシュ":
            self.print_msg(f"  {target.name}は空中で攻撃を華麗にかわした！")
            return

        dmg = self.calculate_damage(actor, target, skill, dist)
        target.hp -= dmg
        
        msg = f"  命中！ {target.name}に{dmg}のダメージ！"
        
        if skill.name == "捨て身のフラッシュ":
            msg += " 【結界・防御貫通の致命傷!!】"
            if target.barrier_active:
                target.barrier_active = False
                self.print_msg("  相手の結界が粉々に砕け散った！")
        else:
            if target.barrier_active:
                if skill.attr == ATTR_PHYS:
                    msg += " 【物理貫通!!】"
                else:
                    msg += " (結界で魔法半減)"
                        
            if actor.is_in_barrier_zone(dist):
                msg += " 【結界領域バフ(必中＆1.4倍)!!】"

            if target.vulnerable: msg += " 【カウンターヒット(1.4倍)!!】"
            elif target.is_guarding: msg += " (ガード半減)"
            
        self.print_msg(msg)

        if target.barrier_active and skill.attr == ATTR_PHYS and skill.name != "捨て身のフラッシュ":
            thorn_dmg = max(10, target.mag // 2)
            actor.hp -= thorn_dmg
            self.print_msg(f"  ⚡【結界反撃】 結界の魔力障壁が弾け、{actor.name}に{thorn_dmg}の反射ダメージ！")

        if target.charge_skill and dmg >= 20:
            self.print_msg(f"  ！！ {target.name}の詠唱が中断された！")
            target.charge_skill = None
            target.charge_wait = 0

        if skill.name == "ウィンドプッシュ":
            self.print_msg("  風圧で相手を2マス吹き飛ばす！")
            dir = 1 if target.pos > actor.pos else -1
            for _ in range(2):
                if FIELD_MIN <= target.pos + dir <= FIELD_MAX:
                    target.pos += dir
                else:
                    self.print_msg("  【壁激突】 相手は壁に叩きつけられた！(追加15ダメージ＆大隙)")
                    target.hp -= 15
                    target.vulnerable = True
                    break
                
        if skill.name == "ワールウィンド" and random.random() < 0.35 and not target.is_guarding:
            self.print_msg("  突風が相手を押し流す！")
            dir = 1 if target.pos > actor.pos else -1
            if FIELD_MIN <= target.pos + dir <= FIELD_MAX: target.pos += dir
            else:
                self.print_msg("  【壁激突】 相手は壁に叩きつけられた！(追加15ダメージ＆大隙)")
                target.hp -= 15; target.vulnerable = True

        if target.is_flying and dmg >= 22:
            self.print_msg("  ！！ 強い衝撃で撃ち落とされた！(落下10ダメージ＆大隙)")
            target.is_flying = False; target.hp -= 10; target.vulnerable = True

    def step_turn(self, auto_p1=False):
        for p in [self.p1, self.p2]:
            p.is_guarding = False
            p.vulnerable = False
            p.is_jumping = False
            
            if not p.barrier_active:
                p.sp = min(p.max_sp, p.sp + 5)
            elif p.barrier_life > 0:
                p.barrier_life -= 1
                if p.barrier_life == 0:
                    p.barrier_active = False
                    self.print_msg(f"[{p.name}] アイスシールドが消滅した！")

        self.print_status()

        if auto_p1:
            act1 = self.cpu_action(self.p1, self.get_valid_actions(self.p1, self.p2))
        else:
            act1 = self.ui_action(self.p1, self.get_valid_actions(self.p1, self.p2))
        act2 = self.cpu_action(self.p2, self.get_valid_actions(self.p2, self.p1))

        speed1 = self.p1.speed + random.randint(0, 3)
        speed2 = self.p2.speed + random.randint(0, 3)
        
        q = [
            (self.p1, self.p2, act1, act1[1], speed1),
            (self.p2, self.p1, act2, act2[1], speed2)
        ]
        q.sort(key=lambda x: (x[3], -x[4]))

        if not self.silent:
            print("\n★★★ COMMAND OPEN ★★★")
            self.print_msg(f"P1 {self.p1.name}: {act1[0].name if isinstance(act1[0], Skill) else act1[0]}")
            self.print_msg(f"P2 {self.p2.name}: {act2[0].name if isinstance(act2[0], Skill) else act2[0]}")
            print("★"*23)

        for item in q:
            if item[0].is_alive() and item[1].is_alive():
                self.resolve_action(item[0], item[1], item[2])

        self.turn_count += 1

    def run(self):
        print("【Crystals on the Glassboard - Ver1.6.0 BARRIER REWORK】")
        while self.p1.is_alive() and self.p2.is_alive():
            self.step_turn(auto_p1=False)
        
        print("\n=== K.O. ===")
        winner = self.p1 if self.p1.is_alive() else self.p2
        print(f"勝者: {winner.name} !!")

    def run_headless(self, max_turns=100):
        while self.p1.is_alive() and self.p2.is_alive() and self.turn_count <= max_turns:
            self.step_turn(auto_p1=True)
            
        # 決着判定（最大ターン到達時はHP割合が高い方の判定勝ち）
        if self.p1.is_alive() and not self.p2.is_alive():
            return self.p1
        elif self.p2.is_alive() and not self.p1.is_alive():
            return self.p2
        else:
            r1 = self.p1.hp / self.p1.max_hp
            r2 = self.p2.hp / self.p2.max_hp
            if r1 != r2:
                return self.p1 if r1 > r2 else self.p2
            return random.choice([self.p1, self.p2])

    def ui_action(self, p, actions):
        if len(actions) == 1 and actions[0][0] == "詠唱継続": return actions[0]
        
        print(f">> {p.name} の行動選択:")
        for i, a in enumerate(actions):
            act_obj, prio, cost, usable, reason = a
            act_name = act_obj.name if isinstance(act_obj, Skill) else act_obj
            
            if usable:
                info = f"[優先:{prio} | SP:{cost}]"
                if getattr(act_obj, "is_rush", False): info += " ＞1マス前進後＜"
                if isinstance(act_obj, Skill):
                    if act_obj.name == "捨て身のフラッシュ":
                        info += f" ＞{act_obj.desc}＜"
                    else:
                        eff_r = self.get_effective_range(p, act_obj)
                        info += f" {act_obj.attr}/威力:{act_obj.power}/射程:{eff_r[0]}-{eff_r[1]}"
                        if act_obj.charge > 0:
                            if p.barrier_active and p.barrier_life == -1:
                                info += " 【結界共鳴:無詠唱!】"
                            else:
                                info += " (1T詠唱)"
                if getattr(act_obj, "desc", "") and act_name != "捨て身のフラッシュ": 
                    info += f" - {act_obj.desc}"
                print(f"{i+1:>2}. {act_name} {info}")
            else:
                print(f"[{i+1:>2}. {act_name}] --- 選択不可 ({reason}) ---")
            
        while True:
            try:
                x = int(input("No: ")) - 1
                if 0 <= x < len(actions):
                    if actions[x][3]: return actions[x]
                    else: print(" !! その行動は現在選択できません !!")
            except ValueError: pass

    def cpu_action(self, cpu, actions):
        valid_actions = [a for a in actions if a[3]]
        if len(valid_actions) == 1 and valid_actions[0][0] == "詠唱継続": return valid_actions[0]
        
        dist = self.get_dist()
        enemy = self.p1 if cpu == self.p2 else self.p2

        # 1. 相手が結界を張っており、距離2以内なら「結界をけずる」を積極的に狙う
        if enemy.barrier_active and dist <= 2:
            brk = [a for a in valid_actions if a[0] == "相手の結界をけずる"]
            if brk and random.random() < 0.55:
                return brk[0]

        # 2. 結界持ちキャラの戦術ルーチン
        if cpu.can_barrier:
            if not cpu.barrier_active and cpu.sp >= 35:
                barriers = [a for a in valid_actions if a[0] == "結界構築"]
                if barriers and (dist <= 2 or random.random() < 0.65):
                    return barriers[0]

            if cpu.barrier_active and dist <= 1:
                atks = [a for a in valid_actions if isinstance(a[0], Skill) and a[0].name != "捨て身のフラッシュ"]
                if atks:
                    atks.sort(key=lambda x: x[0].power, reverse=True)
                    return atks[0]

            if cpu.name == "藤沢美幸" and cpu.barrier_active:
                sutemi = [a for a in valid_actions if getattr(a[0], "name", "") == "捨て身のフラッシュ"]
                if sutemi and (dist >= 3 or enemy.hp <= 85 or cpu.hp <= 45) and random.random() < 0.65:
                    return sutemi[0]

            if cpu.barrier_active and dist >= 2:
                fwd = [a for a in valid_actions if a[0] == "間合いを詰める"]
                if fwd and random.random() < 0.8:
                    return fwd[0]

        # 林正洋のアイスシールド判断
        if cpu.name == "林正洋" and not cpu.barrier_active and cpu.sp >= 35 and dist <= 2:
            ice = [a for a in valid_actions if a[0] == "アイスシールド"]
            if ice and random.random() < 0.45:
                return ice[0]

        # 3. 白沢恵子の近接拒否ロジック
        if cpu.name == "白沢恵子" and dist <= 1:
            push = [a for a in valid_actions if getattr(a[0], "name", "") == "ウィンドプッシュ"]
            if push: return push[0]
            back = [a for a in valid_actions if a[0] == "ステップバック"]
            if back and cpu.pos not in [FIELD_MIN, FIELD_MAX]: return back[0]

        # 4. SP枯渇時は様子見
        if cpu.sp < 20:
            guards = [a for a in valid_actions if "様子見" in str(a[0])]
            if guards and random.random() < 0.8: return guards[0]

        # 5. 射程内の有効な攻撃スキルを選択
        valid_atks = []
        for a in valid_actions:
            if isinstance(a[0], Skill) and a[0].name != "捨て身のフラッシュ":
                eff_dist = max(0, dist - 1) if getattr(a[0], "is_rush", False) else dist
                eff_r = self.get_effective_range(cpu, a[0])
                if eff_r[0] <= eff_dist <= eff_r[1]:
                    valid_atks.append(a)

        if valid_atks and random.random() < 0.75:
            return random.choice(valid_atks)
            
        if cpu.name != "白沢恵子" and dist > 1:
            fwds = [a for a in valid_actions if a[0] == "間合いを詰める"]
            if fwds: return fwds[0]

        safe_acts = [a for a in valid_actions if not isinstance(a[0], Skill)]
        return random.choice(safe_acts if safe_acts else valid_actions)

def create_characters():
    chars = []
    
    c = Fighter("藤沢美幸", hp=105, sp=100, atk=12, mag=22, speed=12, desc="主人公/結界急接近と超必殺技")
    c.can_barrier = True
    c.add_skill(Skill("マジックアロー", 20, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15, desc="結界時は距離0-1必中＆1.4倍"))
    c.add_skill(Skill("捨て身のフラッシュ", 75, [0,6], ATTR_MAG, PRIO_SYSTEM, 0, req_barrier=True, desc="絶対追尾・防御貫通・自傷20/SP0"))
    chars.append(c)
    
    c = Fighter("黎", hp=105, sp=120, atk=10, mag=28, speed=11, desc="魔導師/結界内の無詠唱グレーターが脅威")
    c.can_barrier = True
    c.add_skill(Skill("マジックアロー", 20, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15))
    c.add_skill(Skill("グレーターマジック", 45, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 35, charge=1, desc="大魔法(結界時は無詠唱＆距離0-1)"))
    chars.append(c)

    c = Fighter("安土利一", hp=115, sp=95, atk=16, mag=25, speed=11, desc="炎術師/無詠唱の中・近距離アタッカー")
    c.add_skill(Skill("ファイアボール", 28, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="安定した無詠唱炎撃")) 
    c.add_skill(Skill("フレイムバースト", 35, [0,1], ATTR_MAG, PRIO_FAST_ATK, 25, desc="近接迎撃の爆炎"))
    chars.append(c)

    c = Fighter("林正洋", hp=120, sp=85, atk=26, mag=14, speed=13, desc="氷格闘/氷盾と高速突進")
    c.add_skill(Skill("アイスナックル", 26, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="物理(結界貫通)"))
    c.add_skill(Skill("氷滑り(突進)", 18, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="実効射程1-2の突進打撃")) 
    chars.append(c)

    c = Fighter("山口春香", hp=95, sp=110, atk=10, mag=27, speed=13, desc="精霊使い/結界内の無詠唱サラマンダー")
    c.can_barrier = True
    c.add_skill(Skill("スピリットダート", 16, [1,3], ATTR_MAG, PRIO_FAST_ATK, 12, desc="牽制用の精霊弾"))
    c.add_skill(Skill("サラマンダー", 50, [0,4], ATTR_MAG, PRIO_SLOW_ATK, 30, charge=1, desc="高火力召喚(結界時は無詠唱)"))
    chars.append(c)

    c = Fighter("シルレイム", hp=135, sp=85, atk=28, mag=5, speed=11, desc="重装剣士/高耐久・安定物理")
    c.add_skill(Skill("ブロードソード", 30, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="物理(結界貫通)"))
    c.add_skill(Skill("ステップイン", 20, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="実効射程1-2の踏み込み斬り")) 
    chars.append(c)

    c = Fighter("林健次", hp=120, sp=80, atk=35, mag=5, speed=12, desc="剛剣士/超火力・大振り")
    c.add_skill(Skill("フランベルジュ", 38, [0,1], ATTR_PHYS, PRIO_SLOW_ATK, 20, desc="遅いが強烈な大剣斬り"))
    c.add_skill(Skill("猛追撃", 22, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 25, is_rush=True, desc="実効射程1-2の高速突進斬り")) 
    chars.append(c)

    c = Fighter("白沢恵子", hp=95, sp=105, atk=8, mag=30, speed=13, desc="風術師/遠距離特化(近接被ダメ1.4倍)")
    c.add_skill(Skill("ワールウィンド", 26, [2,6], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="遠距離ほど高威力＋吹き飛ばし")) 
    c.add_skill(Skill("ウィンドプッシュ", 12, [0,1], ATTR_MAG, PRIO_DEFEND, 15, desc="最速発生・2マス突き放し")) 
    chars.append(c)
    
    c = Fighter("ブラウ", hp=130, sp=95, atk=24, mag=22, speed=9, desc="飛竜/飛行回避とブレス・爪撃")
    c.add_skill(Skill("ファイアーブレス", 32, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20, desc="中距離ブレス"))
    c.add_skill(Skill("ドラゴンクロー", 26, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="近接物理(結界貫通)"))
    c.is_flying = True
    chars.append(c)
    
    return chars

# --- 総当たりシミュレーター ---
def run_tournament(matches_per_pair=100):
    base_chars = create_characters()
    n = len(base_chars)
    names = [c.name for c in base_chars]
    short_names = [name[:3] for name in names]

    # wins[i][j] = キャラi が キャラj に勝った回数
    wins = [[0] * n for _ in range(n)]
    total_turns = 0
    total_matches = 0
    barrier_uses = {c.name: 0 for c in base_chars}
    barrier_wins = {c.name: 0 for c in base_chars}

    t0 = time.time()
    print(f"\n全キャラ総当たりシミュレーション実行中 (各カード {matches_per_pair} 戦 / 計 {n*(n-1)*matches_per_pair//2} 試合)...")

    for i in range(n):
        for j in range(i + 1, n):
            for m in range(matches_per_pair):
                c1 = copy.deepcopy(base_chars[i])
                c2 = copy.deepcopy(base_chars[j])
                
                # P1/P2の初期位置による有利不利をなくすため、1戦ごとに左右を入れ替える
                if m % 2 == 0:
                    game = Game(c1, c2, silent=True)
                else:
                    game = Game(c2, c1, silent=True)
                    
                winner = game.run_headless()
                total_turns += game.turn_count
                total_matches += 1

                if c1.used_barrier:
                    barrier_uses[c1.name] += 1
                    if winner == c1: barrier_wins[c1.name] += 1
                if c2.used_barrier:
                    barrier_uses[c2.name] += 1
                    if winner == c2: barrier_wins[c2.name] += 1

                if winner == c1:
                    wins[i][j] += 1
                else:
                    wins[j][i] += 1

    elapsed = time.time() - t0
    print(f"完了！ ({elapsed:.2f}秒 / 平均決着ターン: {total_turns / total_matches:.1f} Turn)\n")

    # 勝率マトリクス表示
    header = "キャラ名   | " + " ".join([f"{sn:>4}" for sn in short_names]) + " | 総合勝率"
    print("=" * len(header))
    print("【勝率マトリクス (単位: % / 横が自キャラ・縦が対戦相手)】")
    print("-" * len(header))
    print(header)
    print("-" * len(header))

    ranking = []
    for i in range(n):
        row_cells = []
        total_w = sum(wins[i])
        total_g = matches_per_pair * (n - 1)
        win_rate = (total_w / total_g) * 100
        ranking.append((names[i], win_rate, total_w, total_g))

        for j in range(n):
            if i == j:
                row_cells.append("  - ")
            else:
                rate = int(round((wins[i][j] / matches_per_pair) * 100))
                row_cells.append(f"{rate:>3}% ")
        print(f"{names[i]:<6} | " + "".join(row_cells) + f"|  {win_rate:>5.1f}%")
    print("=" * len(header))

    # 総合ランキング表示
    ranking.sort(key=lambda x: x[1], reverse=True)
    print("\n【総合勝率ランキング】")
    for rank, (name, rate, w, g) in enumerate(ranking, 1):
        b_info = ""
        if barrier_uses[name] > 0:
            b_win_rate = (barrier_wins[name] / barrier_uses[name]) * 100
            b_info = f" (結界・氷盾展開数: {barrier_uses[name]}回 / 展開時勝率: {b_win_rate:.1f}%)"
        print(f"  {rank}位: {name:<6} - 勝率 {rate:>5.1f}% ({w:>3}勝 {g-w:>3}敗){b_info}")

def main():
    print("モードを選択してください:")
    print("1. 通常対戦プレイ (Player vs CPU)")
    print("2. 全キャラ総当たりAIシミュレーション (各100戦)")
    mode = input("No (1 or 2): ").strip()

    if mode == "2":
        run_tournament(matches_per_pair=100)
        return

    chars = create_characters()
    print("\n使用キャラを選択:")
    for i, c in enumerate(chars):
        print(f"{i+1}. {c.name:<6} (HP:{c.max_hp:>3} SP:{c.max_sp:>3} ATK:{c.atk:>2} MAG:{c.mag:>2} SPD:{c.speed:>2}) - {c.desc}")
    try: player = chars[int(input("No: ")) - 1]
    except: player = chars[0]
        
    enemy = copy.deepcopy(random.choice([c for c in chars if c.name != player.name]))
    Game(player, enemy).run()

if __name__ == "__main__":
    main()
    inp = input("\nHit ENTER key to exit : ")
