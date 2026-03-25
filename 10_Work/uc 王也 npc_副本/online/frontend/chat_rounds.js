/**
 * 异人体检站 — 5轮问诊系统「3+1+1」结构
 * 
 * Q1 ⚡ 破冰·测应激反应 [浅·IP友好]
 * Q2 ⚔️ 格斗·测战斗风格 [中·贴游戏]
 * Q3 ⚖️ 灰度·测道德观 [深·有争议]
 * Q4 🌌 底色·测孤独观 [深·情感]
 * Q5 💫 终极之问 [核心·开放]
 * 
 * 导出：ESM模块格式，兼容直接script引入（检测window环境）
 */

// ==================== 5轮问诊数据 ====================

const CHAT_ROUNDS = [
  // ===== Q1 ⚡ 破冰·测应激反应 [浅·IP友好] =====
  {
    round: 1,
    title: '破冰 · 测应激反应',
    aiMessage: '在异人界，遇事先看反应。假设——你走在路上，前面有人被三个异人围攻，对方实力明显比你强。你会？',
    storyContext: null, // 通用场景不需要故事背景
    options: [
      { id: 'A', text: '冲上去帮忙。打不过也要上', emoji: '🔥' },
      { id: 'B', text: '先观察。搞清楚状况再说', emoji: '🧊' },
    ],
    hasFreeInput: true,
    isFinalRound: false,
    responses: {
      'A': '愣头青一个。不过这股子不怕死的劲儿，在擂台上倒是优势——至少不会还没打就怂了。',
      'B': '沉得住气。但你得想清楚——观察到最佳时机的时候，人可能已经被打死了。反应快不等于出手快。',
      'free': '有自己的一套。行，记下了。',
    },
  },

  // ===== Q2 ⚔️ 格斗·测战斗风格 [中·贴游戏] =====
  {
    round: 2,
    title: '格斗 · 测战斗风格',
    aiMessage: '格斗的事讲究风格。擂台上对手比你壮两圈，你开局怎么打？',
    storyContext: null,
    options: [
      { id: 'A', text: '正面硬刚。气势上不能输', emoji: '💪' },
      { id: 'B', text: '先防守，找破绽再反击', emoji: '🎯' },
      { id: 'C', text: '灵活走位，消耗他体力', emoji: '🌊' },
    ],
    hasFreeInput: true,
    isFinalRound: false,
    responses: {
      'A': '好。敢正面刚的人不多。但记住——蛮力打不过技巧，技巧赢不了天赋，天赋抗不过经验。你属于哪一种，打了才知道。',
      'B': '后发先至？跟我路数有点像。不过防守反击有个前提——你得扛得住对方前三拳。扛不住就白搭。',
      'C': '游击战术。聪明倒是聪明，但擂台就那么大，你能跑多远？不过如果你的速度够快的话……倒也不是不行。',
      'free': '不走寻常路。行，招式可以不规矩，但别连自己要什么都没想清楚。',
    },
  },

  // ===== Q3 ⚖️ 灰度·测道德观 [深·有争议] =====
  {
    round: 3,
    title: '灰度 · 测道德观',
    aiMessage: '说个真事。你师兄为了保护家人，背叛了师门，投靠了对手。三年后你们在擂台上重逢——你怎么打？',
    storyContext: {
      title: '背叛者的擂台',
      characters: [
        { name: '你的师兄', desc: '曾经最信任的人，为了保护家人选择叛变' },
      ],
      story: '他不是坏人。只是在师门和家人之间，他选了家人。但这三年里，他的背叛让师门付出了沉重的代价。现在你们站在擂台上，规则只有一条：分出胜负。',
      crux: '忠义和亲情冲突时，哪个优先？面对曾经最亲近的人，你能下得了手吗？',
    },
    options: [
      { id: 'A', text: '全力以赴。擂台上没有师兄弟', emoji: '⚔️' },
      { id: 'B', text: '留手。他有他的苦衷', emoji: '🤝' },
    ],
    hasFreeInput: true,
    isFinalRound: false,
    responses: {
      'A': '决绝。能在擂台上放下私情的人不多——但你确定这是理性，不是在用「规则」逃避情感？',
      'B': '有情义。但你留手的时候，他可不一定留手。在异人界，心软是要付代价的。',
      'free': '你这回答……比选A或B都复杂。行，复杂的人适合在灰色地带生存。',
    },
  },

  // ===== Q4 🌌 底色·测孤独观 [深·情感] =====
  {
    round: 4,
    title: '底色 · 测孤独观',
    aiMessage: '最后认真问你一个。格斗说到底是一个人的事——上了擂台，没人能替你挨拳头。你更怕哪个：一个人上场，还是所有人都在看着你？',
    storyContext: null,
    options: [
      { id: 'A', text: '怕一个人上场。没人在身后，心里没底', emoji: '💫' },
      { id: 'B', text: '怕所有人看着。压力太大，发挥不出来', emoji: '👁️' },
    ],
    hasFreeInput: true,
    isFinalRound: false,
    responses: {
      'A': '怕孤独。说明你是靠关系和信任运转的人。优点是团队里你最可靠，缺点是——真正的高手，都是在孤独中练出来的。',
      'B': '怕被注视。意思是你在乎别人的看法？在擂台上这是最大的弱点。但反过来想——在乎，说明你有想守护的东西。',
      'free': '你这回答跳出了二选一。好。独来独往但不孤独的人，在异人界叫——隐世高手。',
    },
  },

  // ===== Q5 💫 终极之问 [核心·开放] =====
  {
    round: 5,
    title: '终极之问',
    aiMessage: '最后一问。在异人的世界里，很多选择没有「正确答案」，只有「代价」。如果是你——你最愿意为什么付出代价？三个字。',
    storyContext: null,
    options: [], // 纯自由输入
    hasFreeInput: true,
    isFinalRound: true,
    responses: {
      'free': null, // 由 generateFinalResponse 动态生成
    },
  },
];

// ==================== 最终轮动态回复 ====================

/**
 * 生成最终轮的动态回复
 * @param {string} selfEval - 用户输入的三个字
 * @param {Array} userChoices - 用户前几轮的选择记录
 * @returns {string} 王也的回复文本
 */
function generateFinalResponse(selfEval, userChoices) {
  const templates = [
    `"${selfEval}"？四道选择题，你每一道都在权衡代价。现在告诉我你最愿意为"${selfEval}"付出代价——说明你想明白了。这世上没有正确答案，只有你愿意为之承受的东西。记住这三个字，它会在你每一次面对选择的时候提醒你。`,
    `"${selfEval}"——有人为了保护家人背叛师门，有人在擂台上放不下私情，有人宁愿孤独也不愿被注视。你说你愿意为"${selfEval}"付出代价？行。那等代价真的来了，别后悔就行。`,
    `"${selfEval}"。我问了你四个没有标准答案的问题，你都认真答了。这说明你不是那种逃避选择的人。在异人的世界里，敢选的人不一定活得好，但至少活得明白。你这三个字，我记下了。`,
  ];
  return templates[Math.abs(selfEval.length) % templates.length];
}

// ==================== 六维属性计算 ====================

/**
 * 基于5轮选择计算六维格斗属性
 * 
 * 六维说明：
 * - attack（攻击性）：进攻倾向与爆发力
 * - defense（防御力）：防守能力与抗打击
 * - reaction（反应速）：应激反应与适应力
 * - read（读招力）：观察、分析与洞察
 * - pressure（抗压值）：心理承受与逆境表现
 * - slack（摸鱼值）：道家无为与灵活度
 * 
 * @param {Array} choices - 用户5轮的选择记录 ['A'|'B'|'C'|'free', ...]
 * @returns {Object} { attack, defense, reaction, read, pressure, slack }
 */
function calculateDimensions(choices) {
  // 基础值
  let attack = 50, defense = 50, reaction = 50, read = 50, pressure = 50, slack = 40;

  // 兼容两种输入格式：
  // 1. 字符串数组 ['A', 'B', 'free', ...]
  // 2. 对象数组 [{type: 'option', optionId: 'A', ...}, {type: 'free', ...}, ...]
  const normalized = choices.map(c => {
    if (typeof c === 'string') return c;
    if (c && typeof c === 'object') {
      if (c.type === 'free') return 'free';
      return c.optionId || c.id || 'free';
    }
    return 'free';
  });

  normalized.forEach((c, i) => {
    switch (i) {
      // Q1 应激反应
      case 0:
        if (c === 'A') {
          attack += 12; reaction += 8;       // 冲上去 → 攻击性+反应速
        } else if (c === 'B') {
          read += 12; defense += 8;          // 观察 → 读招力+防御力
        } else {
          // 自由输入
          attack += 4; defense += 4; reaction += 6; read += 8; pressure += 4; slack += 5;
        }
        break;

      // Q2 格斗风格
      case 1:
        if (c === 'A') {
          attack += 15; pressure += 8;       // 硬刚 → 攻击性+抗压
        } else if (c === 'B') {
          read += 12; reaction += 10;        // 防反 → 读招力+反应速
        } else if (c === 'C') {
          reaction += 12; slack += 8;        // 游击 → 反应速+摸鱼值
        } else {
          // 自由输入
          attack += 4; defense += 4; reaction += 6; read += 8; pressure += 4; slack += 5;
        }
        break;

      // Q3 道德灰度
      case 2:
        if (c === 'A') {
          attack += 10; pressure += 10;      // 全力以赴 → 攻击性+抗压
        } else if (c === 'B') {
          defense += 10; read += 8;          // 留手 → 防御力+读招力
        } else {
          // 自由输入
          attack += 4; defense += 4; reaction += 6; read += 8; pressure += 4; slack += 5;
        }
        break;

      // Q4 孤独观
      case 3:
        if (c === 'A') {
          defense += 12; pressure += 8;      // 怕孤独 → 防御力+抗压
        } else if (c === 'B') {
          reaction += 10; slack += 10;       // 怕注视 → 反应速+摸鱼值
        } else {
          // 自由输入
          attack += 4; defense += 4; reaction += 6; read += 8; pressure += 4; slack += 5;
        }
        break;

      // Q5 终极之问（纯自由输入）
      case 4:
        // 终极之问只有自由输入，展示独立思考
        attack += 4; defense += 4; reaction += 6; read += 8; pressure += 4; slack += 5;
        break;

      default:
        break;
    }
  });

  // 限制范围 30-95
  const clamp = (v) => Math.min(95, Math.max(30, v));
  return {
    attack: clamp(attack),
    defense: clamp(defense),
    reaction: clamp(reaction),
    read: clamp(read),
    pressure: clamp(pressure),
    slack: clamp(slack),
  };
}

// ==================== 战斗风格判定 ====================

/**
 * 根据六维属性判定战斗风格
 * 保留原版5种战斗风格
 * 
 * @param {Object} dims - 六维属性 { attack, defense, reaction, read, pressure, slack }
 * @returns {Object} 战斗风格对象
 */
function determineCombatStyle(dims) {
  const styles = [
    {
      name: '压制型 · 正面强攻',
      desc: '以力制胜',
      condition: () => dims.attack > 75 && dims.pressure > 65,
      tags: ['#正面刚王', '#不服就打', '#输了再来'],
      faction: '武当',
      master: '张灵玉',
      ability: '炁体源流 · 刚猛',
      partner: '陆瑾',
      enemy: '吕良',
      personalityTags: ['#热血沸腾', '#不服就干', '#拳头说话'],
    },
    {
      name: '反击型 · 后发先至',
      desc: '以柔克刚',
      condition: () => dims.read > 70 && dims.reaction > 65,
      tags: ['#后发先至', '#读招大师', '#你先请'],
      faction: '武当',
      master: '王也',
      ability: '风后奇门',
      partner: '诸葛青',
      enemy: '陆瑾',
      personalityTags: ['#外冷内热', '#深藏不露', '#以退为进'],
    },
    {
      name: '铁壁型 · 打不死的小强',
      desc: '防守为王',
      condition: () => dims.defense > 75 && dims.pressure > 70,
      tags: ['#打不死的小强', '#越打越精神', '#你打累了没'],
      faction: '全性',
      master: '吕良',
      ability: '炁体源流 · 坚',
      partner: '冯宝宝',
      enemy: '张灵玉',
      personalityTags: ['#沉默寡言', '#意志如铁', '#大器晚成'],
    },
    {
      name: '摸鱼型 · 上擂台也想摸鱼',
      desc: '道家无为',
      condition: () => dims.slack > 65,
      tags: ['#上擂台也想摸鱼', '#道家无为', '#你打你的'],
      faction: '武当',
      master: '王也',
      ability: '通天箓（偷学的）',
      partner: '张楚岚',
      enemy: '加班',
      personalityTags: ['#佛系', '#随缘', '#有实力但不想动'],
    },
    {
      name: '灵活型 · 见招拆招',
      desc: '均衡全面',
      condition: () => true, // 兜底：所有未命中的归这里
      tags: ['#见招拆招', '#灵活多变', '#什么都会一点'],
      faction: '天师府',
      master: '张之维',
      ability: '炁体源流',
      partner: '冯宝宝',
      enemy: '全性',
      personalityTags: ['#外冷内热', '#嘴硬心软', '#社恐但能打'],
    },
  ];

  return styles.find(s => s.condition()) || styles[styles.length - 1];
}

// ==================== 深度评语生成 ====================

/**
 * 基于5轮回答生成王也的深度评语
 * 
 * @param {string} inputId - 用户输入的ID/名字
 * @param {Object} fortuneData - 批命数据
 * @param {Array} choices - 用户5轮的选择记录
 * @param {Object} style - 战斗风格对象
 * @returns {string} 深度评语文本
 */
function generateDeepComment(inputId, fortuneData, choices, style) {
  // 统计 A/B/C/free 的比例来判断倾向
  const aCount = choices.filter(c => c === 'A').length;
  const bCount = choices.filter(c => c === 'B').length;
  const cCount = choices.filter(c => c === 'C').length;
  const freeCount = choices.filter(c => c === 'free').length;

  let tendency = '';
  if (aCount >= 3) {
    tendency = '你的选择偏向果决——面对危机先冲、面对对手硬刚、面对背叛不留情。这不是莽撞，是一种不给自己退路的狠劲。';
  } else if (bCount >= 3) {
    tendency = '你的选择偏向稳健——先观察再行动、先防守再反击、面对矛盾留有余地。这不是软弱，是明白「活着才有下一局」的道理。';
  } else if (freeCount >= 3) {
    tendency = '你不喜欢被框在选项里——这说明你不是非黑即白的人。在异人的世界里，灰色地带才是最危险也最真实的。';
  } else {
    tendency = '你的选择时而果断时而克制，说明你不是教条主义者——你会根据具体情境做判断。这在格斗场上是最稀缺的能力。';
  }

  // 根据具体选择添加个性化细节
  let detail = '';
  // Q1 应激反应的评价
  if (choices[0] === 'A') {
    detail += '三个异人围攻的局面你选择冲上去——勇气可嘉，';
  } else if (choices[0] === 'B') {
    detail += '三个异人围攻的局面你选择先观察——冷静得可怕，';
  } else {
    detail += '面对危机你给出了自己的方案——独立思考这点不错，';
  }

  // Q3 道德观的评价
  if (choices[2] === 'A') {
    detail += '面对叛变的师兄你能下得了狠手，说明你分得清公私。';
  } else if (choices[2] === 'B') {
    detail += '面对叛变的师兄你选择留手，说明你心里有杆秤——不是所有事都能用对错衡量。';
  } else {
    detail += '面对师兄的背叛你没有简单选边站，说明你能看到问题背后更深的东西。';
  }

  return `你这人吧，表面上取了个"${inputId}"的名字，第一眼我就看出——${fortuneData?.comment?.substring(0, 20) || '不简单'}。\n\n五道问题答下来，${tendency}\n\n${detail}\n\n${style.master}要是看到你，估计会说：「${style.master === '王也' ? '这小子有意思，值得摸鱼时聊聊' : '还行，至少不无聊'}。」\n\n记住了——在异人的世界里，最难的不是选对，是选了之后不后悔。`;
}

// ==================== 命运预言生成 ====================

/**
 * 根据战斗风格生成命运预言
 * 
 * @param {Object} style - 战斗风格对象
 * @returns {string} 命运预言文本
 */
function generateProphecy(style) {
  const prophecies = [
    '选择即代价，代价即修行。你已在路上。',
    '世间没有绝对的正义，只有你愿意守住的东西。守好了，就是你的道。',
    '擂台上没有永远的敌人，只有此刻的对手。打完了，该喝茶喝茶。',
    '力量不是正义，但没有力量，连选择的资格都没有。先变强，再谈对错。',
    '孤独是格斗者的宿命，但不孤独是格斗者的选择。',
  ];
  return prophecies[Math.abs(style.name.length) % prophecies.length];
}

// ==================== 完整报告生成 ====================

/**
 * 生成完整的体检报告数据
 * 
 * @param {string} inputId - 用户输入的ID/名字
 * @param {Object} fortuneData - 批命数据
 * @param {Array} userChoices - 用户5轮的选择记录
 * @returns {Object} 完整报告数据
 */
function generateReport(inputId, fortuneData, userChoices) {
  // 根据选择生成六维属性
  const dims = calculateDimensions(userChoices);
  const style = determineCombatStyle(dims);

  return {
    report_id: `rpt_demo_${Date.now()}`,
    status: 'ready',
    mode: 'full',
    report: {
      user_name: inputId,
      fighting_profile: {
        style: style.name,
        style_desc: style.desc,
        dimensions: [
          { name: '攻击性', score: dims.attack, label: dims.attack > 70 ? '重拳出击' : '内敛型', unlocked: true, color: '#e05c5c' },
          { name: '防御力', score: dims.defense, label: dims.defense > 70 ? '铜墙铁壁' : '纸糊型', unlocked: true, color: '#5c8ae0' },
          { name: '反应速', score: dims.reaction, label: dims.reaction > 70 ? '闪电反应' : '慢半拍', unlocked: true, color: '#5ce07a' },
          { name: '读招力', score: dims.read, label: dims.read > 70 ? '擂台诸葛' : '凭直觉', unlocked: true, color: '#d4a853' },
          { name: '抗压值', score: dims.pressure, label: dims.pressure > 70 ? '不动如山' : '心态波动', unlocked: true, color: '#c47a4a' },
          { name: '摸鱼值', score: dims.slack, label: dims.slack > 70 ? '道家无为' : '勤奋苦修', unlocked: true, color: '#5ce0d8' },
        ],
        tags: style.tags,
      },
      alien_personality: {
        faction: style.faction,
        master: style.master,
        ability: style.ability,
        partner: style.partner,
        enemy: style.enemy,
        confidence: 'confirmed',
        personality_tags: style.personalityTags,
      },
      deep_comment: generateDeepComment(inputId, fortuneData, userChoices, style),
      destiny_prophecy: generateProphecy(style),
      share_summary: `王也说我骨子里藏着${style.ability}，你也来测测？`,
      completion_rate: 100,
    },
  };
}

// ==================== 模块导出 ====================

// 直接 script 引入（非模块环境）挂载到 window
if (typeof window !== 'undefined') {
  window.CHAT_ROUNDS = CHAT_ROUNDS;
  window.generateFinalResponse = generateFinalResponse;
  window.calculateDimensions = calculateDimensions;
  window.determineCombatStyle = determineCombatStyle;
  window.generateDeepComment = generateDeepComment;
  window.generateProphecy = generateProphecy;
  window.generateReport = generateReport;
}
