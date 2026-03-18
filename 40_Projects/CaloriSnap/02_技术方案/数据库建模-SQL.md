# 🗄️ CaloriSnap 数据库建模（Supabase / PostgreSQL）

> 基于种子数据设计的正式数据库 Schema
> 目标数据库: Supabase (PostgreSQL)

---

## 📊 ER 关系图

```
users ─────────┐
               │ 1:N
brands ──┐     │
   1:N   │     │
drinks ──┤     │
   N:M   │     │
toppings ┘     │
               │
         drink_records
               │
               │ N:M
         record_toppings
```

---

## 📝 建表 SQL

```sql
-- ============================================================
-- CaloriSnap 数据库 Schema
-- 数据库: Supabase (PostgreSQL)
-- 版本: 0.1.0
-- ============================================================

-- 启用 UUID
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- 1. 品牌表
-- ============================================================
CREATE TABLE brands (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL UNIQUE,        -- 标准品牌名: 瑞幸咖啡、喜茶
    aliases     TEXT[] DEFAULT '{}',          -- 别名: ['瑞幸', 'luckin', 'Luckin Coffee']
    logo_url    TEXT,                         -- 品牌 Logo
    category    TEXT NOT NULL DEFAULT '奶茶', -- 奶茶 / 咖啡 / 果茶
    label_style TEXT,                         -- 标签风格描述
    ocr_friendly INTEGER DEFAULT 3,          -- OCR 友好度 1-5
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 品牌别名搜索索引
CREATE INDEX idx_brands_aliases ON brands USING GIN (aliases);
CREATE INDEX idx_brands_name ON brands (name);

COMMENT ON TABLE brands IS '饮品品牌表';
COMMENT ON COLUMN brands.aliases IS '品牌别名，用于 OCR 文字模糊匹配';
COMMENT ON COLUMN brands.ocr_friendly IS 'OCR 友好度: 1=很难识别, 5=很容易识别';

-- ============================================================
-- 2. 饮品表
-- ============================================================
CREATE TABLE drinks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand_id        UUID NOT NULL REFERENCES brands(id) ON DELETE CASCADE,
    name            TEXT NOT NULL,             -- 饮品名: 生椰拿铁
    aliases         TEXT[] DEFAULT '{}',       -- 别名: ['椰拿']
    category        TEXT,                      -- 美式/拿铁/果茶/奶茶/...
    
    -- 热量数据（基于标准杯/标准糖/标准冰）
    base_calories   INTEGER NOT NULL,          -- 基础热量 (kcal)
    calories_note   TEXT,                      -- 热量说明（如"去芝士+0卡糖"）
    
    -- 分杯型热量（如果品牌有精确数据）
    calories_small  INTEGER,                   -- 小杯热量
    calories_medium INTEGER,                   -- 中杯热量
    calories_large  INTEGER,                   -- 大杯热量
    calories_xlarge INTEGER,                   -- 超大杯热量
    
    -- 元数据
    sugar_grams     REAL,                      -- 含糖量 (g)
    fat_grams       REAL,                      -- 脂肪 (g)
    protein_grams   REAL,                      -- 蛋白质 (g)
    caffeine_mg     REAL,                      -- 咖啡因 (mg)
    
    -- 数据质量
    data_source     TEXT DEFAULT '第三方实测',  -- 官方/第三方实测/估算
    confidence      INTEGER DEFAULT 3,         -- 数据置信度 1-5
    
    is_active       BOOLEAN DEFAULT TRUE,
    is_seasonal     BOOLEAN DEFAULT FALSE,     -- 是否季节限定
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(brand_id, name)
);

CREATE INDEX idx_drinks_brand ON drinks (brand_id);
CREATE INDEX idx_drinks_name ON drinks (name);
CREATE INDEX idx_drinks_aliases ON drinks USING GIN (aliases);
CREATE INDEX idx_drinks_category ON drinks (category);

COMMENT ON TABLE drinks IS '饮品表，存储每种饮品的基础热量信息';

-- ============================================================
-- 3. 加料/小料表
-- ============================================================
CREATE TABLE toppings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,       -- 小料名: 珍珠
    aliases         TEXT[] DEFAULT '{}',        -- 别名: ['波霸', '粉圆']
    calories        INTEGER NOT NULL,           -- 每份热量 (kcal)
    serving_grams   INTEGER DEFAULT 50,         -- 每份重量 (g)
    level           TEXT DEFAULT 'medium',      -- 热量等级: low/medium/high
    category        TEXT,                       -- 分类: 珍珠类/冻类/酱料类
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_toppings_name ON toppings (name);
CREATE INDEX idx_toppings_aliases ON toppings USING GIN (aliases);

COMMENT ON TABLE toppings IS '加料/小料表';

-- ============================================================
-- 4. 糖度配置表
-- ============================================================
CREATE TABLE sugar_levels (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL UNIQUE,       -- 糖度名: 半糖
    aliases         TEXT[] DEFAULT '{}',        -- 别名: ['五分甜', '少甜']
    extra_calories  INTEGER DEFAULT 0,          -- 相对于"正常糖"的额外热量
    sugar_ratio     REAL DEFAULT 0.7,           -- 糖量比例 (0-1)
    sort_order      INTEGER DEFAULT 0,          -- 排序
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE sugar_levels IS '糖度配置表';

-- ============================================================
-- 5. 用户表（Supabase Auth 扩展）
-- ============================================================
CREATE TABLE user_profiles (
    id              UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    nickname        TEXT,
    avatar_url      TEXT,
    
    -- 健康目标
    daily_calorie_budget INTEGER DEFAULT 500,   -- 每日饮品热量预算 (kcal)
    weekly_calorie_budget INTEGER DEFAULT 2500,  -- 每周饮品热量预算
    
    -- 统计
    total_records   INTEGER DEFAULT 0,
    streak_days     INTEGER DEFAULT 0,          -- 连续记录天数
    
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_profiles IS '用户画像表，扩展 Supabase Auth';

-- ============================================================
-- 6. 饮品记录表（核心）
-- ============================================================
CREATE TABLE drink_records (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- 识别信息
    drink_id        UUID REFERENCES drinks(id),          -- 匹配到的饮品（可能为空）
    brand_name      TEXT,                                -- 识别出的品牌名
    drink_name      TEXT,                                -- 识别出的饮品名
    size            TEXT DEFAULT '中杯',                  -- 杯型
    sugar_level     TEXT DEFAULT '正常糖',                -- 糖度
    temperature     TEXT DEFAULT '冰',                    -- 温度
    
    -- 热量
    total_calories  INTEGER NOT NULL,                    -- 计算出的总热量
    match_type      TEXT DEFAULT 'estimated',            -- exact/fuzzy/estimated
    
    -- OCR 原始数据
    photo_url       TEXT,                                -- 标签照片 URL
    ocr_raw_text    TEXT,                                -- OCR 原始识别文字
    ocr_extracted   JSONB,                               -- LLM 结构化提取结果
    
    -- 时间
    consumed_at     TIMESTAMPTZ DEFAULT NOW(),            -- 饮用时间
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_records_user ON drink_records (user_id);
CREATE INDEX idx_records_user_date ON drink_records (user_id, consumed_at DESC);
CREATE INDEX idx_records_drink ON drink_records (drink_id);

COMMENT ON TABLE drink_records IS '用户饮品记录表，每次拍照识别生成一条';

-- ============================================================
-- 7. 记录-加料关联表
-- ============================================================
CREATE TABLE record_toppings (
    record_id       UUID NOT NULL REFERENCES drink_records(id) ON DELETE CASCADE,
    topping_id      UUID REFERENCES toppings(id),
    topping_name    TEXT NOT NULL,              -- 冗余存储，方便展示
    calories        INTEGER NOT NULL,           -- 该加料的热量
    PRIMARY KEY (record_id, topping_name)
);

CREATE INDEX idx_record_toppings_record ON record_toppings (record_id);

-- ============================================================
-- 8. 视图: 用户每日/每周热量汇总
-- ============================================================
CREATE OR REPLACE VIEW v_daily_summary AS
SELECT
    user_id,
    DATE(consumed_at AT TIME ZONE 'Asia/Shanghai') AS date,
    COUNT(*) AS drink_count,
    SUM(total_calories) AS total_calories,
    ARRAY_AGG(DISTINCT brand_name) AS brands,
    AVG(total_calories)::INTEGER AS avg_calories
FROM drink_records
GROUP BY user_id, DATE(consumed_at AT TIME ZONE 'Asia/Shanghai');

CREATE OR REPLACE VIEW v_weekly_summary AS
SELECT
    user_id,
    DATE_TRUNC('week', consumed_at AT TIME ZONE 'Asia/Shanghai')::DATE AS week_start,
    COUNT(*) AS drink_count,
    SUM(total_calories) AS total_calories,
    AVG(total_calories)::INTEGER AS avg_per_drink,
    MAX(total_calories) AS max_single,
    MIN(total_calories) AS min_single
FROM drink_records
GROUP BY user_id, DATE_TRUNC('week', consumed_at AT TIME ZONE 'Asia/Shanghai');

COMMENT ON VIEW v_daily_summary IS '用户每日饮品热量汇总';
COMMENT ON VIEW v_weekly_summary IS '用户每周饮品热量汇总';

-- ============================================================
-- 9. RLS（行级安全策略）
-- ============================================================
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE drink_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE record_toppings ENABLE ROW LEVEL SECURITY;

-- 用户只能读写自己的数据
CREATE POLICY "users_own_profile" ON user_profiles
    FOR ALL USING (auth.uid() = id);

CREATE POLICY "users_own_records" ON drink_records
    FOR ALL USING (auth.uid() = user_id);

CREATE POLICY "users_own_record_toppings" ON record_toppings
    FOR ALL USING (
        record_id IN (SELECT id FROM drink_records WHERE user_id = auth.uid())
    );

-- 品牌/饮品/加料/糖度 对所有用户只读
ALTER TABLE brands ENABLE ROW LEVEL SECURITY;
ALTER TABLE drinks ENABLE ROW LEVEL SECURITY;
ALTER TABLE toppings ENABLE ROW LEVEL SECURITY;
ALTER TABLE sugar_levels ENABLE ROW LEVEL SECURITY;

CREATE POLICY "public_read_brands" ON brands FOR SELECT USING (TRUE);
CREATE POLICY "public_read_drinks" ON drinks FOR SELECT USING (TRUE);
CREATE POLICY "public_read_toppings" ON toppings FOR SELECT USING (TRUE);
CREATE POLICY "public_read_sugar_levels" ON sugar_levels FOR SELECT USING (TRUE);

-- ============================================================
-- 10. 触发器: 自动更新 updated_at
-- ============================================================
CREATE OR REPLACE FUNCTION update_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER brands_updated_at
    BEFORE UPDATE ON brands
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER drinks_updated_at
    BEFORE UPDATE ON drinks
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();

CREATE TRIGGER user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_modified_column();
```

---

## 📊 种子数据插入脚本

详见 `ocr_test/drink_db.json`，正式上线时通过脚本导入。

**数据统计：**
| 表 | 记录数 |
|---|--------|
| brands | 7 |
| drinks | 160+ |
| toppings | 35+ |
| sugar_levels | 18 |

---

## 🔍 关键查询示例

### 根据品牌+饮品名模糊搜索
```sql
SELECT d.*, b.name AS brand_name
FROM drinks d
JOIN brands b ON d.brand_id = b.id
WHERE b.name = '瑞幸咖啡'
  AND d.name ILIKE '%拿铁%';
```

### 通过别名匹配品牌
```sql
SELECT * FROM brands
WHERE name ILIKE '%瑞幸%'
   OR '瑞幸' = ANY(aliases)
   OR 'luckin' = ANY(aliases);
```

### 用户本周热量统计
```sql
SELECT * FROM v_weekly_summary
WHERE user_id = $1
  AND week_start = DATE_TRUNC('week', NOW() AT TIME ZONE 'Asia/Shanghai')::DATE;
```

### 用户今日记录
```sql
SELECT dr.*, b.name AS brand_name, d.name AS drink_name
FROM drink_records dr
LEFT JOIN drinks d ON dr.drink_id = d.id
LEFT JOIN brands b ON d.brand_id = b.id
WHERE dr.user_id = $1
  AND DATE(dr.consumed_at AT TIME ZONE 'Asia/Shanghai') = CURRENT_DATE
ORDER BY dr.consumed_at DESC;
```

---

## 📝 后续优化方向

- [ ] 全文搜索 (pg_trgm) — 支持更好的模糊匹配
- [ ] 饮品向量化 — 用 embedding 做语义匹配
- [ ] 数据版本管理 — 支持历史热量数据变更记录
- [ ] UGC 贡献表 — 用户提交新品数据的审核流程
