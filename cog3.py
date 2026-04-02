import random
import time
import copy

# --- 定数定義 ---
FIELD_MIN = 0
FIELD_MAX = 6

ATTR_PHYS = "物理"
ATTR_MAG = "魔法"

# 優先度（フレーム：数字が小さいほど先に動く）
PRIO_SYSTEM = 0   # 最速
PRIO_DEFEND = 1   # 回避、結界、結界解除
PRIO_FAST_ATK = 2 # 基本攻撃、突進技
PRIO_MOVE = 3     # 通常の前進
PRIO_SLOW_ATK = 4 # 大技、大魔法

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

    def add_skill(self, skill):
        self.skills.append(skill)

    def is_alive(self): return self.hp > 0
    def is_in_barrier_zone(self, dist): return self.barrier_active and dist <= 1

# --- ゲームシステム ---
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
        time.sleep(0.4)

    def draw_field(self):
        field = ["＿"] * (FIELD_MAX + 1)
        if self.p1.pos == self.p2.pos: field[self.p1.pos] = "激" 
        else:
            field[self.p1.pos] = "①"
            field[self.p2.pos] = "②"
        print(f"\n【壁】 {' '.join(field)} 【壁】 (間合い: {self.get_dist()})")

    def print_status(self):
        print(f"\n{'='*15} Turn {self.turn_count} {'='*15}")
        self.draw_field()
        for i, p in enumerate([self.p1, self.p2]):
            st = []
            if p.pos == FIELD_MIN or p.pos == FIELD_MAX: st.append("<壁際>")
            if p.charge_skill: st.append(f"<詠唱中>")
            if p.barrier_active: st.append("[結界(外部攻撃不可)]") 
            if p.vulnerable: st.append("<大隙!!>")
            if p.name == "白沢恵子" and self.get_dist() <= 1: st.append("<近接致命傷!>")
            
            print(f"P{i+1} {p.name}: HP {int(p.hp):>3}/{p.max_hp} | SP {int(p.sp):>2}/{p.max_sp} " + " ".join(st))
        print("="*42)

    def get_valid_actions(self, actor, enemy):
        if actor.charge_skill: return [("詠唱継続", PRIO_SYSTEM, 0, True, "")]
            
        acts = []
        dist = self.get_dist()
        
        for s in actor.skills:
            usable = True
            reason = ""
            if actor.sp < s.sp_cost: 
                usable = False; reason = "SP不足"
            elif getattr(s, 'req_barrier', False) and not actor.barrier_active: 
                usable = False; reason = "結界が必要"
            elif actor.barrier_active and s.name != "捨て身のフラッシュ" and dist >= 2:
                usable = False; reason = "結界内から遠距離攻撃不可"
                
            acts.append((s, s.priority, s.sp_cost, usable, reason))

        acts.append(("様子見（防御・SP回復）", PRIO_DEFEND, 0, True, ""))

        if actor.barrier_active:
            acts.append(("結界を解く", PRIO_DEFEND, 0, True, "攻撃のために解く"))
        else:
            u_barrier = actor.can_barrier and actor.sp >= 25
            acts.append(("結界構築", PRIO_DEFEND, 25, u_barrier, "SP不足" if not u_barrier else ""))
            if actor.name == "林正洋":
                u_ice = actor.sp >= 20
                acts.append(("アイスシールド", PRIO_DEFEND, 20, u_ice, "SP不足" if not u_ice else ""))

        u_break = actor.barrier_active and enemy.barrier_active and dist <= 1 and actor.sp >= 10
        acts.append(("相手の結界をけずる", PRIO_MOVE, 10, u_break, "条件不一致" if not u_break else ""))

        acts.append(("間合いを詰める", PRIO_MOVE, 5, actor.sp >= 5, "SP不足"))
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
            actor.charge_wait -= 1
            if actor.charge_wait <= 0:
                s = actor.charge_skill
                actor.charge_skill = None
                self.print_msg(f"★ {actor.name}の詠唱完了！ 「{s.name}」発動！")
                self.fire_skill(actor, target, s)
            else:
                self.print_msg(f"★ {actor.name}は詠唱継続中... (あと{actor.charge_wait})")
            return

        self.print_msg(f"\n★ {actor.name}のアクション: {act.name if isinstance(act, Skill) else act}")
        actor.sp -= cost
        dist = self.get_dist()

        if act == "様子見（防御・SP回復）":
            actor.is_guarding = True
            actor.sp = min(actor.max_sp, actor.sp + 40)
            self.print_msg("  防御を固めた！(ダメージ半減＆SP大幅回復)")
            return

        if act == "間合いを詰める":
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                actor.pos += dir
                self.print_msg(f"  前に出た！ (間合い: {self.get_dist()})")
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
            self.print_msg("  空中に逃れた！(回避率UP)")
            if act == "ジャンプ": actor.is_jumping = True
            else: actor.is_flying = True
            return

        if act == "結界構築":
            actor.charge_skill = Skill("結界構築",0,[0,0],ATTR_MAG,PRIO_SYSTEM,0,1)
            actor.charge_wait = 1
            self.print_msg("  結界領域の展開準備に入った...")
            return

        if act == "結界を解く":
            actor.barrier_active = False
            self.print_msg("  結界を自ら解除し、遠距離攻撃の態勢をとった！")
            return

        if act == "アイスシールド":
            actor.barrier_active = True
            actor.barrier_life = 2
            self.print_msg("  氷の盾を展開した！(2ターン限定)")
            return
            
        if act == "相手の結界をけずる":
            if dist <= 1:
                if dist == 1:
                    dir = 1 if target.pos > actor.pos else -1
                    actor.pos += dir
                    self.print_msg(f"  踏み込みながら相手の結界に干渉！ (間合い: {self.get_dist()})")

                dmg = 20 + actor.mag // 3
                if target.is_guarding:
                    self.print_msg("  ガードブレイク！ 防御ごと結界を削る！")
                    dmg = int(dmg * 1.5)
                    target.vulnerable = True
                target.hp -= dmg
                self.print_msg(f"  結界を削り、{dmg}のダメージ！")
                if random.random() < 0.5:
                    self.print_msg("  相手の結界が砕け散った！")
                    target.barrier_active = False
            else:
                self.print_msg("  【空振り】 相手が遠すぎて干渉できない！(隙が発生)")
                actor.vulnerable = True
            return

        if isinstance(act, Skill):
            if act.charge > 0:
                actor.charge_skill = act
                actor.charge_wait = act.charge
                self.print_msg(f"  「{act.name}」の詠唱を開始した！")
                return

            self.fire_skill(actor, target, act)

    # ★ 抜け落ちていた結界展開処理を復活・分離 ★
    def fire_skill(self, actor, target, skill):
        # 結界の展開完了
        if skill.name == "結界構築":
            actor.barrier_active = True
            actor.barrier_life = -1
            self.print_msg("  強力な結界領域が展開された！ (被魔法ダメージ半減 / 外部攻撃不可)")
            return

        if skill.name == "捨て身のフラッシュ":
            actor.barrier_active = False
            actor.pos = target.pos # 相手が逃げても絶対密着
            self.print_msg(f"\n！！！ {actor.name}は自らの結界を限界まで圧縮した ！！！")
            self.print_msg("「これで……決めるッ！」")
            self.print_msg(f"  結界を大爆発させ、閃光となって{target.name}の懐へ超突進！！")
            actor.hp -= 30
            actor.sp = 0
            actor.vulnerable = True

        elif getattr(skill, "is_rush", False):
            dir = 1 if target.pos > actor.pos else -1
            if actor.pos != target.pos:
                actor.pos += dir
                self.print_msg(f"  鋭く踏み込んだ！！ (間合い: {self.get_dist()})")
        
        current_dist = self.get_dist()
        
        # --- 空振り・不発判定（詠唱完了後の魔法もここで判定される） ---
        if skill.name != "捨て身のフラッシュ":
            if actor.barrier_active and current_dist >= 2:
                self.print_msg("  【不発!!】 自身の結界の壁に阻まれ、外部へ魔法が放てない！(大隙)")
                actor.vulnerable = True
                return
            if not (skill.range_req[0] <= current_dist <= skill.range_req[1]):
                self.print_msg("  【空振り!!】 間合いが合わず、攻撃は空を切った！(大隙)")
                actor.vulnerable = True
                return

        self.resolve_skill(actor, target, skill, current_dist)

    def calculate_damage(self, attacker, defender, skill, dist):
        base = attacker.atk if skill.attr == ATTR_PHYS else attacker.mag
        dmg = base + skill.power

        if attacker.name == "白沢恵子" and skill.name == "ワールウィンド":
            dmg *= (0.5 + (dist * 0.2)) 

        if attacker.is_jumping: dmg *= 1.5
        if attacker.is_flying: dmg *= 1.2
        
        if skill.name != "捨て身のフラッシュ":
            if attacker.is_in_barrier_zone(dist): 
                dmg *= 1.5 
                
            if defender.barrier_active:
                if skill.attr == ATTR_PHYS:
                    pass # 物理貫通
                else:
                    dmg *= 0.5 # 結界魔法半減

            if defender.is_guarding: dmg *= 0.5

        if defender.name == "白沢恵子" and dist <= 1: dmg *= 1.8 
        if defender.vulnerable: dmg *= 1.5

        return int(dmg)

    def resolve_skill(self, actor, target, skill, dist=None):
        if dist is None: dist = self.get_dist()
        
        hit_rate = 1.0
        if target.is_jumping: hit_rate = 0.4
        if target.is_flying: hit_rate = 0.6
        if random.random() > hit_rate and skill.name != "捨て身のフラッシュ":
            self.print_msg(f"  {target.name}は攻撃をかわした！")
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
                    msg += " 【物理貫通!!(軽減不可)】"
                else:
                    msg += " (結界領域で魔法半減)"
                        
            if actor.barrier_active and dist <= 1:
                msg += " 【結界内バフ(威力1.5倍)!!】"

            if target.vulnerable: msg += " 【カウンターヒット!!】"
            elif target.is_guarding: msg += " (ガード半減)"
            
        self.print_msg(msg)

        if actor.is_jumping:
            actor.is_jumping = False
            actor.vulnerable = True 

        if target.charge_skill and dmg >= 20:
            self.print_msg(f"  ！！ {target.name}の詠唱が中断された！")
            target.charge_skill = None
            target.charge_wait = 0

        if skill.name == "ウィンドプッシュ":
            self.print_msg("  風圧で相手を押し返す！")
            dir = 1 if target.pos > actor.pos else -1
            if FIELD_MIN <= target.pos + dir <= FIELD_MAX: target.pos += dir
            else:
                self.print_msg("  【壁激突】 相手は壁に叩きつけられた！(追加15D)")
                target.hp -= 15; target.vulnerable = True
                
        if skill.name == "ワールウィンド" and random.random() < 0.3 and not target.is_guarding:
            self.print_msg("  突風が相手を吹き飛ばす！")
            dir = 1 if target.pos > actor.pos else -1
            if FIELD_MIN <= target.pos + dir <= FIELD_MAX: target.pos += dir
            else:
                self.print_msg("  【壁激突】 相手は壁に叩きつけられた！(追加15D)")
                target.hp -= 15; target.vulnerable = True

        if target.is_flying and dmg >= 20:
            self.print_msg("  ！！ 撃ち落とされた！")
            target.is_flying = False; target.hp -= 15; target.vulnerable = True

    def battle_start_msg(self):
        if self.p1.name == "藤沢美幸" and self.p2.name == "白沢恵子":
            print("美幸「お姉さま・・・女同士の甘やかな官能の世界に誘ってさしあげるわ」")
            print("恵子「やめい！　小娘」")
        elif self.p1.name == "藤沢美幸" and self.p2.name == "山口春香":
            print("春香「美幸ちゃあん、やめようよお　みんな・・・仲良く」")
            print("美幸「春香、邪魔しないで」")
            print("春香「もおお・・・美幸ちゃんだからって容赦しないからね？」")
        elif self.p1.name == "安土利一" and self.p2.name == "白沢恵子":
            print("安土「恵子ちゃん・・・ここは通せない」")
            print("恵子「力づくで通させてもらうわ」")
        elif self.p1.name == "藤沢美幸" and self.p2.name == "黎":
            print("黎「まさか私たちがこんなことになろうとはな」")
            print("美幸「こうなった以上仕方ないわ」")
        elif self.p1.name == "藤沢美幸" and self.p2.name == "林正洋":
            print("正洋「きみの力は危険だ。封じさせてもらう」")
            print("美幸「やれるもんならやってみなさいよ」")

 
    def run(self):
        print("【Crystals on the Glassboard - Ver1.4.1 BUG FIX & AI UPDATE】")
        self.battle_start_msg()
        while self.p1.is_alive() and self.p2.is_alive():
            for p in [self.p1, self.p2]:
                p.is_guarding = False
                p.vulnerable = False
                if p.barrier_active and p.barrier_life == -1:
                    p.sp -= 5
                    if p.sp < 0:
                        p.sp = 0; p.barrier_active = False
                        self.print_msg(f"[{p.name}] 魔力(SP)切れで結界が消滅！")
                elif p.barrier_active and p.barrier_life > 0:
                    p.barrier_life -= 1
                    if p.barrier_life == 0:
                        p.barrier_active = False
                        self.print_msg(f"[{p.name}] アイスシールドが消滅した！")

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

            print("\n★★★ COMMAND OPEN ★★★")
            self.print_msg(f"P1 {self.p1.name}: {act1[0].name if isinstance(act1[0], Skill) else act1[0]}")
            self.print_msg(f"P2 {self.p2.name}: {act2[0].name if isinstance(act2[0], Skill) else act2[0]}")
            print("★"*23)

            for item in q:
                if item[0].is_alive():
                    self.resolve_action(item[0], item[1], item[2])

            self.turn_count += 1
        
        print("\n=== K.O. ===")
        winner = self.p1 if self.p1.is_alive() else self.p2
        print(f"勝者: {winner.name} !!")

    def ui_action(self, p, actions):
        if len(actions) == 1 and actions[0][0] == "詠唱継続": return actions[0]
        
        print(f">> {p.name} の行動選択:")
        for i, a in enumerate(actions):
            act_obj, prio, cost, usable, reason = a
            act_name = act_obj.name if isinstance(act_obj, Skill) else act_obj
            
            if usable:
                info = f"[優先:{prio} | SP:{cost}]"
                if getattr(act_obj, "is_rush", False): info += " ＞突進＜"
                if isinstance(act_obj, Skill):
                    if act_obj.name == "捨て身のフラッシュ":
                        info += f" ＞{act_obj.desc}＜"
                    else:
                        info += f" {act_obj.attr}/射程:{act_obj.range_req[0]}-{act_obj.range_req[1]}"
                        if act_obj.charge > 0: info += " (詠唱)"
                if getattr(act_obj, "desc", "") and act_name != "捨て身のフラッシュ": 
                    info += f" - {act_obj.desc}"
                print(f"{i+1}. {act_name} {info}")
            else:
                print(f"[{i+1}. {act_name}] --- 封印中 ({reason}) ---")
            
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

        # ★ AI強化：結界を持っていない場合は高確率で張ろうとする
        if cpu.can_barrier and not cpu.barrier_active and cpu.sp >= 25:
            barriers = [a for a in valid_actions if isinstance(a[0], str) and a[0] == "結界構築"]
            if barriers and random.random() < 0.6: return barriers[0]
        
        if cpu.barrier_active and dist >= 2:
            options = []
            fwd = [a for a in valid_actions if a[0] == "間合いを詰める"]
            rel = [a for a in valid_actions if a[0] == "結界を解く"]
            if fwd and cpu.sp >= 5: options.append(fwd[0])
            if rel: options.append(rel[0])
            if options: return random.choice(options)

        if cpu.name == "藤沢美幸" and cpu.barrier_active:
            sutemi = [a for a in valid_actions if getattr(a[0], "name", "") == "捨て身のフラッシュ"]
            enemy = self.p1 if cpu == self.p2 else self.p2
            if sutemi and (cpu.hp < 50 or enemy.hp < 100) and random.random() < 0.4:
                return sutemi[0]
        
        if cpu.sp < 20:
            guards = [a for a in valid_actions if "様子見" in str(a[0])]
            if guards and random.random() < 0.8: return guards[0]
            
        if cpu.name == "白沢恵子" and dist <= 1:
            push = [a for a in valid_actions if getattr(a[0], "name", "") == "ウィンドプッシュ"]
            if push: return push[0]
            back = [a for a in valid_actions if a[0] == "ステップバック"]
            if back and cpu.pos not in [FIELD_MIN, FIELD_MAX]: return back[0]

        atks = [a for a in valid_actions if isinstance(a[0], Skill)]
        if atks and random.random() < 0.7:
            valid = []
            for a in atks:
                if getattr(a[0], "name", "") == "捨て身のフラッシュ": continue
                eff_dist = dist - 1 if getattr(a[0], "is_rush", False) else dist
                if a[0].range_req[0] <= eff_dist <= a[0].range_req[1]:
                    valid.append(a)
            if valid: return random.choice(valid)
            return random.choice(atks) 
            
        if cpu.name in ["シルレイム", "林健次", "林正洋"] and dist > 1:
            fwds = [a for a in valid_actions if a[0] == "間合いを詰める"]
            if fwds: return fwds[0]

        return random.choice(valid_actions)

def create_characters():
    chars = []
    
    c = Fighter("藤沢美幸", hp=100, sp=100, atk=10, mag=22, speed=12, desc="主人公/結界からの超必殺技")
    c.can_barrier = True
    c.add_skill(Skill("マジックアロー", 20, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15))
    c.add_skill(Skill("捨て身のフラッシュ", 80, [0,6], ATTR_MAG, PRIO_SYSTEM, 0, req_barrier=True, desc="絶対追尾・防御貫通・自傷30/SP0"))
    chars.append(c)
    
    c = Fighter("黎", hp=130, sp=120, atk=15, mag=30, speed=14, desc="最強魔法使い")
    c.can_barrier = True
    c.add_skill(Skill("マジックアロー", 25, [1,4], ATTR_MAG, PRIO_FAST_ATK, 15))
    c.add_skill(Skill("グレーターマジック", 45, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 40, charge=1))
    chars.append(c)

    c = Fighter("安土利一", hp=110, sp=90, atk=12, mag=25, speed=10, desc="炎/中距離")
    c.add_skill(Skill("ファイアボール", 30, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20)) 
    chars.append(c)

    c = Fighter("林正洋", hp=120, sp=80, atk=28, mag=10, speed=13, desc="氷/近接")
    c.add_skill(Skill("アイスナックル", 30, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="物理(結界貫通)"))
    c.add_skill(Skill("氷滑り(突進)", 20, [0,2], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="前進打撃(物理)")) 
    chars.append(c)

    c = Fighter("山口春香", hp=90, sp=110, atk=8, mag=28, speed=13, desc="精霊使い")
    c.can_barrier = True
    c.add_skill(Skill("サラマンダー", 55, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 30, charge=1))
    chars.append(c)

    c = Fighter("シルレイム", hp=140, sp=80, atk=32, mag=5, speed=11, desc="剣士/高体力")
    c.add_skill(Skill("ブロードソード", 35, [0,1], ATTR_PHYS, PRIO_FAST_ATK, 15, desc="物理(結界貫通)"))
    c.add_skill(Skill("ステップイン", 25, [0,2], ATTR_PHYS, PRIO_FAST_ATK, 20, is_rush=True, desc="前進斬り(物理)")) 
    chars.append(c)

    c = Fighter("林健次", hp=125, sp=80, atk=42, mag=5, speed=12, desc="剣士/超火力")
    c.add_skill(Skill("フランベルジュ", 45, [0,0], ATTR_PHYS, PRIO_SLOW_ATK, 20, desc="物理(結界貫通)"))
    c.add_skill(Skill("猛追撃", 30, [0,2], ATTR_PHYS, PRIO_FAST_ATK, 25, is_rush=True, desc="前進斬り(物理)")) 
    chars.append(c)

    c = Fighter("白沢恵子", hp=85, sp=100, atk=5, mag=32, speed=9, desc="風/遠距離(近接紙装甲)")
    c.add_skill(Skill("ワールウィンド", 30, [2,6], ATTR_MAG, PRIO_SLOW_ATK, 25)) 
    c.add_skill(Skill("ウィンドプッシュ", 10, [0,1], ATTR_MAG, PRIO_DEFEND, 20, desc="近接拒否")) 
    chars.append(c)
    
    c = Fighter("ブラウ", hp=130, sp=90, atk=20, mag=20, speed=8, desc="竜")
    c.add_skill(Skill("ファイアーブレス", 35, [1,4], ATTR_MAG, PRIO_SLOW_ATK, 20))
    c.is_flying = True
    chars.append(c)
    
    return chars

def main():
    chars = create_characters()
    print("使用キャラを選択:")
    for i, c in enumerate(chars): print(f"{i+1}. {c.name}")
    try: player = chars[int(input("No: ")) - 1]
    except: player = chars[0]
        
    enemy = copy.deepcopy(random.choice([c for c in chars if c.name != player.name]))
    # enemy = chars[7]
    Game(player, enemy).run()

if __name__ == "__main__":
    main()
    inp = input("Hit ENTER key to exit : ")
