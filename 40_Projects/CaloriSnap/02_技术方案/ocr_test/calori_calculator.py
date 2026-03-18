#!/usr/bin/env python3
"""
CaloriSnap — 热量计算引擎
根据识别出的饮品信息（品牌/品名/杯型/糖度/加料）查询数据库并计算总热量

使用方法:
    from calori_calculator import CaloriCalculator
    calc = CaloriCalculator("drink_db.json")
    result = calc.calculate({
        "brand": "瑞幸咖啡",
        "drink_name": "生椰拿铁",
        "size": "大杯",
        "sugar_level": "半糖",
        "temperature": "冰",
        "toppings": ["珍珠"]
    })
"""

import json
from pathlib import Path
from typing import Optional
from difflib import SequenceMatcher


class CaloriCalculator:
    """热量计算器"""

    # 杯型系数
    SIZE_FACTORS = {
        "小杯": 0.75,
        "中杯": 1.0,
        "大杯": 1.3,
        "超大杯": 1.5,
        # 星巴克
        "tall": 0.85,
        "grande": 1.0,
        "venti": 1.2,
    }

    # 糖度额外热量 (kcal)
    SUGAR_EXTRA = {
        "无糖": 0,
        "去糖": 0,
        "不另外加糖": 0,
        "0分甜": 0,
        "微糖": 30,
        "一分甜": 30,
        "少少少甜": 30,
        "少糖": 60,
        "三分甜": 60,
        "少少甜": 60,
        "半糖": 90,
        "五分甜": 90,
        "少甜": 90,
        "正常糖": 0,  # 基准，已含在基础热量中
        "标准糖": 0,
        "七分甜": 0,
        "多甜": 0,
        "全糖": 30,  # 比正常糖稍多
        "十分甜": 30,
    }

    # 温度系数
    TEMP_FACTORS = {
        "冰": 0.95,
        "少冰": 0.97,
        "去冰": 1.05,  # 去冰=更多液体
        "常温": 1.0,
        "热": 1.0,
    }

    # 通用小料热量 (kcal/份)
    TOPPING_CALORIES = {
        "珍珠": 120,
        "波霸": 130,
        "粉圆": 120,
        "椰果": 40,
        "仙草": 35,
        "烧仙草": 40,
        "寒天": 35,
        "红豆": 33,
        "绿豆": 30,
        "芋头": 79,
        "芋泥": 94,
        "芋头泥": 94,
        "芋圆": 118,
        "芋圆啵啵": 118,
        "西米": 75,
        "布丁": 100,
        "燕麦": 38,
        "青稞": 40,
        "红柚": 30,
        "红柚颗粒": 30,
        "弹弹冻": 31,
        "桂花冻": 44,
        "椰椰雪糕": 183,
        "芝士": 181,
        "奶盖": 180,
        "奥利奥碎": 90,
        "奥利奥": 90,
        "蜜豆": 93,
        "黑波波": 163,
        "小青团": 144,
        "冰淇淋": 160,
        "胶原脆啵啵": 71,
        "脆波波": 71,
        "脆啵啵": 71,
        "混珠": 66,
        "血糯米": 74,
    }

    def __init__(self, db_path: Optional[str] = None):
        """初始化，加载饮品数据库"""
        self.drinks_db = {}
        if db_path and Path(db_path).exists():
            with open(db_path, "r", encoding="utf-8") as f:
                self.drinks_db = json.load(f)

    def _fuzzy_match(self, query: str, candidates: list, threshold: float = 0.6) -> Optional[str]:
        """模糊匹配，返回最接近的候选项"""
        best_match = None
        best_score = 0
        query_lower = query.lower().strip()

        for candidate in candidates:
            cand_lower = candidate.lower().strip()
            # 完全匹配
            if query_lower == cand_lower:
                return candidate
            # 包含匹配
            if query_lower in cand_lower or cand_lower in query_lower:
                score = 0.9
            else:
                score = SequenceMatcher(None, query_lower, cand_lower).ratio()

            if score > best_score:
                best_score = score
                best_match = candidate

        if best_score >= threshold:
            return best_match
        return None

    def find_drink(self, brand: str, drink_name: str) -> Optional[dict]:
        """在数据库中查找饮品"""
        if not self.drinks_db:
            return None

        brands = self.drinks_db.get("brands", {})
        # 模糊匹配品牌
        matched_brand = self._fuzzy_match(brand, list(brands.keys()))
        if not matched_brand:
            return None

        brand_data = brands[matched_brand]
        drinks = brand_data.get("drinks", {})

        # 模糊匹配饮品名
        matched_drink = self._fuzzy_match(drink_name, list(drinks.keys()))
        if not matched_drink:
            return None

        drink_info = drinks[matched_drink]
        drink_info["matched_brand"] = matched_brand
        drink_info["matched_drink"] = matched_drink
        return drink_info

    def calculate(self, info: dict) -> dict:
        """
        根据识别信息计算热量

        参数:
            info: {
                "brand": "品牌",
                "drink_name": "饮品名",
                "size": "杯型",
                "sugar_level": "糖度",
                "temperature": "温度",
                "toppings": ["加料1", "加料2"]
            }

        返回:
            {
                "total_calories": 总热量,
                "breakdown": 分项明细,
                "matched": 是否匹配到数据库,
                ...
            }
        """
        brand = info.get("brand", "")
        drink_name = info.get("drink_name", "")
        size = info.get("size", "中杯")
        sugar_level = info.get("sugar_level", "正常糖")
        temperature = info.get("temperature", "冰")
        toppings = info.get("toppings", [])

        # 1. 查找数据库
        drink_info = self.find_drink(brand, drink_name)

        if drink_info:
            base_calories = drink_info.get("base_calories", 200)
            match_type = "exact"
            matched_brand = drink_info.get("matched_brand", brand)
            matched_drink = drink_info.get("matched_drink", drink_name)
        else:
            # 数据库没匹配到，用通用估算
            base_calories = 200  # 默认估算值
            match_type = "estimated"
            matched_brand = brand
            matched_drink = drink_name

        # 2. 杯型系数
        size_key = size.lower() if size else "中杯"
        size_factor = self.SIZE_FACTORS.get(size_key, 1.0)

        # 3. 糖度额外热量
        sugar_extra = 0
        if sugar_level:
            sugar_extra = self.SUGAR_EXTRA.get(sugar_level, 0)

        # 4. 温度系数
        temp_key = temperature if temperature else "冰"
        temp_factor = self.TEMP_FACTORS.get(temp_key, 1.0)

        # 5. 加料热量
        topping_details = []
        topping_total = 0
        for topping in (toppings or []):
            # 模糊匹配小料
            matched_topping = self._fuzzy_match(topping, list(self.TOPPING_CALORIES.keys()))
            if matched_topping:
                cal = self.TOPPING_CALORIES[matched_topping]
                topping_details.append({"name": topping, "matched": matched_topping, "calories": cal})
                topping_total += cal
            else:
                # 未知小料，估算 80 kcal
                topping_details.append({"name": topping, "matched": None, "calories": 80, "estimated": True})
                topping_total += 80

        # 6. 计算总热量
        drink_calories = round(base_calories * size_factor * temp_factor)
        total = drink_calories + sugar_extra + topping_total

        # 7. 生成直观对比
        equivalents = self._get_equivalents(total)

        return {
            "total_calories": total,
            "match_type": match_type,
            "matched_brand": matched_brand,
            "matched_drink": matched_drink,
            "breakdown": {
                "base": base_calories,
                "size_factor": size_factor,
                "temp_factor": temp_factor,
                "drink_subtotal": drink_calories,
                "sugar_extra": sugar_extra,
                "toppings": topping_details,
                "topping_total": topping_total,
            },
            "display": {
                "calories": f"{total} kcal",
                "equivalents": equivalents,
                "sugar_level": sugar_level,
                "size": size,
                "temperature": temperature,
            },
            "input": info,
        }

    def _get_equivalents(self, calories: int) -> list:
        """将热量换算成直观的等价物"""
        equivalents = []
        # 一碗米饭 ≈ 230 kcal
        bowls = round(calories / 230, 1)
        equivalents.append(f"≈ {bowls} 碗米饭")
        # 跑步消耗 ≈ 60 kcal/10分钟
        run_min = round(calories / 6)
        equivalents.append(f"≈ 跑步 {run_min} 分钟消耗")
        # 走路 ≈ 3.5 kcal/分钟
        walk_min = round(calories / 3.5)
        equivalents.append(f"≈ 快走 {walk_min} 分钟消耗")
        return equivalents

    def format_result(self, result: dict) -> str:
        """格式化计算结果为用户友好的文本"""
        lines = []
        lines.append(f"🔥 热量计算结果")
        lines.append(f"{'='*40}")
        lines.append(f"🏷️ {result['matched_brand']} · {result['matched_drink']}")
        lines.append(f"📏 {result['display']['size']} | 🍬 {result['display']['sugar_level']} | 🧊 {result['display']['temperature']}")

        if result["breakdown"]["toppings"]:
            toppings_str = ", ".join(
                f"{t['name']}(+{t['calories']})" for t in result["breakdown"]["toppings"]
            )
            lines.append(f"🍡 加料: {toppings_str}")

        lines.append(f"{'─'*40}")
        lines.append(f"  饮品基础: {result['breakdown']['base']} kcal")
        lines.append(f"  × 杯型系数: {result['breakdown']['size_factor']}")
        lines.append(f"  × 温度系数: {result['breakdown']['temp_factor']}")
        lines.append(f"  = 饮品小计: {result['breakdown']['drink_subtotal']} kcal")

        if result["breakdown"]["sugar_extra"]:
            lines.append(f"  + 糖度调整: +{result['breakdown']['sugar_extra']} kcal")

        if result["breakdown"]["topping_total"]:
            lines.append(f"  + 加料合计: +{result['breakdown']['topping_total']} kcal")

        lines.append(f"{'─'*40}")
        lines.append(f"  🔥 总热量: {result['total_calories']} kcal")
        lines.append(f"{'='*40}")

        for eq in result["display"]["equivalents"]:
            lines.append(f"  📊 {eq}")

        if result["match_type"] == "estimated":
            lines.append(f"\n  ⚠️ 数据库未精确匹配，热量为估算值")

        return "\n".join(lines)


# ============================================================
# 命令行测试
# ============================================================

def demo_calculate():
    """演示热量计算"""
    db_path = Path(__file__).parent / "drink_db.json"
    calc = CaloriCalculator(str(db_path) if db_path.exists() else None)

    test_cases = [
        {
            "brand": "瑞幸咖啡", "drink_name": "生椰拿铁",
            "size": "大杯", "sugar_level": "半糖",
            "temperature": "冰", "toppings": ["珍珠"]
        },
        {
            "brand": "喜茶", "drink_name": "多肉葡萄",
            "size": "中杯", "sugar_level": "三分甜",
            "temperature": "少冰", "toppings": ["芋圆啵啵"]
        },
        {
            "brand": "霸王茶姬", "drink_name": "伯牙绝弦",
            "size": "大杯", "sugar_level": "不另外加糖",
            "temperature": "冰", "toppings": []
        },
        {
            "brand": "星巴克", "drink_name": "焦糖玛奇朵",
            "size": "grande", "sugar_level": "正常糖",
            "temperature": "冰", "toppings": []
        },
        {
            "brand": "茶百道", "drink_name": "招牌芋圆奶茶",
            "size": "大杯", "sugar_level": "七分糖",
            "temperature": "正常冰", "toppings": ["椰果", "布丁"]
        },
    ]

    print("🧮 CaloriSnap 热量计算引擎 - 演示\n")

    for i, tc in enumerate(test_cases, 1):
        print(f"\n{'▸'*3} 测试用例 {i}")
        result = calc.calculate(tc)
        print(calc.format_result(result))
        print()


if __name__ == "__main__":
    demo_calculate()
