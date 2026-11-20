GitHubのリポジトリトップで海外のエンジニアやゲームデザイナーの目を一気に引きつけられるよう、**英語を先頭、日本語を後半に配置した構成の `README.md**` です。

そのままコピーして `README.md` として保存できます（ファイル名が異なる場合は `python3 main.py` の部分のみ書き換えてください）。

```markdown
# Crystals on the Glassboard (Ver 1.6.0)

**A Zero-Dependency 1D Tactical Fighting Simulator & Monte Carlo Balance Engine in Pure Python**  
**純粋なPython標準ライブラリのみで実装された、1次元タクティカル格闘シミュレーター＆高速バランス検証エンジン**

![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Dependencies](https://img.shields.io/badge/dependencies-zero-brightgreen)
![License](https://img.shields.io/badge/license-MIT-orange)

---

## 🌍 English Overview

**Crystals on the Glassboard** distills the core essence of 2D fighting games—spacing (*maai*), frame priority, counter-hits, corner pressure, and domain control—into a discrete **1-dimensional 7-tile grid (`0` to `6`)**. 

Written in a single file using **100% Python Standard Library (Zero external dependencies)**, it includes both an interactive CLI fighting mode and a headless Monte Carlo simulation engine capable of resolving **3,600 AI-vs-AI matches in ~0.3 seconds** to output a complete win-rate matrix.

### ⚡ Core Mechanics & Game Design

#### 1. Simultaneous Turn Resolution & Priority Frames
Both players select their actions simultaneously. Execution order is governed by strict **Priority Frames (`0` to `4`)**, with `Speed + 1d4` acting as a tie-breaker within the same frame:
* **`PRIO 0` (System / Ultra):** Ultimate arts (*Desperate Flash*). Bypasses standard neutral checks.
* **`PRIO 1` (Defend / Evasion / Domain):** Guarding, Step-back, Jump, Wind Push, and **Barrier Deployment**.
* **`PRIO 2` (Fast Attack / Rush):** Pokings and lunging strikes (`is_rush` advances 1 tile before hitbox check).
* **`PRIO 3` (Movement / Breaker):** Standard advancing and Barrier Shattering.
* **`PRIO 4` (Heavy Attack / Spell Release):** High-impact slashes, heavy projectiles, and **1-turn Chanted Spells**.
  * *Counter & Whiff Punish:* Whiffing an attack or stepping back into a wall (`pos 0` or `6`) inflicts the `<Vulnerable>` state, causing the next incoming hit to deal **1.4x Counter-Hit damage**. Taking 20+ damage during a chant interrupts the spell.

#### 2. The "Barrier Domain" Rule-Rewrite Mechanic
In typical tactical games, mages kite from afar. Here, mages possess **Barrier Deployment (`can_barrier`)**, which fundamentally inverted the spacing meta by acting as a close-quarters "Domain Expansion":
* **Trade-off (Self-Sealing):** While a Barrier is active, the user **cannot attack targets at distance 2 or greater**.
* **Domain Resonance (Close-Range Supremacy):** Within distance `0–1`, all of the user's spells dynamically rewrite their effective range to `[0, 1]`, become **100% guaranteed to hit** (ignoring Jump/Flight evasion), deal **1.4x damage**, and **skip all chanting turns (Instant Cast)**.
* **Magnetic Pull:** Advancing while a Barrier is active pulls the user **2 tiles forward** instead of 1, dragging the opponent into the execution zone.
* **Arcane Thorns:** Physical attacks pierce the Barrier's 50% magic mitigation, but trigger an automatic **arcane recoil (`MAG // 2`)** back onto the attacker.
* **Counter-Play:** Opponents can either kite outside distance 2 or use the dedicated **"Shatter Barrier"** command (`PRIO 3`) from distance `<= 2` to step in, destroy the domain, and inflict `<Vulnerable>`.

#### 3. Built-in Monte Carlo Balance Simulator
Select Mode `2` at launch to run a full round-robin tournament across all 9 asymmetric fighters (36 matchups × 100 games = 3,600 matches, swapping P1/P2 sides every game to eliminate positional bias). It tracks win-rate matrices, average match length, and Barrier activation conversion rates.

### 🚀 Quick Start

No `pip install` required. Runs on any environment with Python 3.

```bash
git clone [https://github.com/YOUR_USERNAME/crystals-on-the-glassboard.git](https://github.com/YOUR_USERNAME/crystals-on-the-glassboard.git)
cd crystals-on-the-glassboard
python3 main.py

```

---

## 🇯🇵 日本語解説 (Japanese Overview)

**『Crystals on the Glassboard』** は、対戦格闘ゲームにおける「間合い管理」「発生フレーム（優先度）」「差し返し（大隙へのカウンター）」「画面端の壁激突」「領域展開によるルール書き換え」のエッセンスを、**1次元の7マス空間（座標 `0` 〜 `6`）** に凝縮したタクティカル・バトルシミュレーターです。

外部ライブラリを一切使用しない **Python標準ライブラリのみ（単一ファイル完結）** で実装されており、対CPUのコマンド対戦モードに加え、**全キャラ総当たり3,600試合を約0.3秒で高速演算して勝率マトリクスを出力するヘッドレス・シミュレーター**を内蔵しています。

### ⚡ 独自システムと設計思想

```text
================ Turn 3 ================
【壁】 ＿ ① ＿ ② ＿ ＿ ＿ 【壁】 (間合い: 2)
P1 黎: HP 105/105 | SP  95/120 【結界展開中(近接強化/無詠唱/物理反射)】
P2 林健次: HP 120/120 | SP  80/80 
========================================

```

#### 1. 同時ターン制と5段階の優先度フレーム（Priority Frames）

お互いの行動を同時に選択し、以下の優先度（数字が小さいほど高速）に従って処理されます。同一優先度内では `Speed + 乱数(0〜3)` で先後が決まります。

* **`PRIO 0` (最速・超必殺):** 『捨て身のフラッシュ』など、あらゆる行動に割り込むシステム級アクション。
* **`PRIO 1` (防御・回避・領域):** 様子見（ガード＆SP回復）、ステップバック、ジャンプ、拒否技、および『結界構築』。
* **`PRIO 2` (速攻・突進技):** 牽制技および、1マス踏み込んでから攻撃判定を出す突進技（`is_rush`）。
* **`PRIO 3` (移動・結界割り):** 通常の前進、および相手の結界を踏み込みながら粉砕する『相手の結界をけずる』。
* **`PRIO 4` (大技・詠唱魔法の発動):** 高火力の大剣技や、1ターン詠唱完了後の大魔法。
* **差し返しと詠唱中断:** 射程外での空振りや、壁際（座標`0`または`6`）でのバックステップ失敗は `<大隙!!>` となり、被ダメージが **1.4倍（カウンターヒット）** に増加します。また、詠唱中に20ダメージ以上を受けると詠唱が中断されます。



#### 2. 遠距離の常識を覆す「結界領域（Barrier Domain）」システム

本作の魔導師（美幸・黎・春香）が持つ『結界構築』は、単なる防御バフではなく「遠距離攻撃を自ら封印する代わりに、近距離（間合い0〜1）を絶対的な処刑空間に変える」領域展開ギミックです。

* **即時展開と外部攻撃制限:** 優先度1で即座に展開され、被魔法ダメージを半減しますが、展開中は**距離2以上の相手へ一切攻撃できなくなります**。
* **結界共鳴（無詠唱・必中・密着対応・1.4倍）:** 結界展開中、相手を間合い `0〜1` に捉えると、本来は密着（距離0）で空振りする魔法も含め全スキルの有効射程が `[0, 1]` に書き換わり、必中化・威力1.4倍・さらに大魔法の詠唱が完全省略（即時発動）されます。
* **空間引き寄せ（2マス前進）:** 結界展開中に「間合いを詰める」を選ぶと、通常の2倍（2マス）一気に前進して相手を領域内へ引きずり込みます。
* **魔力障壁の荊（物理反射）:** 物理攻撃は結界のダメージ半減を貫通しますが、攻撃側に **`MAG // 2` の反射ダメージ**を強制的に与えます。
* **対策と読み合い:** 結界を張られた側は「距離2以上に逃げて不発（大隙）を誘う」か、相手が前進・様子見するタイミングを読んで距離2以内から『相手の結界をけずる（優先度3）』を差し込み、結界粉砕＋スタンを奪う駆け引きが生まれます。

#### 3. 3,600戦を瞬時に回すモンテカルロ・バランス検証機能

起動時にモード `2` を選択すると、画面表示とウェイトをバイパスしたヘッドレスモード（`run_headless`）が起動します。全9キャラクターの総当たり戦（36カード×100戦＝3,600試合、位置有利を排除するため1戦ごとにP1/P2の初期座標を入れ替え）を高速実行し、勝率マトリクスと結界展開時の勝率統計を出力します。

```text
【勝率マトリクス (単位: % / 横が自キャラ・縦が対戦相手)】
------------------------------------------------------------
キャラ名   |  藤沢美  黎   安土利  林正洋  山口春  シルレ  林健次  白沢恵  ブラウ | 総合勝率
------------------------------------------------------------
藤沢美幸   |   -   48%  55%  52%  46%  58%  60%  59%  53% |   53.9%
黎         |  52%   -   58%  54%  49%  61%  62%  55%  58% |   56.1%
...

```

### ⚔️ キャラクターロスター (Characters)

1. **藤沢美幸 (Miyuki Fujisawa)** - 結界からの急接近と、結界を圧縮爆破して放つ絶対追尾・防御貫通の超必殺技『捨て身のフラッシュ』を持つ主人公。
2. **黎 (Rei)** - 結界領域内での無詠唱『グレーターマジック』が圧倒的な破壊力を誇る正統派魔導師。
3. **安土利一 (Riichi Azuchi)** - 結界を持たない代わりに、無詠唱の中距離炎撃と近接迎撃の『フレイムバースト』を使い分けるオールラウンダー。
4. **林正洋 (Masahiro Hayashi)** - 2ターン持続する固有バリア『アイスシールド』と突進技『氷滑り』で懐に潜り込む氷の格闘家。
5. **山口春香 (Haruka Yamaguchi)** - 高速の精霊弾と、結界共鳴で無詠唱化する大召喚『サラマンダー』を操る精霊使い。
6. **シルレイム (Silreim)** - 全キャラ最大のHPと安定した物理剣技で結界を上から殴り抜く重装剣士。
7. **林健次 (Kenji Hayashi)** - 発生は遅いが一撃必殺級の威力を誇る『フランベルジュ』と高速突進『猛追撃』を持つ剛剣士。
8. **白沢恵子 (Keiko Shirasawa)** - 近接で被ダメージが1.4倍になる弱点を持つ代わりに、距離が離れるほど威力が上がる『ワールウィンド』と最速の突き放し技『ウィンドプッシュ』で画面端へハメ込む風術師。
9. **ブラウ (Blau)** - 常時『飛行』状態による高い回避率と攻撃補正を持ち、ブレスと爪撃を使い分ける飛竜（大ダメージ被弾で撃墜スタン）。

### 📄 License

This project is licensed under the MIT License.

```

<ElicitationsGroup message="リポジトリの完成度をさらに高める場合:">
  <Elicitation label="コード内に型ヒント（Type Hints）と英語コメントを追加する" query="海外の開発者もコード自体を読みやすいよう、Ver1.6.0のコードに標準ライブラリのtypingを使った型ヒントと簡潔な英語Docstringを追加して。"/>
  <Elicitation label="コマンドライン引数（--simなど）で直接実行できるようにする" query="ターミナルから python3 main.py --sim 500 のように引数つきで直接シミュレーターを回せるよう、sys.argvによるCLI引数処理を追加して。"/>
  <Elicitation label="全キャラの勝率がより拮抗するよう微調整する" query="総当たりシミュレーションの勝率マトリクスで、下位キャラ（白沢恵子・林健次・ブラウ）の勝率が50%に近づくようパラメータとAIを微調整して。"/>
</ElicitationsGroup>

```
