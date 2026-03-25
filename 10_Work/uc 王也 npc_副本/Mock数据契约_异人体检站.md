# Mock 数据契约：「异人体检站」前后端接口

**版本**: v1.0 | **日期**: 2026-03-22 | **作者**: Tech Lead  
**用途**: 前端 Mock 开发 + 产品逻辑对齐 | **优先级**: P1（T-9 周 Day 1-2 必须完成）

---

## 总览

本文档定义前后端交互的核心接口契约（JSON Schema），前端可据此生成 Mock 数据并行开发，无需等待后端/算法完成。

### 接口清单

| # | 接口 | 方法 | 场景 | 状态 |
|---|------|------|------|------|
| 1 | `/api/v1/fortune/tell` | POST | STEP 1 批命 | ⬜ 待确认 |
| 2 | `/api/v1/chat/start` | POST | STEP 2 开始对话 | ⬜ 待确认 |
| 3 | `/api/v1/chat/message` | POST (SSE) | STEP 2 对话消息 | ⬜ 待确认 |
| 4 | `/api/v1/report/generate` | POST | STEP 3 生成报告 | ⬜ 待确认 |
| 5 | `/api/v1/report/get` | GET | STEP 3 获取报告 | ⬜ 待确认 |
| 6 | `/api/v1/share/card` | POST | 批命卡分享图 | ⬜ 待确认 |
| 7 | `/api/v1/share/report` | POST | 报告分享图 | ⬜ 待确认 |
| 8 | `/api/v1/queue/status` | GET | 排队状态查询 | ⬜ 待确认 |

---

## 1. STEP 1 批命接口

### `POST /api/v1/fortune/tell`

**场景**：用户输入 ID，获取批命结果（吐槽 + 批命卡数据）

#### Request

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["user_id", "input_id"],
  "properties": {
    "user_id": {
      "type": "string",
      "description": "用户唯一标识（微信 openid 或设备指纹）",
      "example": "wx_oAbc123def456"
    },
    "input_id": {
      "type": "string",
      "description": "用户输入的 ID/昵称/姓名",
      "maxLength": 50,
      "example": "张楚岚"
    },
    "source": {
      "type": "string",
      "enum": ["direct", "share_link", "kol"],
      "description": "来源渠道",
      "default": "direct"
    },
    "utm": {
      "type": "object",
      "properties": {
        "campaign": { "type": "string" },
        "medium": { "type": "string" },
        "source": { "type": "string" }
      }
    }
  }
}
```

#### Response

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["code", "data"],
  "properties": {
    "code": {
      "type": "integer",
      "enum": [0, 1001, 1002, 5000],
      "description": "0=成功, 1001=排队中, 1002=内容审核拦截, 5000=服务异常"
    },
    "message": { "type": "string" },
    "data": {
      "type": "object",
      "required": ["session_id", "fortune_text", "fortune_card"],
      "properties": {
        "session_id": {
          "type": "string",
          "description": "会话 ID，后续接口需携带",
          "example": "sess_2026032200001"
        },
        "fortune_text": {
          "type": "string",
          "description": "王也的批命吐槽文字（流式推送的完整版）",
          "example": "张楚岚？这名字一看就是个能惹事儿的……你这八字里带着点邪乎劲儿，不像普通人啊。行，让我好好看看你。"
        },
        "fortune_card": {
          "type": "object",
          "description": "批命卡数据",
          "required": ["title", "subtitle", "personality_tag", "element", "fortune_score"],
          "properties": {
            "title": {
              "type": "string",
              "description": "批命卡标题",
              "example": "张楚岚的异人体检报告"
            },
            "subtitle": {
              "type": "string",
              "description": "副标题/一句话总结",
              "example": "表面老实人，内心藏着个小怪物"
            },
            "personality_tag": {
              "type": "string",
              "description": "人格标签（2-4 字）",
              "example": "隐忍型"
            },
            "element": {
              "type": "string",
              "enum": ["金", "木", "水", "火", "土"],
              "description": "五行属性"
            },
            "fortune_score": {
              "type": "integer",
              "minimum": 1,
              "maximum": 100,
              "description": "命数分（1-100）"
            },
            "completion_rate": {
              "type": "integer",
              "description": "体检完整度百分比（STEP 1 完成后为 14）",
              "example": 14
            },
            "background_style": {
              "type": "string",
              "enum": ["gold", "wood", "water", "fire", "earth"],
              "description": "卡片背景风格，对应五行"
            }
          }
        },
        "hit_source": {
          "type": "string",
          "enum": ["exact", "fuzzy", "realtime"],
          "description": "命中来源（精确匹配/模糊匹配/实时推理），用于数据分析"
        },
        "queue_info": {
          "type": "object",
          "description": "排队信息（仅 code=1001 时有值）",
          "properties": {
            "position": { "type": "integer", "description": "排队位置" },
            "estimated_wait_seconds": { "type": "integer", "description": "预计等待秒数" }
          }
        }
      }
    }
  }
}
```

#### Mock 数据示例

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "session_id": "sess_2026032200001",
    "fortune_text": "张楚岚？这名字一看就是个能惹事儿的……你这八字里带着点邪乎劲儿，不像普通人啊。行，让我好好看看你。",
    "fortune_card": {
      "title": "张楚岚的异人体检报告",
      "subtitle": "表面老实人，内心藏着个小怪物",
      "personality_tag": "隐忍型",
      "element": "火",
      "fortune_score": 78,
      "completion_rate": 14,
      "background_style": "fire"
    },
    "hit_source": "fuzzy",
    "queue_info": null
  }
}
```

---

## 2. STEP 2 开始对话

### `POST /api/v1/chat/start`

**场景**：用户从批命卡点击「深度体检」，初始化对话

#### Request

```json
{
  "type": "object",
  "required": ["session_id"],
  "properties": {
    "session_id": {
      "type": "string",
      "description": "STEP 1 返回的 session_id"
    }
  }
}
```

#### Response

```json
{
  "type": "object",
  "required": ["code", "data"],
  "properties": {
    "code": { "type": "integer" },
    "data": {
      "type": "object",
      "properties": {
        "chat_id": {
          "type": "string",
          "description": "对话 ID",
          "example": "chat_2026032200001"
        },
        "first_message": {
          "type": "string",
          "description": "王也的开场白",
          "example": "刚才看了你的名字，有点意思。来，咱们聊点深的——你平时遇到事儿，是先想还是先动手？"
        },
        "total_rounds": {
          "type": "integer",
          "description": "总对话轮数",
          "example": 7
        },
        "current_round": {
          "type": "integer",
          "example": 1
        },
        "options": {
          "type": "array",
          "description": "当前轮可选项（如有）",
          "items": {
            "type": "object",
            "properties": {
              "id": { "type": "string" },
              "text": { "type": "string" },
              "emoji": { "type": "string" }
            }
          },
          "example": [
            { "id": "A", "text": "先想三步再动", "emoji": "🧠" },
            { "id": "B", "text": "直接上", "emoji": "👊" },
            { "id": "C", "text": "看情况", "emoji": "🤔" }
          ]
        }
      }
    }
  }
}
```

---

## 3. STEP 2 对话消息（SSE 流式）

### `POST /api/v1/chat/message`

**场景**：用户发送/选择答案，流式接收王也回复

#### Request

```json
{
  "type": "object",
  "required": ["chat_id", "round", "content"],
  "properties": {
    "chat_id": { "type": "string" },
    "round": {
      "type": "integer",
      "description": "当前轮次（1-7）"
    },
    "content": {
      "type": "object",
      "properties": {
        "type": {
          "type": "string",
          "enum": ["option", "text"],
          "description": "选项选择 or 自由文本"
        },
        "option_id": {
          "type": "string",
          "description": "选项 ID（type=option 时）"
        },
        "text": {
          "type": "string",
          "description": "自由文本（type=text 时）",
          "maxLength": 200
        }
      }
    },
    "context_hash": {
      "type": "string",
      "description": "前端 localStorage 中 context 的 HMAC 签名，防篡改"
    }
  }
}
```

#### SSE Response（流式事件）

```
事件类型定义：

event: message_start
data: {"chat_id": "chat_xxx", "round": 2}

event: message_delta  
data: {"delta": "嗯，"}   // 逐 token 流式推送

event: message_delta
data: {"delta": "你这个选择"}

event: message_delta
data: {"delta": "有意思……"}

event: message_complete
data: {
  "full_text": "嗯，你这个选择有意思……看来你骨子里是个不服输的主。",
  "round": 2,
  "total_rounds": 7,
  "next_options": [
    {"id": "A", "text": "选项A文案", "emoji": "🔥"},
    {"id": "B", "text": "选项B文案", "emoji": "💨"},
    {"id": "C", "text": "选项C文案", "emoji": "⚡"}
  ],
  "completion_rate": 28,
  "is_last_round": false
}

event: error
data: {"code": 5001, "message": "推理超时", "fallback_text": "等等……我再想想。"}
```

#### Mock 说明

前端 Mock 可通过 `setTimeout` 模拟 SSE 流：

```javascript
// Mock SSE 流式推送
const mockSSE = (fullText, onDelta, onComplete) => {
  const tokens = fullText.split('');
  let i = 0;
  const timer = setInterval(() => {
    if (i < tokens.length) {
      onDelta({ delta: tokens[i] });
      i++;
    } else {
      clearInterval(timer);
      onComplete({ full_text: fullText, round: 2, total_rounds: 7 });
    }
  }, 50); // 50ms per token, simulating ~20 token/s
};
```

---

## 4. STEP 3 生成报告

### `POST /api/v1/report/generate`

**场景**：对话完成（或中途退出 ≥4 轮），触发报告生成

#### Request

```json
{
  "type": "object",
  "required": ["chat_id", "mode"],
  "properties": {
    "chat_id": { "type": "string" },
    "mode": {
      "type": "string",
      "enum": ["full", "partial"],
      "description": "full=完整报告(7轮), partial=简版报告(4-6轮)"
    }
  }
}
```

#### Response

```json
{
  "type": "object",
  "properties": {
    "code": { "type": "integer" },
    "data": {
      "type": "object",
      "properties": {
        "report_id": {
          "type": "string",
          "example": "rpt_2026032200001"
        },
        "status": {
          "type": "string",
          "enum": ["generating", "ready", "failed"],
          "description": "generating=生成中（前端轮询 /report/get）"
        },
        "estimated_seconds": {
          "type": "integer",
          "description": "预计生成时间（秒）",
          "example": 5
        }
      }
    }
  }
}
```

### `GET /api/v1/report/get?report_id=xxx`

**场景**：轮询或回调获取报告数据

#### Response

```json
{
  "type": "object",
  "properties": {
    "code": { "type": "integer" },
    "data": {
      "type": "object",
      "properties": {
        "report_id": { "type": "string" },
        "status": {
          "type": "string",
          "enum": ["generating", "ready", "failed"]
        },
        "mode": {
          "type": "string",
          "enum": ["full", "partial"]
        },
        "report": {
          "type": "object",
          "description": "报告完整数据（status=ready 时）",
          "properties": {
            "user_name": {
              "type": "string",
              "example": "张楚岚"
            },
            "fighting_profile": {
              "type": "object",
              "description": "格斗画像",
              "properties": {
                "style": {
                  "type": "string",
                  "description": "格斗风格",
                  "example": "以柔克刚型"
                },
                "dimensions": {
                  "type": "array",
                  "description": "7 个维度评分",
                  "items": {
                    "type": "object",
                    "properties": {
                      "name": { "type": "string" },
                      "score": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "maximum": 100,
                        "description": "null 表示未解锁（简版报告）"
                      },
                      "label": { "type": "string" },
                      "unlocked": { "type": "boolean" }
                    }
                  },
                  "example": [
                    { "name": "攻击性", "score": 65, "label": "内敛型", "unlocked": true },
                    { "name": "防御力", "score": 82, "label": "铜墙铁壁", "unlocked": true },
                    { "name": "速度", "score": 71, "label": "疾风步", "unlocked": true },
                    { "name": "耐力", "score": 88, "label": "持久战王", "unlocked": true },
                    { "name": "技巧", "score": null, "label": "待解锁", "unlocked": false },
                    { "name": "直觉", "score": null, "label": "待解锁", "unlocked": false },
                    { "name": "意志力", "score": null, "label": "待解锁", "unlocked": false }
                  ]
                }
              }
            },
            "alien_personality": {
              "type": "object",
              "description": "异人人格",
              "properties": {
                "faction": {
                  "type": "string",
                  "description": "门派",
                  "example": "天师府"
                },
                "master": {
                  "type": "string",
                  "description": "师父",
                  "example": "张之维"
                },
                "ability": {
                  "type": "string",
                  "description": "异能",
                  "example": "炁体源流"
                },
                "confidence": {
                  "type": "string",
                  "enum": ["confirmed", "preliminary"],
                  "description": "confirmed=完整报告, preliminary=简版（初步判定）"
                }
              }
            },
            "deep_comment": {
              "type": "string",
              "description": "王也的深度评语",
              "example": "你这人吧，表面上一副人畜无害的样子，其实骨子里倔得很。遇到事儿能忍，但真被逼急了，那股子邪劲儿谁都挡不住。你适合天师府的路子——讲究以柔克刚，但关键时刻能爆发。张之维那老头子要是收了你当徒弟，估计又高兴又头疼。"
            },
            "destiny_prophecy": {
              "type": "string",
              "description": "命运预言",
              "example": "你命里有一劫，但别怕——劫后就是机缘。记住了，该出手时别犹豫。"
            },
            "share_summary": {
              "type": "string",
              "description": "用于分享的一句话摘要",
              "example": "王也说我骨子里藏着炁体源流，你也来测测？"
            },
            "completion_rate": {
              "type": "integer",
              "example": 100
            }
          }
        },
        "render_url": {
          "type": "string",
          "description": "服务端渲染好的报告长图 URL（Puppeteer 生成）",
          "example": "https://cdn.example.com/reports/rpt_2026032200001.png"
        }
      }
    }
  }
}
```

#### Mock 数据示例（完整版）

```json
{
  "code": 0,
  "data": {
    "report_id": "rpt_2026032200001",
    "status": "ready",
    "mode": "full",
    "report": {
      "user_name": "张楚岚",
      "fighting_profile": {
        "style": "以柔克刚型",
        "dimensions": [
          { "name": "攻击性", "score": 65, "label": "内敛型", "unlocked": true },
          { "name": "防御力", "score": 82, "label": "铜墙铁壁", "unlocked": true },
          { "name": "速度", "score": 71, "label": "疾风步", "unlocked": true },
          { "name": "耐力", "score": 88, "label": "持久战王", "unlocked": true },
          { "name": "技巧", "score": 75, "label": "四两拨千斤", "unlocked": true },
          { "name": "直觉", "score": 90, "label": "第六感", "unlocked": true },
          { "name": "意志力", "score": 95, "label": "不动如山", "unlocked": true }
        ]
      },
      "alien_personality": {
        "faction": "天师府",
        "master": "张之维",
        "ability": "炁体源流",
        "confidence": "confirmed"
      },
      "deep_comment": "你这人吧，表面上一副人畜无害的样子，其实骨子里倔得很。遇到事儿能忍，但真被逼急了，那股子邪劲儿谁都挡不住。你适合天师府的路子——讲究以柔克刚，但关键时刻能爆发。张之维那老头子要是收了你当徒弟，估计又高兴又头疼。",
      "destiny_prophecy": "你命里有一劫，但别怕——劫后就是机缘。记住了，该出手时别犹豫。",
      "share_summary": "王也说我骨子里藏着炁体源流，你也来测测？",
      "completion_rate": 100
    },
    "render_url": "https://cdn.example.com/reports/rpt_2026032200001.png"
  }
}
```

---

## 5. 分享图生成

### `POST /api/v1/share/card`

**场景**：生成批命卡分享长图

#### Request

```json
{
  "type": "object",
  "required": ["session_id"],
  "properties": {
    "session_id": { "type": "string" },
    "style": {
      "type": "string",
      "enum": ["default", "dark", "neon"],
      "default": "default"
    }
  }
}
```

#### Response

```json
{
  "type": "object",
  "properties": {
    "code": { "type": "integer" },
    "data": {
      "type": "object",
      "properties": {
        "image_url": {
          "type": "string",
          "description": "分享图 CDN URL",
          "example": "https://cdn.example.com/cards/sess_xxx.png"
        },
        "share_text": {
          "type": "string",
          "description": "分享文案",
          "example": "王也给我算了一卦，说我命里带火🔥 你也来试试？"
        },
        "share_url": {
          "type": "string",
          "description": "分享链接（带 utm 参数）",
          "example": "https://yr.example.com/?utm_source=share&utm_medium=card&ref=sess_xxx"
        }
      }
    }
  }
}
```

### `POST /api/v1/share/report`

（结构同上，替换 `session_id` 为 `report_id`，`image_url` 为报告长图 URL）

---

## 6. 排队状态查询

### `GET /api/v1/queue/status?session_id=xxx`

#### Response

```json
{
  "type": "object",
  "properties": {
    "code": { "type": "integer" },
    "data": {
      "type": "object",
      "properties": {
        "in_queue": { "type": "boolean" },
        "position": { "type": "integer", "example": 42 },
        "estimated_wait_seconds": { "type": "integer", "example": 15 },
        "fun_fact": {
          "type": "string",
          "description": "排队时显示的趣味知识",
          "example": "你知道吗？王也的通天箓其实是从他师父那偷学的。"
        }
      }
    }
  }
}
```

---

## 7. 错误码约定

| 错误码 | 含义 | 前端处理 |
|--------|------|----------|
| 0 | 成功 | 正常渲染 |
| 1001 | 排队中 | 展示排队 UI + 轮询 queue/status |
| 1002 | 内容审核拦截 | 提示"王也说这名字不太好算" + 引导重输 |
| 1003 | Session 过期 | 引导重新开始 |
| 2001 | 参数错误 | 前端表单校验兜底 |
| 3001 | AI 推理超时 | 展示兜底回复 + 重试按钮 |
| 3002 | AI 推理降级 | 静默走离线链路，用户无感 |
| 4001 | 渲染失败 | "报告生成中，请稍候" + 自动重试 |
| 5000 | 服务异常 | "王也闭关中" + 预计恢复时间 |

---

## 8. 公共 Header 约定

```
所有请求必须携带：
X-Request-ID: {uuid}           // 请求追踪
X-Client-Version: {version}    // 前端版本号
X-Platform: {h5|webview}       // 平台标识

认证方式：
Authorization: Bearer {token}  // 由 /api/v1/auth/init 获取（微信 JSSDK 静默授权）
```

---

## 9. 降级 Feature Flag

```json
{
  "type": "object",
  "description": "从配置中心获取的降级开关，前端初始化时拉取",
  "properties": {
    "degradation_level": {
      "type": "integer",
      "enum": [0, 1, 2, 3, 4],
      "description": "0=正常, 1=AI限速, 2=纯选项模式, 3=静态版, 4=熔断"
    },
    "features": {
      "type": "object",
      "properties": {
        "enable_realtime_inference": { "type": "boolean", "default": true },
        "enable_sse_streaming": { "type": "boolean", "default": true },
        "enable_server_render": { "type": "boolean", "default": true },
        "enable_share": { "type": "boolean", "default": true },
        "max_chat_rounds": { "type": "integer", "default": 7 },
        "queue_threshold_qpm": { "type": "integer", "default": 30000 }
      }
    },
    "maintenance": {
      "type": "object",
      "properties": {
        "message": { "type": "string" },
        "estimated_recovery": { "type": "string", "format": "date-time" }
      }
    }
  }
}
```

---

> 📌 本文档为前后端 Mock 开发契约，正式开发阶段后端可在此基础上调整字段，变更需同步通知前端。所有接口遵循 RESTful 规范，错误返回统一格式 `{ code, message, data }`。
