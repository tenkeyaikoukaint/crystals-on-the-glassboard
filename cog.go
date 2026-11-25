package main

import (
	"bufio"
	"fmt"
	"math/rand"
	"os"
	"sort"
	"strconv"
	"strings"
	"time"
)

// --- 定数定義 ---
const (
	FIELD_MIN = 0
	FIELD_MAX = 6

	ATTR_PHYS = "物理"
	ATTR_MAG  = "魔法"

	// 優先度（フレーム：数字が小さいほど先に動く）
	PRIO_SYSTEM   = 0 // 最速（超必殺技・システム処理）
	PRIO_DEFEND   = 1 // 回避、防御、結界構築・解除、拒否技
	PRIO_FAST_ATK = 2 // 牽制攻撃、突進技
	PRIO_MOVE     = 3 // 通常の前進、結界削り
	PRIO_SLOW_ATK = 4 // 大技、大魔法、詠唱完了発動
)

// --- ヘルパー関数 ---
func absInt(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func minInt(a, b int) int {
	if a < b {
		return a
	}
	return b
}

func maxInt(a, b int) int {
	if a > b {
		return a
	}
	return b
}

// --- 構造体定義 ---
type Skill struct {
	Name       string
	Power      int
	RangeReq   [2]int
	Attr       string
	Priority   int
	SPCost     int
	Charge     int
	IsRush     bool
	ReqBarrier bool
	Desc       string
}

type Fighter struct {
	Name          string
	MaxHP         int
	HP            int
	MaxSP         int
	SP            int
	Atk           int
	Mag           int
	Speed         int
	Desc          string
	Pos           int
	BarrierActive bool
	BarrierLife   int
	IsFlying      bool
	IsJumping     bool
	IsGuarding    bool
	Vulnerable    bool
	ChargeSkill   *Skill
	ChargeWait    int
	Skills        []*Skill
	CanBarrier    bool
}

func NewFighter(name string, hp, sp, atk, mag, speed int, desc string) *Fighter {
	return &Fighter{
		Name:        name,
		MaxHP:       hp,
		HP:          hp,
		MaxSP:       sp,
		SP:          sp,
		Atk:         atk,
		Mag:         mag,
		Speed:       speed,
		Desc:        desc,
		BarrierLife: -1,
	}
}

func (f *Fighter) AddSkill(s *Skill) {
	f.Skills = append(f.Skills, s)
}

func (f *Fighter) IsAlive() bool {
	return f.HP > 0
}

func (f *Fighter) IsInBarrierZone(dist int) bool {
	return f.BarrierActive && f.BarrierLife == -1 && dist <= 1
}

func (f *Fighter) Clone() *Fighter {
	cp := *f
	cp.Skills = make([]*Skill, len(f.Skills))
	for i, s := range f.Skills {
		sc := *s
		cp.Skills[i] = &sc
	}
	return &cp
}

type Action struct {
	Skill    *Skill // スキル行動の場合は非nil
	Name     string // 通常行動名（スキルの場合はスキル名）
	Priority int
	Cost     int
	Usable   bool
	Reason   string
}

// --- ゲームシステム ---
type Game struct {
	P1        *Fighter
	P2        *Fighter
	TurnCount int
	scanner   *bufio.Scanner
}

func NewGame(p1, p2 *Fighter, scanner *bufio.Scanner) *Game {
	p1.Pos = 1
	p2.Pos = 5
	return &Game{
		P1:        p1,
		P2:        p2,
		TurnCount: 1,
		scanner:   scanner,
	}
}

func (g *Game) GetDist() int {
	return absInt(g.P1.Pos - g.P2.Pos)
}

func (g *Game) PrintMsg(text string) {
	fmt.Println(text)
	time.Sleep(350 * time.Millisecond)
}

func (g *Game) DrawField() {
	field := make([]string, FIELD_MAX+1)
	for i := range field {
		field[i] = "＿"
	}
	if g.P1.Pos == g.P2.Pos {
		field[g.P1.Pos] = "激"
	} else {
		field[g.P1.Pos] = "①"
		field[g.P2.Pos] = "②"
	}
	fmt.Printf("\n【壁】 %s 【壁】 (間合い: %d)\n", strings.Join(field, " "), g.GetDist())
}

func (g *Game) PrintStatus() {
	fmt.Printf("\n%s Turn %d %s\n", strings.Repeat("=", 15), g.TurnCount, strings.Repeat("=", 15))
	g.DrawField()
	players := []*Fighter{g.P1, g.P2}
	for i, p := range players {
		var st []string
		if p.Pos == FIELD_MIN || p.Pos == FIELD_MAX {
			st = append(st, "<壁際>")
		}
		if p.ChargeSkill != nil {
			st = append(st, fmt.Sprintf("<詠唱中:%s>", p.ChargeSkill.Name))
		}
		if p.BarrierActive {
			if p.BarrierLife > 0 {
				st = append(st, fmt.Sprintf("[氷盾(残%d)]", p.BarrierLife))
			} else {
				st = append(st, "【結界展開中(近接強化/無詠唱/物理反射)】")
			}
		}
		if p.IsFlying {
			st = append(st, "<飛行中>")
		}
		if p.Vulnerable {
			st = append(st, "<大隙!!>")
		}
		if p.Name == "白沢恵子" && g.GetDist() <= 1 {
			st = append(st, "<近接危険!>")
		}

		fmt.Printf("P%d %s: HP %3d/%d | SP %3d/%d %s\n",
			i+1, p.Name, p.HP, p.MaxHP, p.SP, p.MaxSP, strings.Join(st, " "))
	}
	fmt.Println(strings.Repeat("=", 42))
}

func (g *Game) GetEffectiveRange(actor *Fighter, skill *Skill) [2]int {
	// 結界展開中は、すべての魔法が距離0〜1（結界領域内）に最適化される
	if actor.BarrierActive && actor.BarrierLife == -1 && skill.Name != "捨て身のフラッシュ" {
		return [2]int{0, 1}
	}
	return skill.RangeReq
}

func (g *Game) GetValidActions(actor, enemy *Fighter) []Action {
	if actor.ChargeSkill != nil {
		return []Action{{Name: "詠唱継続", Priority: PRIO_SLOW_ATK, Cost: 0, Usable: true}}
	}

	var acts []Action
	dist := g.GetDist()

	for _, s := range actor.Skills {
		usable := true
		reason := ""
		if actor.SP < s.SPCost {
			usable = false
			reason = "SP不足"
		} else if s.ReqBarrier && !(actor.BarrierActive && actor.BarrierLife == -1) {
			usable = false
			reason = "結界領域が必要"
		} else if actor.BarrierActive && actor.BarrierLife == -1 && s.Name != "捨て身のフラッシュ" && dist >= 2 {
			usable = false
			reason = "結界外(距離2以上)へは攻撃不可・接近が必要"
		}
		acts = append(acts, Action{
			Skill:    s,
			Name:     s.Name,
			Priority: s.Priority,
			Cost:     s.SPCost,
			Usable:   usable,
			Reason:   reason,
		})
	}

	acts = append(acts, Action{Name: "様子見（防御・SP回復）", Priority: PRIO_DEFEND, Cost: 0, Usable: true})

	if actor.BarrierActive && actor.BarrierLife == -1 {
		acts = append(acts, Action{Name: "結界を解く", Priority: PRIO_DEFEND, Cost: 0, Usable: true, Reason: "解除＋SP15回収"})
	} else if !actor.BarrierActive {
		if actor.CanBarrier {
			uBarrier := actor.SP >= 20
			reason := "即時展開・近接無詠唱化"
			if !uBarrier {
				reason = "SP不足"
			}
			acts = append(acts, Action{Name: "結界構築", Priority: PRIO_DEFEND, Cost: 20, Usable: uBarrier, Reason: reason})
		}
		if actor.Name == "林正洋" {
			uIce := actor.SP >= 20
			reason := "2T魔法半減＋物理反撃"
			if !uIce {
				reason = "SP不足"
			}
			acts = append(acts, Action{Name: "アイスシールド", Priority: PRIO_DEFEND, Cost: 20, Usable: uIce, Reason: reason})
		}
	}

	uBreak := enemy.BarrierActive && dist <= 2 && actor.SP >= 10
	breakReason := "1マス前進＋結界粉砕"
	if !uBreak {
		breakReason = "距離2以内＆相手結界時のみ"
	}
	acts = append(acts, Action{Name: "相手の結界をけずる", Priority: PRIO_MOVE, Cost: 10, Usable: uBreak, Reason: breakReason})

	fwdReason := "SP不足"
	if dist == 0 {
		fwdReason = "密着中"
	}
	acts = append(acts, Action{Name: "間合いを詰める", Priority: PRIO_MOVE, Cost: 5, Usable: actor.SP >= 5 && dist > 0, Reason: fwdReason})
	acts = append(acts, Action{Name: "ステップバック", Priority: PRIO_DEFEND, Cost: 15, Usable: actor.SP >= 15, Reason: "SP不足"})

	if actor.Name != "ブラウ" && !actor.IsJumping {
		acts = append(acts, Action{Name: "ジャンプ", Priority: PRIO_DEFEND, Cost: 15, Usable: actor.SP >= 15, Reason: "SP不足"})
	}
	if actor.Name == "ブラウ" && !actor.IsFlying {
		acts = append(acts, Action{Name: "飛行", Priority: PRIO_DEFEND, Cost: 20, Usable: actor.SP >= 20, Reason: "SP不足"})
	}

	return acts
}

func (g *Game) ResolveAction(actor, target *Fighter, act Action) {
	if !actor.IsAlive() {
		return
	}

	if act.Name == "詠唱継続" {
		if actor.ChargeSkill == nil {
			g.PrintMsg(fmt.Sprintf("★ %sは詠唱を中断されており動けない！", actor.Name))
			return
		}
		actor.ChargeWait--
		if actor.ChargeWait <= 0 {
			s := actor.ChargeSkill
			actor.ChargeSkill = nil
			g.PrintMsg(fmt.Sprintf("\n★ %sの詠唱完了！ 「%s」発動！", actor.Name, s.Name))
			g.FireSkill(actor, target, s)
		} else {
			g.PrintMsg(fmt.Sprintf("\n★ %sは詠唱継続中... (あと%d)", actor.Name, actor.ChargeWait))
		}
		return
	}

	g.PrintMsg(fmt.Sprintf("\n★ %sのアクション: %s", actor.Name, act.Name))
	actor.SP -= act.Cost
	dist := g.GetDist()

	switch act.Name {
	case "様子見（防御・SP回復）":
		actor.IsGuarding = true
		actor.SP = minInt(actor.MaxSP, actor.SP+35)
		g.PrintMsg("  防御を固めた！(ダメージ半減＆SP+35回復)")
		return

	case "間合いを詰める":
		dir := -1
		if target.Pos > actor.Pos {
			dir = 1
		}
		if actor.Pos != target.Pos {
			steps := 1
			if actor.BarrierActive && actor.BarrierLife == -1 && dist >= 2 {
				steps = 2
			}
			for i := 0; i < steps; i++ {
				if actor.Pos != target.Pos {
					actor.Pos += dir
				}
			}
			if steps == 2 {
				g.PrintMsg(fmt.Sprintf("  結界領域ごと一気に間合いを詰めた！ (間合い: %d)", g.GetDist()))
			} else {
				g.PrintMsg(fmt.Sprintf("  前に出た！ (間合い: %d)", g.GetDist()))
			}
		} else {
			g.PrintMsg("  すでに密着している！")
		}
		return

	case "ステップバック":
		dir := 1
		if target.Pos > actor.Pos {
			dir = -1
		}
		newPos := actor.Pos + dir
		if FIELD_MIN <= newPos && newPos <= FIELD_MAX {
			actor.Pos = newPos
			g.PrintMsg(fmt.Sprintf("  素早く後ろへ下がった！ (間合い: %d)", g.GetDist()))
		} else {
			g.PrintMsg("  しかし背後は壁だ！ 下がれない！(大きな隙が発生)")
			actor.Vulnerable = true
		}
		return

	case "ジャンプ":
		actor.IsJumping = true
		g.PrintMsg("  高く跳躍した！(このターンの被弾率大幅減)")
		return

	case "飛行":
		actor.IsFlying = true
		g.PrintMsg("  空中に舞い上がった！(回避率UP・攻撃力1.2倍)")
		return

	case "結界構築":
		actor.BarrierActive = true
		actor.BarrierLife = -1
		g.PrintMsg("  【結界領域・即時展開！】")
		g.PrintMsg("  (効果: 被魔法半減 / 物理被弾時に反射ダメージ / 距離0-1で全スキル無詠唱＆威力1.4倍)")
		return

	case "結界を解く":
		actor.BarrierActive = false
		actor.SP = minInt(actor.MaxSP, actor.SP+15)
		g.PrintMsg("  結界を自ら解除し、魔力を回収した！(SP+15)")
		return

	case "アイスシールド":
		actor.BarrierActive = true
		actor.BarrierLife = 2
		g.PrintMsg("  氷の盾を展開した！(2ターン魔法半減・物理被弾時に冷気反撃)")
		return

	case "相手の結界をけずる":
		if dist <= 2 && target.BarrierActive {
			if dist >= 1 {
				dir := -1
				if target.Pos > actor.Pos {
					dir = 1
				}
				actor.Pos += dir
				g.PrintMsg(fmt.Sprintf("  踏み込みながら相手の結界に干渉！ (間合い: %d)", g.GetDist()))
			}
			if g.GetDist() <= 1 {
				dmg := 15 + maxInt(actor.Atk, actor.Mag)/2
				if target.IsGuarding {
					g.PrintMsg("  ガードブレイク！ 防御ごと結界を砕く！")
					dmg = int(float64(dmg) * 1.5)
				}
				target.HP -= dmg
				target.BarrierActive = false
				target.Vulnerable = true
				g.PrintMsg(fmt.Sprintf("  相手の結界を粉砕し、%dダメージ＆大隙を与えた！", dmg))
			} else {
				g.PrintMsg("  【空振り】 相手が遠すぎて届かなかった！(隙が発生)")
				actor.Vulnerable = true
			}
		} else {
			g.PrintMsg("  【空振り】 すでに結界がないか遠すぎる！(隙が発生)")
			actor.Vulnerable = true
		}
		return
	}

	if act.Skill != nil {
		if act.Skill.Charge > 0 {
			if actor.BarrierActive && actor.BarrierLife == -1 {
				g.PrintMsg(fmt.Sprintf("  【結界共鳴】 詠唱を省略し、「%s」を即時発動！！", act.Skill.Name))
			} else {
				actor.ChargeSkill = act.Skill
				actor.ChargeWait = act.Skill.Charge
				g.PrintMsg(fmt.Sprintf("  「%s」の詠唱を開始した！(次ターン発動)", act.Skill.Name))
				return
			}
		}
		g.FireSkill(actor, target, act.Skill)
	}
}

func (g *Game) FireSkill(actor, target *Fighter, skill *Skill) {
	if skill.Name == "捨て身のフラッシュ" {
		actor.BarrierActive = false
		actor.Pos = target.Pos
		g.PrintMsg(fmt.Sprintf("\n！！！ %sは自らの結界を限界まで圧縮した ！！！", actor.Name))
		g.PrintMsg("「これで……決めるッ！」")
		g.PrintMsg(fmt.Sprintf("  結界を大爆発させ、閃光となって%sの懐へ超突進！！", target.Name))
		actor.HP = maxInt(1, actor.HP-20)
		actor.SP = 0
		actor.Vulnerable = true
	} else if skill.IsRush {
		dir := -1
		if target.Pos > actor.Pos {
			dir = 1
		}
		if actor.Pos != target.Pos {
			actor.Pos += dir
			g.PrintMsg(fmt.Sprintf("  鋭く踏み込んだ！！ (間合い: %d)", g.GetDist()))
		}
	}

	currentDist := g.GetDist()
	effRange := g.GetEffectiveRange(actor, skill)

	if skill.Name != "捨て身のフラッシュ" {
		if actor.BarrierActive && actor.BarrierLife == -1 && currentDist >= 2 {
			g.PrintMsg("  【不発!!】 相手が結界領域の外(距離2以上)に離れたため届かない！(大隙)")
			actor.Vulnerable = true
			return
		}
		if !(effRange[0] <= currentDist && currentDist <= effRange[1]) {
			g.PrintMsg("  【空振り!!】 間合いが合わず、攻撃は空を切った！(大隙)")
			actor.Vulnerable = true
			return
		}
	}

	g.ResolveSkill(actor, target, skill, currentDist)
}

func (g *Game) CalculateDamage(attacker, defender *Fighter, skill *Skill, dist int) int {
	base := attacker.Mag
	if skill.Attr == ATTR_PHYS {
		base = attacker.Atk
	}
	dmg := float64(base + skill.Power)

	if attacker.Name == "白沢恵子" && skill.Name == "ワールウィンド" {
		dmg *= (0.7 + float64(dist)*0.15)
	}
	if attacker.IsFlying {
		dmg *= 1.2
	}

	if skill.Name != "捨て身のフラッシュ" {
		if attacker.IsInBarrierZone(dist) {
			dmg *= 1.4
		}
		if defender.BarrierActive && skill.Attr != ATTR_PHYS {
			dmg *= 0.5
		}
		if defender.IsGuarding {
			dmg *= 0.5
		}
	}

	if defender.Name == "白沢恵子" && dist <= 1 {
		dmg *= 1.4
	}
	if defender.Vulnerable {
		dmg *= 1.4
	}

	return int(dmg)
}

func (g *Game) ResolveSkill(actor, target *Fighter, skill *Skill, dist int) {
	hitRate := 1.0
	if target.IsJumping {
		hitRate = 0.35
	} else if target.IsFlying {
		hitRate = 0.70
	}
	if actor.IsInBarrierZone(dist) {
		hitRate = 1.0
	}

	if rand.Float64() > hitRate && skill.Name != "捨て身のフラッシュ" {
		g.PrintMsg(fmt.Sprintf("  %sは空中で攻撃を華麗にかわした！", target.Name))
		return
	}

	dmg := g.CalculateDamage(actor, target, skill, dist)
	target.HP -= dmg

	msg := fmt.Sprintf("  命中！ %sに%dのダメージ！", target.Name, dmg)

	if skill.Name == "捨て身のフラッシュ" {
		msg += " 【結界・防御貫通の致命傷!!】"
		if target.BarrierActive {
			target.BarrierActive = false
			g.PrintMsg("  相手の結界が粉々に砕け散った！")
		}
	} else {
		if target.BarrierActive {
			if skill.Attr == ATTR_PHYS {
				msg += " 【物理貫通!!】"
			} else {
				msg += " (結界で魔法半減)"
			}
		}
		if actor.IsInBarrierZone(dist) {
			msg += " 【結界領域バフ(必中＆1.4倍)!!】"
		}
		if target.Vulnerable {
			msg += " 【カウンターヒット(1.4倍)!!】"
		} else if target.IsGuarding {
			msg += " (ガード半減)"
		}
	}
	g.PrintMsg(msg)

	// 結界に対する物理攻撃への魔力反射カウンター
	if target.BarrierActive && skill.Attr == ATTR_PHYS && skill.Name != "捨て身のフラッシュ" {
		thornDmg := maxInt(10, target.Mag/2)
		actor.HP -= thornDmg
		g.PrintMsg(fmt.Sprintf("  ⚡【結界反撃】 結界の魔力障壁が弾け、%sに%dの反射ダメージ！", actor.Name, thornDmg))
	}

	if target.ChargeSkill != nil && dmg >= 20 {
		g.PrintMsg(fmt.Sprintf("  ！！ %sの詠唱が中断された！", target.Name))
		target.ChargeSkill = nil
		target.ChargeWait = 0
	}

	if skill.Name == "ウィンドプッシュ" {
		g.PrintMsg("  風圧で相手を2マス吹き飛ばす！")
		dir := -1
		if target.Pos > actor.Pos {
			dir = 1
		}
		for i := 0; i < 2; i++ {
			if FIELD_MIN <= target.Pos+dir && target.Pos+dir <= FIELD_MAX {
				target.Pos += dir
			} else {
				g.PrintMsg("  【壁激突】 相手は壁に叩きつけられた！(追加15ダメージ＆大隙)")
				target.HP -= 15
				target.Vulnerable = true
				break
			}
		}
	}

	if skill.Name == "ワールウィンド" && rand.Float64() < 0.35 && !target.IsGuarding {
		g.PrintMsg("  突風が相手を押し流す！")
		dir := -1
		if target.Pos > actor.Pos {
			dir = 1
		}
		if FIELD_MIN <= target.Pos+dir && target.Pos+dir <= FIELD_MAX {
			target.Pos += dir
		} else {
			g.PrintMsg("  【壁激突】 相手は壁に叩きつけられた！(追加15ダメージ＆大隙)")
			target.HP -= 15
			target.Vulnerable = true
		}
	}

	if target.IsFlying && dmg >= 22 {
		g.PrintMsg("  ！！ 強い衝撃で撃ち落とされた！(落下10ダメージ＆大隙)")
		target.IsFlying = false
		target.HP -= 10
		target.Vulnerable = true
	}
}

func (g *Game) Run() {
	fmt.Println("【Crystals on the Glassboard - Ver1.6.0 BARRIER REWORK】")
	for g.P1.IsAlive() && g.P2.IsAlive() {
		for _, p := range []*Fighter{g.P1, g.P2} {
			p.IsGuarding = false
			p.Vulnerable = false
			p.IsJumping = false

			if !p.BarrierActive {
				p.SP = minInt(p.MaxSP, p.SP+5)
			} else if p.BarrierLife > 0 {
				p.BarrierLife--
				if p.BarrierLife == 0 {
					p.BarrierActive = false
					g.PrintMsg(fmt.Sprintf("[%s] アイスシールドが消滅した！", p.Name))
				}
			}
		}

		g.PrintStatus()

		act1 := g.UIAction(g.P1, g.GetValidActions(g.P1, g.P2))
		act2 := g.CPUAction(g.P2, g.GetValidActions(g.P2, g.P1))

		speed1 := g.P1.Speed + rand.Intn(4)
		speed2 := g.P2.Speed + rand.Intn(4)

		type queueItem struct {
			actor  *Fighter
			target *Fighter
			act    Action
			prio   int
			speed  int
		}

		q := []queueItem{
			{g.P1, g.P2, act1, act1.Priority, speed1},
			{g.P2, g.P1, act2, act2.Priority, speed2},
		}
		sort.Slice(q, func(i, j int) bool {
			if q[i].prio != q[j].prio {
				return q[i].prio < q[j].prio
			}
			return q[i].speed > q[j].speed
		})

		fmt.Println("\n★★★ COMMAND OPEN ★★★")
		g.PrintMsg(fmt.Sprintf("P1 %s: %s", g.P1.Name, act1.Name))
		g.PrintMsg(fmt.Sprintf("P2 %s: %s", g.P2.Name, act2.Name))
		fmt.Println(strings.Repeat("★", 23))

		for _, item := range q {
			if item.actor.IsAlive() && item.target.IsAlive() {
				g.ResolveAction(item.actor, item.target, item.act)
			}
		}

		g.TurnCount++
	}

	fmt.Println("\n=== K.O. ===")
	winner := g.P2
	if g.P1.IsAlive() {
		winner = g.P1
	}
	fmt.Printf("勝者: %s !!\n", winner.Name)
}

func (g *Game) UIAction(p *Fighter, actions []Action) Action {
	if len(actions) == 1 && actions[0].Name == "詠唱継続" {
		return actions[0]
	}

	fmt.Printf(">> %s の行動選択:\n", p.Name)
	for i, a := range actions {
		if a.Usable {
			info := fmt.Sprintf("[優先:%d | SP:%d]", a.Priority, a.Cost)
			if a.Skill != nil {
				if a.Skill.IsRush {
					info += " ＞1マス前進後＜"
				}
				if a.Skill.Name == "捨て身のフラッシュ" {
					info += fmt.Sprintf(" ＞%s＜", a.Skill.Desc)
				} else {
					effR := g.GetEffectiveRange(p, a.Skill)
					info += fmt.Sprintf(" %s/威力:%d/射程:%d-%d", a.Skill.Attr, a.Skill.Power, effR[0], effR[1])
					if a.Skill.Charge > 0 {
						if p.BarrierActive && p.BarrierLife == -1 {
							info += " 【結界共鳴:無詠唱!】"
						} else {
							info += " (1T詠唱)"
						}
					}
					if a.Skill.Desc != "" {
						info += fmt.Sprintf(" - %s", a.Skill.Desc)
					}
				}
			}
			fmt.Printf("%2d. %s %s\n", i+1, a.Name, info)
		} else {
			fmt.Printf("[%2d. %s] --- 選択不可 (%s) ---\n", i+1, a.Name, a.Reason)
		}
	}

	for {
		fmt.Print("No: ")
		if !g.scanner.Scan() {
			return actions[0]
		}
		x, err := strconv.Atoi(strings.TrimSpace(g.scanner.Text()))
		if err != nil {
			continue
		}
		idx := x - 1
		if 0 <= idx && idx < len(actions) {
			if actions[idx].Usable {
				return actions[idx]
			}
			fmt.Println(" !! その行動は現在選択できません !!")
		}
	}
}

func (g *Game) CPUAction(cpu *Fighter, actions []Action) Action {
	var validActions []Action
	for _, a := range actions {
		if a.Usable {
			validActions = append(validActions, a)
		}
	}
	if len(validActions) == 1 && validActions[0].Name == "詠唱継続" {
		return validActions[0]
	}

	dist := g.GetDist()
	enemy := g.P1
	if cpu == g.P1 {
		enemy = g.P2
	}

	findByName := func(name string) (Action, bool) {
		for _, a := range validActions {
			if a.Name == name {
				return a, true
			}
		}
		return Action{}, false
	}

	// 1. 相手が結界を張っており、距離2以内なら「結界をけずる」を積極的に狙う
	if enemy.BarrierActive && dist <= 2 {
		if brk, ok := findByName("相手の結界をけずる"); ok && rand.Float64() < 0.55 {
			return brk
		}
	}

	// 2. 結界持ちキャラの戦術ルーチン
	if cpu.CanBarrier {
		if !cpu.BarrierActive && cpu.SP >= 35 {
			if br, ok := findByName("結界構築"); ok && (dist <= 2 || rand.Float64() < 0.65) {
				return br
			}
		}
		if cpu.BarrierActive && dist <= 1 {
			var atks []Action
			for _, a := range validActions {
				if a.Skill != nil && a.Skill.Name != "捨て身のフラッシュ" {
					atks = append(atks, a)
				}
			}
			if len(atks) > 0 {
				sort.Slice(atks, func(i, j int) bool {
					return atks[i].Skill.Power > atks[j].Skill.Power
				})
				return atks[0]
			}
		}
		if cpu.Name == "藤沢美幸" && cpu.BarrierActive {
			if sutemi, ok := findByName("捨て身のフラッシュ"); ok {
				if (dist >= 3 || enemy.HP <= 85 || cpu.HP <= 45) && rand.Float64() < 0.65 {
					return sutemi
				}
			}
		}
		if cpu.BarrierActive && dist >= 2 {
			if fwd, ok := findByName("間合いを詰める"); ok && rand.Float64() < 0.8 {
				return fwd
			}
		}
	}

	// 3. 白沢恵子の近接拒否ロジック
	if cpu.Name == "白沢恵子" && dist <= 1 {
		if push, ok := findByName("ウィンドプッシュ"); ok {
			return push
		}
		if back, ok := findByName("ステップバック"); ok && cpu.Pos != FIELD_MIN && cpu.Pos != FIELD_MAX {
			return back
		}
	}

	// 4. SP枯渇時は様子見
	if cpu.SP < 20 {
		for _, a := range validActions {
			if strings.Contains(a.Name, "様子見") && rand.Float64() < 0.8 {
				return a
			}
		}
	}

	// 5. 射程内の有効な攻撃スキルを選択
	var validAtks []Action
	for _, a := range validActions {
		if a.Skill != nil && a.Skill.Name != "捨て身のフラッシュ" {
			effDist := dist
			if a.Skill.IsRush {
				effDist = maxInt(0, dist-1)
			}
			effR := g.GetEffectiveRange(cpu, a.Skill)
			if effR[0] <= effDist && effDist <= effR[1] {
				validAtks = append(validAtks, a)
			}
		}
	}
	if len(validAtks) > 0 && rand.Float64() < 0.75 {
		return validAtks[rand.Intn(len(validAtks))]
	}

	if cpu.Name != "白沢恵子" && dist > 1 {
		if fwd, ok := findByName("間合いを詰める"); ok {
			return fwd
		}
	}

	var safeActs []Action
	for _, a := range validActions {
		if a.Skill == nil {
			safeActs = append(safeActs, a)
		}
	}
	if len(safeActs) > 0 {
		return safeActs[rand.Intn(len(safeActs))]
	}
	return validActions[rand.Intn(len(validActions))]
}

func createCharacters() []*Fighter {
	var chars []*Fighter

	c := NewFighter("藤沢美幸", 105, 100, 12, 22, 12, "主人公/結界急接近と超必殺技")
	c.CanBarrier = true
	c.AddSkill(&Skill{Name: "マジックアロー", Power: 20, RangeReq: [2]int{1, 4}, Attr: ATTR_MAG, Priority: PRIO_FAST_ATK, SPCost: 15, Desc: "結界時は距離0-1必中＆1.4倍"})
	c.AddSkill(&Skill{Name: "捨て身のフラッシュ", Power: 75, RangeReq: [2]int{0, 6}, Attr: ATTR_MAG, Priority: PRIO_SYSTEM, SPCost: 0, ReqBarrier: true, Desc: "絶対追尾・防御貫通・自傷20/SP0"})
	chars = append(chars, c)

	c = NewFighter("黎", 105, 120, 10, 28, 11, "魔導師/結界内の無詠唱グレーターが脅威")
	c.CanBarrier = true
	c.AddSkill(&Skill{Name: "マジックアロー", Power: 20, RangeReq: [2]int{1, 4}, Attr: ATTR_MAG, Priority: PRIO_FAST_ATK, SPCost: 15})
	c.AddSkill(&Skill{Name: "グレーターマジック", Power: 45, RangeReq: [2]int{1, 4}, Attr: ATTR_MAG, Priority: PRIO_SLOW_ATK, SPCost: 35, Charge: 1, Desc: "大魔法(結界時は無詠唱＆距離0-1)"})
	chars = append(chars, c)

	c = NewFighter("安土利一", 115, 95, 16, 25, 11, "炎術師/無詠唱の中・近距離アタッカー")
	c.AddSkill(&Skill{Name: "ファイアボール", Power: 28, RangeReq: [2]int{1, 4}, Attr: ATTR_MAG, Priority: PRIO_SLOW_ATK, SPCost: 20, Desc: "安定した無詠唱炎撃"})
	c.AddSkill(&Skill{Name: "フレイムバースト", Power: 35, RangeReq: [2]int{0, 1}, Attr: ATTR_MAG, Priority: PRIO_FAST_ATK, SPCost: 25, Desc: "近接迎撃の爆炎"})
	chars = append(chars, c)

	c = NewFighter("林正洋", 120, 85, 26, 14, 13, "氷格闘/氷盾と高速突進")
	c.AddSkill(&Skill{Name: "アイスナックル", Power: 26, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 15, Desc: "物理(結界貫通)"})
	c.AddSkill(&Skill{Name: "氷滑り(突進)", Power: 18, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 20, IsRush: true, Desc: "実効射程1-2の突進打撃"})
	chars = append(chars, c)

	c = NewFighter("山口春香", 95, 110, 10, 27, 13, "精霊使い/結界内の無詠唱サラマンダー")
	c.CanBarrier = true
	c.AddSkill(&Skill{Name: "スピリットダート", Power: 16, RangeReq: [2]int{1, 3}, Attr: ATTR_MAG, Priority: PRIO_FAST_ATK, SPCost: 12, Desc: "牽制用の精霊弾"})
	c.AddSkill(&Skill{Name: "サラマンダー", Power: 50, RangeReq: [2]int{0, 4}, Attr: ATTR_MAG, Priority: PRIO_SLOW_ATK, SPCost: 30, Charge: 1, Desc: "高火力召喚(結界時は無詠唱)"})
	chars = append(chars, c)

	c = NewFighter("シルレイム", 135, 85, 28, 5, 11, "重装剣士/高耐久・安定物理")
	c.AddSkill(&Skill{Name: "ブロードソード", Power: 30, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 15, Desc: "物理(結界貫通)"})
	c.AddSkill(&Skill{Name: "ステップイン", Power: 20, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 20, IsRush: true, Desc: "実効射程1-2の踏み込み斬り"})
	chars = append(chars, c)

	c = NewFighter("林健次", 120, 80, 35, 5, 12, "剛剣士/超火力・大振り")
	c.AddSkill(&Skill{Name: "フランベルジュ", Power: 38, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_SLOW_ATK, SPCost: 20, Desc: "遅いが強烈な大剣斬り"})
	c.AddSkill(&Skill{Name: "猛追撃", Power: 22, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 25, IsRush: true, Desc: "実効射程1-2の高速突進斬り"})
	chars = append(chars, c)

	c = NewFighter("白沢恵子", 95, 105, 8, 30, 13, "風術師/遠距離特化(近接被ダメ1.4倍)")
	c.AddSkill(&Skill{Name: "ワールウィンド", Power: 26, RangeReq: [2]int{2, 6}, Attr: ATTR_MAG, Priority: PRIO_SLOW_ATK, SPCost: 20, Desc: "遠距離ほど高威力＋吹き飛ばし"})
	c.AddSkill(&Skill{Name: "ウィンドプッシュ", Power: 12, RangeReq: [2]int{0, 1}, Attr: ATTR_MAG, Priority: PRIO_DEFEND, SPCost: 15, Desc: "最速発生・2マス突き放し"})
	chars = append(chars, c)

	c = NewFighter("ブラウ", 130, 95, 24, 22, 9, "飛竜/飛行回避とブレス・爪撃")
	c.AddSkill(&Skill{Name: "ファイアーブレス", Power: 32, RangeReq: [2]int{1, 4}, Attr: ATTR_MAG, Priority: PRIO_SLOW_ATK, SPCost: 20, Desc: "中距離ブレス"})
	c.AddSkill(&Skill{Name: "ドラゴンクロー", Power: 26, RangeReq: [2]int{0, 1}, Attr: ATTR_PHYS, Priority: PRIO_FAST_ATK, SPCost: 15, Desc: "近接物理(結界貫通)"})
	c.IsFlying = true
	chars = append(chars, c)

	return chars
}

func main() {
	scanner := bufio.NewScanner(os.Stdin)
	chars := createCharacters()

	fmt.Println("使用キャラを選択:")
	for i, c := range chars {
		fmt.Printf("%d. %-6s (HP:%3d SP:%3d ATK:%2d MAG:%2d SPD:%2d) - %s\n",
			i+1, c.Name, c.MaxHP, c.MaxSP, c.Atk, c.Mag, c.Speed, c.Desc)
	}

	fmt.Print("No: ")
	player := chars[0]
	if scanner.Scan() {
		if idx, err := strconv.Atoi(strings.TrimSpace(scanner.Text())); err == nil && idx >= 1 && idx <= len(chars) {
			player = chars[idx-1]
		}
	}

	var candidates []*Fighter
	for _, c := range chars {
		if c.Name != player.Name {
			candidates = append(candidates, c)
		}
	}
	enemy := candidates[rand.Intn(len(candidates))].Clone()

	NewGame(player, enemy, scanner).Run()

	fmt.Print("Hit ENTER key to exit : ")
	scanner.Scan()
}