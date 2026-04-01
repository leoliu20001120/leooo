-- ============================================================
-- 海克斯大乱斗 · 符文评分数据取数 SQL
-- ============================================================
--
-- 整体思路：
--   Step 0：建1张大宽表临时表 + 1张总人次表（底表只扫一次）
--   之后5个查询全部基于临时表，按需展开/配对
--
-- 临时表结构（一行 = 一个玩家 × 一局对局）：
--   dt, puuid, game_id, championid, winner,
--   player_augment_1 ~ player_augment_5
--
-- 日期参数：
--   ${start_date} = 起始日期（如 '20260101'）
--   ${end_date}   = 截止日期（如 '20260325'）
-- ============================================================


-- ============================================================
-- Step 0：建临时表
-- ============================================================

-- 大宽表：一行 = 一个玩家一局，保留所有符文列 + 天级别日期
DROP TABLE IF EXISTS lol_coach_db.tmp_hextech_base_0101_0325;
CREATE TABLE lol_coach_db.tmp_hextech_base_0101_0325 AS
SELECT
    SUBSTR(tdbank_imp_date, 1, 8) AS dt,  -- 天级别日期 YYYYMMDD
    puuid,
    game_id,
    championid,
    win AS winner,
    player_augment_1,
    player_augment_2,
    player_augment_3,
    player_augment_4,
    player_augment_5
FROM
    ieg_tdbank::idata_lolapp_dsl_eogdrawdatajoined_fht0
WHERE
    tdbank_imp_date >= '${start_date}00'
    AND tdbank_imp_date <= '${end_date}23'
    AND gamequeueconfigid = '2400'
;

-- 总对局人次（全局常量）
DROP TABLE IF EXISTS lol_coach_db.tmp_hextech_total_0101_0325;
CREATE TABLE lol_coach_db.tmp_hextech_total_0101_0325 AS
SELECT
    COUNT(DISTINCT puuid, game_id) AS game_cnt
FROM
    lol_coach_db.tmp_hextech_base_0101_0325
;


-- ============================================================
-- Step 1.1：单个符文胜率 & 选取率
-- ============================================================
-- show_rate = 选了该符文的对局人次 / 总对局人次
-- win_rate  = 选了该符文且赢的人次 / 选了该符文的人次

SELECT
    player_augment,
    ROUND(show_cnt / game_cnt, 6) AS show_rate,
    ROUND(win_cnt / show_cnt, 6) AS win_rate
FROM
(
    SELECT
        a.player_augment,
        t.game_cnt,
        COUNT(DISTINCT a.game_id, a.puuid) AS show_cnt,
        COUNT(CASE WHEN a.winner = 'Win' THEN a.game_id || a.puuid END) AS win_cnt
    FROM
    (
        SELECT puuid, game_id, winner, player_augment_1 AS player_augment FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> ''
        UNION ALL
        SELECT puuid, game_id, winner, player_augment_2 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> ''
        UNION ALL
        SELECT puuid, game_id, winner, player_augment_3 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> ''
        UNION ALL
        SELECT puuid, game_id, winner, player_augment_4 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_4 IS NOT NULL AND player_augment_4 <> ''
        UNION ALL
        SELECT puuid, game_id, winner, player_augment_5 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_5 IS NOT NULL AND player_augment_5 <> ''
    ) a
    LEFT JOIN lol_coach_db.tmp_hextech_total_0101_0325 t ON 1=1
    GROUP BY a.player_augment, t.game_cnt
)
;


-- ============================================================
-- Step 1.2：英雄×符文 胜率 & 选取率
-- ============================================================
-- show_rate = 某英雄选了某符文的人次 / 总对局人次
-- win_rate  = 某英雄选了某符文且赢的人次 / 该英雄选了该符文的人次

SELECT
    player_augment,
    championid,
    ROUND(show_cnt / game_cnt, 6) AS show_rate,
    ROUND(win_cnt / show_cnt, 6) AS win_rate
FROM
(
    SELECT
        a.player_augment,
        a.championid,
        t.game_cnt,
        COUNT(DISTINCT a.game_id, a.puuid) AS show_cnt,
        COUNT(CASE WHEN a.winner = 'Win' THEN a.game_id || a.puuid END) AS win_cnt
    FROM
    (
        SELECT puuid, game_id, championid, winner, player_augment_1 AS player_augment FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> ''
        UNION ALL
        SELECT puuid, game_id, championid, winner, player_augment_2 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> ''
        UNION ALL
        SELECT puuid, game_id, championid, winner, player_augment_3 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> ''
        UNION ALL
        SELECT puuid, game_id, championid, winner, player_augment_4 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_4 IS NOT NULL AND player_augment_4 <> ''
        UNION ALL
        SELECT puuid, game_id, championid, winner, player_augment_5 FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_5 IS NOT NULL AND player_augment_5 <> ''
    ) a
    LEFT JOIN lol_coach_db.tmp_hextech_total_0101_0325 t ON 1=1
    GROUP BY a.player_augment, a.championid, t.game_cnt
)
;


-- ============================================================
-- Step 1.3：英雄选取率（出场率）& 英雄胜率
-- ============================================================
-- pick_rate = 某英雄出场的对局人次 / 总对局人次
-- win_rate  = 某英雄赢的对局人次 / 该英雄出场的对局人次

SELECT
    championid,
    ROUND(champ_cnt / game_cnt, 6) AS pick_rate,
    ROUND(win_cnt / champ_cnt, 6) AS win_rate
FROM
(
    SELECT
        b.championid,
        t.game_cnt,
        COUNT(DISTINCT b.game_id, b.puuid) AS champ_cnt,
        COUNT(CASE WHEN b.winner = 'Win' THEN b.game_id || b.puuid END) AS win_cnt
    FROM
        lol_coach_db.tmp_hextech_base_0101_0325 b
        LEFT JOIN lol_coach_db.tmp_hextech_total_0101_0325 t ON 1=1
    GROUP BY
        b.championid, t.game_cnt
)
;


-- ============================================================
-- Step 1.4：符文×符文 组合胜率 & 选取率
-- ============================================================
-- C(5,2)=10种两两配对，LEAST/GREATEST保证去重
-- pair_show_rate = 同时选了A和B的人次 / 总对局人次
-- pair_win_rate  = 同时选了A和B且赢的人次 / 同时选了A和B的人次

SELECT
    aug_a,
    aug_b,
    ROUND(pair_cnt / game_cnt, 6) AS pair_show_rate,
    ROUND(pair_win_cnt / pair_cnt, 6) AS pair_win_rate
FROM
(
    SELECT
        aug_a, aug_b, t.game_cnt,
        COUNT(DISTINCT game_id, puuid) AS pair_cnt,
        COUNT(CASE WHEN winner = 'Win' THEN game_id || puuid END) AS pair_win_cnt
    FROM
    (
        -- 1×2
        SELECT puuid, game_id, winner, LEAST(player_augment_1, player_augment_2) AS aug_a, GREATEST(player_augment_1, player_augment_2) AS aug_b
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_1 <> player_augment_2
        UNION ALL
        -- 1×3
        SELECT puuid, game_id, winner, LEAST(player_augment_1, player_augment_3), GREATEST(player_augment_1, player_augment_3)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_1 <> player_augment_3
        UNION ALL
        -- 1×4
        SELECT puuid, game_id, winner, LEAST(player_augment_1, player_augment_4), GREATEST(player_augment_1, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_1 <> player_augment_4
        UNION ALL
        -- 1×5
        SELECT puuid, game_id, winner, LEAST(player_augment_1, player_augment_5), GREATEST(player_augment_1, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_1 <> player_augment_5
        UNION ALL
        -- 2×3
        SELECT puuid, game_id, winner, LEAST(player_augment_2, player_augment_3), GREATEST(player_augment_2, player_augment_3)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_2 <> player_augment_3
        UNION ALL
        -- 2×4
        SELECT puuid, game_id, winner, LEAST(player_augment_2, player_augment_4), GREATEST(player_augment_2, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_2 <> player_augment_4
        UNION ALL
        -- 2×5
        SELECT puuid, game_id, winner, LEAST(player_augment_2, player_augment_5), GREATEST(player_augment_2, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_2 <> player_augment_5
        UNION ALL
        -- 3×4
        SELECT puuid, game_id, winner, LEAST(player_augment_3, player_augment_4), GREATEST(player_augment_3, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_3 <> player_augment_4
        UNION ALL
        -- 3×5
        SELECT puuid, game_id, winner, LEAST(player_augment_3, player_augment_5), GREATEST(player_augment_3, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_3 <> player_augment_5
        UNION ALL
        -- 4×5
        SELECT puuid, game_id, winner, LEAST(player_augment_4, player_augment_5), GREATEST(player_augment_4, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_4 <> player_augment_5
    ) pairs
    LEFT JOIN lol_coach_db.tmp_hextech_total_0101_0325 t ON 1=1
    GROUP BY aug_a, aug_b, t.game_cnt
)
;


-- ============================================================
-- Step 1.5：英雄×符文×符文 组合胜率 & 选取率
-- ============================================================
-- 与1.4相同的配对逻辑，GROUP BY多一个championid

SELECT
    championid,
    aug_a,
    aug_b,
    ROUND(pair_cnt / game_cnt, 6) AS pair_show_rate,
    ROUND(pair_win_cnt / pair_cnt, 6) AS pair_win_rate
FROM
(
    SELECT
        championid, aug_a, aug_b, t.game_cnt,
        COUNT(DISTINCT game_id, puuid) AS pair_cnt,
        COUNT(CASE WHEN winner = 'Win' THEN game_id || puuid END) AS pair_win_cnt
    FROM
    (
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_1, player_augment_2) AS aug_a, GREATEST(player_augment_1, player_augment_2) AS aug_b
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_1 <> player_augment_2
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_1, player_augment_3), GREATEST(player_augment_1, player_augment_3)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_1 <> player_augment_3
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_1, player_augment_4), GREATEST(player_augment_1, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_1 <> player_augment_4
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_1, player_augment_5), GREATEST(player_augment_1, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_1 IS NOT NULL AND player_augment_1 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_1 <> player_augment_5
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_2, player_augment_3), GREATEST(player_augment_2, player_augment_3)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_2 <> player_augment_3
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_2, player_augment_4), GREATEST(player_augment_2, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_2 <> player_augment_4
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_2, player_augment_5), GREATEST(player_augment_2, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_2 IS NOT NULL AND player_augment_2 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_2 <> player_augment_5
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_3, player_augment_4), GREATEST(player_augment_3, player_augment_4)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_3 <> player_augment_4
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_3, player_augment_5), GREATEST(player_augment_3, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_3 IS NOT NULL AND player_augment_3 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_3 <> player_augment_5
        UNION ALL
        SELECT puuid, game_id, championid, winner, LEAST(player_augment_4, player_augment_5), GREATEST(player_augment_4, player_augment_5)
        FROM lol_coach_db.tmp_hextech_base_0101_0325 WHERE player_augment_4 IS NOT NULL AND player_augment_4 <> '' AND player_augment_5 IS NOT NULL AND player_augment_5 <> '' AND player_augment_4 <> player_augment_5
    ) pairs
    LEFT JOIN lol_coach_db.tmp_hextech_total_0101_0325 t ON 1=1
    GROUP BY championid, aug_a, aug_b, t.game_cnt
)
;


-- ============================================================
-- 清理临时表（全部查询跑完后执行）
-- ============================================================
-- DROP TABLE IF EXISTS lol_coach_db.tmp_hextech_base_0101_0325;
-- DROP TABLE IF EXISTS lol_coach_db.tmp_hextech_total_0101_0325;
